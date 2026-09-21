
================================================================================
AUTONOMOUS DIAGNOSTIC REPORT — Gmail signup bypass methods
================================================================================

This diagnostic exercises the *testable slice* of the methods in
../references/bypass_playbook.md under local conditions. Many methods
(M1, M2, M3, M4, M5, M6, M7, M8) cannot be run here and are recorded
as blocked-with-reason. M9 (skip-button gamble) is partially testable
through the skip-at-phone-step configs.

The goal is not to declare a "winner method". The goal is to observe:
  - Under what local conditions does Google show QR, CAPTCHA, phone
    prompt, skip, or block?
  - Which configuration had the least friction?
  - What does that imply about the non-testable methods?
================================================================================

## 1. Method catalog: testable vs blocked

ID    Testable here?   Method name                                            
------------------------------------------------------------------------------------------
M1    NO               PVACreator commercial automation                       
M2    NO               TCP-fingerprint spoof + antidetect browser             
M3    NO               Real Android device + cellular data                    
M4    NO               Cloud phone platforms (GeeLark / DuoPlus)              
M5    NO               Linux fingerprint browser + regional proxy             
M6    NO               Alternative Google entry points (YouTube app, Android  
M7    NO               QR decode + programmatic SMS send from carrier-connect 
M8    NO               Pre-verified / ready-made accounts                     
M9    YES              Skip-button timing + low-trust-signal session          

## 2. Blocked methods — why and what we can infer

### M1 — PVACreator commercial automation

- **Not testable here:** Requires PVACreator license and its own proxy/SMS/fingerprint bindings; black-box to us.
- **Inference:** Our testable slice cannot reproduce this. The only evidence is vendor demos (V1/V3/V4). If a Google signup under our config already shows QR/CAPTCHA/phone-prompt at low volume, a vendor claiming QR bypass should be treated as a claim, not proof.

### M2 — TCP-fingerprint spoof + antidetect browser

- **Not testable here:** Requires TCP-layer fingerprint spoofing proxy (e.g. Voidmob-style) plus an antidetect browser profile. Not available here.
- **Inference:** Our desktop-vs-mobile UA runs are a weak proxy for whether device-class signals matter. If mobile UA changes the phone-vs-QR prompt while the underlying connection is still a datacenter IP, that is evidence that device-class signals are read separately from IP class.

### M3 — Real Android device + cellular data

- **Not testable here:** Requires a physical Android phone on a cellular connection.
- **Inference:** Cannot test directly. If mobile UA without a real carrier connection still does not get SMS, that is weak evidence that carrier/device attestation matters more than UA alone.

### M4 — Cloud phone platforms (GeeLark / DuoPlus)

- **Not testable here:** Requires a cloud-phone subscription; not available here.
- **Inference:** Cannot test directly.

### M5 — Linux fingerprint browser + regional proxy

- **Not testable here:** Requires a fingerprint-browser license and a residential proxy from a regional pool; not available here.
- **Inference:** Cannot test directly.

### M6 — Alternative Google entry points (YouTube app, Android Settings, Drive/Docs)

- **Not testable here:** Requires a mobile device with the Google apps; not available here.
- **Inference:** Different entry points may trigger different challenge logic. Cannot test here, but worth noting for defenders: a single signup-protection policy may not be uniform across all Google entry points.

### M7 — QR decode + programmatic SMS send from carrier-connected phone

- **Not testable here:** Requires a camera-capable phone on a carrier connection that can scan the QR and send the resulting SMS. Not available here.
- **Inference:** Our qr_bypass module can detect a QR screen and attempt online decode. What we cannot do here is the second half of M7: sending the SMS from a real device. If Google shows a QR that decodes to a phone-bound action rather than a simple code-to-enter, that is a signal that the check is partly about device/carrier proof, not just code receipt.

### M8 — Pre-verified / ready-made accounts

- **Not testable here:** Requires buying accounts that were already created and verified.
- **Inference:** Not a registration-time bypass; it sidesteps registration. Defenders should watch for post-creation patterns that look like transferred/pre-verified inventory rather than only registration-time signals.

## 3. Run results

### A4_desktop_human_no_skip

- desc: Desktop UA + human pacing + do not try to skip phone step. Used to compare skip vs not-skip under otherwise identical conditions.
- method_family_ref: control (desktop, no skip attempt)
- success: True
- email: stephanienguyen926@gmail.com
- full_name: Stephanie Nguyen
- wallclock: 64.69s
- qr_seen: False
- captcha_seen: False
- phone_prompt_seen: True
- skip_offered_and_used: False
- skip_offered_but_not_used: False
- block_seen: False
- otp_prompted: False
- otp_sent: False
- errors: 0

- friction score:
    - total_friction: 1.25
    - wallclock_seconds: 64.69
    - phone_prompt_seen: count=2 weight=1.0 contrib=2.0
    - slow_run_over_60s: count=1 weight=0.25 contrib=0.25

- event timeline (first 40):
    - [1790033230.09] run_start:diagnostic :: config=A4_desktop_human_no_skip
    - [1790033230.31] run_start:entry :: config=desktop pacing=human phone_policy=skip_if_offered try_skip=False
    - [1790033234.85] step_enter:entry :: Navigated to Google signup
    - [1790033243.64] step_enter:birthday_gender :: On birthday/gender page
    - [1790033250.39] step_exit:birthday_gender :: Birthday and gender submitted; advancing to email
    - [1790033250.45] step_enter:email :: On email/username page
    - [1790033256.49] step_exit:email :: Email/username submitted; advancing to password
    - [1790033266.56] step_exit:captcha :: CAPTCHA check complete
    - [1790033266.60] step_enter:phone_or_qr :: At phone/QR decision gate
    - [1790033266.60] PhonePrompt:phone_sms :: Phone verification prompt detected
    - [1790033286.62] PhonePrompt:phone_skip :: SMS unavailable; attempting skip fallbacks
    - [1790033286.62] step_exit:phone_or_qr :: Phone/QR step complete
    - [1790033294.72] step_exit:final :: Account creation complete

## 4. Smoothest-first ranking (by total friction)

rank   config                       total_friction   success   qr    captcha   phone   skip_used   
--------------------------------------------------------------------------------------------------------------
1      A4_desktop_human_no_skip     1.25             True      False False     True    False       

## 5. Smoothest run — detail

Config: A4_desktop_human_no_skip
Total friction: 1.25
Success: True
Email: stephanienguyen926@gmail.com
Wallclock: 64.69s
Reason it is smoothest (from scoring):
  - phone_prompt_seen: 2 x weight 1.0 = 2.0
  - slow_run_over_60s: 1 x weight 0.25 = 0.25

Interpretation:
  The smoothest run under *these local conditions* was A4_desktop_human_no_skip.
  That does NOT mean this config replicates any specific M1..M9 method.
  It means: under the current IP/environment, this configuration
  produced the fewest Google friction signals before finishing (or failing).

## 6. Method-smoothness cross-reference

How to read this against references/bypass_playbook.md:

- **M1 PVACreator commercial automation**:
  - Not testable here. Our testable slice cannot reproduce this. The only evidence is vendor demos (V1/V3/V4). If a Google signup under our config already shows QR/CAPTCHA/phone-prompt at low volume, a vendor claiming QR bypass should be treated as a claim, not proof.
- **M2 TCP-fingerprint spoof + antidetect browser**:
  - Not testable here. Our desktop-vs-mobile UA runs are a weak proxy for whether device-class signals matter. If mobile UA changes the phone-vs-QR prompt while the underlying connection is still a datacenter IP, that is evidence that device-class signals are read separately from IP class.
- **M3 Real Android device + cellular data**:
  - Not testable here. Cannot test directly. If mobile UA without a real carrier connection still does not get SMS, that is weak evidence that carrier/device attestation matters more than UA alone.
- **M4 Cloud phone platforms (GeeLark / DuoPlus)**:
  - Not testable here. Cannot test directly.
- **M5 Linux fingerprint browser + regional proxy**:
  - Not testable here. Cannot test directly.
- **M6 Alternative Google entry points (YouTube app, Android Settings, Drive/Docs)**:
  - Not testable here. Different entry points may trigger different challenge logic. Cannot test here, but worth noting for defenders: a single signup-protection policy may not be uniform across all Google entry points.
- **M7 QR decode + programmatic SMS send from carrier-connected phone**:
  - Not testable here. Our qr_bypass module can detect a QR screen and attempt online decode. What we cannot do here is the second half of M7: sending the SMS from a real device. If Google shows a QR that decodes to a phone-bound action rather than a simple code-to-enter, that is a signal that the check is partly about device/carrier proof, not just code receipt.
- **M8 Pre-verified / ready-made accounts**:
  - Not testable here. Not a registration-time bypass; it sidesteps registration. Defenders should watch for post-creation patterns that look like transferred/pre-verified inventory rather than only registration-time signals.
- **M9 Skip-button timing + low-trust-signal session**:
  - Testable here via the skip-group configs (A1..A4).
  - See ranking above for which related config felt smoothest.

================================================================================
END OF REPORT
================================================================================
