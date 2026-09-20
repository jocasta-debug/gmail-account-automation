"""
Configuration loader.
Reads .env (Python-dotenv-style, no external dependency) and config files.
"""

import os
import json
import random
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"


def _parse_env(path: Path) -> dict:
    """Parse a simple KEY=VALUE .env file (no quoting, no sections)."""
    result = {}
    if not path.exists():
        return result
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            result[key.strip()] = value.strip()
    return result


ENV = _parse_env(BASE_DIR / ".env")


def get(key: str, default=None):
    return ENV.get(key, default)


def required(key: str) -> str:
    value = get(key)
    if not value:
        raise EnvironmentError(f"Missing required config: {key} (set it in .env)")
    return value


# ── Derived config ──────────────────────────────────────────────────────────

TWOCAPTCHA_API_KEY = get("TWOCAPTCHA_API_KEY", "")
FIVE_SIM_API_KEY = get("FIVE_SIM_API_KEY", "")
THREADS = int(get("THREADS", "3"))
SMS_COUNTRY = get("SMS_COUNTRY", "usa")
SMS_SERVICE = get("SMS_SERVICE", "google")
THREAD_STAGGER = float(get("THREAD_STAGGER", "5"))
MAX_RETRIES = int(get("MAX_RETRIES", "2"))
PROXY_FILE = CONFIG_DIR / get("PROXIES_FILE", "config/proxies.txt")


# ── Proxy pool ──────────────────────────────────────────────────────────────

class ProxyPool:
    """Round-robin proxy allocator.  Returns None if pool is empty."""

    def __init__(self, path: Path):
        self.proxies = []
        if path.exists():
            for line in path.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    self.proxies.append(line)
        self._idx = 0

    def next(self) -> Optional[str]:
        if not self.proxies:
            return None
        proxy = self.proxies[self._idx % len(self.proxies)]
        self._idx += 1
        return proxy

    def size(self) -> int:
        return len(self.proxies)


PROXY_POOL = ProxyPool(PROXY_FILE)


# ── Name pool ───────────────────────────────────────────────────────────────

class NamePool:
    def __init__(self, path: Path):
        with open(path) as f:
            data = json.load(f)
        self.first = data["first_names"]
        self.last = data["last_names"]

    def random_identity(self) -> dict:
        first = random.choice(self.first)
        last = random.choice(self.last)
        year = random.randint(1985, 2000)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        return {
            "first_name": first,
            "last_name": last,
            "birthday": f"{month:02d}{day:02d}{year}",
            "gender": random.choice(["male", "female"]),
        }


NAME_POOL = NamePool(CONFIG_DIR / "names.json")


# ── 2Captcha ────────────────────────────────────────────────────────────────

def get_2captcha_key() -> str:
    return required("TWOCAPTCHA_API_KEY")


# ── 5sim ────────────────────────────────────────────────────────────────────

def get_5sim_key() -> str:
    return required("FIVE_SIM_API_KEY")


def has_5sim_key() -> bool:
    """Non-raising check — returns True if key is configured."""
    return bool(get("FIVE_SIM_API_KEY"))


# ── Logging helper ───────────────────────────────────────────────────────────

import logging

log = logging.getLogger("gmail_automation")
log.setLevel(logging.INFO)

_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(threadName)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
))
log.addHandler(_handler)
