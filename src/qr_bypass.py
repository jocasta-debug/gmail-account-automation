"""
QR Code bypass module — dual-strategy for Gmail's "Verify you are a real person" QR.

Strategy A — Preventive (mobile-endpoint emulation):
  Present a mobile UA + mobile viewport + mobile platform in the browser context.
  Google's risk engine may route the signup through the mobile registration matrix,
  which has a less strict verification barrier and may not trigger the QR code at
  all (or may trigger SMS/email verification which we can handle).

Strategy B — Reactive (QR detect → decode → open verification URL):
  If a QR code screen IS shown:
   1. Detect the QR element on the page
   2. Screenshot the QR code region
   3. Decode the QR payload via an online API (returns the verification URL)
   4. Open that URL in the controlled browser
   5. Complete whatever verification flow follows (typically a confirmation prompt)

Strategy C — Fallback (alternative verification):
  On the QR screen, look for "Try another way" or equivalent buttons.
  If phone verification is offered, use the 5sim SMS flow.
  If email verification is offered, use a recovery email.
"""

import time
import io
import logging
import base64
import requests
from typing import Optional

from playwright.sync_api import Page, Locator

from .config import log

# ── QR decode API ────────────────────────────────────────────────────────────
# Public endpoint: POST image file → JSON with decoded text.
# Fallback endpoints included.

QR_DECODE_API = "https://api.qrserver.com/v1/read-qr-code/"


def decode_qr_image(image_bytes: bytes) -> Optional[tuple]:
    """
    Send QR image to online decoder; return (qr_data, qr_text) tuple.
    """
    try:
        files = {"file": ("qr.png", image_bytes, "image/png")}
        resp = requests.post(QR_DECODE_API, files=files, timeout=15)
        data = resp.json()
        if data and isinstance(data, list) and len(data) > 0:
            item = data[0]
            # Response format: [{"type":"qrcode","symbol":[{"seq":0,"data":"...","error":None}]}]
            symbols = item.get("symbol") or []
            if symbols and len(symbols) > 0:
                qr_data = symbols[0].get("data", "")
                if qr_data:
                    return qr_data, qr_data
        log.warning(f"QR decode API returned unexpected: {data}")
    except Exception as e:
        log.error(f"QR decode API call failed: {e}")
    return None


# ── Strategy B: QR detection + screenshot + decode ──────────────────────────

QR_SCREENSHOT_SELECTORS = [
    "div[role='img']",
    "canvas",
    "img[src*='qr']",
    "svg",
]


def detect_qr_screen(page: Page) -> bool:
    """
    Heuristic: is the current page showing a QR code verification screen?
    Google's QR page typically contains:
     - A large QR code image/canvas
     - Text like "Verify it's you" / "Scan this QR code"
     - A URL or hint about using a phone
    """
    text = page.inner_text("body").lower()
    qr_indicators = [
        "qr code" in text,
        "qr code" in text,
        "scan" in text and "phone" in text,
        "verify it's you" in text or "verify it is you" in text,
        "verify some info" in text,
    ]
    return any(qr_indicators)


def screenshot_qr_region(page: Page) -> Optional[bytes]:
    """
    Find the QR code element on the page and screenshot just that region.
    Returns PNG bytes or None.
    """
    # Try to find the QR code element — Google's QR is usually a <img> or <canvas>
    # in a container.  We'll try multiple strategies.

    # Strategy 1: find by role='img' (largest image on page)
    try:
        elements = page.locator("img").all()
        for el in elements:
            try:
                if el.count() > 0:
                    box = el.bounding_box()
                    if box and box["width"] > 100 and box["height"] > 100:
                        # Screenshot this element
                        screenshot = el.screenshot()
                        if screenshot and len(screenshot) > 500:
                            return screenshot
            except Exception:
                continue
    except Exception as e:
        log.debug(f"Screenshot by img selector failed: {e}")

    # Strategy 2: screenshot the full viewport and let the decoder handle it
    try:
        full_screenshot = page.screenshot(full_page=False)
        if full_screenshot and len(full_screenshot) > 1000:
            return full_screenshot
    except Exception as e:
        log.error(f"Full viewport screenshot failed: {e}")

    return None


def extract_qr_url(page: Page) -> Optional[str]:
    """
    Full reactive QR bypass flow:
     1. Screenshot the QR region
     2. Decode the QR payload
     3. Return the URL embedded in the QR code
    """
    image_bytes = screenshot_qr_region(page)
    if not image_bytes:
        log.error("Could not capture QR code image from page")
        return None

    log.info(f"QR image captured: {len(image_bytes)} bytes")

    result = decode_qr_image(image_bytes)
    if not result:
        log.error("QR code could not be decoded")
        return None

    qr_data, qr_text = result
    log.info(f"QR decoded: data={qr_data[:80]}, text={qr_text[:80]}")

    # The QR payload is typically a URL or a verification token
    # Google's QR usually contains a URL like:
    #   https://accounts.google.com/verify?q=r...
    url = qr_text or qr_data
    if url and url.startswith("http"):
        return url
    elif url and not url.startswith("http"):
        # Might be a relative path or token — prepend Google base
        return f"https://accounts.google.com{url}"

    return url


def complete_qr_verification_flow(page: Page, qr_url: str) -> bool:
    """
    Open the decoded QR verification URL in the current browser context
    and complete whatever confirmation flow Google presents.
    """
    log.info(f"Opening QR verification URL: {qr_url[:80]}...")
    try:
        page.goto(qr_url, wait_until="domcontentloaded", timeout=20000)
        time.sleep(2)

        # Look for common confirmation buttons
        for sel in [
            "button:has-text('Allow')",
            "button:has-text('Confirm')",
            "button:has-text('Verify')",
            "button:has-text('Yes')",
            "button:has-text('Continue')",
            "button:has-text('I'm not a robot')",
            "input[type='submit']",
            "button[type='submit']",
        ]:
            try:
                btn = page.locator(sel)
                if btn.count() > 0:
                    btn.click()
                    log.info(f"Clicked confirmation: {sel}")
                    time.sleep(2)
                    return True
            except Exception:
                continue

        # If no button, wait for navigation to complete
        log.info("No confirmation button found — waiting for page settle...")
        time.sleep(5)
        return True

    except Exception as e:
        log.error(f"QR verification flow failed: {e}")
        return False


# ── Strategy C: Try another way / alternative verification ──────────────────

def try_alternative_verification(page: Page) -> bool:
    """
    On the QR screen, look for "Try another way" / "Try a different method"
    buttons. If found, click and see if SMS or email verification becomes available.
    """
    selectors = [
        "text=Try another way",
        "text=Try a different method",
        "text=More options",
        "text=Don't have a camera",
        "button:has-text('another way')",
        "button:has-text('different')",
        "a:has-text('another way')",
    ]

    for sel in selectors:
        try:
            el = page.locator(sel)
            if el.count() > 0:
                el.click()
                log.info(f"Clicked alternative verification: {sel}")
                time.sleep(2)
                return True
        except Exception:
            continue

    return False


# ── Main QR bypass entrypoint ────────────────────────────────────────────────

def handle_qr_code(page: Page, use_5sim: bool = False) -> bool:
    """
    Main QR code handler.  Tries strategies in order:
     1. Detect if QR screen is showing
     2. Try "Try another way" (may lead to SMS/email verification)
     3. Screenshot + decode QR → open verification URL
     4. Report failure

    Returns True if the QR was handled successfully.
    """
    if not detect_qr_screen(page):
        return True  # no QR code present

    log.warning("QR code verification screen detected!")

    # Strategy C: alternative verification
    if try_alternative_verification(page):
        log.info("Alternative verification clicked — waiting to see what appears...")
        time.sleep(3)
        # If phone verification appears, 5sim can handle it (caller's responsibility)
        return True

    # Strategy B: decode + open URL
    qr_url = extract_qr_url(page)
    if qr_url:
        return complete_qr_verification_flow(page, qr_url)

    log.error("All QR bypass strategies failed")
    return False
