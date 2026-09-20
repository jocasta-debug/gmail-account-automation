# Gmail Account Creation Automation Framework

Reverse-engineered from PVACreator's QR-code bypass approach

🔗 GitHub: https://github.com/jocasta-debug/gmail-account-automation

## Install

```bash
pip3 install playwright 2captcha-python pyzbar Pillow requests
python3 -m playwright install chromium
```

(zbar system lib not required — we use an online QR decode API)

## Configure

- Edit `.env` with your keys and proxy list
- Edit `config/names.json` if you want custom name pools

## Run

```bash
python3 main.py --accounts N --threads N --stagger S
```

## What it does

- **Fingerprint spoofing**: Canvas/WebGL/Audio fingerprint noise, UA rotation, navigator property hiding
- **Custom ARIA dropdowns**: Google uses `div[role="combobox"]` + `ul[aria-label="..."]` listboxes — not HTML `<select>`
- **2Captcha integration**: reCAPTCHA v2 solving
- **5sim SMS integration**: phone verification code retrieval
- **QR code bypass**: dual-strategy — preventive (mobile UA/viewport) + reactive (screenshot → API decode → programmatic completion)
- **Humanizer**: variable-timing typing, random mouse movements, scrolling
- **Multi-threaded**: configurable thread pool for parallel account creation
