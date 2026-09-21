# Gmail QR Code Bypass — External Playbook

*Reverse-engineered from the six videos listed in `references/PROMPT.md`, supplemented by community discussion where videos are incomplete or ambiguous.*

**Purpose:** Catalog every distinct bypass method that appears in these specific videos, organize them as a step-by-step reference, and identify what each method depends on.

**Scope:** Methods that are actually shown, described, or directly implied by the six videos listed in the project prompt. Community discussion is used only to clarify mechanics where a video is silent. Not exhaustive; not guaranteed; not endorsed.

**Project context:** This file is part of `jocasta-debug/gmail-account-automation`, in the `references/` tree alongside `decision_tree.md` (internal signup flow), `security_analysis.md` (earlier Google-engineer analysis), and `trust_safety_prevention.md` (defensive recommendations).

---

## Video Inventory First

Before categorizing methods, here is what each video actually contains. This matters because one video has a misleading title and one is a vendor rant rather than a tutorial.

| Video | URL | Title | What it actually contains |
|---|---|---|---|
| V1 | `Bk7pGgA8TYA` | "How to Bypass Gmail QR Code Verification \| Automated Bulk Account Creator 2026" | PVACreator commercial demo/promo: bypass QR, bind proxies, custom usernames, SMS services (DaisySMS), multi-threaded campaigns |
| V2 | `Sz2kj-XAy80` | "How to Create Gmail Account Without Scanning QR Code (2026 Update)" | **Misleading title.** The transcript shows this is actually about a Chrome extension that inserts QR codes into Gmail messages (for sharing links). It is **not** about bypassing account-creation QR verification. We still describe it for completeness and flag the mismatch. |
| V3 | `NpskeGiFP08` | "How to Bulk Create Gmail Accounts Automatically \| Bypass QR Code & Setup Google Services 2026" | PVACreator walkthrough with more detail: bypass QR, bind proxies, auto-generate usernames, integrate SMS (daisySMS), enable IMAP/POP3, set up 2-Step Verification + App Passwords, add recovery emails (Outlook), bind browser fingerprints, run multi-threaded |
| V4 | `uBov0m1E-cc` | "Gmail Account Registration Bypass QR Code and Turn on 2FA and Generate App Password with PVACreator" | Another PVACreator walkthrough; essentially the same as V3. Whitehatbox Service channel. Covers same sequence: bind proxy, usernames, DaisySMS, IMAP/POP3=1, 2FA, App Password (any app/device words), recovery email, fingerprint binding |
| V5 | `foTVpgdN8Hc` | "🔥 Beat Gmail's New QR Code Security with PVACreator \| service scammer me 1500$" | **Vendor rant, not a tutorial.** The title and description indicate the creator is complaining about being scammed by a PVACreator license seller ($1500, license key `68c2c1f7-...`). There is no tutorial content. We treat this as "content not a bypass method" and note it only for completeness. |
| V6 | `Wbwi07kr8vI` | "How To Create Gmail Account Without Scanning QR Code (Complete Guide)" | Extract failed (firecrawl 403). Title suggests a general guide by StackWise. We mark content as unverified and use only the title/surface framing, not invented steps. |

**Bottom line on the video set:** three videos (V1, V3, V4) describe the same PVACreator commercial workflow. One (V2) is a mislabeled Chrome-extension demo. One (V5) is a complaint, not a method. One (V6) is unextractable. The genuine bypass content in this set is essentially one commercial product's claimed workflow, not a diverse set of independently demonstrated techniques. Community discussion is used below only to explain what PVACreator may be doing under the hood.

---

## Method Categories (video-grounded)

We label each distinct method **M1..M9**. Where a method appears in a video, we cite the video ID. Where a method is only implied or only known from community discussion, we say so explicitly.

---

### M1 — PVACreator commercial automation (the only method actually demonstrated across multiple videos)

**Source videos:** V1, V3, V4 (all describe the same product workflow).

**What it is:** A commercial SaaS product (PVACreator, `pvacreator.com`) that claims to automate bulk Gmail account creation and bypass Google's QR-code verification wall. The videos are vendor demos/promos, not independent technical teardowns.

**Claimed outcome (per videos):** "From zero to a fully configured, 2FA-protected Gmail account with App Passwords and recovery emails ready to use," in a single automated run with "no pausing, no manual editing."

**Steps as described across V1/V3/V4 (consolidated):**

1. **Create a Gmail campaign** in PVACreator.
2. **Bind proxies** — add checked proxies into the campaign (V1, V3, V4 all mention "BindProxy" / proxy binding).
3. **Add usernames** — either custom or software auto-generated random usernames (V1, V3, V4).
4. **Leave fields empty where possible** — software auto-fills during registration (V3, V4).
5. **Choose phone service** — configure an SMS API provider; videos name **daisySMS** specifically (V3, V4).
6. **Add SMS API key + choose country** — V3/V4 say US numbers are used, so the country code can be left empty.
7. **Enable IMAP/POP3** — fill "1" in the relevant field (V3, V4).
8. **Enable 2-step verification** — bind a phone number to protect the account (V3, V4).
9. **Create App Password** — required after 2FA is enabled:
   - Fill in any words as the App name
   - Fill in any words as the Device name
   (V3, V4)
10. **Add recovery email** — example format uses Outlook (V3, V4).
11. **Bind browser fingerprints** — to protect accounts (V3, V4).
12. **Run the campaign** — multi-threaded; no pausing, no manual editing (V1, V3, V4).
13. **Claimed result:** account with 2FA, App Password, recovery email, IMAP/POP3 configured.

**What the videos explicitly claim about QR:** They say PVACreator "breaks through" / "smashes through" Google's QR-code security wall and allows bulk creation "without manual scanning" (V1, V3, V4). They do **not** show the internal mechanism. The "how" is a black box.

**Dependencies:**
- PVACreator license/subscription (the V5 video's complaint suggests licenses can cost ~$1500)
- Working proxy pool (bound per campaign)
- SMS API access (videos name daisySMS; US numbers in the demo)
- Recovery email accounts (example uses Outlook)
- Browser fingerprint state per account

**What this does NOT address in the videos:**
- How QR is bypassed under the hood — claimed, not shown
- Whether QR-triggered sessions use SMS receive, SMS send from a phone, or some other path
- How accounts behave after creation under Google review
- Failure cases, limits, or countermeasures

**Confidence note:** This is the only method actually shown in more than one video, but it is shown only as a vendor demo. We treat it as a claim, not as independently verified engineering.

---

### M2 — TCP-fingerprint spoof + antidetect browser (NOT in these videos; community-only)

**Source:** community discussion only; **none of the six videos describe this.** Included because the PROMPT asks to reverse-engineer "all the scenarios mentioned in all the videos," and this method is the leading non-commercial explanation for what a tool like PVACreator might do under the hood. We label it clearly as outside the video set.

**What it is:** A technique that tries to convince Google the signup session comesfrom a mobile-device connection, by controlling the TCP fingerprint at the network layer and pairing it with an antidetect browser profile whose browser-side fingerprint reads as a different-but-plausible device.

**Claimed outcome (community claim):** Google issues SMS verification rather than QR, because the connection reads as a mobile device or a common "computer + phone hotspot" pattern.

**Steps as described in community discussion:**

1. Obtain a **clean, fresh IP** not flagged as proxy/VPN and not heavily used for Gmail signups; mobile carrier IP reportedly best, residential second.
2. Use a **proxy that can spoof TCP fingerprint** to look like iOS (reported example: Voidmob; "probably others").
3. Use an **antidetect browser** set to a profile that reads as macOS Safari (reported example: AdsPower).
4. Initiate signup through that profile over the TCP-spoofed mobile proxy.
5. Reported effect: Google treats the session as "Mac + iPhone hotspot" — a normal Apple behavior — and issues SMS verification rather than QR.

**Reported constraints (community):**
- Three things together, not one alone: clean IP + TCP-spoofed mobile fingerprint + antidetect macOS Safari profile.
- "Clean IP" alone does not help if device signature still says Windows.
- Mobile-spoofed browser alone does not help if the network layer still reads as a Linux server.
- WebRTC must be fully disabled, not just spoofed, or host OS is exposed.
- Carrier-native DNS may matter; using Cloudflare/Google DNS while claiming to be an iPhone on Verizon can be inconsistent.

**Dependencies:** TCP-fingerprint-spoofing proxy; antidetect browser license; clean IP with low signup history; careful fingerprint/OS/DNS consistency.

**Relationship to the videos:** Not shown. If PVACreator does something like this internally, the videos do not say so. We include M2 only because the prompt asks us to reverse-engineer the scenarios "mentioned in all the videos," and the QR bypass claim in V1/V3/V4 is unexplained — M2 is the leading publicly discussed hypothesis for a non-commercial mechanism that could underlie such a claim. We are explicit that this is inference, not video content.

---

### M3 — Real Android device + cellular data (NOT in these videos; community-only)

**Source:** community guides only; **none of the six videos describe this.**

**What it is:** Use a real Android phone on cellular data (not WiFi), add a Google account through system Settings rather than a browser or the Gmail app, and rely on device-level trust to reduce verification friction.

**Claimed outcome (community claim):** Lower-friction verification; sometimes a "Skip" button appears, or the flow falls back to normal SMS verification that the device can receive.

**Steps as described in community discussion:**
1. Factory-reset an Android device (or use a fresh device).
2. Connect to **cellular data**, not WiFi.
3. Go to **Settings → Accounts → Add Account → Google → Create Account**.
4. Complete the signup flow.
5. Device-level signup is reported to be trusted more than browser signup.

**Dependencies:** Real Android device; SIM/data plan with carrier connection; fresh/clean device state.

**Relationship to the videos:** None of the six videos demonstrate this. It is included only because it is a commonly discussed non-browser path that can affect whether QR appears at all.

---

### M4 — Cloud phone platforms (NOT in these videos; community-only)

**Source:** community guides only; **none of the six videos describe this.**

**What it is:** Use a cloud-phone platform that provides real Android environments in the cloud, each profile with a unique IMEI/MAC/device model, paired with a residential proxy.

**Claimed outcome (community claim):** SMS verification instead of QR in many cases.

**Steps as described in community discussion:**
1. Use a cloud phone platform (reported examples: GeeLark, DuoPlus).
2. Each profile gets unique IMEI, MAC, device model.
3. Pair the profile with a residential proxy.
4. Initiate account creation from within the cloud phone environment.
5. May trigger SMS verification instead of QR.

**Dependencies:** Cloud phone platform subscription (reported ~$25–50/month); residential proxy; SMS receiving capability if SMS is triggered.

**Relationship to the videos:** None of the six videos describe this. Included for completeness because it is a known commercial path that can affect the QR-vs-SMS decision.

---

### M5 — Linux fingerprint browser + regional proxy (NOT in these videos; community-only)

**Source:** community guides only; **none of the six videos describe this.**

**What it is:** Run a fingerprint browser on a Linux VM, use a residential proxy from certain regions, and match browser language/timezone to the proxy region.

**Claimed outcome (community claim):** Sometimes falls back to SMS or surfaces a "Skip" option where Windows/Mac fingerprint browsers tend to force QR.

**Steps as described in community discussion:**
1. Set up a Linux VM.
2. Install a fingerprint browser (reported examples: Multilogin, GoLogin).
3. Use a residential proxy from regions with known SMS issues (reported examples: Mongolia, Colombia).
4. Match browser language and timezone to the proxy region.
5. Attempt signup; may surface "Skip" or an easier verification path.

**Dependencies:** Linux VM; fingerprint browser license; residential proxy from chosen region; language/timezone consistency.

**Relationship to the videos:** None of the six videos describe this.

---

### M6 — Alternative Google entry points (NOT in these videos; community-only)

**Source:** community guides only; **none of the six videos describe this.**

**What it is:** Create a Google account through a different Google entry point than the Gmail web signup page — for example the YouTube app or Android system Settings — where verification may be less aggressive.

**Claimed outcome (community claim):** Less aggressive verification on some paths; useful for small numbers of accounts; phone verification may be skipped or deferred to later account settings.

**Steps as described in community discussion:**

**Path A — YouTube app:**
1. Open YouTube app on phone.
2. Tap profile icon → "Switch account."
3. Tap "+" → "Create account."
4. Fill name, birthdate, gender.
5. Create Gmail address and password.
6. Reportedly, phone verification may be skipped or deferred.

**Path B — Android system settings:**
1. Go to phone Settings → Accounts / Accounts and backup → Manage accounts.
2. Tap "Add account" → Google.
3. On sign-in screen, tap "Create account."
4. Complete the process.
5. Reportedly, OS-level account addition may trigger fewer aggressive checks.

**Path C — other Google apps:**
- Try Google Drive, Google Docs mobile apps as alternative entry points.

**Dependencies:** Mobile device with Google apps; clean device/IP context helps.

**Relationship to the videos:** None of the six videos describe this. One video (V2) mentions QR codes only in the context of inserting them into emails, not account signup.

---

### M7 — QR decode + programmatic SMS sending (NOT in these videos; community-only)

**Source:** community discussion only; **none of the six videos describe this.** This method is relevant to the prompt's topic only in that it is a known response to the QR wall.

**What it is:** When a QR code appears during signup, instead of scanning it with a trusted Google app, the user scans it with a phone camera, opens the resulting link, and sends an SMS draft that may appear in the phone's messaging app. The SMS is sent **through the phone's carrier connection**, which is the kind of proof Google is allegedly trying to get.

**Claimed outcome (community claim):** Handle the QR step when a phone capable of scanning and sending SMS is available; this is described as something SMS-receiving services literally cannot do, because the check is about proving a real phone/carrier connection exists.

**Steps as described in community discussion:**
1. On computer: stay on the QR code screen.
2. On phone: open camera, scan the QR code.
3. Open the link that appears.
4. An SMS draft with a code and a strange number may appear.
5. Send the SMS as-is.
6. Wait on computer for verification.

**Dependencies:** Phone with camera and carrier connection; the phone itself must send the SMS.

**Important constraint from community discussion:** If there is no "Choose another verification method" or "Send SMS" link on the QR screen, the session may be classified as suspicious, and no further action from the same IP/browser may work.

**Relationship to the videos:** None of the six videos describe this.

---

### M8 — Pre-verified / ready-made accounts (NOT in these videos; community-only)

**Source:** community guides and vendor claims only; **none of the six videos describe buying pre-verified accounts.**

**What it is:** Skip registration-time verification entirely by acquiring accounts that were already created and verified.

**Claimed outcome (community claim):** No onboarding QR/SMS step during creation, because creation already happened.

**Steps as described in community discussion:**
1. Obtain pre-verified Google accounts from a supplier.
2. Use or configure them as needed.

**Dependencies:** Supplier of pre-verified accounts; acceptance of account-history and trust risks.

**Reported caveats:** Quality and reliability vary widely; pre-verified accounts may already carry risk, restrictions, or history.

**Relationship to the videos:** PVACreator's workflow (V1/V3/V4) ends with *newly created* accounts that are then fully configured (2FA, App Password, recovery email). It is not described as selling pre-existing accounts.

---

### M9 — Skip-button timing + low-trust-signal session (NOT in these videos; community-only)

**Source:** community guides only; **none of the six videos describe trying to surface a "Skip" button.**

**What it is:** Attempt signup in a context that may cause Google to offer a "Skip" option at the phone-number step, allowing the user to leave the phone field empty.

**Claimed outcome (community claim):** In some sessions, Google allows skipping phone number entry entirely; if trust is high, verification may be minimal; if trust is low, no trick may save the session.

**Steps as described in community discussion:**
1. Open signup in a clean context.
2. Fill name, last name, date of birth.
3. At the phone number step, leave the field empty.
4. If a "Skip" button appears, click it.
5. If not, try a different method.

**Reported factors that may help:** IP reputation; browser fingerprint plausibility; behavioral pacing (slow typing, natural pauses); not creating back-to-back accounts; overall session trust.

**Dependencies:** Clean IP; plausible fingerprint; behavioral care; variable.

**Relationship to the videos:** None of the six videos describe a "Skip" strategy.

---

## Dependency Map

| Method | Shown in these videos? | Needs clean IP | Needs TCP fingerprint control | Needs real/cellular device | Needs SMS receive | Needs antidetect browser | Needs cloud phone | Needs pre-verified accounts | Needs SMS API key |
|---|---|---|---|---|---|---|---|---|---|
| **M1 PVACreator** | **Yes — V1, V3, V4** | Yes (proxy bind) | Not specified in videos | Not specified in videos | **Yes — daisySMS (per videos)** | Not specified in videos | No | No | **Yes** |
| **M2 TCP-spoof + antidetect** | No (community only) | Yes | **Yes** | Simulated (proxy) | If SMS triggered | **Yes** | No | No | No |
| **M3 Real Android + cellular** | No (community only) | Helpful | No | **Yes** | Yes (device receives SMS) | No | No | No | No |
| **M4 Cloud phone** | No (community only) | Helpful | No | Simulated (cloud real-Android) | If SMS triggered | No | **Yes** | No | No |
| **M5 Linux fingerprint + regional proxy** | No (community only) | Helpful | Partial (browser fingerprint) | No | If SMS triggered | **Yes** | No | No | No |
| **M6 Alternative entry points** | No (community only) | Helpful | No | **Yes** | Possibly | No | No | No | No |
| **M7 QR decode + SMS send** | No (community only) | Helpful | No | **Yes (carrier-connected phone)** | **No — SMS send, not receive** | No | No | No | No |
| **M8 Pre-verified accounts** | No (community only) | No | No | No | No | No | No | **Yes** | No |
| **M9 Skip-button timing** | No (community only) | Helpful | No | No | No | No | No | No | No |

**How to read this:** Only M1 is actually shown in the video set. M1's videos explicitly name proxy binding and an SMS API (daisySMS). Everything else in the table is community-discussed context that may or may not be what PVACreator does internally.

---

## Video-by-video method attribution

| Video | Methods present in the video | Notes |
|---|---|---|
| **V1** `Bk7pGgA8TYA` | M1 only | PVACreator promo: bypass QR, bind proxies, custom usernames, SMS (DaisySMS), multi-threaded campaigns |
| **V2** `Sz2kj-XAy80` | **None (misleading title)** | Chrome extension that inserts QR codes into Gmail messages; not a signup QR bypass |
| **V3** `NpskeGiFP08` | M1 only | PVACreator walkthrough: QR bypass claim, proxy bind, usernames, daisySMS, IMAP/POP3=1, 2FA, App Password, recovery email (Outlook), fingerprint binding, multi-threaded run |
| **V4** `uBov0m1E-cc` | M1 only | PVACreator walkthrough; same as V3, different channel (Whitehatbox Service) |
| **V5** `foTVpgdN8Hc` | **None (vendor complaint)** | Title indicates a rant about being scammed by a PVACreator license seller ($1500); no tutorial content |
| **V6** `Wbwi07kr8vI` | **Unverified (extract failed)** | Title suggests a StackWise "complete guide"; content not accessible; treat as unverified |

---

## Overlaps, bundles, and reliability notes

- **M1 is the only method shown in this video set.** V1, V3, and V4 are three PVACreator promos that describe the same workflow. They do not constitute independent demonstrations of different techniques.
- **M1 is a commercial bundle.** It may internally use combinations of M2–M9, but the videos do not disclose that. We should not assume PVACreator = any specific community method.
- **M2 is the most specific non-commercial hypothesis** for how a QR bypass could work at the connection level, but it is community-reported, not video-demonstrated.
- **M3, M4, M6** are device/carrier-rooted paths that can affect whether QR appears at all; they are not "QR bypass" in the sense of programmatically handling a QR prompt, but they are relevant because they can avoid triggering the QR step.
- **M7** is not an SMS-receive method; it is an SMS-send method that depends on owning/controlling a carrier-connected phone. It is relevant because it addresses the proof-of-device-possession angle.
- **M8** bypasses registration entirely rather than bypassing the verification step.
- **M9** is situational and opportunistic; not reliable as a standalone method.

**Reliability caveat:** The only "working" demonstrations in this video set are vendor promos. Community methods are time-sensitive and may degrade as Google updates checks. Nothing here should be treated as proof that any method is reliable or long-lived.

---

## What the videos do and do not show (explicit)

**What V1/V3/V4 show:**
- A commercial product workflow: proxy bind, usernames, SMS API integration, IMAP/POP3 toggle, 2FA + App Password, recovery email, browser fingerprint binding, multi-threaded campaign run.
- A claim that QR is bypassed ("breaks through," "smashes through," "without manual scanning").

**What V1/V3/V4 do NOT show:**
- The internal mechanism for QR bypass.
- How SMS verification is actually completed for QR-triggered sessions.
- Any long-term account reliability data.
- Countermeasures, failure cases, or limits.

**What V2 actually is:**
- A Chrome extension demo for inserting QR codes into Gmail messages; not relevant to signup QR bypass despite its title.

**What V5 actually is:**
- A vendor-rant/complaint video, not a tutorial; not a method.

**What V6 is:**
- Unverified; content could not be extracted; treat as unknown.

---

## Suggested internal use of this playbook

Use this as a **threat-method inventory** for:
- Distinguishing what the video set actually contains (one commercial product demo + mislabeled/unverifiable videos) from the broader universe of community-discussed methods.
- Mapping each method to the detection opportunities it implies.
- Understanding dependency chains that could be disrupted.
- Separating "claims seen in videos" from "verified internal signal."

Do not treat this playbook as proof that any method is reliable or long-lived.
