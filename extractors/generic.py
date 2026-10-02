import re
from bs4 import BeautifulSoup
from typing import Optional
from .base import ShipmentInfo

class GenericExtractor:
    NAME = "Generic Courier"

    @classmethod
    def can_handle(cls, subject: str, sender: str, html: str, text: str) -> bool:
        lower_sub = subject.lower()
        lower_text = text.lower()
        
        # Exclude non-arrival subjects strictly
        excluded = [
            "recuerda", "recordatorio", "reminder", "reembolso", "favorito", 
            "opinión", "valora", "qué tal", "novedades", "confirmación", "alerta"
        ]
        if any(ex in lower_sub for ex in excluded):
            return False

        arrival_signals = ["ya puedes recoger", "ha llegado", "entregado en tu punto", "disponible para recogida"]
        return any(sig in lower_sub or sig in lower_text for sig in arrival_signals)

    @classmethod
    def extract(cls, subject: str, sender: str, html: str, text: str) -> Optional[ShipmentInfo]:
        soup = BeautifulSoup(html, 'html.parser')
        plain_text = soup.get_text('\n', strip=True)

        # Look for PIN / Code
        code_match = re.search(r'(?:código|pin|code|introduce)[\s:]*([A-Za-z0-9]{4,8})\b', plain_text, re.IGNORECASE)
        pickup_code = code_match.group(1).strip() if code_match else None

        # Look for postal code + city (Spanish standard 5 digits e.g. 46007 Valencia)
        addr_match = re.search(r'([^\n,]+,\s*\d+[^,\n]*)\s*\n+(\d{5}\s+[A-Za-zÀ-ÿ\s]+)', plain_text)
        address = ""
        store_name = "Pickup Point"
        if addr_match:
            address = f"{addr_match.group(1).strip()}, {addr_match.group(2).strip()}"
        else:
            street_match = re.search(r'(?:Calle|Avinguda|Av\.|Plaza|C/|Paseo)\s+[^,\n]+,\s*\d+', plain_text, re.IGNORECASE)
            if street_match:
                address = street_match.group(0).strip()

        # Check for images that might be a QR
        qr_url = None
        for img in soup.find_all('img'):
            src = img.get('src', '')
            alt = img.get('alt', '')
            if 'qr' in src.lower() or 'barcode' in src.lower() or 'qr' in alt.lower():
                qr_url = src
                break

        # Carrier / Merchant name
        merchant = "Courier"
        if "gls" in sender.lower() or "gls" in subject.lower():
            merchant = "GLS"
            store_match = re.search(r'en\s+(PS\s+GLS\s+[^,\n]+)', subject, re.IGNORECASE)
            if store_match:
                store_name = store_match.group(1).strip()
        elif "correos" in sender.lower() or "correos" in subject.lower():
            merchant = "Correos"
        elif "ups" in sender.lower() or "ups" in subject.lower():
            merchant = "UPS"
        elif "dhl" in sender.lower() or "dhl" in subject.lower():
            merchant = "DHL"

        return ShipmentInfo.create(
            courier=merchant,
            store_name=store_name,
            address=address or "See original email",
            merchant=merchant,
            pickup_code=pickup_code,
            qr_code_url=qr_url
        )
