"""
Gmail/Google account creation flow.
Drives the full signup sequence inside a Playwright browser context.

Flow:
  1. Navigate to Google signup entry point
  2. Fill personal info (name, birthday, gender)
  3. Choose email (suggested or custom)
  4. Set password
  5. Handle phone verification (skip / 5sim SMS)
  6. Handle QR code if it appears (qr_bypass)
  7. Handle reCAPTCHA via 2Captcha
  8. Complete creation
  9. Return credentials

The flow uses mobile-endpoint emulation by default — the browser context
presents a mobile UA/viewport/platform to try to avoid the desktop QR wall.
"""

import time
import random
import re
import logging
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any

from playwright.sync_api import Page, BrowserContext, Browser, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from .config import (
    NAME_POOL, PROXY_POOL, MAX_RETRIES, TWOCAPTCHA_API_KEY,
    log, get_2captcha_key, get_5sim_key,
)
from .fingerprint import build_inject_script, mobile_fingerprint, desktop_fingerprint
from .humanizer import (
    human_type, human_click, human_pause, human_pause_long,
    human_move_to, human_scroll, warm_up_browser,
)
from .captcha import solve_recaptcha_v2
from .sms import get_google_verification_code
from .qr_bypass import handle_qr_code, detect_qr_screen
from . import birthday_gender


# ── Data class ────────────────────────────────────────────────────────────────

@dataclass
class AccountResult:
    email: str = ""
    password: str = ""
    full_name: str = ""
    success: bool = False
    phone_used: str = ""
    errors: list[str] = None
    steps: list[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.steps is None:
            self.steps = []


# ── URL constants ────────────────────────────────────────────────────────────

GOOGLE_SIGNUP_URL = "https://accounts.google.com/signup/v2"
GOOGLE_LOGIN_URL = "https://accounts.google.com/"


# ── Random password generator ────────────────────────────────────────────────

def random_password(length: int = 14) -> str:
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%"
    return "".join(random.choices(chars, k=length))


# ── Random email (if not pre-filled) ────────────────────────────────────────

def suggest_email(first_name: str, last_name: str) -> str:
    """Generate a random-looking Gmail address."""
    sep = random.choice([".", "", "_"])
    variant = random.randint(1, 999)
    return f"{first_name}{sep}{last_name}{variant}@gmail.com"


# ── Proxy string → Playwright proxy dict ─────────────────────────────────────

def proxy_to_dict(proxy_str: str) -> dict:
    """Parse 'ip:port:user:pass' or 'ip:port' into Playwright proxy dict."""
    parts = proxy_str.split(":")
    if len(parts) == 2:
        return {"server": f"http://{parts[0]}:{parts[1]}"}
    elif len(parts) == 4:
        return {
            "server": f"http://{parts[0]}:{parts[1]}",
            "username": parts[2],
            "password": parts[3],
        }
    return {"server": f"http://{proxy_str}"}


# ── Wait helpers ─────────────────────────────────────────────────────────────

def wait_for_page(page: Page, timeout: int = 15000) -> None:
    try:
        page.wait_for_load_state("domcontentloaded", timeout=timeout)
    except PlaywrightTimeout:
        pass


def wait_for_selector(page: Page, selector: str, timeout: int = 10000) -> bool:
    try:
        page.locator(selector).wait_for(state="visible", timeout=timeout)
        return True
    except PlaywrightTimeout:
        return False


# ── The main signup flow ─────────────────────────────────────────────────────

def create_account(
    browser: Browser,
    context: BrowserContext,
    page: Page,
    identity: dict,
    use_mobile: bool = True,
    sms_enabled: bool = True,
    attempt: int = 1,
) -> AccountResult:
    """
    Execute the full Gmail signup flow in the given page/context.
    Returns an AccountResult with credentials on success.
    """
    # Use a screenshots directory for this run
    import datetime, os
    run_ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    shot_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "screenshots", f"run_{run_ts}")
    os.makedirs(shot_dir, exist_ok=True)
    sc = lambda name: os.path.join(shot_dir, name)

    # Helper: take screenshot with logging
    def take_screenshot(page, filename, log_msg=None):
        try:
            path = sc(filename)
            page.screenshot(path=path)
            if log_msg:
                log.info(f"  📸 {log_msg}: {path}")
            return path
        except Exception as e:
            log.debug(f"  Screenshot failed for {filename}: {e}")
            return None

    # Helper: dump page DOM info as screenshot annotation
    def dump_inputs(page, log_msg):
        try:
            inputs = page.evaluate("""() => {
                const els = document.querySelectorAll('input, select, textarea, button');
                return Array.from(els).slice(0, 20).map(el => ({
                    tag: el.tagName,
                    type: el.type || '',
                    name: el.name || '',
                    ariaLabel: el.getAttribute('aria-label') || '',
                    placeholder: el.placeholder || '',
                    text: (el.textContent || '').trim().substring(0, 50),
                    visible: el.offsetParent !== null,
                }));
            }""")
            log.debug(f"  {log_msg}: {inputs}")
        except Exception:
            pass

    result = AccountResult(
        full_name=f"{identity['first_name']} {identity['last_name']}",
        errors=[],
        steps=[],
    )
    password = random_password()
    result.password = password

    log.info(f"[{identity['first_name']}] Starting signup (attempt {attempt})...")

    try:
        # ── Step 0: Warm-up (if first attempt) ──────────────────────────
        if attempt == 1:
            warm_up_browser(page, count=random.randint(1, 2))
            human_pause(0.5, 1.5)

        # ── Step 1: Navigate to signup ──────────────────────────────────
        log.info(f"[{identity['first_name']}] Navigating to Google signup...")
        page.goto(GOOGLE_SIGNUP_URL, wait_until="domcontentloaded", timeout=20000)
        human_pause(1, 3)
        take_screenshot(page, "01_signup_entry.png", "Signup entry page")

        # ── Step 2: Fill personal information ───────────────────────────
        log.info(f"[{identity['first_name']}] Filling personal info...")

        # First name — use the specific ID Google assigns
        if wait_for_selector(page, "input[id='firstName']", timeout=10000):
            human_type(page, "input[id='firstName']",
                       identity["first_name"], base_delay=0.12, mistake_prob=0.02)
            human_pause(0.3, 0.8)
            page.keyboard.press("Tab")
            human_pause(0.2, 0.5)

        # Last name
        if wait_for_selector(page, "input[id='lastName']", timeout=8000):
            human_type(page, "input[id='lastName']",
                       identity["last_name"], base_delay=0.12, mistake_prob=0.02)
            human_pause(0.3, 0.8)

        # Screenshot: personal info filled
        take_screenshot(page, "02_personal_info_filled.png", "Personal info filled")
        dump_inputs(page, "Personal info page elements")

        # Click Next — direct click, no mouse movement
        next_clicked = False
        for sel in [
            "button:has-text('Next')",
            "div[role='button']:has-text('Next')",
            "div[data-primary-action-label='Next']",
        ]:
            try:
                el = page.locator(sel).first
                if el.count() > 0:
                    el.click()
                    log.info(f"  Next clicked via: {sel}")
                    next_clicked = True
                    break
            except Exception:
                continue

        if not next_clicked:
            log.warning("  Next: could not click — continuing anyway")

        human_pause_long(2, 5)

        # Verify the page advanced — if still on name step, try JS click
        if next_clicked:
            try:
                page.wait_for_timeout(1000)
                current_url = page.url.lower()
                body_text = page.inner_text("body")
                if "first name" in body_text.lower() and "last name" in body_text.lower():
                    log.warning("  Page did not advance after Next — trying JS click")
                    page.evaluate("""() => {
                        const btn = document.querySelector('button:has-text("Next"), div[role="button"]:has-text("Next")');
                        if (btn) btn.click();
                    }""")
                    human_pause_long(2, 5)
            except Exception:
                pass

        result.steps.append("personal_info_filled")

        # ── DEBUG: dump DOM to understand Google's actual selectors ──
        # (kept for debugging — screenshots handle visualization now)

        # ── Step 3: Birthday and Gender ────────────────────────────────
        log.info(f"[{identity['first_name']}] Filling birthday/gender...")

        # Screenshot: birthday page before filling
        take_screenshot(page, "03_birthday_page.png", "Birthday/gender page")
        dump_inputs(page, "Birthday page elements")

        birthday = identity["birthday"]  # format: MMDDYYYY
        mm, dd, yyyy = birthday[:2], birthday[2:4], birthday[4:]

        # Birthday: Google uses text inputs for Month/Day/Year
        # Try multiple selector strategies for each field
        birthday_filled = True

        # Month — Google uses a custom ARIA combobox (div[role="combobox"]),
        # NOT an HTML <select>. Clicking the trigger opens ul[aria-label="Month"].
        month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ]
        month_name = month_names[int(mm) - 1] if mm.isdigit() and 1 <= int(mm) <= 12 else mm
        month_filled = birthday_gender._select_combobox_option(
            page, "Month", month_name, log)

        # Day
        day_filled = False
        for sel in ["input[name='day']", "input[aria-label*='day' i]", "input[aria-label*='Day' i]",
                    "input[placeholder*='Day']"]:
            try:
                el = page.locator(sel).first
                if el.count() > 0:
                    el.click()
                    el.fill(dd)
                    log.info(f"  Day filled via: {sel}")
                    day_filled = True
                    break
            except Exception:
                continue
        if not day_filled:
            try:
                page.locator("input[aria-label*='day' i]").first.click()
                page.keyboard.type(dd)
                day_filled = True
                log.info("  Day filled via keyboard")
            except Exception:
                pass

        # Year
        year_filled = False
        for sel in ["input[name='year']", "input[aria-label*='year' i]", "input[aria-label*='Year' i]",
                    "input[placeholder*='Year']"]:
            try:
                el = page.locator(sel).first
                if el.count() > 0:
                    el.click()
                    el.fill(yyyy)
                    log.info(f"  Year filled via: {sel}")
                    year_filled = True
                    break
            except Exception:
                continue
        if not year_filled:
            try:
                page.locator("input[aria-label*='year' i]").first.click()
                page.keyboard.type(yyyy)
                year_filled = True
                log.info("  Year filled via keyboard")
            except Exception:
                pass

        if not (month_filled and day_filled and year_filled):
            log.warning(f"  Birthday: partial fill (month={month_filled}, day={day_filled}, year={year_filled})")

        human_pause(0.3, 0.8)

        # Gender — Google uses a custom ARIA combobox, same as month.
        gender = identity.get("gender", "male")
        gender_label = gender.capitalize()
        gender_filled = birthday_gender._select_combobox_option(
            page, "Gender", gender_label, log)

        # Screenshot: birthday+gender filled
        take_screenshot(page, "04_birthday_gender_filled.png", "Birthday and gender filled")
        dump_inputs(page, "After birthday/gender")

        human_pause(0.3, 0.8)

        # Next button — direct click, no mouse movement
        next_clicked = False
        for sel in [
            "button:has-text('Next')",
            "div[role='button']:has-text('Next')",
            "div[data-primary-action-label='Next']",
        ]:
            try:
                el = page.locator(sel).first
                if el.count() > 0:
                    el.click()
                    log.info(f"  Next clicked via: {sel}")
                    next_clicked = True
                    break
            except Exception:
                continue
        if not next_clicked:
            log.warning("  Next: could not click — continuing anyway")
        human_pause_long(2, 5)

        result.steps.append("birthday_gender_filled")

        # ── Step 4: Email / Username ────────────────────────────────────
        log.info(f"[{identity['first_name']}] Choosing email...")

        # Debug: screenshot the email page
        try:
            page.screenshot(path="/tmp/google_email_debug.png")
            log.debug("  Email page screenshot saved")
        except Exception:
            pass

        # Debug: dump what inputs are actually on the page
        try:
            inputs_info = page.evaluate("""() => {
                const inputs = document.querySelectorAll('input');
                return Array.from(inputs).map(i => ({
                    type: i.type,
                    name: i.name,
                    ariaLabel: i.getAttribute('aria-label') || '',
                    placeholder: i.placeholder || '',
                    id: i.id || '',
                    value: i.value || '',
                }));
            }""")
            log.debug(f"  Page inputs: {inputs_info}")
        except Exception:
            pass

        # Google may show suggested emails or ask to create your own
        suggested = page.locator("div[role='button']:has-text('@gmail')")
        if suggested.count() > 0:
            log.info("  Using suggested Gmail address")
            suggested.first.click()
            human_pause(0.5, 1.5)
            # Extract the email
            email_el = page.locator("input[type='email']")
            if email_el.count() > 0:
                result.email = email_el.input_value()
        else:
            # Create own email — look for the actual email/username input
            log.info("  Creating custom Gmail address")
            username = f"{identity['first_name'].lower()}{identity['last_name'].lower()}" \
                f"{random.randint(1, 999)}"

            # Try email-type input first, then text input with email-related attributes
            email_input = page.locator("input[type='email']")
            if email_input.count() == 0:
                # Google uses input[name='Username'] with aria-label="Create a Gmail address"
                email_input = page.locator(
                    "input[name='Username'], "
                    "input[aria-label*='Gmail address' i], "
                    "input[aria-label*='email' i], "
                    "input[aria-label*='Email' i], "
                    "input[type='text'][aria-label*='username' i]"
                )
            if email_input.count() == 0:
                # Last resort: any visible text input that isn't the gender field
                email_input = page.locator(
                    "input[type='text']:not([aria-label*='gender' i])"
                )

            if email_input.count() > 0:
                email_input = email_input.first
                # Wait for the email input to be visible and interactable
                try:
                    email_input.wait_for(state="visible", timeout=15000)
                except Exception:
                    log.warning("  Email input not visible — trying JS fallback")
                    try:
                        page.evaluate("""(name) => {
                            const el = document.querySelector('input[name="Username"]');
                            if (el) { el.focus(); return true; }
                            return false;
                        }""", "Username")
                    except Exception:
                        pass
                
                # Type into the specific input element directly
                email_input.click()
                human_type(page, email_input, username,
                           base_delay=0.1, mistake_prob=0.01)
                human_pause(0.3, 0.8)
                result.email = f"{username}@gmail.com"

                # Screenshot: email selected
                take_screenshot(page, "05_email_selected.png", "Email/username selected")
                dump_inputs(page, "Email page elements")

                # Check availability / next — direct click
                next_clicked = False
                for sel in [
                    "button:has-text('Next')",
                    "div[role='button']:has-text('Next')",
                    "div[data-primary-action-label='Next']",
                ]:
                    try:
                        el = page.locator(sel).first
                        if el.count() > 0:
                            el.click()
                            log.info(f"  Next clicked via: {sel}")
                            next_clicked = True
                            break
                    except Exception:
                        continue
                if next_clicked:
                    human_pause(2, 4)
            else:
                log.warning("  Could not find email input field")

        result.steps.append("email_selected")

        # ── Step 5: Password ────────────────────────────────────────────
        log.info(f"[{identity['first_name']}] Setting password...")

        if wait_for_selector(page, "input[type='password'][aria-label='Password']", timeout=10000):
            pw_input = page.locator("input[type='password'][aria-label='Password']").first
            human_type(page, pw_input, password, base_delay=0.1, mistake_prob=0.01)
            human_pause(0.3, 0.8)

            # Confirm password
            confirm = page.locator("input[type='password'][aria-label='Confirm']").first
            if confirm.count() > 0:
                human_type(page, confirm, password, base_delay=0.1, mistake_prob=0.01)
                human_pause(0.5, 1.0)

            # Screenshot: password set
            take_screenshot(page, "06_password_set.png", "Password set")
            dump_inputs(page, "Password page elements")

            # Next
            if wait_for_selector(page, "div[role='button']:has-text('Next')", timeout=8000):
                human_click(page, "div[role='button']:has-text('Next')")
                human_pause_long(3, 6)

        result.steps.append("password_set")

        # ── Step 6: CAPTCHA check ───────────────────────────────────────
        log.info(f"[{identity['first_name']}] Checking for CAPTCHA...")
        if solve_recaptcha_v2(page, timeout=120):
            log.info("CAPTCHA solved")
            human_pause(1, 3)
            take_screenshot(page, "07_captcha_solved.png", "CAPTCHA solved")
        else:
            log.info("No CAPTCHA detected or solving failed")
            take_screenshot(page, "07_no_captcha.png", "No CAPTCHA page")

        # ── Step 7: Phone verification / QR check ──────────────────────
        log.info(f"[{identity['first_name']}] Checking phone/QR step...")

        # Detect what screen we're on
        page_text = page.inner_text("body").lower()
        take_screenshot(page, "08_phone_qr_check.png", "Phone/QR check page")
        dump_inputs(page, "Phone/QR page elements")

        if "qr code" in page_text or "scan" in page_text:
            log.warning(f"[{identity['first_name']}] QR code screen detected!")
            if handle_qr_code(page):
                log.info("QR code handled")
                human_pause(2, 4)
            else:
                result.errors.append("QR bypass failed")
                log.error("QR bypass failed — this account likely failed")

        # ── Step 8: Phone verification (if asked) ──────────────────────
        if "phone number" in page_text or "mobile" in page_text or \
           "telephone" in page_text or "verify" in page_text:

            # Look for skip button first
            skip_selectors = [
                "text=Skip",
                "text=No, thanks",
                "text=Do not add",
                "button:has-text('Skip')",
            ]
            skipped = False
            for sel in skip_selectors:
                try:
                    el = page.locator(sel).first
                    if el.count() > 0:
                        el.click()
                        log.info("Phone verification skipped")
                        skipped = True
                        break
                except Exception:
                    continue

            if not skipped and sms_enabled and get_5sim_key():
                log.info("Attempting SMS verification via 5sim...")
                code = get_google_verification_code(timeout=90)
                if code:
                    # Enter phone number
                    phone_input = page.locator("input[type='tel'], input[type='text']").first
                    if phone_input.count() > 0:
                        # We need a phone number — 5sim gives us one via buy_number
                        from .sms import buy_number
                        number, _ = buy_number()
                        if number:
                            human_type(page, phone_input, number.replace("+", ""),
                                       base_delay=0.1)
                            human_pause(0.5, 1.5)
                            # Click Next / Verify
                            if wait_for_selector(page, "div[role='button']:has-text('Next')",
                                                  timeout=8000) or \
                               wait_for_selector(page, "div[role='button']:has-text('Verify')",
                                                  timeout=8000):
                                human_click(page, "div[role='button']:has-text('Next'), div[role='button']:has-text('Verify')")
                                human_pause(2, 4)
                                # Enter SMS code
                                if wait_for_selector(page, "input[type='text'], input[type='tel']",
                                                      timeout=10000):
                                    code_input = page.locator(
                                        "input[type='text'], input[type='tel']").first
                                    human_type(page, code_input, code,
                                               base_delay=0.05, mistake_prob=0.0)
                                    human_pause(0.5, 1.0)
                                    # Submit
                                    if wait_for_selector(page, "div[role='button']:has-text('Next')",
                                                          timeout=8000) or \
                                       wait_for_selector(page,
                                                         "div[role='button']:has-text('Verify')",
                                                          timeout=8000):
                                        human_click(page, "div[role='button']")
                                        human_pause_long(3, 6)
                                        result.phone_used = number
            else:
                log.info("SMS not enabled or no 5sim key — attempting skip...")
                # Final attempt to find and click any skip option
                for sel in [
                    "text=Skip for now",
                    "text=Maybe later",
                    "button:has-text('skip'):not([disabled])",
                ]:
                    try:
                        el = page.locator(sel)
                        if el.count() > 0:
                            el.click()
                            log.info(f"Clicked: {sel}")
                            break
                    except Exception:
                        continue

        result.steps.append("phone_handled")

        # ── Step 9: Final completion ─────────────────────────────────────
        log.info(f"[{identity['first_name']}] Waiting for account creation to complete...")

        # Wait for either success (no more "Next" buttons, welcome screen) or failure
        human_pause_long(5, 12)

        # Screenshot: final page
        take_screenshot(page, "09_final_result.png", "Final page")

        # Check if we're on a success/welcome page
        welcome_indicators = [
            "welcome" in page.inner_text("body").lower(),
            "your account is ready" in page.inner_text("body").lower(),
            "gmail" in page.url and "signup" not in page.url,
        ]
        if any(welcome_indicators):
            result.success = True
            log.info(f"[{identity['first_name']}] ✅ Account created: {result.email}")
        else:
            # Check for failure indicators
            error_indicators = [
                "this account has been disabled" in page.inner_text("body").lower(),
                "couldn't create your account" in page.inner_text("body").lower(),
                "try again" in page.inner_text("body").lower(),
            ]
            if any(error_indicators):
                result.errors.append("Google rejected account creation")
                log.warning(f"[{identity['first_name']}] ❌ Account creation rejected")
            else:
                # Uncertain — might still be on a pending screen
                log.info(f"[{identity['first_name']}] ⏳ Unknown state — email may be valid")
                result.success = result.email != ""

        result.steps.append("creation_complete")

    except Exception as e:
        result.errors.append(f"Flow exception: {e}")
        log.error(f"[{identity['first_name']}] 💥 Signup flow crashed: {e}")

    return result


# ── Convenience: create a context + page for one account ────────────────────

def setup_account_context(
    browser: Browser,
    use_mobile: bool = True,
    proxy_str: str = None,
) -> tuple[BrowserContext, Page]:
    """
    Create a new incognito browser context with fingerprint spoofing,
    optional proxy, and return (context, page).
    """
    fingerprint = mobile_fingerprint() if use_mobile else desktop_fingerprint()
    proxy_dict = proxy_to_dict(proxy_str) if proxy_str else None

    context = browser.new_context(
        user_agent=fingerprint["user_agent"],
        viewport=fingerprint["viewport"],
        timezone_id=fingerprint["timezone"],
        locale="en-US",
        is_mobile=fingerprint.get("mobile", False),
        has_touch=fingerprint.get("has_touch", False),
        device_scale_factor=fingerprint.get("device_scale_factor", 1),
        proxy=proxy_dict,
    )

    # Inject fingerprint spoofing scripts before any page loads
    inject_js = build_inject_script(mobile=use_mobile)
    context.add_init_script(inject_js)

    page = context.new_page()
    return context, page
