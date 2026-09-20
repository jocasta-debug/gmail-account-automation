# Gmail Account Creation Automation
# ==================================
#
# Reverse-engineered from PVACreator's QR-code bypass approach:
#   - Mobile-endpoint emulation to avoid desktop QR wall
#   - Per-thread fingerprint randomization (Canvas/WebGL/Audio/UA/navigation)
#   - Human-like interaction (typing, mouse, scrolling, pauses)
#   - 2Captcha reCAPTCHA solving
#   - 5sim SMS phone verification
#   - QR code reactive bypass (screenshot → decode → open URL)
#
# Dependencies:
#   pip3 install playwright 2captcha-python pyzbar Pillow requests
#   python3 -m playwright install chromium
#
# Configure:
#   Edit .env with your API keys and proxy list
#
# Run:
#   python3 main.py --accounts 10

import sys
import os

# Ensure src is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.campaign import run_campaign

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Gmail Account Creation Automation (PVACreator-style)",
    )
    parser.add_argument(
        "--accounts", "-n", type=int, default=10,
        help="Number of accounts to create (default: 10)",
    )
    parser.add_argument(
        "--threads", "-t", type=int, default=None,
        help="Concurrent threads (default: from .env, fallback 3)",
    )
    parser.add_argument(
        "--desktop", action="store_true",
        help="Use desktop fingerprint mode (default: mobile emulation)",
    )
    parser.add_argument(
        "--no-sms", action="store_true",
        help="Disable 5sim SMS verification",
    )
    parser.add_argument(
        "--stagger", "-s", type=float, default=None,
        help="Delay between thread starts in seconds (default: 5)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print config and exit without running",
    )

    args = parser.parse_args()

    if args.dry_run:
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
        from src.config import TWOCAPTCHA_API_KEY, FIVE_SIM_API_KEY, PROXY_POOL

        print("Configuration:")
        print(f"  Accounts:     {args.accounts}")
        print(f"  Threads:      {args.threads or os.environ.get('THREADS', '3')}")
        print(f"  Mode:         {'desktop' if args.desktop else 'mobile emulation'}")
        print(f"  SMS:          {'disabled' if args.no_sms else '5sim (if key configured)'}")
        print(f"  Stagger:      {args.stagger or 5.0}s")
        print()
        print("API keys:")
        print(f"  2Captcha:    {'✅ configured' if TWOCAPTCHA_API_KEY else '❌ missing'}")
        print(f"  5sim:        {'✅ configured' if FIVE_SIM_API_KEY else '❌ missing'}")
        print()
        print("Proxy pool:")
        print(f"  {PROXY_POOL.size()} proxies loaded")
        print()
        print("Run without --dry-run to start the campaign.")
        sys.exit(0)

    print()
    print("╔" + "═" * 60 + "╗")
    print("║  Gmail Account Automation  —  starting campaign             ║")
    print("╚" + "═" * 60 + "╝")
    print()

    run_campaign(
        total_accounts=args.accounts,
        mobile_mode=False,  # desktop baseline for diagnostic
        sms_enabled=not args.no_sms,
        stagger=args.stagger or 5.0,
    )
