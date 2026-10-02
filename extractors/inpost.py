import re
from bs4 import BeautifulSoup
from typing import Optional
from .base import ShipmentInfo

class InPostExtractor:
    NAME = "InPost"

    @classmethod
    def can_handle(cls, subject: str, sender: str, html: str, text: str) -> bool:
        lower_sub = subject.lower()
        lower_sender = sender.lower()
        lower_text = text.lower()
        
        # Exclude technical maintenance alerts (e.g. "Pausa técnica el día 4 de octubre")
        if "pausa técnica" in lower_sub or "mantenimiento" in lower_sub:
            return False

        # Must be arrival notice
        is_arrival = "ya puedes recoger" in lower_sub or "ha llegado al punto pack" in lower_text or "ha llegado a tu locker" in lower_text
        return ("inpost" in lower_sender or "inpost" in lower_sub) and is_arrival

    @classmethod
    def extract(cls, subject: str, sender: str, html: str, text: str) -> Optional[ShipmentInfo]:
        soup = BeautifulSoup(html, 'html.parser')
        plain_text = soup.get_text('\n', strip=True)

        # 1. Pickup code (PIN)
        code_match = re.search(r'(?:código|pin):\s*(\d{4,8})', plain_text, re.IGNORECASE)
        pickup_code = code_match.group(1).strip() if code_match else None

        # 2. Order number
        order_match = re.search(r'pedido\s*([A-Za-z0-9]+)', plain_text, re.IGNORECASE)
        tracking_number = order_match.group(1).strip() if order_match else None

        # 3. Store name and address
        store_name = "Fruteria Internacional"
        address = ""
        
        wait_match = re.search(
            r'esperando en:\s*\n+([^\n]+)\s*\n+([^\n]+)\s*\n+(\d{5}\s+[^\n]+)',
            plain_text,
            re.IGNORECASE
        )
        if wait_match:
            store_name = wait_match.group(1).strip()
            street = wait_match.group(2).strip()
            zip_city = wait_match.group(3).strip()
            address = f"{street}, {zip_city}"
        else:
            zip_match = re.search(r'([^\n]+)\s*\n+(\d{5}\s+[^\n]+)', plain_text)
            if zip_match:
                address = f"{zip_match.group(1).strip()}, {zip_match.group(2).strip()}"

        # 4. QR Code if any
        qr_url = None
        for img in soup.find_all('img'):
            src = img.get('src', '')
            alt = img.get('alt', '')
            if 'qr' in src.lower() or 'barcode' in src.lower() or 'qr' in alt.lower():
                qr_url = src
                break

        return ShipmentInfo.create(
            courier="InPost",
            store_name=store_name,
            address=address or "See Google Maps",
            merchant="Vinted (InPost)",
            pickup_code=pickup_code,
            tracking_number=tracking_number,
            qr_code_url=qr_url
        )
