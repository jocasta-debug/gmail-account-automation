"""
Fixed birthday + gender flow for Google's custom ARIA combobox dropdowns.

DOM findings:
  - Month: div[role="combobox"] (aria-labelledby → "Month") → ul[aria-label="Month"] listbox
  - Gender: div[role="combobox"] (aria-labelledby → "Gender") → ul[aria-label="Gender"] listbox
  - The combobox trigger has NO id and NO aria-label — only aria-labelledby
  - aria-labelledby points to elements whose text content identifies the field
  - Strategy: enumerate comboboxes, match by aria-labelledby target text, click by index
"""

import logging
from typing import Optional
from playwright.sync_api import Page

log = logging.getLogger("gmail")


def fill_birthday_gender(page: Page, birthday: str, gender: str = "male") -> dict:
    """Fill Google's birthday + gender step using custom ARIA combobox dropdowns."""
    mm, dd, yyyy = birthday[:2], birthday[2:4], birthday[4:]
    month_names = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]
    month_name = month_names[int(mm) - 1] if mm.isdigit() and 1 <= int(mm) <= 12 else mm
    gender_label = gender.capitalize()

    result = {"month_filled": False, "day_filled": False,
              "year_filled": False, "gender_filled": False}

    # Wait for dropdowns to be ready
    try:
        page.wait_for_selector("text=Enter your birthday and gender", timeout=10000)
        log.info("  Birthday page ready")
    except Exception:
        log.warning("  Birthday page not detected")

    # Wait for "Loading" overlay to clear
    page.wait_for_timeout(2000)

    # Month
    result["month_filled"] = _select_combobox_option(
        page, "Month", month_name, log)

    # Day — text input
    result["day_filled"] = _fill_text_input(
        page, ["input[placeholder='Day']", "input[aria-label='Day']",
               "input[aria-label='day']", "input[name='day']"],
        dd, "Day", log)

    # Year — text input
    result["year_filled"] = _fill_text_input(
        page, ["input[placeholder='Year']", "input[aria-label='Year']",
               "input[aria-label='year']", "input[name='year']"],
        yyyy, "Year", log)

    # Gender
    result["gender_filled"] = _select_combobox_option(
        page, "Gender", gender_label, log)

    return result


def _get_combobox_index_by_label(page: Page, target_label: str) -> Optional[int]:
    """Find the combobox index whose aria-labelledby target contains target_label."""
    try:
        data = page.evaluate("""() => {
            const triggers = document.querySelectorAll('div[role="combobox"]');
            return Array.from(triggers).map(t => {
                const labelledby = t.getAttribute('aria-labelledby') || '';
                const ids = labelledby.split(' ').filter(Boolean);
                const labelEls = ids.map(id => document.getElementById(id)).filter(Boolean);
                const labels = labelEls.map(el => el ? el.textContent.trim() : '');
                return labels.join(' ').toLowerCase();
            });
        }""")
        if not data:
            return None
        for i, labels in enumerate(data):
            if target_label.lower() in labels:
                return i
        return None
    except Exception:
        return None


def _select_combobox_option(page: Page, aria_label: str, option_text: str,
                           log) -> bool:
    """
    Click a custom ARIA combobox dropdown and select an option.

    Flow:
     1. Find the combobox trigger by matching aria-labelledby target text
     2. Click the trigger to open the listbox
     3. Wait for the listbox ul[aria-label="..."] to become visible
     4. Click the option li inside the listbox
    """
    idx = _get_combobox_index_by_label(page, aria_label)
    if idx is None:
        log.warning(f"  {aria_label}: combobox trigger not found (no matching aria-labelledby)")
        return False

    try:
        trigger = page.locator("div[role='combobox']").nth(idx)
        if not trigger.count() or not trigger.is_visible():
            log.warning(f"  {aria_label}: trigger #{idx} not visible")
            return False

        trigger.click()
        log.info(f"  {aria_label} combobox clicked (trigger #{idx})")
        page.wait_for_timeout(300)

        # Wait for listbox to become visible
        listbox = page.locator(f"ul[aria-label='{aria_label}']").first
        try:
            listbox.wait_for(state="visible", timeout=5000)
            log.info(f"  {aria_label} listbox visible")
        except Exception:
            log.warning(f"  {aria_label}: listbox did not become visible")
            page.wait_for_timeout(500)

        # Find and click the option
        for opt_sel in [
                f"ul[aria-label='{aria_label}'] li:has-text('{option_text}')",
                f"ul[aria-label='{aria_label}'] div:has-text('{option_text}')",
                f"ul[aria-label='{aria_label}'] [role='option']:has-text('{option_text}')",
                f"li:has-text('{option_text}')",
        ]:
            try:
                opt = page.locator(opt_sel).first
                if opt.count() and opt.is_visible():
                    opt.click()
                    log.info(f"  {aria_label}: selected '{option_text}'")
                    page.wait_for_timeout(200)
                    return True
            except Exception:
                continue

        # Last resort: click first li in the listbox
        try:
            first_li = page.locator(f"ul[aria-label='{aria_label}'] li").first
            if first_li.count() and first_li.is_visible():
                first_li.click()
                log.info(f"  {aria_label}: selected first option (fallback)")
                page.wait_for_timeout(200)
                return True
        except Exception:
            pass

        log.warning(f"  {aria_label}: option '{option_text}' not found in listbox")
        return False

    except Exception as e:
        log.debug(f"  {aria_label}: combobox interaction failed: {e}")
        return False


def _fill_text_input(page: Page, selectors: list, value: str,
                     label: str, log) -> bool:
    """Try to fill a text input using multiple selectors."""
    for sel in selectors:
        try:
            el = page.locator(sel).first
            if el.count() and el.is_visible():
                el.click()
                el.fill(value)
                log.info(f"  {label}: filled '{value}' via '{sel}'")
                return True
        except Exception:
            continue

    # Fallback: JS injection
    try:
        js = (
            f"(() => {{"
            f"  const val = {repr(value)};"
        )
        for i, sel in enumerate(selectors[:2]):
            esc = sel.replace("'", "\\'")
            js += f"\n  const el{i} = document.querySelector('{esc}');"
        js += (
            "\n  if (el0 && el0.offsetParent !== null) {"
            "    el0.value = val; el0.dispatchEvent(new Event('input',{bubbles:true})); return true;"
            "  }"
            "  if (el1 && el1.offsetParent !== null) {"
            "    el1.value = val; el1.dispatchEvent(new Event('input',{bubbles:true})); return true;"
            "  }"
            "  return false;"
            "})()"
        )
        result = page.evaluate(js)
        if result:
            log.info(f"  {label}: filled via JS")
            return True
    except Exception:
        pass

    log.warning(f"  {label}: could not fill '{value}'")
    return False
