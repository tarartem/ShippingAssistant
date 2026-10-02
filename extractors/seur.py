import re
from bs4 import BeautifulSoup
from typing import Optional
from .base import ShipmentInfo

class SeurExtractor:
    NAME = "SEUR"

    @classmethod
    def can_handle(cls, subject: str, sender: str, html: str, text: str) -> bool:
        lower_sub = subject.lower()
        lower_sender = sender.lower()
        lower_text = text.lower()
        
        # Exclude satisfaction surveys or post-delivery feedback
        if "qué tal ha ido" in lower_sub or "feedback" in lower_sub:
            return False

        # Only pickup arrival
        is_arrival = "entregado en tu punto" in lower_sub or "disponible para su recogida" in lower_text
        return ("seur" in lower_sender or "seur" in lower_sub or "seur" in lower_text) and is_arrival

    @classmethod
    def extract(cls, subject: str, sender: str, html: str, text: str) -> Optional[ShipmentInfo]:
        soup = BeautifulSoup(html, 'html.parser')
        plain_text = soup.get_text('\n', strip=True)

        # 1. Tracking number
        track_match = re.search(r'Tu envío (?:VINTED|SEUR)\s*n[°º]?\s*([A-Za-z0-9]+)', plain_text, re.IGNORECASE)
        tracking_number = track_match.group(1).strip() if track_match else None

        # 2. Store name & Deadline from initial greeting
        store_match = re.search(r'siguiente tienda SEUR Pickup:\s*([^,]+)', plain_text, re.IGNORECASE)
        store_name = store_match.group(1).strip() if store_match else "SEUR Pickup"

        deadline_match = re.search(r'hasta el próximo\s*([^,\.]+,\s*\d+\s+de\s+[a-z]+\s+de\s+\d{4})', plain_text, re.IGNORECASE)
        if not deadline_match:
            deadline_match = re.search(r'hasta el próximo\s*([^\.\n]+)', plain_text, re.IGNORECASE)
        deadline = deadline_match.group(1).strip() if deadline_match else None

        # 3. Destination Address
        address = ""
        dest_match = re.search(r'A:\s*\n+([^\n]+)\s*\n+([^\n]+)\s*\n+(\d{5}\s+[^\n]+)', plain_text)
        if dest_match:
            store_name = dest_match.group(1).strip()
            street = dest_match.group(2).strip()
            zip_city = dest_match.group(3).strip()
            address = f"{street}, {zip_city}"
        else:
            zip_match = re.search(r'([^\n]+)\s*\n+(\d{5}\s+[^\n]+)', plain_text)
            if zip_match:
                address = f"{zip_match.group(1).strip()}, {zip_match.group(2).strip()}"

        # 4. QR Code URL
        qr_url = None
        for img in soup.find_all('img'):
            src = img.get('src', '')
            alt = img.get('alt', '')
            if 'AztecCode' in src or 'barcode' in src or 'qr code' in alt.lower() or 'pickup-services.com' in src:
                qr_url = src
                break

        # 5. Recipient
        recip_match = re.search(r'Hola\s+([^!]+)!', plain_text)
        recipient = recip_match.group(1).strip() if recip_match else None

        return ShipmentInfo.create(
            courier="SEUR",
            store_name=store_name,
            address=address or "See Google Maps",
            merchant="Vinted (SEUR)",
            tracking_number=tracking_number,
            deadline=deadline,
            qr_code_url=qr_url,
            recipient_name=recipient
        )
