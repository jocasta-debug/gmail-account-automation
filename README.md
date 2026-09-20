# Gmail Account Creation Automation Framework
# Reverse-engineered from PVACreator's QR-code bypass approach

# ── Install ──────────────────────────────────────────────────────────────────
#   pip3 install playwright 2captcha-python pyzbar Pillow requests
#   python3 -m playwright install chromium
#   (zbar system lib not required — we use an online QR decode API)

# ── Configure ────────────────────────────────────────────────────────────────
#   Edit .env with your keys and proxy list
#   Edit config/names.json if you want custom name pools

# ── Run ──────────────────────────────────────────────────────────────────────
#   python3 main.py
