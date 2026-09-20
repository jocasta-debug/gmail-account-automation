"""
5sim SMS verification provider.
Purchase a virtual number for Google, poll for the SMS code, return it.

API:
  - Buy:   GET https://5sim.net/v1/user/buy/activation/<country>/<operator>/<service>
           Headers: Authorization: Bearer <api_key>
  - Status + SMS: GET https://5sim.net/v1/user/check/<id>
           Headers: Authorization: Bearer <api_key>
           Response: {"status": "READY", "sms": [{"text": "Code 12345", ...}]}
           or {"status": "TRY NEXT", ...} or {"status": "DENIED", ...}

We pick the first available operator automatically by trying 'any' or
iterating common operator slugs for the target country.
"""

import time
import random
import requests
from typing import Optional, Tuple

from .config import get_5sim_key, SMS_COUNTRY, SMS_SERVICE, log


FIVE_SIM_BASE = "https://5sim.net/v1/user"


def _get_headers():
    """Lazy headers builder — only called when 5sim key is available."""
    key = get_5sim_key()
    return {
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
    }


# Common operator slugs per country (best-effort)
OPERATORS_BY_COUNTRY = {
    "usa": [" Metro PCS", " T-Mobile", " Verizon", " Cricket", " AT&T", " Mint"],
    "uk": [" Vodafone", " Orange", " Three", " O2", " Tesco"],
    "canada": [" Fido", " Chatr", " Koodo", " Virgin", " Speakout"],
    "germany": [" Vodafone", " O2", " Telekom"],
}


def _available_operators(country: str) -> list[str]:
    return OPERATORS_BY_COUNTRY.get(country.lower(), [" any"])


def buy_number(country: str = None, service: str = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Purchase a number from 5sim for Google verification.
    Returns (number, order_id) or (None, None) on failure / no key.
    """
    key = get_5sim_key()
    if not key:
        log.warning("5sim: no API key configured — skipping number purchase")
        return None, None
    country = (country or SMS_COUNTRY).lower()
    service = (service or SMS_SERVICE).lower()

    operators = _available_operators(country)

    last_err = None
    for op in operators:
        op_slug = op.strip().lower().replace(" ", "")
        url = f"{FIVE_SIM_BASE}/buy/activation/{country}/{op_slug}/{service}"
        try:
            resp = requests.get(url, headers=_get_headers(), timeout=15)
            data = resp.json()
            if data.get("status") == "OK":
                number = data.get("phone") or data.get("number", "")
                order_id = str(data.get("id", ""))
                if number and order_id:
                    log.info(f"5sim: bought number {number} (order {order_id}) via {op_slug}")
                    return number, order_id
            last_err = data
        except Exception as e:
            last_err = str(e)
            log.debug(f"5sim buy failed for operator {op_slug}: {e}")

    log.error(f"5sim: could not buy number for {country}/{service}. Last: {last_err}")
    return None, None


def get_sms_code(order_id: str, timeout: int = 60, poll_interval: float = 4.0) -> Optional[str]:
    """
    Poll 5sim for the SMS code for a given order.
    Returns the code string (e.g. '847293') or None.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            url = f"{FIVE_SIM_BASE}/check/{order_id}"
            resp = requests.get(url, headers=_get_headers(), timeout=10)
            data = resp.json()

            status = data.get("status", "").upper()

            if status == "READY":
                sms_list = data.get("sms") or []
                for sms in sms_list:
                    text = sms.get("text", "")
                    # Try to extract a numeric code from the message
                    code = _extract_code(text)
                    if code:
                        log.info(f"5sim: got SMS code {code} for order {order_id}")
                        return code
                # SMS received but no code found yet — keep polling
                log.debug(f"5sim: SMS received but no code extracted: {text}")

            elif status in ("TRY NEXT", "NO BALANCE", "CANCELLED", "DENIED", "EXPIRED"):
                log.warning(f"5sim order {order_id} status: {status}")
                break

            else:
                log.debug(f"5sim: polling order {order_id}, status={status}")

        except Exception as e:
            log.debug(f"5sim poll error: {e}")

        time.sleep(poll_interval)

    log.error(f"5sim: timed out waiting for SMS code for order {order_id}")
    return None


def _extract_code(text: str) -> Optional[str]:
    """Extract a 4-8 digit numeric code from SMS text."""
    import re
    # Look for common patterns: "Your code is 123456", "123456 is your code",
    # just a number, etc.
    m = re.search(r"\b(\d{4,8})\b", text)
    if m:
        return m.group(1)
    return None


# ── High-level: get a verified Google SMS code ──────────────────────────────

def get_google_verification_code(country: str = None, timeout: int = 90) -> Optional[str]:
    """
    Full flow: buy a number for Google → wait for SMS → return the code.
    Returns None if anything fails.
    """
    number, order_id = buy_number(country, "google")
    if not order_id:
        return None
    return get_sms_code(order_id, timeout=timeout)
