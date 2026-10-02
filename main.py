import argparse
import time
import sys
import config
from database import init_db
from imap_client import GmailShippingMonitor
from notifiers import ConsoleNotifier, WhatsAppBridgeNotifier

def parse_args():
    parser = argparse.ArgumentParser(description="ShippingAssistant - Gmail to WhatsApp E-commerce Monitor")
    parser.add_argument(
        "--mode",
        choices=["once", "daemon", "test-scan"],
        default="once",
        help="Run mode: 'once' (single check), 'daemon' (continuous background loop), or 'test-scan' (dry run of recent emails)"
    )
    parser.add_argument(
        "--notifier",
        choices=["console", "whatsapp", "auto"],
        default="auto",
        help="Notifier destination. 'auto' uses WhatsApp if configured and ready, otherwise console."
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=config.CHECK_INTERVAL_SECONDS,
        help="Check interval in seconds for daemon mode"
    )
    parser.add_argument(
        "--all-emails",
        action="store_true",
        help="Scan both seen and unseen emails (useful for initial import / testing)"
    )
    return parser.parse_args()

def get_notifier(notifier_choice: str):
    if notifier_choice == "console":
        return ConsoleNotifier()
    
    wa_notifier = WhatsAppBridgeNotifier(
        bridge_url=config.WHATSAPP_BRIDGE_URL,
        target_jid=config.WHATSAPP_TARGET_GROUP
    )

    if notifier_choice == "whatsapp":
        return wa_notifier

    # Auto mode
    if config.WHATSAPP_TARGET_GROUP and wa_notifier.is_bridge_ready():
        print(f"📡 WhatsApp Bridge connected. Routing notifications to {config.WHATSAPP_TARGET_GROUP}")
        return wa_notifier
    else:
        print("ℹ️ WhatsApp Bridge not ready or target group not set. Defaulting to Console output.")
        return ConsoleNotifier()

def main():
    args = parse_args()
    init_db()

    notifier = ConsoleNotifier() if args.mode == "test-scan" else get_notifier(args.notifier)
    monitor = GmailShippingMonitor(notifier=notifier)

    if args.mode == "test-scan":
        print("🔍 Running test scan on recent emails (dry-run mode, will not mark as processed)...")
        # Temporarily scan matching emails
        monitor.check_inbox(search_unseen_only=False, max_scan=5)
        print("✅ Test scan finished.")
        return

    if args.mode == "once":
        print("📬 Checking inbox for new shipping notifications...")
        unseen_only = not args.all_emails
        count = monitor.check_inbox(search_unseen_only=unseen_only, max_scan=20)
        print(f"🏁 Finished check. Processed {count} shipment(s).")
        return

    if args.mode == "daemon":
        print(f"🚀 Starting ShippingAssistant daemon (interval: {args.interval}s)...")
        try:
            while True:
                monitor.check_inbox(search_unseen_only=True, max_scan=20)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n🛑 Stopped daemon.")

if __name__ == "__main__":
    main()
