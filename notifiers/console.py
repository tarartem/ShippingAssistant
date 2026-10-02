from .base import BaseNotifier
from extractors.base import ShipmentInfo

class ConsoleNotifier(BaseNotifier):
    """
    Prints notifications directly to stdout with clear visual formatting.
    Useful for local testing, dry runs, and debugging.
    """
    def send(self, info: ShipmentInfo) -> bool:
        print("\n" + "=" * 55)
        print("📢 [NOTIFICATION DISPATCH - CONSOLE]")
        print("=" * 55)
        print(info.format_whatsapp_message())
        if info.qr_code_url:
            print(f"\n[QR Code Link]: {info.qr_code_url}")
        print("=" * 55 + "\n")
        return True
