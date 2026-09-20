"""
Browser fingerprint randomization.
Spoofs Canvas, WebGL, AudioContext, fonts, navigator properties,
and UA to make each account thread look like a unique real device.

Strategy (mirrors what PVACreator/blog describes):
  - Per-thread unique fingerprint (no sharedCanvas/WebGL hash across accounts)
  - Realistic UA matching the OS/platform claim
  - navigator.webdriver = undefined (hide automation flag)
  - Consistent platform/UA/architecture triplet (Google checks for mismatches)
"""

import random
import string
import hashlib
from typing import Any


# ── User-Agent pool ──────────────────────────────────────────────────────────
# Mix of Windows + macOS Chrome UAs.  Android/mobile UAs available
# for the mobile-endpoint emulation path (see mobile_fingerprint()).

DESKTOP_UAS = [
    # Windows 10 / 11 Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    # macOS Chrome
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

MOBILE_UAS = [
    # Android Chrome
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
    # iOS (Safari — used for mobile WebView emulation)
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1",
]


def pick_ua(mobile: bool = False) -> str:
    pool = MOBILE_UAS if mobile else DESKTOP_UAS
    return random.choice(pool)


# ── Canvas fingerprint noise ─────────────────────────────────────────────────
# Add a deterministic-noise transform so the Canvas hash differs per thread
# but stays stable for the lifetime of that thread (Google may re-check).

def _canvas_noise_fn() -> str:
    """Return JavaScript snippet that adds per-instance canvas noise."""
    seed = "".join(random.choices(string.ascii_letters + string.digits, k=16))
    return f"""
(function() {{
    const seed = {seed!r};
    const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function(type, quality) {{
        const ctx = this.getContext('2d');
        if (ctx && type === 'image/png') {{
            const imgData = ctx.getImageData(0, 0, this.width, this.height);
            for (let i = 0; i < imgData.data.length; i += 4) {{
                imgData.data[i] = (imgData.data[i] + (seed.charCodeAt(i % seed.length) % 5)) % 256;
            }}
            ctx.putImageData(imgData, 0, 0);
        }}
        return originalToDataURL.call(this, type, quality);
    }};
}})();
    """.strip()


# ── WebGL vendor/renderer spoofing ──────────────────────────────────────────

WEBGL_SPOOF = """
(function() {
    const fakeVendor = 'Google Inc. (Google)';
    const fakeRenderer = 'Google Chrome';
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(param) {
        if (param === 37445) return fakeVendor;  // VENDOR
        if (param === 37446) return fakeRenderer; // RENDERER
        return getParameter.call(this, param);
    };
})();
"""


# ── AudioContext fingerprint noise ──────────────────────────────────────────

AUDIO_NOISE = """
(function() {
    const origCreate = AudioContext.prototype.createOscillator;
    AudioContext.prototype.createOscillator = function() {
        const osc = origCreate.call(this);
        const origFreq = osc.frequency.setValueAtTime.bind(osc.frequency);
        osc.frequency.setValueAtTime = function(val, time) {
            return origFreq((val + 0.0001) % 20000, time);
        };
        return osc;
    };
})();
"""


# ── Navigator property fixes ────────────────────────────────────────────────

NAVIGATOR_FIXES = """
(function() {
    // Hide webdriver flag
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

    // Plugins — fake a realistic set
    Object.defineProperty(navigator, 'plugins', {
        get: () => [
            { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
            { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
            { name: 'Native Client', filename: 'internal-nacl-plugin' },
        ],
    });

    // Languages
    Object.defineProperty(navigator, 'languages', {
        get: () => ['en-US', 'en'],
    });
})();
"""


# ── Permissions spoofing ────────────────────────────────────────────────────

PERMISSIONS_FIX = """
(function() {
    const origQuery = navigator.permissions.query;
    navigator.permissions.query = function(params) {
        return origQuery.call(navigator.permissions, params).then(result => {
            if (params.name === 'notifications') {
                result.state = 'prompt';
            }
            return result;
        });
    };
})();
"""


# ── Screen / viewport ───────────────────────────────────────────────────────

SCREEN_SIZES = [
    {"width": 1920, "height": 1080},
    {"width": 1920, "height": 1200},
    {"width": 1680, "height": 1050},
    {"width": 1440, "height": 900},
    {"width": 2560, "height": 1440},
    {"width": 1366, "height": 768},
]


def random_screen() -> dict:
    return random.choice(SCREEN_SIZES)


# ── Timezone / locale consistency ───────────────────────────────────────────

def random_timezone() -> str:
    zones = [
        "America/New_York", "America/Chicago", "America/Denver",
        "America/Los_Angeles", "Europe/London", "Europe/Paris",
        "Europe/Berlin", "Asia/Tokyo", "Australia/Sydney",
    ]
    return random.choice(zones)


# ── Build per-thread inject script ──────────────────────────────────────────

def build_inject_script(mobile: bool = False) -> str:
    """Return a single JS string that spoofs everything for one thread."""
    return "\n".join([
        _canvas_noise_fn(),
        WEBGL_SPOOF,
        AUDIO_NOISE,
        NAVIGATOR_FIXES,
        PERMISSIONS_FIX,
    ])


# ── Mobile fingerprint profile ──────────────────────────────────────────────
# Used for the mobile-endpoint emulation path: UA + viewport + platform
# all claim mobile, so Google's risk engine may route through the less-strict
# mobile verification matrix instead of the desktop QR wall.

def mobile_fingerprint() -> dict:
    return {
        "user_agent": random.choice(MOBILE_UAS),
        "viewport": {"width": 390, "height": 844},  # iPhone-ish
        "platform": "Linux armv8l",
        "mobile": True,
        "is_mobile": True,
        "is_tablet": False,
        "device_scale_factor": 3,
        "has_touch": True,
        "timezone": random.choice([
            "America/New_York", "America/Chicago", "America/Denver",
            "America/Los_Angeles",
        ]),
    }


def desktop_fingerprint() -> dict:
    screen = random_screen()
    return {
        "user_agent": pick_ua(mobile=False),
        "viewport": {"width": screen["width"], "height": screen["height"]},
        "platform": "Win32",
        "mobile": False,
        "is_mobile": False,
        "is_tablet": False,
        "device_scale_factor": random.choice([1, 1.25, 1.5]),
        "has_touch": False,
        "timezone": random_timezone(),
    }
