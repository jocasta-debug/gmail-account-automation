"""
Campaign runner — multi-threaded Gmail account creation.

Each thread gets:
  - Its own browser context (incognito)
  - Its own proxy (from the pool)
  - Its own fingerprint (Canvas/WebGL/etc. noise per thread)
  - Its own identity (name, DOB, gender)

Results are collected into a shared output file.
"""

import time
import json
import threading
import random
import sys
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from playwright.sync_api import sync_playwright, Browser

from .config import (
    NAME_POOL, PROXY_POOL, THREADS, THREAD_STAGGER,
    log, get_2captcha_key, get_5sim_key, has_5sim_key,
)
from .signup import (
    create_account, setup_account_context, AccountResult,
    GOOGLE_SIGNUP_URL,
)
from .humanizer import human_pause


OUTPUT_FILE = Path(__file__).resolve().parent.parent / "output" / "accounts.json"


def run_thread(
    thread_id: int,
    account_index: int,
    total_accounts: int,
    mobile_mode: bool,
    sms_enabled: bool,
) -> AccountResult:
    """
    Single-thread account creation loop.
    Handles its own browser lifecycle.
    """
    thread_log = logging.getLogger(f"thread.{thread_id}")
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [T{thread_id}] %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    ))
    thread_log.addHandler(handler)
    thread_log.setLevel(logging.INFO)

    identity = NAME_POOL.random_identity()
    proxy = PROXY_POOL.next()

    thread_log.info(
        f"Starting account #{account_index} — "
        f"{identity['first_name']} {identity['last_name']} "
        f"[{'mobile' if mobile_mode else 'desktop'}] "
        f"proxy={'yes' if proxy else 'no'}"
    )

    result = AccountResult(
        full_name=f"{identity['first_name']} {identity['last_name']}",
        errors=[],
        steps=[],
    )
    browser = None
    context = None
    page = None

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-webrtc",
                    "--disable-extensions",
                    "--disable-background-networking",
                    "--disable-default-apps",
                    "--disable-sync",
                    "--metrics-recording-only",
                    "--safebrowsing-disable-auto-update",
                    "--engine-logging",
                ],
            )

            context, page = setup_account_context(
                browser,
                use_mobile=mobile_mode,
                proxy_str=proxy,
            )

            result = create_account(
                browser=browser,
                context=context,
                page=page,
                identity=identity,
                use_mobile=mobile_mode,
                sms_enabled=sms_enabled,
                attempt=1,
            )

    except Exception as e:
        result.errors.append(f"Thread setup failure: {e}")
        thread_log.error(f"Thread {thread_id} failed: {e}")
    finally:
        try:
            if page:
                page.close()
            if context:
                context.close()
            if browser:
                browser.close()
        except Exception:
            pass

    # ── Save result immediately ────────────────────────────────────────────
    _append_result(result)

    status = "✅" if result.success else "❌"
    thread_log.info(
        f"[{status}] Account #{account_index}: {result.email or 'NO EMAIL'} "
        f"{' — ' + ', '.join(result.errors) if result.errors else ''}"
    )
    return result


def _append_result(result: AccountResult) -> None:
    """Append a single result to the output JSONL file."""
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "email": result.email,
        "password": result.password,
        "full_name": result.full_name,
        "success": result.success,
        "phone_used": result.phone_used,
        "errors": result.errors,
        "steps_completed": result.steps,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(OUTPUT_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ── Campaign orchestrator ─────────────────────────────────────────────────────

def run_campaign(
    total_accounts: int = 10,
    mobile_mode: bool = True,
    sms_enabled: bool = True,
    stagger: float = 5.0,
) -> list[AccountResult]:
    """
    Run a campaign creating `total_accounts` Gmail accounts
    across `THREADS` concurrent threads.
    """
    log.info("=" * 60)
    log.info(f"🚀 Campaign starting — {total_accounts} accounts, "
             f"{THREADS} threads, {'mobile' if mobile_mode else 'desktop'} mode")
    log.info(f"  2Captcha: {'✅' if get_2captcha_key() else '❌ (no key)'}")
    log.info(f"  5sim SMS:  {'✅' if has_5sim_key() else '❌ (no key)'}")
    log.info(f"  Proxies:   {PROXY_POOL.size()} available")
    log.info("=" * 60)

    results = []
    counter = {"idx": 0}
    lock = threading.Lock()

    def _next_identity():
        with lock:
            idx = counter["idx"]
            counter["idx"] += 1
            return idx + 1

    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        futures = []

        for _ in range(total_accounts):
            tid = random.randint(1000, 9999)
            idx = _next_identity()
            future = executor.submit(
                run_thread,
                thread_id=tid,
                account_index=idx,
                total_accounts=total_accounts,
                mobile_mode=mobile_mode,
                sms_enabled=sms_enabled,
            )
            futures.append(future)
            time.sleep(random.uniform(0, stagger))

        for future in as_completed(futures):
            try:
                res = future.result()
                results.append(res)
            except Exception as e:
                log.error(f"Future failed: {e}")
                results.append(AccountResult(
                    success=False,
                    errors=[f"Future exception: {e}"],
                ))

    # ── Summary ─────────────────────────────────────────────────────────────
    log.info("=" * 60)
    log.info("🏁 Campaign complete")
    successes = sum(1 for r in results if r.success)
    log.info(f"  Total:    {len(results)}")
    log.info(f"  Success:  {successes}")
    log.info(f"  Failed:   {len(results) - successes}")
    log.info(f"  Output:   {OUTPUT_FILE}")
    log.info("=" * 60)
    return results


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Gmail Account Creation Campaign")
    parser.add_argument("--accounts", "-n", type=int, default=10,
                        help="Number of accounts to create")
    parser.add_argument("--threads", "-t", type=int, default=None,
                        help="Override THREADS from .env")
    parser.add_argument("--desktop", action="store_true",
                        help="Use desktop fingerprint instead of mobile")
    parser.add_argument("--no-sms", action="store_true",
                        help="Disable 5sim SMS verification")
    parser.add_argument("--stagger", "-s", type=float, default=None,
                        help="Override THREAD_STAGGER from .env")

    args = parser.parse_args()

    if args.threads:
        import os
        os.environ["THREADS"] = str(args.threads)

    run_campaign(
        total_accounts=args.accounts,
        mobile_mode=not args.desktop,
        sms_enabled=not args.no_sms,
        stagger=args.stagger or 5.0,
    )
