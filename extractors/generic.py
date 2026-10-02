import re
import urllib.parse
from bs4 import BeautifulSoup
from typing import Optional
from .base import ShipmentInfo

# Common words to reject as numeric pickup codes
FALSE_POSITIVE_CODES = {
    "para", "este", "esta", "estos", "entre", "desde", "hasta", "lunes", 
    "martes", "codigo", "codigo:", "código", "recoger", "locker", "punto"
}

class GenericExtractor:
    NAME = "Universal Courier"

    @classmethod
    def can_handle(cls, subject: str, sender: str, html: str, text: str) -> bool:
        lower_sub = subject.lower()
        lower_text = text.lower()
        
        # Exclude non-arrival subjects strictly
        excluded = [
            "recuerda", "recordatorio", "reminder", "reembolso", "favorito", 
            "opinión", "valora", "qué tal", "novedades", "confirmación", "alerta",
            "en camino", "ha sido enviado", "pedido enviado", "shipped", "tracking update"
        ]
        if any(ex in lower_sub for ex in excluded):
            return False

        arrival_signals = [
            "ya puedes recoger", "recoge tu paquete", "recoger tu paquete", 
            "ha llegado", "entregado en tu punto", "disponible para recogida",
            "disponible para su recogida", "listo para recoger", "te está esperando en",
            "ready for pickup", "arrived at pickup", "pickup locker", "paczka czeka",
            "gotowa do odbioru", "código de recogida", "codigo de recogida",
            "punto de recogida", "punto de entrega", "punto pack", "citypaq",
            "código de retirada", "puedes pasar a recoger", "puedes ir a recoger",
            "tu paquete ha llegado", "tu envío ha llegado", "tu pedido ha llegado",
            "esperando tu recogida", "test shipping"
        ]
        return any(sig in lower_sub or sig in lower_text for sig in arrival_signals)

    @classmethod
    def extract(cls, subject: str, sender: str, html: str, text: str) -> Optional[ShipmentInfo]:
        soup = BeautifulSoup(html, 'html.parser')
        plain_text = soup.get_text('\n', strip=True)
        lower_sender = sender.lower()
        lower_sub = subject.lower()
        lower_text = plain_text.lower()

        # 1. Look for PIN / Pickup Code
        pickup_code = None
        code_match = re.search(r'(?:código|pin|code|clave|introduce|pass)[\s:]*([A-Za-z0-9]{4,8})\b', plain_text, re.IGNORECASE)
        if code_match:
            candidate = code_match.group(1).strip()
            if candidate.lower() not in FALSE_POSITIVE_CODES:
                pickup_code = candidate

        # 2. Look for Store Name / Location
        store_name = "Punto de recogida"
        
        # Specific recognized locations
        if "coaliment" in lower_text:
            store_name = "Supermercado Coaliment"
        elif "fruteria" in lower_text or "frutería" in lower_text:
            store_name = "FRUTERIA INTERNACIONAL"
        elif "herbolario" in lower_text or "psicotronica" in lower_text:
            store_name = "HERBOLARIO ESTRELLA PSICOTRONICA"
        elif "citypaq" in lower_text:
            citypaq_match = re.search(r'(Citypaq\s+[^,\n\.]+)', plain_text, re.IGNORECASE)
            store_name = citypaq_match.group(1).strip() if citypaq_match else "Correos Citypaq"
        else:
            # Pattern matching for store names
            patterns = [
                r'(?:esperando en|tienda|punto de recogida|punto de entrega)[\s:]+([^\n,\.]{4,40})',
                r'en\s+(?:el|la)?\s*(?:punto|tienda|locker|supermercado|herbolario|fruter[ií]a|estanco|kiosko|bazar|barbershop)\s+([^\n,\.]+)',
                r'A:\s*\n+([^\n]+)'
            ]
            for pat in patterns:
                sm = re.search(pat, plain_text, re.IGNORECASE)
                if sm:
                    c = sm.group(1).strip()
                    if not any(w in c.lower() for w in ["paquete", "recoger", "horario", "correo", "aviso"]):
                        store_name = c
                        break

        # 3. Look for Postal Code + Address
        address = ""
        addr_match = re.search(r'((?:Calle|C/|Carrer|Avinguda|Av\.|Avda\.|Plaza|Pl\.|Paseo|Passeig|Rambla|Camino)\s+[^,\n]+,\s*\d+[^,\n]*)(?:\s*\n+(\d{5}\s+[A-Za-zÀ-ÿ\s]+))?', plain_text, re.IGNORECASE)
        if addr_match:
            street = addr_match.group(1).strip()
            zip_city = addr_match.group(2).strip() if addr_match.group(2) else ""
            address = f"{street}, {zip_city}".rstrip(", ")
        else:
            # Fallback simple street match
            street_match = re.search(r'(?:Calle|C/|Carrer|Avinguda|Av\.|Avda\.|Plaza|Pl\.|Paseo)\s+[^,\n]+,\s*\d+', plain_text, re.IGNORECASE)
            if street_match:
                address = street_match.group(0).strip()

        # 4. QR Code search in img tags
        qr_url = None
        for img in soup.find_all('img'):
            src = img.get('src', '')
            alt = img.get('alt', '')
            if any(k in src.lower() or k in alt.lower() for k in ['qr', 'barcode', 'aztec', 'pickuppass', 'qr_code']):
                qr_url = src
                break

        # 5. Detect Merchant / Platform
        merchant = "Ecommerce"
        if "wallapop" in lower_sender or "wallapop" in lower_sub or "wallapop" in lower_text:
            merchant = "Wallapop"
        elif "vinted" in lower_sender or "vinted" in lower_sub or "vinted" in lower_text:
            merchant = "Vinted"
        elif "amazon" in lower_sender or "amazon" in lower_sub or "amazon" in lower_text:
            merchant = "Amazon"
        elif "correos" in lower_sender or "correos" in lower_sub or "citypaq" in lower_text:
            merchant = "Correos"
        elif "gls" in lower_sender or "gls" in lower_sub or "gls" in lower_text:
            merchant = "GLS"
        elif "inpost" in lower_sender or "inpost" in lower_sub or "inpost" in lower_text:
            merchant = "InPost"
        elif "seur" in lower_sender or "seur" in lower_sub or "seur" in lower_text:
            merchant = "SEUR"
        elif "aliexpress" in lower_sender or "aliexpress" in lower_text:
            merchant = "AliExpress"
        elif "miravia" in lower_sender or "miravia" in lower_text:
            merchant = "Miravia"
        elif "shein" in lower_sender or "shein" in lower_text:
            merchant = "Shein"
        elif "temu" in lower_sender or "temu" in lower_text:
            merchant = "Temu"
        elif "zalando" in lower_sender or "zalando" in lower_text:
            merchant = "Zalando"
        else:
            # Try to get domain name from sender
            domain_match = re.search(r'@([a-zA-Z0-9\-]+)\.', sender)
            if domain_match:
                merchant = domain_match.group(1).capitalize()

        return ShipmentInfo.create(
            courier=merchant,
            store_name=store_name,
            address=address or "See Google Maps",
            merchant=merchant,
            pickup_code=pickup_code,
            qr_code_url=qr_url
        )
