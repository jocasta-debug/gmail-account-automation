# Gmail QR Code Bypass — External Playbook

*Compiled from video walkthroughs, community reports, and reverse-engineered vendor claims.*

**Purpose:** Catalog the known external bypass methods for Google's QR-code verification during account creation, organize them as a step-by-step reference, and identify what each method depends on.

**Scope:** Methods observed from public videos and community discussion as of 2026. Not exhaustive; not guaranteed; not endorsed.

---

## Method Categories at a Glance

| ID | Method | Core Idea | QR → SMS? | Tooling | Cost Signal |
|---|---|---|---|---|---|
| M1 | PVACreator commercial automation | All-in-one SaaS: proxy bind, usernames, SMS API, IMAP/2FA, app passwords, recovery email, fingerprint binding | Varies | PVACreator + DaisySMS + proxy | Paid SaaS + SMS cost |
| M2 | TCP-fingerprint spoof + antidetect browser | Proxy spoofs TCP fingerprint as iOS; antidetect browser profile set to macOS Safari → Google reads "Mac on iPhone hotspot" → SMS prompt | Yes | Voidmob or similar TCP-spoofing proxy + AdsPower/antidetect browser | Proxy cost + browser license |
| M3 | Real Android device, cellular data | Factory-reset Android → cellular data → Settings → Accounts → Add Account → Google → Create Account | Often | Physical Android phone + SIM/data | Device + data plan |
| M4 | Cloud phone platforms | Real Android environment in the cloud, per-profile unique IMEI/MAC/device model, paired with residential proxy | Often | GeeLark, DuoPlus, etc. | ~$25–50/month |
| M5 | Linux fingerprint browser + regional proxy | Linux VM with fingerprint browser, residential proxy from specific regions, language/timezone match | Sometimes | Multilogin/GoLogin on Linux + residential proxy | Proxy cost + browser license |
| M6 | Alternative Google entry points | Create account through YouTube app, Android system settings, Google Drive/Docs rather than Gmail web signup | Sometimes | Mobile device with Google apps | Device needed |
| M7 | QR decode + programmatic SMS sending | Screenshot QR → decode → extract verification URL → open on phone → phone sends SMS through carrier | No (external SMS send, not receive) | QR decode + phone with carrier connection | Device + carrier connection |
| M8 | Pre-verified / ready-made accounts | Buy accounts that were already created and verified | N/A | Marketplaces | Per-account cost, variable trust |
| M9 | Skip-button timing + low-trust-signal session | Attempt signup under conditions that may surface a "Skip" option for phone verification | Sometimes | Clean IP, fingerprint care, behavioral pacing | Variable |

---

## Detailed Step-by-Step for Each Method

### M1 — PVACreator commercial automation (as described in videos)

**Source videos:** `Bk7pGgA8TYA`, `NpskeGiFP08`, `uBov0m1E-cc`

**Claimed outcome:** Bulk Gmail accounts, "from zero to fully configured, 2FA-protected account with App Passwords and Recovery Emails ready to use."

**Steps as described:**

1. **Create a Gmail campaign** in PVACreator
2. **Bind proxies** — add checked proxies into the campaign
3. **Add usernames** — manual or software-generated random usernames
4. **Leave data empty where possible** — software auto-fills during registration
5. **Choose phone service** — configure SMS API provider (e.g., DaisySMS)
6. **Add SMS API key + select country** — video uses US numbers; country code left empty for US
7. **Enable IMAP/POP3** — fill "1" in the relevant field
8. **Enable 2-step verification** — bind a phone number to protect the account
9. **Create App Password** — required after 2FA is enabled
   - Fill in any words as the App name
   - Fill in any words as the Device name
10. **Add recovery email** — example format uses Outlook
11. **Bind browser fingerprints** — to protect accounts
12. **Run campaign** — no pausing, no manual editing
13. **Result:** account with 2FA, App Password, recovery email configured

**Dependencies:**
- PVACreator license/subscription
- Working proxy pool
- SMS API access (DaisySMS or similar)
- Recovery email accounts (example uses Outlook)
- Browser fingerprint state per account

**What this does not explicitly address in the videos:**
- How QR code is bypassed internally — the video frames it as PVACreator "smashing through" QR, but the mechanism is not shown
- Whether SMS is received normally or via QR-linked SMS sending
- How accounts behave after creation under Google review

---

### M2 — TCP fingerprint spoof + antidetect browser

**Source:** community reports / privacy discussion findings

**Claimed outcome:** SMS verification prompt rather than QR, by convincing Google the session is a mobile-device connection.

**Underlying claim:** The QR prompt is driven more by device/TCP fingerprint than by IP alone; it can trigger before JavaScript or IP scoring runs.

**Steps as described:**

1. Obtain a **clean, fresh IP** that has not been used for Gmail signups and is not flagged as proxy/VPN
   - Mobile carrier IP reported as best; residential second
2. Use a **proxy that can spoof TCP fingerprint** to look like iOS
   - Reported tool example: Voidmob (and reportedly similar providers exist)
3. Set up an **antidetect browser profile as macOS Safari**
   - Reported tool example: AdsPower
4. Initiate signup through the macOS Safari profile over the TCP-spoofed mobile proxy
5. Reported effect: Google treats the session as "Mac + iPhone hotspot" — a normal Apple behavior pattern — and issues SMS verification rather than QR

**Reported constraints from community findings:**
- Three things together, not one alone: clean IP + TCP-spoofed mobile fingerprint + antidetect macOS Safari profile
- "Clean IP" alone does not help if device signature still says Windows
- Mobile-spoofed browser alone does not help if the network layer still reads as Linux server
- WebRTC must be fully disabled, not just spoofed, to avoid exposing host OS
- Carrier-native DNS may matter; using Cloudflare/Google DNS while claiming to be an iPhone on Verizon can be inconsistent

**Dependencies:**
- TCP-fingerprint-spoofing proxy
- Antidetect browser license
- Clean IP with low signup history
- Careful fingerprint/OS/DNS consistency

---

### M3 — Real Android device, cellular data

**Source:** community guides

**Claimed outcome:** Lower-friction verification, sometimes "Skip" button or fallback to normal SMS verification.

**Steps as described:**

1. Factory-reset an Android device (or use a fresh device)
2. Connect to **cellular data**, not WiFi
3. Go to **Settings → Accounts → Add Account → Google → Create Account**
4. Complete the signup flow
5. Device-level signup is reported to be trusted more than browser signup
6. May surface "Skip" option or normal SMS verification that the device can receive

**Dependencies:**
- Real Android device
- SIM/data plan with carrier connection
- Fresh/clean device state

**Reported rationale:** Google sees a real device with a carrier connection; that is what the QR check is trying to confirm exists.

---

### M4 — Cloud phone platforms

**Source:** community guides

**Claimed outcome:** SMS verification instead of QR in many cases, using real Android environments without a physical device on hand.

**Steps as described:**

1. Use a cloud phone platform (reported examples: GeeLark, DuoPlus)
2. Each profile gets unique IMEI, MAC, device model
3. Pair profile with a residential proxy
4. Initiate account creation from within the cloud phone environment
5. May trigger SMS verification instead of QR

**Dependencies:**
- Cloud phone platform subscription (reported ~$25–50/month)
- Residential proxy
- SMS receiving capability for the verification step if SMS is triggered

---

### M5 — Linux fingerprint browser + regional proxy

**Source:** community guides

**Claimed outcome:** Sometimes falls back to SMS or "Skip" where Windows/Mac fingerprint browsers tend to force QR.

**Steps as described:**

1. Set up a Linux VM
2. Install fingerprint browser (reported examples: Multilogin, GoLogin)
3. Use a residential proxy from regions with known SMS issues (reported examples: Mongolia, Colombia)
4. Match browser language and timezone to the proxy region
5. Attempt signup
6. May surface "Skip" button or easier verification path

**Dependencies:**
- Linux VM
- Fingerprint browser license
- Residential proxy from chosen region
- Language/timezone consistency

---

### M6 — Alternative Google entry points

**Source:** community guides

**Claimed outcome:** Less aggressive verification on some entry paths; useful for small numbers of accounts.

**Steps as described:**

**Path A — YouTube app:**
1. Open YouTube app on phone
2. Tap profile icon → "Switch account"
3. Tap "+" → "Create account"
4. Fill name, birthdate, gender
5. Create Gmail address and password
6. Reportedly, phone verification may be skipped or deferred to later account settings

**Path B — Android system settings:**
1. Go to phone Settings → Accounts / Accounts and backup → Manage accounts
2. Tap "Add account" → Google
3. On sign-in screen, tap "Create account"
4. Complete process
5. Reportedly, OS-level account addition may trigger fewer aggressive checks

**Path C — other Google apps:**
- Try Google Drive, Google Docs mobile apps as alternative entry points

**Dependencies:**
- Mobile device with Google apps
- Clean device/IP context helps

**Reported notes:**
- For 2–5 accounts, manual methods may be feasible
- Phone number is often still required eventually for recovery/security, but possibly not during the bottleneck step

---

### M7 — QR decode + programmatic SMS sending

**Source:** implied by QR-code mechanism discussions

**Claimed outcome:** Handle the QR step when a phone capable of scanning and sending SMS is available.

**Steps as described:**

1. When QR code appears on desktop, do not scan it with an existing trusted Google app if the goal is to avoid linking to an existing account
2. Alternative path described in community discussions:
   - On computer: stay on the QR code screen
   - On phone: open camera, scan the QR code
   - Open the link that appears
   - An SMS draft with a code and a strange number may appear
   - Send the SMS as-is
   - Wait on computer for verification
3. This sends an SMS **through the phone's carrier connection**, not through an SMS receiving service

**Dependencies:**
- Phone with camera and carrier connection
- The phone itself must send the SMS; SMS receiving platforms cannot provide this
- This is described as mechanically impossible for SMS receiving services to help with, because the check is about proving the phone is real and connected to a carrier

**Reported notes:**
- If there is no "Choose another verification method" or "Send SMS" link on the QR screen, the session may be classified as suspicious
- No further action from the same IP/browser may work in that case

---

### M8 — Pre-verified / ready-made accounts

**Source:** community guides, vendor claims

**Claimed outcome:** Skip registration-time verification entirely by acquiring already-created accounts.

**Steps as described:**

1. Obtain pre-verified Google accounts from a supplier
2. Use or configure them as needed
3. No onboarding QR/SMS step during creation, because creation already happened

**Dependencies:**
- Supplier of pre-verified accounts
- Acceptance of account-history and trust risks

**Reported caveats:**
- Quality and reliability vary widely between suppliers
- Pre-verified accounts may already carry risk, restrictions, or history

---

### M9 — Skip-button timing + low-trust-signal session

**Source:** community guides

**Claimed outcome:** In some sessions, Google may allow skipping phone number entry entirely.

**Steps as described:**

1. Open signup in a clean context
2. Fill name, last name, date of birth
3. At phone number step, leave field empty
4. If "Skip" button appears, click it
5. If not, try a different method

**Reported factors that may help:**
- IP address reputation
- Browser fingerprint plausibility
- Behavioral pacing (slow typing, natural pauses)
- Not creating back-to-back accounts
- Session trust level

**Reported notes:**
- If trust is low, no trick may save the session
- If trust is high, verification may be minimal
- This is situational and not reliable as a standalone method

---

## What the videos do and do not show

**What the PVACreator videos show:**
- The vendor's own workflow and claimed feature set
- Proxy binding, SMS API integration, IMAP/POP3 toggle, 2FA + App Password, recovery email, fingerprint binding
- A commercial pitch for "high-quality, fully configured Gmail accounts"

**What the videos do not show:**
- The internal mechanism for QR bypass — they claim it works but do not demonstrate the bypass mechanics
- How SMS verification is actually completed for QR-triggered sessions
- Any long-term account reliability data
- Countermeasures or failure cases

**Video relevance notes:**
- `Sz2kj-XAy80` appears to be a misleading title — its content is about inserting QR codes into Gmail messages via a Chrome extension, not about bypassing account creation QR verification
- `Wbwi07kr8vI` is an incomplete extract; its title suggests a general guide, but content could not be confirmed here
- `foTVpgdN8Hc` could not be extracted; content unknown

---

## Consolidated dependency map

| Method | Needs clean IP | Needs TCP fingerprint control | Needs real/cellular device | Needs SMS receive | Needs antidetect browser | Needs cloud phone | Needs pre-verified accounts |
|---|---|---|---|---|---|---|---|
| M1 PVACreator | Yes | Not specified | Not specified | Yes (SMS API) | Not specified | No | No |
| M2 TCP spoof + antidetect | Yes | Yes | Simulated | If SMS triggered | Yes | No | No |
| M3 Real Android | Helpful | No | Yes | Yes | No | No | No |
| M4 Cloud phone | Helpful | No | Simulated | If SMS triggered | No | Yes | No |
| M5 Linux fingerprint + regional proxy | Helpful | Partial | No | If SMS triggered | Yes | No | No |
| M6 Alternative entry points | Helpful | No | Yes | Possibly | No | No | No |
| M7 QR decode + SMS send | Helpful | No | Yes | No (SMS send) | No | No | No |
| M8 Pre-verified accounts | No | No | No | No | No | No | Yes |
| M9 Skip-button timing | Helpful | No | No | No | No | No | No |

---

## Observations on overlap and redundancy

- **M1 (PVACreator)** is a commercial bundle. It may internally use combinations of other methods, but the videos do not disclose that.
- **M2** is the most technically specific non-commercial method currently discussed in community sources: it targets the claimed root cause (device/TCP fingerprint), not just IP quality.
- **M3 and M4** are variants of "use a real or real-like device with carrier connectivity."
- **M6** is about entry-point selection rather than fingerprint/SMS mechanics.
- **M7** is not an SMS-receive method; it is an SMS-send method that depends on owning/controlling a phone.
- **M8** bypasses registration entirely rather than bypassing the verification step.
- **M9** is situational and opportunistically dependent on Google's session trust.

---

## Practical cautions from public discussion

- The QR prompt is reportedly triggered in many desktop + commercial VPN + datacenter IP contexts
- Clean IP alone is reportedly insufficient if device fingerprint still reads as desktop OS
- TCP fingerprint mismatch is reported as a common failure point in proxy-based attempts
- WebRTC and DNS inconsistencies are reported as detectable
- Repeated failures from the same IP/device may tighten restrictions rather than loosen them
- Pre-verified accounts carry supply-chain trust risk
- Community claims about what works are time-sensitive and may degrade as Google updates checks

---

## Suggested internal use of this playbook

Use this as a **threat-method inventory** for:
- Prioritizing which bypass techniques are most relevant to monitor
- Mapping each method to the detection opportunities it implies
- Understanding dependency chains that could be disrupted
- Distinguishing "claims seen in videos/community" from "verified internal signal"

Do not treat this playbook as proof that any method is reliable or long-lived.
