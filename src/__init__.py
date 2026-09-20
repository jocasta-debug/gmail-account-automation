"""Gmail Account Creation Automation Framework"""
from .config import log, NAME_POOL, PROXY_POOL, ENV, TWOCAPTCHA_API_KEY, FIVE_SIM_API_KEY
from .fingerprint import build_inject_script, mobile_fingerprint, desktop_fingerprint
from .humanizer import human_type, human_click, human_pause, human_scroll, warm_up_browser
from .captcha import solve_recaptcha_v2
from .sms import get_google_verification_code
from .qr_bypass import handle_qr_code
from .signup import create_account, AccountResult, setup_account_context
from .campaign import run_campaign
