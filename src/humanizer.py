"""
Human-like interaction emulator.
Variable-timing typing, random mouse moves, scrolling, and pauses
to avoid rigid bot-behavior detection.
"""

import time
import random
import math
from typing import Optional


# ── Typing ───────────────────────────────────────────────────────────────────

def human_type(page, target, text: str, base_delay: float = 0.08,
               jitter: float = 0.04, mistake_prob: float = 0.03,
               mistake_fix_delay: float = 0.3) -> None:
    """
    Type `text` into the element matched by `selector` (str) or `target` (Locator).
    """
    if isinstance(target, str):
        el = page.locator(target).first
    else:
        el = target  # already a Locator

    el.wait_for(state="visible", timeout=10000)
    el.click()

    for ch in text:
        # mistake?
        if random.random() < mistake_prob:
            typo_char = random.choice("abcdefghijklmnopqrstuvwxyz")
            page.keyboard.type(typo_char)
            time.sleep(mistake_fix_delay)
            page.keyboard.press("Backspace")
            time.sleep(random.uniform(0.05, 0.15))

        page.keyboard.type(ch)
        delay = base_delay + random.uniform(-jitter, jitter)
        time.sleep(max(0.01, delay))

    # occasional extra pause at end (thinking)
    time.sleep(random.uniform(0.1, 0.4))


def human_type_into(page, selector: str, text: str, **kwargs) -> None:
    """Convenience: focus element then type."""
    human_type(page, selector, text, **kwargs)


# ── Mouse movement ───────────────────────────────────────────────────────────

def human_move_to(page, x: Optional[int] = None, y: Optional[int] = None,
                  duration: float = 0.3) -> None:
    """Move mouse to a point with a curved, non-linear path."""
    viewport = page.viewport_size
    if viewport is None:
        return
    vw, vh = viewport["width"], viewport["height"]

    if x is None:
        x = random.randint(int(vw * 0.1), int(vw * 0.9))
    if y is None:
        y = random.randint(int(vh * 0.1), int(vh * 0.9))

    steps = max(3, int(duration / 0.03))
    start_x = random.randint(int(vw * 0.4), int(vw * 0.6))
    start_y = random.randint(int(vh * 0.4), int(vh * 0.6))

    for i in range(steps + 1):
        t = i / steps
        # ease-in-out + random wobble
        xt = x + int(math.sin(t * math.pi * 2) * random.uniform(-3, 3))
        yt = y + int(math.cos(t * math.pi * 1.5) * random.uniform(-3, 3))
        page.mouse.move(xt, yt)
        time.sleep(duration / steps)


def human_click(page, selector: str, pre_move: bool = True) -> None:
    """Click with human-like mouse movement before."""
    if pre_move:
        human_move_to(page)
        time.sleep(random.uniform(0.05, 0.15))
    el = page.locator(selector).first
    el.wait_for(state="visible", timeout=10000)
    el.click()


# ── Scrolling ────────────────────────────────────────────────────────────────

def human_scroll(page, times: int = 2) -> None:
    """Scroll the page a couple times, like a user checking content."""
    for _ in range(times):
        page.evaluate("window.scrollBy(0, window.innerHeight * 0.5)")
        time.sleep(random.uniform(0.3, 0.8))
    page.evaluate("window.scrollTo(0, 0)")


# ── Random pause (thinking / reading delay) ─────────────────────────────────

def human_pause(min_s: float = 0.5, max_s: float = 2.5) -> None:
    time.sleep(random.uniform(min_s, max_s))


def human_pause_long(min_s: float = 2.0, max_s: float = 8.0) -> None:
    time.sleep(random.uniform(min_s, max_s))


# ── Pre-session warm-up ─────────────────────────────────────────────────────
# Visit a few benign sites to build browser history / cookies before
# hitting Google — mirrors what the GitHub tools call "session warming".

WARMUP_URLS = [
    "https://www.wikipedia.org",
    "https://www.bbc.com",
    "https://www.youtube.com",
    "https://www.bing.com",
]


def warm_up_browser(page, count: int = 2) -> None:
    """Visit 1-2 random benign sites to look like a real user's browser."""
    random.shuffle(WARMUP_URLS)
    for url in WARMUP_URLS[:count]:
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            human_scroll(page, times=1)
            human_pause(0.5, 1.5)
        except Exception:
            pass
