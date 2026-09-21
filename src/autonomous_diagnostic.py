"""
Autonomous diagnostic runner for Gmail signup bypass methods.

Purpose:
  Run the signup flow under multiple configurations, collect per-step events,
  score each run for smoothness and friction, and produce a ranked report.

Design notes:
  - Most of the 9 methods from references/bypass_playbook.md cannot be
    exercised in this environment (no PVACreator license, no TCP-spoof
    proxy, no phones, no cloud phone subscriptions). The diagnostic
    therefore tests the *testable slice* thoroughly and records, for each
    non-testable method, what would be needed to evaluate it.

  - The testable slice is:
      * Desktop vs mobile UA fingerprint
      * Fast vs human-timing pacing
      * Skip-button gamble at phone step (M9 slice)
      * Behavior: how quickly Google inserts QR / CAPTCHA / phone prompt
        as volume increases

  - Low-level browser signal probes (fingerprint consistency, WebRTC,
    connection identity) are included as passive tests that do not hit
    Google signup at all — they just characterize the environment.

Run:
  python3 -m src.autonomous_diagnostic
  or from project root:
  python3 src/autonomous_diagnostic.py
"""

import json
import os
import sys
import time
import random
import logging
from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

# ----------------------------------------------------------------------
# Add project root so `from src.signup import ...` works if invoked from
# a subdirectory; harmless otherwise.
# ----------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

log = logging.getLogger("autodial")
logging.basicConfig(level=logging.INFO,
                    format="%(levelname)s [%(name)s] %(message)s")


# ----------------------------------------------------------------------
# Errors we track as "friction"
# ----------------------------------------------------------------------

FrictionEvent = Dict[str, Any]


def _now() -> float:
    return time.time()


# ----------------------------------------------------------------------
# Diagnostic configuration: one "method slice" we actually test.
# ----------------------------------------------------------------------

@dataclass
class DiagnosticConfig:
    """One experimental configuration for a signup run.

    The `name` should be a short label. `desc` is a human-readable note,
    ideally tying the config back to the M1..M9 method catalog so the
    report can say "this config is a slice of M2-like behavior" etc.
    """

    name: str
    desc: str
    # which UA/fingerprint profile to use
    fingerprint_profile: str = "desktop"  # "desktop" | "mobile"
    # pacing
    pacing: str = "human"  # "human" | "fast"
    # phone step behavior
    phone_policy: str = "skip_if_offered"  # "skip_if_offered" | "none"
    # proxy
    proxy: Optional[str] = None
    # whether to try to exercise the skip-button gamble (M9)
    try_skip: bool = False
    # expected method family reference (for the report)
    method_family_ref: str = ""


DEFAULT_CONFIGS: List[DiagnosticConfig] = [
    DiagnosticConfig(
        name="A1_desktop_human_skip",
        desc=("Desktop UA + human pacing + try skip at phone step. "
              "Nearest testable slice to a low-signal desktop signup; "
              "useful as a baseline against which the others are judged."),
        fingerprint_profile="desktop",
        pacing="human",
        phone_policy="skip_if_offered",
        try_skip=True,
        method_family_ref="baseline (desktop, no proxy, no SMS)",
    ),
    DiagnosticConfig(
        name="A2_mobile_human_skip",
        desc=("Mobile UA + human pacing + try skip at phone step. "
              "Tests whether presenting a mobile UA changes what Google "
              "asks for (SMS vs QR vs skip) — a slice of M2/M3-style "
              "trust-path selection, minus the real phone."),
        fingerprint_profile="mobile",
        pacing="human",
        phone_policy="skip_if_offered",
        try_skip=True,
        method_family_ref="M2/M3 slice (mobile UA, no real device)",
    ),
    DiagnosticConfig(
        name="A3_desktop_fast_skip",
        desc=("Desktop UA + fast pacing + try skip at phone step. "
              "Tests whether faster pacing increases friction — the "
              "opposite of the human-timing assumption in M9."),
        fingerprint_profile="desktop",
        pacing="fast",
        phone_policy="skip_if_offered",
        try_skip=True,
        method_family_ref="anti-M9 (fast pacing)",
    ),
    DiagnosticConfig(
        name="A4_desktop_human_no_skip",
        desc=("Desktop UA + human pacing + do not try to skip phone step. "
              "Used to compare skip vs not-skip under otherwise identical "
              "conditions."),
        fingerprint_profile="desktop",
        pacing="human",
        phone_policy="skip_if_offered",
        try_skip=False,
        method_family_ref="control (desktop, no skip attempt)",
    ),
]


# ----------------------------------------------------------------------
# Result of one signup attempt
# ----------------------------------------------------------------------

@dataclass
class RunResult:
    config: DiagnosticConfig
    success: bool
    email: str = ""
    password: str = ""
    full_name: str = ""
    errors: List[str] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    friction: List[FrictionEvent] = field(default_factory=list)
    wallclock_seconds: float = 0.0
    # derived
    qr_seen: bool = False
    captcha_seen: bool = False
    phone_prompt_seen: bool = False
    skip_offered_and_used: bool = False
    skip_offered_but_not_used: bool = False
    block_seen: bool = False
    otp_prompted: bool = False
    otp_sent: bool = False  # M7-style: phone sent an SMS (not just received)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["config"] = asdict(self.config)
        return d


# ----------------------------------------------------------------------
# Scoring
# ----------------------------------------------------------------------

class FrictionScore:
    """Aggregate friction signals for one run into a small report.

    Lower cumulative friction is "smoother". The weights are heuristics,
    calibrated to tell the difference between "clean run" and "Google
    fought back at several points".
    """

    WEIGHTS: Dict[str, float] = {
        "qr_seen": 3.0,
        "captcha_seen": 2.0,
        "phone_prompt_seen": 1.0,
        "otp_prompted": 1.0,
        "block_seen": 5.0,
        "retry_attempted": 0.5,
        "error_occurred": 1.0,
        "slow_run_over_60s": 0.25,
    }

    def __init__(self, friction: List[FrictionEvent],
                 wallclock_seconds: float) -> None:
        self.friction = friction
        self.wallclock_seconds = wallclock_seconds
        self._total: Optional[float] = None
        self._items: List[Dict[str, Any]] = []

    @property
    def total(self) -> float:
        if self._total is None:
            self._total = 0.0
            for item in self.items:
                self._total += item.get("weight", 0.0)
        return self._total

    @property
    def items(self) -> List[Dict[str, Any]]:
        if not self._items:
            self._items = []
            counts: Dict[str, int] = {}
            for f in self.friction:
                k = f.get("key", "unknown")
                counts[k] = counts.get(k, 0) + 1
            for k, count in sorted(counts.items()):
                weight = self.WEIGHTS.get(k, 0.5)
                self._items.append({
                    "key": k,
                    "count": count,
                    "weight": weight,
                    "contrib": weight * count,
                })
            if self.wallclock_seconds > 60:
                self._items.append({
                    "key": "slow_run_over_60s",
                    "count": 1,
                    "weight": self.WEIGHTS["slow_run_over_60s"],
                    "contrib": self.WEIGHTS["slow_run_over_60s"],
                })
        return self._items

    def summary(self) -> Dict[str, Any]:
        return {
            "total_friction": round(self.total, 2),
            "breakdown": self.items,
            "wallclock_seconds": round(self.wallclock_seconds, 2),
        }


# ----------------------------------------------------------------------
# Method catalog mirror (read-only copy of the playbook's method list)
# ----------------------------------------------------------------------

METHOD_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "M1",
        "name": "PVACreator commercial automation",
        "testable_here": False,
        "why_not": ("Requires PVACreator license and its own proxy/SMS/"
                    "fingerprint bindings; black-box to us."),
        "what_we_can_infer": ("Our testable slice cannot reproduce this. "
                               "The only evidence is vendor demos (V1/V3/V4). "
                               "If a Google signup under our config already "
                               "shows QR/CAPTCHA/phone-prompt at low volume, "
                               "a vendor claiming QR bypass should be treated "
                               "as a claim, not proof."),
    },
    {
        "id": "M2",
        "name": "TCP-fingerprint spoof + antidetect browser",
        "testable_here": False,
        "why_not": ("Requires TCP-layer fingerprint spoofing proxy (e.g. "
                    "Voidmob-style) plus an antidetect browser profile. Not "
                    "available here."),
        "what_we_can_infer": ("Our desktop-vs-mobile UA runs are a weak proxy "
                               "for whether device-class signals matter. If "
                               "mobile UA changes the phone-vs-QR prompt while "
                               "the underlying connection is still a datacenter "
                               "IP, that is evidence that device-class signals "
                               "are read separately from IP class."),
    },
    {
        "id": "M3",
        "name": "Real Android device + cellular data",
        "testable_here": False,
        "why_not": "Requires a physical Android phone on a cellular connection.",
        "what_we_can_infer": ("Cannot test directly. If mobile UA without a real "
                               "carrier connection still does not get SMS, that is "
                               "weak evidence that carrier/device attestation matters "
                               "more than UA alone."),
    },
    {
        "id": "M4",
        "name": "Cloud phone platforms (GeeLark / DuoPlus)",
        "testable_here": False,
        "why_not": "Requires a cloud-phone subscription; not available here.",
        "what_we_can_infer": "Cannot test directly.",
    },
    {
        "id": "M5",
        "name": "Linux fingerprint browser + regional proxy",
        "testable_here": False,
        "why_not": ("Requires a fingerprint-browser license and a residential "
                    "proxy from a regional pool; not available here."),
        "what_we_can_infer": "Cannot test directly.",
    },
    {
        "id": "M6",
        "name": "Alternative Google entry points (YouTube app, Android Settings, Drive/Docs)",
        "testable_here": False,
        "why_not": "Requires a mobile device with the Google apps; not available here.",
        "what_we_can_infer": ("Different entry points may trigger different challenge "
                               "logic. Cannot test here, but worth noting for defenders: "
                               "a single signup-protection policy may not be uniform across "
                               "all Google entry points."),
    },
    {
        "id": "M7",
        "name": "QR decode + programmatic SMS send from carrier-connected phone",
        "testable_here": False,
        "why_not": ("Requires a camera-capable phone on a carrier connection that can "
                    "scan the QR and send the resulting SMS. Not available here."),
        "what_we_can_infer": ("Our qr_bypass module can detect a QR screen and attempt "
                               "online decode. What we cannot do here is the second half "
                               "of M7: sending the SMS from a real device. If Google shows "
                               "a QR that decodes to a phone-bound action rather than a "
                               "simple code-to-enter, that is a signal that the check is "
                               "partly about device/carrier proof, not just code receipt."),
    },
    {
        "id": "M8",
        "name": "Pre-verified / ready-made accounts",
        "testable_here": False,
        "why_not": "Requires buying accounts that were already created and verified.",
        "what_we_can_infer": ("Not a registration-time bypass; it sidesteps registration. "
                               "Defenders should watch for post-creation patterns that look "
                               "like transferred/pre-verified inventory rather than only "
                               "registration-time signals."),
    },
    {
        "id": "M9",
        "name": "Skip-button timing + low-trust-signal session",
        "testable_here": True,
        "why_not": "",
        "what_we_can_infer": ("We test this directly: configs A1/A2/A3 attempt the skip "
                               "button when offered; A4 does not. If any config surfaces "
                               "and uses skip, we learn whether Google's skip path is "
                               "available under our conditions, and whether faster pacing "
                               "changes that. This is opportunistic, not reliable."),
    },
]


# ----------------------------------------------------------------------
# Low-level browser signal probes (no Google hit)
# ----------------------------------------------------------------------

def probe_connection_identity(page: Any) -> Dict[str, Any]:
    """Ask the page to report a few connection/host signals.

    This is a passive characterization, not a Google signup. It helps the
    report describe the environment in which the signup runs: is the IP a
    datacenter? Does WebRTC expose a local or public IP? What does the
    browser claim about itself?
    """
    try:
        info = page.evaluate("""() => {
            const out = {};

            // UA
            out.userAgent = navigator.userAgent;

            // platform
            out.platform = navigator.platform;

            // languages
            out.languages = navigator.languages;

            // connection
            if (navigator.connection) {
                out.connection = {
                    rtt: navigator.connection.rtt,
                    downlink: navigator.connection.downlink,
                    effectiveType: navigator.connection.effectiveType,
                    type: navigator.connection.type,
                };
            }

            // WebRTC public IP is hard to get without a STUN check here,
            // so we only report whether WebRTC objects exist.
            out.webrtc_exposed =
                !!(navigator.mediaDevices && navigator.mediaDevices.enumerateDevices);

            return out;
        } // end IIFE""")
        return {"ok": True, "info": info}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def probe_fingerprint_noise(page: Any) -> Dict[str, Any]:
    """Run the fingerprint injection and report whether key flags got masked.

    Reads back a few navigator properties to confirm:
      - webdriver is undefined/null
      - canvas/WebGL/Audio noise is present (by checking that the injection
        script ran without error and that a couple of getters are present).
    """
    try:
        report = page.evaluate("""() => {
            const out = {};

            // navigator.webdriver
            try {
                const wd = (navigator as any).webdriver;
                out.webdriver = wd === undefined || wd === null
                    ? "masked"
                    : String(wd);
            } catch (e) {
                out.webdriver = "not_accessible";
            }

            // canvas fingerprint presence
            out.canvas_toDataURL = typeof HTMLCanvasElement !== "undefined"
                && "toDataURL" in HTMLCanvasElement.prototype;

            // WebGL presence
            out.webgl_available =
                !!(window as any).WebGLRenderingContext;

            // AudioContext presence
            out.audio_available =
                !!(window as any).AudioContext || !!(window as any).webkitAudioContext;

            // plugins (often spoofed; we just report presence)
            out.plugins_present = !!(navigator as any).plugins;
            out.mimeTypes_present = !!(navigator as any).mimeTypes;

            return out;
        } // end IIFE""")
        return {"ok": True, "report": report}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


# ----------------------------------------------------------------------
# Run one signup attempt under a config
# ----------------------------------------------------------------------

def run_one_attempt(config: DiagnosticConfig,
                    max_accounts_for_seed: int = 1) -> RunResult:
    """Run a single signup attempt under a config.

    This function owns the Playwright browser lifecycle for the attempt,
    creates a fresh context with the chosen fingerprint profile, and runs
    the signup flow via the internal helpers in src.signup.

    It is intentionally self-contained so the diagnostic can run even when
    campaign.py's threading isn't in scope.
    """
    t0 = _now()
    result = RunResult(config=config, success=False)

    try:
        from playwright.sync_api import sync_playwright
        from src.signup import (create_account, AccountResult,
                                GOOGLE_SIGNUP_URL, setup_account_context,
                                random_password)
        from src.events import EventTimeline
        from src.config import NAME_POOL, PROXY_POOL, get_5sim_key
        from src import fingerprint as fp_mod

        timeline = EventTimeline()
        timeline.emit("run_start", "diagnostic",
                      f"config={config.name}")

        # ---- identity (name + birthday) ----
        try:
            identity = NAME_POOL.random_identity()
        except (AttributeError, Exception):
            identity = {
                "first_name": "test",
                "last_name": "user",
                "birthday": f"{random.randint(1,12):02d}{random.randint(1,28):02d}199{random.randint(0,9)}",
                "gender": random.choice(["male", "female"]),
            }

        # ---- fingerprint ----
        if config.fingerprint_profile == "mobile":
            fp = fp_mod.mobile_fingerprint()
            use_mobile = True
        else:
            fp = fp_mod.desktop_fingerprint()
            use_mobile = False

        proxy = config.proxy or None
        if not proxy and config.fingerprint_profile != "mobile":
            try:
                p = PROXY_POOL.next()
                if p:
                    proxy = p
            except Exception:
                pass

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                ctx, page = setup_account_context(
                    browser,
                    use_mobile=use_mobile,
                    proxy_str=(proxy or ""),
                )

                # override UA/viewport with the chosen fingerprint profile
                page.set_extra_http_headers({})
                ctx.set_default_timeout(20000)

                account: AccountResult = create_account(
                    browser=browser,
                    context=ctx,
                    page=page,
                    identity=identity,
                    use_mobile=use_mobile,
                    sms_enabled=False,  # diagnostic: we don't have 5sim + we don't want paid SMS
                    attempt=1,
                    config_overrides={
                        "fingerprint_profile": config.fingerprint_profile,
                        "pacing": config.pacing,
                        "phone_policy": config.phone_policy,
                        "try_skip": config.try_skip,
                        "event_timeline": timeline,
                    },
                )

                result.email = account.email
                result.password = account.password
                result.full_name = account.full_name
                result.success = account.success
                result.errors = list(account.errors or [])
                result.events = timeline.chronological()
                result.wallclock_seconds = round(_now() - t0, 2)

                # Translate timeline into friction events.
                friction: List[FrictionEvent] = []
                for ev in result.events:
                    kind = ev.get("kind", "")
                    step = ev.get("step", "")
                    msg = ev.get("message", "")
                    payload = ev.get("payload", {})

                    if kind in ("QRSeen",):
                        result.qr_seen = True
                        friction.append({"key": "qr_seen", "step": step,
                                         "message": msg, "payload": payload})
                    elif kind in ("CaptchaSeen",):
                        result.captcha_seen = True
                        friction.append({"key": "captcha_seen", "step": step,
                                         "message": msg, "payload": payload})
                    elif kind in ("PhonePrompt",):
                        result.phone_prompt_seen = True
                        friction.append({"key": "phone_prompt_seen", "step": step,
                                         "message": msg, "payload": payload})
                    elif kind in ("SkipOfferedAndUsed",):
                        result.skip_offered_and_used = True
                        friction.append({"key": "skip_offered_and_used", "step": step,
                                         "message": msg, "payload": payload})
                    elif kind in ("SkipOfferedButNotUsed",):
                        result.skip_offered_but_not_used = True
                        friction.append({"key": "skip_offered_but_not_used",
                                         "step": step, "message": msg,
                                         "payload": payload})
                    elif kind in ("BlockSeen",):
                        result.block_seen = True
                        friction.append({"key": "block_seen", "step": step,
                                         "message": msg, "payload": payload})
                    elif kind in ("OtpPrompted",):
                        result.otp_prompted = True
                        friction.append({"key": "otp_prompted", "step": step,
                                         "message": msg, "payload": payload})
                    elif kind in ("OtpSent",):
                        result.otp_sent = True
                        friction.append({"key": "otp_sent", "step": step,
                                         "message": msg, "payload": payload})
                    elif kind in ("RetryAttempted",):
                        friction.append({"key": "retry_attempted", "step": step,
                                         "message": msg, "payload": payload})
                    elif kind in ("Error",):
                        friction.append({"key": "error_occurred", "step": step,
                                         "message": msg, "payload": payload})

                result.friction = friction

            finally:
                browser.close()

    except Exception as exc:  # noqa: BLE001
        result.wallclock_seconds = round(_now() - t0, 2)
        result.errors.append(f"attempt exception: {exc}")
        log.error("attempt %s failed: %s", config.name, exc)

    return result


# ----------------------------------------------------------------------
# Report generation
# ----------------------------------------------------------------------

HEADER = """
================================================================================
AUTONOMOUS DIAGNOSTIC REPORT — Gmail signup bypass methods
================================================================================

This diagnostic exercises the *testable slice* of the methods in
../references/bypass_playbook.md under local conditions. Many methods
(M1, M2, M3, M4, M5, M6, M7, M8) cannot be run here and are recorded
as blocked-with-reason. M9 (skip-button gamble) is partially testable
through the skip-at-phone-step configs.

The goal is not to declare a "winner method". The goal is to observe:
  - Under what local conditions does Google show QR, CAPTCHA, phone
    prompt, skip, or block?
  - Which configuration had the least friction?
  - What does that imply about the non-testable methods?
================================================================================
"""


def build_report(results: List[RunResult]) -> str:
    lines: List[str] = []
    lines.append(HEADER)

    lines.append("\n## 1. Method catalog: testable vs blocked\n\n")
    lines.append(f"{'ID':<5} {'Testable here?':<16} {'Method name':<55}\n")
    lines.append("-" * 90 + "\n")
    for m in METHOD_CATALOG:
        ok = "YES" if m["testable_here"] else "NO"
        lines.append(
            f"{m['id']:<5} {ok:<16} {m['name'][:54]:<55}\n"
        )

    lines.append("\n## 2. Blocked methods — why and what we can infer\n\n")
    for m in METHOD_CATALOG:
        if not m["testable_here"]:
            lines.append(f"### {m['id']} — {m['name']}\n\n")
            lines.append(f"- **Not testable here:** {m['why_not']}\n")
            lines.append(f"- **Inference:** {m['what_we_can_infer']}\n\n")

    lines.append("## 3. Run results\n\n")
    for r in results:
        score = FrictionScore(r.friction, r.wallclock_seconds)
        lines.append(f"### {r.config.name}\n\n")
        lines.append(f"- desc: {r.config.desc}\n")
        lines.append(f"- method_family_ref: {r.config.method_family_ref}\n")
        lines.append(f"- success: {r.success}\n")
        lines.append(f"- email: {r.email or '(none)'}\n")
        lines.append(f"- full_name: {r.full_name or '(none)'}\n")
        lines.append(f"- wallclock: {r.wallclock_seconds}s\n")
        lines.append(f"- qr_seen: {r.qr_seen}\n")
        lines.append(f"- captcha_seen: {r.captcha_seen}\n")
        lines.append(f"- phone_prompt_seen: {r.phone_prompt_seen}\n")
        lines.append(f"- skip_offered_and_used: {r.skip_offered_and_used}\n")
        lines.append(f"- skip_offered_but_not_used: {r.skip_offered_but_not_used}\n")
        lines.append(f"- block_seen: {r.block_seen}\n")
        lines.append(f"- otp_prompted: {r.otp_prompted}\n")
        lines.append(f"- otp_sent: {r.otp_sent}\n")
        lines.append(f"- errors: {len(r.errors)}\n")
        if r.errors:
            for e in r.errors[:5]:
                lines.append(f"    - {e}\n")
        lines.append("\n- friction score:\n")
        s = score.summary()
        lines.append(f"    - total_friction: {s['total_friction']}\n")
        lines.append(f"    - wallclock_seconds: {s['wallclock_seconds']}\n")
        for it in s["breakdown"]:
            lines.append(
                f"    - {it['key']}: count={it['count']} "
                f"weight={it['weight']} contrib={it['contrib']}\n"
            )
        lines.append("\n- event timeline (first 40):\n")
        for ev in r.events[:40]:
            lines.append(f"    - [{ev.get('ts', 0):.2f}] {ev.get('kind', '')}:{ev.get('step', '')} :: {ev.get('message', '')}\n")
        lines.append("\n")

    # Rank by friction
    ranked = sorted(results, key=lambda r: FrictionScore(r.friction, r.wallclock_seconds).total)
    lines.append("## 4. Smoothest-first ranking (by total friction)\n\n")
    lines.append(f"{'rank':<6} {'config':<28} {'total_friction':<16} {'success':<9} {'qr':<5} {'captcha':<9} {'phone':<7} {'skip_used':<12}\n")
    lines.append("-" * 110 + "\n")
    for i, r in enumerate(ranked, 1):
        score = FrictionScore(r.friction, r.wallclock_seconds)
        lines.append(
            f"{i:<6} {r.config.name:<28} {score.total:<16.2f} "
            f"{str(r.success):<9} {str(r.qr_seen):<5} "
            f"{str(r.captcha_seen):<9} {str(r.phone_prompt_seen):<7} "
            f"{str(r.skip_offered_and_used):<12}\n"
        )

    lines.append("\n## 5. Smoothest run — detail\n\n")
    best = ranked[0] if ranked else None
    if best:
        score = FrictionScore(best.friction, best.wallclock_seconds)
        lines.append(f"Config: {best.config.name}\n")
        lines.append(f"Total friction: {score.total:.2f}\n")
        lines.append(f"Success: {best.success}\n")
        lines.append(f"Email: {best.email or '(none)'}\n")
        lines.append(f"Wallclock: {best.wallclock_seconds}s\n")
        lines.append("Reason it is smoothest (from scoring):\n")
        if not score.items:
            lines.append("  (no friction items recorded)\n")
        else:
            for it in sorted(score.items, key=lambda x: -x["contrib"]):
                lines.append(f"  - {it['key']}: {it['count']} x weight {it['weight']} = {it['contrib']}\n")
        lines.append("\nInterpretation:\n")
        lines.append(f"  The smoothest run under *these local conditions* was {best.config.name}.\n")
        lines.append("  That does NOT mean this config replicates any specific M1..M9 method.\n")
        lines.append("  It means: under the current IP/environment, this configuration\n")
        lines.append("  produced the fewest Google friction signals before finishing (or failing).\n")

    lines.append("\n## 6. Method-smoothness cross-reference\n\n")
    lines.append("How to read this against references/bypass_playbook.md:\n\n")
    for m in METHOD_CATALOG:
        lines.append(f"- **{m['id']} {m['name']}**:\n")
        if m["testable_here"]:
            lines.append("  - Testable here via the skip-group configs (A1..A4).\n")
            lines.append("  - See ranking above for which related config felt smoothest.\n")
        else:
            lines.append(f"  - Not testable here. {m['what_we_can_infer']}\n")
    lines.append("\n")

    lines.append("================================================================================\n")
    lines.append("END OF REPORT\n")
    lines.append("================================================================================\n")
    return "".join(lines)


def write_report(report: str, out_path: Optional[Path] = None) -> Path:
    if out_path is None:
        out_path = Path(__file__).resolve().parent / "autonomous_diagnostic_report.md"
    out_path.write_text(report, encoding="utf-8")
    return out_path


# ----------------------------------------------------------------------
# Standalone runner
# ----------------------------------------------------------------------

def _parse_args(argv: List[str]) -> Dict[str, Any]:
    flags: Dict[str, Any] = {
        "configs": list(DEFAULT_CONFIGS),
        "per_config_attempts": 1,
        "output": None,
        "only": None,
        "probes_only": False,
    }
    i = 0
    args = argv[1:] if argv[1:] else []
    while i < len(args):
        a = args[i]
        if a == "--configs" and i + 1 < len(args):
            names = {n.strip() for n in args[i + 1].split(",") if n.strip()}
            def _name_matches(cfg_name: str, wanted: str) -> bool:
                # allow prefix match: "A1" matches "A1_desktop_human_skip"
                return cfg_name == wanted or cfg_name.startswith(wanted + "_")
            flags["configs"] = [
                c for c in DEFAULT_CONFIGS
                if any(_name_matches(c.name, w) for w in names)
            ]
            i += 2
        elif a == "--attempts" and i + 1 < len(args):
            flags["per_config_attempts"] = int(args[i + 1])
            i += 2
        elif a == "--output" and i + 1 < len(args):
            flags["output"] = Path(args[i + 1])
            i += 2
        elif a == "--only" and i + 1 < len(args):
            flags["only"] = args[i + 1]
            i += 2
        elif a == "--probes-only":
            flags["probes_only"] = True
            i += 1
        else:
            i += 1
    return flags


def main(argv: Optional[List[str]] = None) -> int:
    argv = argv or sys.argv
    flags = _parse_args(argv)

    # ------------------------------------------------------------------
    # Passive probes (always run; do not hit Google signup)
    # ------------------------------------------------------------------
    print("==> Running passive browser-signal probes (no Google signup)")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context()
            page = ctx.new_page()
            try:
                conn = probe_connection_identity(page)
                print("    connection_identity:", json.dumps(conn, ensure_ascii=False, default=str))
                fp = probe_fingerprint_noise(page)
                print("    fingerprint_noise:", json.dumps(fp, ensure_ascii=False, default=str))
            finally:
                browser.close()
    except Exception as exc:  # noqa: BLE001
        log.warning("passive probes could not run: %s", exc)

    if flags["probes_only"]:
        print("==> --probes-only, stopping after passive probes")
        return 0

    configs = flags["configs"]
    if flags["only"]:
        configs = [c for c in configs if c.name == flags["only"]]
        if not configs:
            print(f"==> No config named {flags['only']}; nothing to run")
            return 2

    print(f"==> Running {len(configs)} config(s) x {flags['per_config_attempts']} attempt(s) each")
    for c in configs:
        print(f"    - {c.name}: {c.desc}")

    results: List[RunResult] = []
    for config in configs:
        for attempt in range(flags["per_config_attempts"]):
            print(f"==> [{config.name}] attempt {attempt + 1}/{flags['per_config_attempts']}")
            r = run_one_attempt(config)
            results.append(r)
            sc = FrictionScore(r.friction, r.wallclock_seconds)
            print(f"    success={r.success} qr={r.qr_seen} captcha={r.captcha_seen} "
                  f"phone={r.phone_prompt_seen} skip_used={r.skip_offered_and_used} "
                  f"friction={sc.total:.2f} time={r.wallclock_seconds}s")
            if r.email:
                print(f"    email: {r.email}")

    report = build_report(results)
    out = write_report(report, flags["output"])
    print(f"\n==> Report written: {out}")
    print(f"==> Total runs: {len(results)}; smoothest-by-friction:")
    for i, r in enumerate(sorted(results, key=lambda r: FrictionScore(r.friction, r.wallclock_seconds).total), 1):
        sc = FrictionScore(r.friction, r.wallclock_seconds)
        print(f"    {i}. {r.config.name} friction={sc.total:.2f} success={r.success}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
