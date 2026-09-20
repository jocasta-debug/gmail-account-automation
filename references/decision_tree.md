# Gmail Account Creation — Decision Tree & Flow Documentation

## Overview

This document describes the complete decision flow for automated Gmail account creation, including all fallback paths, decision points, and how the system behaves with or without SMS/phone verification capabilities.

---

## Decision Tree

```
┌─────────────────────────────────────────────────────────────────┐
│                    START: Campaign Runner                        │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ FOR EACH account in accounts:                               │ │
│  │   ┌───────────────────────────────────────────────────────┐ │ │
│  │   │ INITIALIZE THREAD                                       │ │ │
│  │   │  ├─ Select random identity (name, DOB, gender)        │ │ │
│  │   │  ├─ Select proxy from pool (or none)                   │ │ │
│  │   │  ├─ Generate browser fingerprint (Canvas, WebGL,      │ │ │
│  │   │  │   Audio, UA, viewport, timezone, locale)           │ │ │
│  │   │  ├─ Launch headless Chromium                           │ │ │
│  │   │  └─ Create incognito context with fingerprint inject  │ │ │
│  │   └───────────────────────────────────────────────────────┘ │ │
│  │                                                              │ │
│  │   ┌─ STEP 1: Navigate to Google Signup ───────────────────┐ │ │
│  │   │  URL: accounts.google.com/signup/v2                    │ │ │
│  │   │  Screenshot: 01_signup_entry.png                       │ │ │
│  │   └────────────────────────────────────────────────────────┘ │ │
│  │                                                              │ │
│  │   ┌─ STEP 2: Fill Personal Info ───────────────────────────┐ │ │
│  │   │  Decision: Can we find firstName input?                │ │ │
│  │   │  ├─ YES → human_type first name                        │ │ │
│  │   │  └─ NO  → Skip (use empty name)                       │ │ │
│  │   │  Decision: Can we find lastName input?                 │ │ │
│  │   │  ├─ YES → human_type last name                         │ │ │
│  │   │  └─ NO  → Skip (use empty name)                       │ │ │
│  │   │  Action: Click "Next" button                          │ │ │
│  │   │  │                                                     │ │ │
│  │   │  │  Fallback chain for Next button:                    │ │ │
│  │   │  │  1. button:has-text('Next')                         │ │ │
│  │   │  │  2. div[role='button']:has-text('Next')             │ │ │
│  │   │  │  3. div[data-primary-action-label='Next']           │ │ │
│  │   │  │  4. JS evaluate click (last resort)                 │ │ │
│  │   │  │                                                     │ │ │
│  │   │  │  Verification: If page didn't advance, retry with   │ │ │
│  │   │  │  JS click.                                            │ │ │
│  │   │  Screenshot: 02_personal_info_filled.png              │ │ │
│  │   └────────────────────────────────────────────────────────┘ │ │
│  │                                                              │ │
│  │   ┌─ STEP 3: Birthday & Gender ────────────────────────────┐ │ │
│  │   │  ┌─ MONTH ────────────────────────────────────────────┐ │ │
│  │   │  │  Google uses CUSTOM ARIA COMBOBOX (not <select>): │ │ │
│  │   │  │  div[role="combobox"] → ul[aria-label="Month"]     │ │ │
│  │   │  │                                                     │ │ │
│  │   │  │  Strategy:                                          │ │ │
│  │   │  │  1. Enumerate all div[role="combobox"] elements    │ │ │
│  │   │  │  2. Match by aria-labelledby → label text          │ │ │
│  │   │  │     (e.g., "Month" → trigger #0)                   │ │ │
│  │   │  │  3. Click trigger → listbox opens                  │ │ │
│  │   │  │  4. Wait for ul[aria-label="Month"] visible        │ │ │
│  │   │  │  5. Click li:has-text("September")                 │ │ │
│  │   │  │                                                     │ │ │
│  │   │  │  FALLBACK:                                         │ │ │
│  │   │  │  ├─ If trigger not visible → wait + retry          │ │ │
│  │   │  │  ├─ If listbox not visible → wait + retry          │ │ │
│  │   │  │  └─ If option not found → click first li (fallback)│ │ │
│  │   │  └────────────────────────────────────────────────────┘ │ │
│  │   │  ┌─ DAY ──────────────────────────────────────────────┐ │ │
│  │   │  │  Selectors (in order):                             │ │ │
│  │   │  │  1. input[name='day']                              │ │ │
│  │   │  │  2. input[aria-label*='day' i]                    │ │ │
│  │   │  │  3. input[aria-label*='Day' i]                    │ │ │
│  │   │  │  4. input[placeholder*='Day']                      │ │ │
│  │   │  │  5. Click + keyboard.type (last resort)            │ │ │
│  │   │  └────────────────────────────────────────────────────┘ │ │
│  │   │  ┌─ YEAR ─────────────────────────────────────────────┐ │ │
│  │   │  │  Same selector chain as Day, but for year.         │ │ │
│  │   │  └────────────────────────────────────────────────────┘ │ │
│  │   │  ┌─ GENDER ───────────────────────────────────────────┐ │ │
│  │   │  │  Same ARIA combobox strategy as Month:             │ │ │
│  │   │  │  1. Find combobox with aria-labelledby → "Gender" │ │ │
│  │   │  │  2. Click trigger → ul[aria-label="Gender"] opens │ │ │
│  │   │  │  3. Click li:has-text("Male"/"Female"/...)        │ │ │
│  │   │  │  FALLBACK: Click first li in listbox              │ │ │
│  │   │  └────────────────────────────────────────────────────┘ │ │
│  │   │  Action: Click "Next" (same fallback chain)           │ │ │
│  │   │  Screenshot: 04_birthday_gender_filled.png            │ │ │
│  │   └────────────────────────────────────────────────────────┘ │ │
│  │                                                              │ │
│  │   ┌─ STEP 4: Email / Username ──────────────────────────────┐ │ │
│  │   │  Decision: Does page show suggested emails?            │ │ │
│  │   │  ├─ YES (div[role='button']:has-text('@gmail'))       │ │ │
│  │   │  │  → Click suggested email                           │ │ │
│  │   │  │  → Extract email from input[type='email']          │ │ │
│  │   │  └─ NO → Create custom email                          │ │ │
│  │   │     ┌─ Find email input ─────────────────────────────┐ │ │
│  │   │     │  Selectors (in order):                         │ │ │
│  │   │     │  1. input[type='email']                         │ │ │
│  │   │     │  2. input[name='Username']                      │ │ │
│  │   │     │  3. input[aria-label*='Gmail address' i]       │ │ │
│  │   │     │  4. input[aria-label*='email' i]               │ │ │
│  │   │     │  5. input[aria-label*='Email' i]               │ │ │
│  │   │     │  6. input[type='text'][aria-label*='username'] │ │ │
│  │   │     │  7. input[type='text']:not([aria-label*gender])│ │ │
│  │   │     │  8. JS fallback: querySelector('input[name      │ │ │
│  │   │     │     ="Username"]') → focus()                    │ │ │
│  │   │     └─────────────────────────────────────────────────┘ │ │
│  │   │     Action: human_type username, click Next            │ │ │
│  │   │     Screenshot: 05_email_selected.png                 │ │ │
│  │   └────────────────────────────────────────────────────────┘ │ │
│  │                                                              │ │
│  │   ┌─ STEP 5: Password ───────────────────────────────────────┐ │ │
│  │   │  Generate random 14-char password                     │ │ │
│  │   │  Fill: input[type='password'][aria-label='Password']  │ │ │
│  │   │  Fill: input[type='password'][aria-label='Confirm']   │ │ │
│  │   │  Click "Next"                                         │ │ │
│  │   │  Screenshot: 06_password_set.png                      │ │ │
│  │   └────────────────────────────────────────────────────────┘ │ │
│  │                                                              │ │
│  │   ┌─ STEP 6: CAPTCHA Check ────────────────────────────────┐ │ │
│  │   │  Decision: Is reCAPTCHA present?                      │ │ │
│  │   │  ├─ YES → Solve via 2Captcha API                     │ │ │
│  │   │  │  1. Detect site key from page                     │ │ │
│  │   │  │  2. Submit to 2Captcha                            │ │ │
│  │   │  │  3. Poll for solution                              │ │ │
│  │   │  │  4. Submit g-recaptcha-response                   │ │ │
│  │   │  │  5. Screenshot: 07_captcha_solved.png             │ │ │
│  │   │  └─ NO → Screenshot: 07_no_captcha.png               │ │ │
│  │   └────────────────────────────────────────────────────────┘ │ │
│  │                                                              │ │
│  │   ┌─ STEP 7: Phone Verification / QR Code ──────────────────┐ │ │
│  │   │  Detect page type from body text:                     │ │ │
│  │   │  ┌─ QR CODE SCREEN ──────────────────────────────────┐ │ │
│  │   │  │  Triggered when: "qr code" or "scan" in body     │ │ │
│  │   │  │  (typically on mobile/desktop without trusted     │ │ │
│  │   │  │   device)                                          │ │ │
│  │   │  │  Strategy:                                         │ │ │
│  │   │  │  1. Screenshot the QR code                          │ │ │
│  │   │  │  2. Send to online QR decode API                   │ │ │
│  │   │  │  3. Extract verification URL from decoded text     │ │ │
│  │   │  │  4. Open verification URL in browser               │ │ │
│  │   │  │  5. Complete verification flow                     │ │ │
│  │   │  │                                                     │ │ │
│  │   │  │  PREVENTIVE STRATEGY (preferred):                   │ │ │
│  │   │  │  Use mobile UA + viewport + platform emulation     │ │ │
│  │   │  │  to AVOID the QR wall entirely.                    │ │ │
│  │   │  │  If that fails, fall back to QR decode.            │ │ │
│  │   │  └────────────────────────────────────────────────────┘ │ │
│  │   │  ┌─ PHONE VERIFICATION SCREEN ───────────────────────┐ │ │
│  │   │  │  Triggered when: "phone number"/"mobile"/         │ │ │
│  │   │  │  "verify" in body text.                           │ │ │
│  │   │  │                                                     │ │ │
│  │   │  │  Decision: SMS/phone API available?               │ │ │
│  │   │  │  ├─ YES (5sim key configured) →                   │ │ │
│  │   │  │  │  1. Buy phone number via 5sim API              │ │ │
│  │   │  │  │  2. Enter number on Google form                │ │ │
│  │   │  │  │  3. Click Next/Verify                           │ │ │
│  │   │  │  │  4. Poll 5sim API for SMS code                 │ │ │
│  │   │  │  │  5. Enter SMS code                              │ │ │
│  │   │  │  │  6. Submit → account created                   │ │ │
│  │   │  │  │                                                   │ │ │
│  │   │  │  ├─ NO (no SMS key) →                            │ │ │
│  │   │  │  │  1. Look for "Skip" button                     │ │ │
│  │   │  │  │  2. Try: "Skip", "No thanks", "Do not add",   │ │ │
│  │   │  │  │     "Skip for now", "Maybe later"              │ │ │
│  │   │  │  │  3. If skip found → click → continue          │ │ │
│  │   │  │  │  4. If no skip → account may be restricted     │ │ │
│  │   │  │  │                                                   │ │ │
│  │   │  │  └─ SMS KEY PRESENT but buy fails →              │ │ │
│  │   │  │    Fall back to skip button attempt               │ │ │
│  │   │  └────────────────────────────────────────────────────┘ │ │
│  │   │  Screenshot: 08_phone_qr_check.png                    │ │ │
│  │   └────────────────────────────────────────────────────────┘ │ │
│  │                                                              │ │
│  │   ┌─ STEP 8: Final Wait & Result ───────────────────────────┐ │ │
│  │   │  Wait 5-12 seconds for account creation to complete   │ │ │
│  │   │  Screenshot: 09_final_result.png                     │ │ │
│  │   │  Decision: Are we on a welcome/success page?         │ │ │
│  │   │  ├─ YES → Account created ✅                         │ │ │
│  │   │  ├─ ERROR indicators → Account rejected ❌           │ │ │
│  │   │  └─ UNKNOWN → Email may be valid (uncertain)         │ │ │
│  │   └────────────────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## With SMS/Phone API (5sim) — Full Flow

When `FIVE_SIM_API_KEY` is configured in `.env`:

```
Phone verification screen appears
         │
         ▼
  ┌──────────────────────┐
  │ Buy number via 5sim  │
  │ POST /v1 buy_number  │
  │ → returns +1 (206)…  │
  └──────────┬───────────┘
             │
             ▼
  ┌──────────────────────┐
  │ Type number into     │
  │ Google's phone input │
  │ Click Next/Verify    │
  └──────────┬───────────┘
             │
             ▼
  ┌──────────────────────┐
  │ Poll 5sim for SMS:   │
  │ GET /v1 check_number │
  │ Retry every 10s      │
  │ Timeout: 90s         │
  └──────────┬───────────┘
             │
             ▼
  ┌──────────────────────┐
  │ SMS arrives → code   │
  │ Enter code → Submit  │
  │ Account created! ✅  │
  └──────────────────────┘
```

**Country selection for cost optimization:**
- Canada ($0.11) — best value for Gmail (North American, English locale, high trust)
- Indonesia ($0.08) — cheapest but riskier for Gmail
- Argentina ($0.14), Colombia ($0.16) — mid-range options

---

## Without SMS — Skip Flow

When no SMS API key is configured:

```
Phone verification screen appears
         │
         ▼
  ┌──────────────────────┐
  │ Try skip buttons:    │
  │ 1. "Skip"            │
  │ 2. "No, thanks"      │
  │ 3. "Do not add"      │
  │ 4. "Skip for now"    │
  │ 5. "Maybe later"     │
  └──────────┬───────────┘
             │
             ▼
    ┌────────┴────────┐
    │  Skip found?    │
    ├─────────────────┤
    │ YES → Click →   │
    │     Continue    │
    │                 │
    │ NO → Account    │
    │     may be      │
    │     restricted  │
    └─────────────────┘
```

Without phone verification, Google may:
- Allow the account but with restrictions (no Google Pay, limited storage)
- Require phone verification later when the account is used
- Block the account creation entirely

---

## Proxy Decision Flow

```
┌────────────────────────────────────┐
│  PROXY POOL EMPTY?                 │
├────────────────────────────────────┤
│ YES → Run without proxy           │
│       ⚠️ Higher detection risk    │
│       ⚠️ Google sees home IP      │
│                                    │
│ NO → Use next proxy from pool     │
│       ├─ Residential/mobile ✓     │
│       │  Best: blends with real   │
│       │  user traffic             │
│       ├─ Datacenter ✗            │
│       │  Google flags these      │
│       │  immediately             │
│       └─ Free proxy ✗            │
│          All dead/stale in tests  │
└────────────────────────────────────┘
```

---

## CAPTCHA Decision Flow

```
┌────────────────────────────────────┐
│  reCAPTCHA DETECTED?              │
├────────────────────────────────────┤
│ NO → Continue (most runs)         │
│                                    │
│ YES → Check 2Captcha key          │
│       ├─ Key configured →         │
│       │  Solve via API            │
│       │  Cost: ~$2-3 per 1000    │
│       │                           │
│       └─ No key →                │
│          Cannot solve            │
│          Account likely fails    │
└────────────────────────────────────┘
```

---

## Mobile vs Desktop Mode

```
┌────────────────────────────────────┐
│  MOBILE MODE? (default: YES)      │
├────────────────────────────────────┤
│ YES → Mobile UA + viewport        │
│       ├─ Pros:                   │
│       │  • May avoid QR code     │
│       │  • Looks like real phone │
│       │  • Different signup flow │
│       │                           │
│       └─ Cons:                  │
│          • Gender UI differs    │
│          • Email step differs   │
│          • Some fields behave   │
│            differently          │
│                                    │
│ NO (desktop) → Desktop UA        │
│       ├─ Pros:                  │
│       │  • More stable selectors│
│       │  • Easier to debug      │
│       │  • Known working flow   │
│       │                           │
│       └─ Cons:                  │
│          • QR code wall likely  │
│          • Higher scrutiny      │
└────────────────────────────────────┘
```

---

## Error Recovery & Retry

```
Account creation fails
         │
         ▼
  ┌──────────────────────┐
  │ Check error type:    │
  │                      │
  │ • Username taken →  │
  │   Generate new      │
  │   username + retry  │
  │                      │
  │ • CAPTCHA failed → │
  │   Retry (different  │
  │   fingerprint)      │
  │                      │
  │ • Phone required → │
  │   Need SMS API or   │
  │   skip button       │
  │                      │
  │ • QR code →        │
  │   Decode + complete │
  │                      │
  │ • Generic error →  │
  │   Retry with new   │
  │   proxy + fingerprint
  └──────────┬───────────┘
             │
             ▼
  ┌──────────────────────┐
  │ MAX_RETRIES = 3     │
  │ If exhausted →     │
  │ mark as failed      │
  └──────────────────────┘
```

---

## File Reference

| File | Purpose |
|------|---------|
| `main.py` | Entry point, argument parsing, campaign orchestration |
| `src/campaign.py` | Multi-threaded runner, thread management |
| `src/signup.py` | Full signup flow orchestrator (this decision tree) |
| `src/birthday_gender.py` | ARIA combobox dropdown handling |
| `src/fingerprint.py` | Canvas/WebGL/Audio/UA fingerprint spoofing |
| `src/humanizer.py` | Human-like typing, mouse, scroll, pauses |
| `src/captcha.py` | 2Captcha reCAPTCHA v2 integration |
| `src/sms.py` | 5sim SMS API (buy number + poll for code) |
| `src/qr_bypass.py` | QR code detection + online decode + verification |
| `src/config.py` | Configuration, proxy pool, name pool, API keys |
