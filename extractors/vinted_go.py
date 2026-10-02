import re
from bs4 import BeautifulSoup
from typing import Optional
from .base import ShipmentInfo

class VintedGoExtractor:
    NAME = "Vinted Go"

    @classmethod
    def can_handle(cls, subject: str, sender: str, html: str, text: str) -> bool:
        lower_sub = subject.lower()
        lower_sender = sender.lower()
        lower_text = text.lower()
        
        # Exclude reminders
        if "recuerda" in lower_sub or "recordatorio" in lower_sub or "reminder" in lower_sub:
            return False

        # Exclude InPost and SEUR which are often sent via shipping@relay.vinted.com
        if "inpost" in lower_sender or "inpost" in lower_sub or "seur" in lower_sender or "seur" in lower_sub:
            return False

        # Must be an arrival / ready for pickup email
        is_arrival = "liberar espacio" in lower_sub or "recoge tu paquete" in lower_sub or "ha llegado" in lower_text
        return ("vinted" in lower_sender or "vinted" in lower_sub) and is_arrival

    @classmethod
    def extract(cls, subject: str, sender: str, html: str, text: str) -> Optional[ShipmentInfo]:
        soup = BeautifulSoup(html, 'html.parser')
        plain_text = soup.get_text('\n', strip=True)

        # 1. Pickup code (PIN)
        code_match = re.search(r'introduce:\s*(\d{4,8})', plain_text, re.IGNORECASE)
        pickup_code = code_match.group(1) if code_match else None

        # 2. Deadline
        deadline_match = re.search(r'Recoger antes del\s*([0-9]{2}/[0-9]{2}/[0-9]{4})', plain_text, re.IGNORECASE)
        deadline = deadline_match.group(1) if deadline_match else None

        # 3. Tracking / Order number
        tracking_match = re.search(r'N\.º\s*de seguimiento:\s*([A-Za-z0-9]+)', plain_text, re.IGNORECASE)
        if not tracking_match:
            tracking_match = re.search(r'#([A-Za-z0-9]{8,})', subject)
        tracking_number = tracking_match.group(1) if tracking_match else None

        # 4. Store name and address
        store_name = "Supermercado Coaliment"
        address = ""
        
        dir_match = re.search(
            r'Dirección\s*\n+(?:tienda de Vinted Go\s*\n+)?([^\n]+)\s*\n+([^\n]+)\s*\n+([^\n]+)',
            plain_text,
            re.IGNORECASE
        )
        if dir_match:
            store_candidate = dir_match.group(1).strip()
            street = dir_match.group(2).strip()
            city = dir_match.group(3).strip()
            if "tienda de" in store_candidate.lower():
                store_name = "Supermercado Coaliment"
            else:
                store_name = store_candidate
            address = f"{street}, {city}"
        else:
            addr_match = re.search(r'(Calle|Avinguda|Av\.|Plaza|C/)\s+[^,\n]+,\s*\d+[^,\n]*', plain_text, re.IGNORECASE)
            if addr_match:
                address = addr_match.group(0).strip()

        # 5. QR Code URL
        qr_url = None
        for img in soup.find_all('img'):
            src = img.get('src', '')
            alt = img.get('alt', '')
            if 'qr_codes' in src or 'barcode' in src or 'qr code' in alt.lower():
                qr_url = src
                break

        # 6. Recipient
        recipient_match = re.search(r'Hola,?\s*([^\n:]+):', plain_text)
        recipient = recipient_match.group(1).strip() if recipient_match else None

        # 7. Item details
        item_match = re.search(r'Detalles del pedido\s*\n+([^\n]+)', plain_text)
        item_details = item_match.group(1).strip() if item_match else None

        return ShipmentInfo.create(
            courier="Vinted Go",
            store_name=store_name,
            address=address or "See Google Maps",
            merchant="Vinted",
            pickup_code=pickup_code,
            tracking_number=tracking_number,
            deadline=deadline,
            qr_code_url=qr_url,
            recipient_name=recipient,
            item_details=item_details
        )
