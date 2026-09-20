"""
2Captcha integration — solves reCAPTCHA v2 ("I'm not a robot") via the API.

Uses the `twocaptcha` Python library that's already installed.
"""

import time
import logging
from typing import Optional

from twocaptcha import TwoCaptcha

from .config import get_2captcha_key, log

solver = TwoCaptcha(get_2captcha_key())


def solve_recaptcha_v2(page, timeout: int = 120) -> Optional[str]:
    """
    Detect a reCAPTCHA v2 on the current page, solve it via 2Captcha,
    and inject the token.

    Returns the token on success, None on failure/timeout.
    """
    try:
        log.info("Checking for reCAPTCHA...")
        # Get the site key from the page
        site_key = page.evaluate(
            "()" + """=> {
                const el = document.querySelector('[data-sitekey]');
                return el ? el.dataset.sitekey : null;
            }"""
        )
        if not site_key:
            log.info("No reCAPTCHA site key found on page.")
            return None

        # Get page URL
        page_url = page.url

        log.info(f"Solving reCAPTCHA: site_key={site_key[:20]}..., url={page_url}")

        result = solver.recaptcha(
            sitekey=site_key,
            url=page_url,
            timeout=timeout,
        )

        token = result.get("code") or result.get("g-recaptcha-response")
        if token:
            log.info(f"reCAPTCHA solved, token received ({len(token)} chars)")
            # Inject token into the page
            page.evaluate(
                "(token) => {"
                "  const el = document.querySelector('[name=\"g-recaptcha-response\"]');"
                "  if (el) el.textContent = token;"
                "  document.getElementById('g-recaptcha-response')?.textContent = token;"
                "}",
                token,
            )
            # Also click any "Verify" / submit button that may appear
            time.sleep(1)
            return token
        else:
            log.error(f"2Captcha returned no token: {result}")
            return None

    except Exception as e:
        log.error(f"2Captcha solve failed: {e}")
        return None


def solve_captcha_generic(page, timeout: int = 120) -> bool:
    """
    Try to detect and solve whatever CAPTCHA is on the page.
    Falls back to reCAPTCHA v2 detection.
    """
    token = solve_recaptcha_v2(page, timeout)
    return token is not None
