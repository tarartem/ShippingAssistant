import re
from bs4 import BeautifulSoup
from typing import Optional
from .base import ShipmentInfo

class WallapopExtractor:
    NAME = "Wallapop"

    @classmethod
    def can_handle(cls, subject: str, sender: str, html: str, text: str) -> bool:
        lower_sub = subject.lower()
        lower_sender = sender.lower()
        lower_text = text.lower()

        # Exclude reviews, payment confirmations, bids, favorites
        excluded = ["valoración", "valora", "pago recibido", "oferta", "ha marcado como favorito", "mensaje nuevo"]
        if any(ex in lower_sub for ex in excluded):
            return False

        has_wallapop = "wallapop" in lower_sender or "wallapop" in lower_sub or "wallapop" in lower_text
        is_arrival = (
            "recoge" in lower_sub or "recoger" in lower_sub or "recogida" in lower_sub or
            "ha llegado" in lower_sub or "punto de entrega" in lower_sub or "punto de recogida" in lower_sub or
            "listo para recoger" in lower_sub or "disponible" in lower_sub or
            "código de recogida" in lower_text or "disponible para su recogida" in lower_text or
            "ha llegado a tu punto" in lower_text or "ya puedes ir a buscar" in lower_text
        )
        return has_wallapop and is_arrival

    @classmethod
    def extract(cls, subject: str, sender: str, html: str, text: str) -> Optional[ShipmentInfo]:
        soup = BeautifulSoup(html, 'html.parser')
        plain_text = soup.get_text('\n', strip=True)

        # 1. Pickup code (PIN)
        code_match = re.search(r'(?:código|pin|code|clave)[\s:]*([A-Za-z0-9]{4,8})\b', plain_text, re.IGNORECASE)
        pickup_code = code_match.group(1).strip() if code_match else None

        # 2. Tracking / Order number
        tracking_match = re.search(r'(?:seguimiento|pedido|envío)[\s:#]*([A-Za-z0-9]{8,})', plain_text, re.IGNORECASE)
        tracking_number = tracking_match.group(1).strip() if tracking_match else None

        # 3. Store name & Address
        store_name = "Punto de recogida Wallapop"
        address = ""

        # Check for store name patterns
        store_match = re.search(r'(?:en el punto|en la tienda|en|punto de entrega)[\s:]+([^\n,\.]{4,40})', plain_text, re.IGNORECASE)
        if store_match:
            candidate = store_match.group(1).strip()
            if not any(w in candidate.lower() for w in ["wallapop", "paquete", "recoger", "horario"]):
                store_name = candidate

        # Address match
        addr_match = re.search(r'((?:Calle|C/|Carrer|Avinguda|Av\.|Avda\.|Plaza|Pl\.|Paseo|Passeig|Rambla|Camino)\s+[^,\n]+,\s*\d+[^,\n]*)(?:\s*\n+(\d{5}\s+[A-Za-zÀ-ÿ\s]+))?', plain_text, re.IGNORECASE)
        if addr_match:
            street = addr_match.group(1).strip()
            zip_city = addr_match.group(2).strip() if addr_match.group(2) else ""
            address = f"{street}, {zip_city}".rstrip(", ")

        # 4. QR Code if present
        qr_url = None
        for img in soup.find_all('img'):
            src = img.get('src', '')
            alt = img.get('alt', '')
            if 'qr' in src.lower() or 'barcode' in src.lower() or 'qr' in alt.lower():
                qr_url = src
                break

        return ShipmentInfo.create(
            courier="Wallapop Envíos",
            store_name=store_name,
            address=address or "See Google Maps",
            merchant="Wallapop",
            pickup_code=pickup_code,
            tracking_number=tracking_number,
            qr_code_url=qr_url
        )
