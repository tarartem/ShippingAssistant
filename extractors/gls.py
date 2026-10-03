import re
from bs4 import BeautifulSoup
from typing import Optional
from .base import ShipmentInfo

class GLSExtractor:
    NAME = "GLS"

    @classmethod
    def can_handle(cls, subject: str, sender: str, html: str, text: str) -> bool:
        lower_sub = subject.lower()
        lower_sender = sender.lower()
        lower_text = text.lower()

        # Exclude satisfaction surveys or post-delivery feedback
        if "qué tal ha ido" in lower_sub or "feedback" in lower_sub or "opinión" in lower_sub or "entregado tu envío" in lower_sub:
            return False

        # Exclude out for delivery / in transit notices (not ready for pickup yet)
        if "está en camino" in lower_sub or "en reparto" in lower_sub or "prevemos entregar" in lower_sub:
            return False

        is_gls = "gls" in lower_sender or "gls" in lower_sub or "gls" in lower_text
        is_ready = "ya puedes recoger" in lower_sub or "ya puedes recoger" in lower_text or "ya te espera en" in lower_text

        return is_gls and is_ready

    @classmethod
    def extract(cls, subject: str, sender: str, html: str, text: str) -> Optional[ShipmentInfo]:
        soup = BeautifulSoup(html, 'html.parser')
        plain_text = soup.get_text('\n', strip=True)

        # 1. Tracking number
        track_match = re.search(r'seguimiento GLS\s*[:\n]?\s*([A-Za-z0-9]+)', plain_text, re.IGNORECASE)
        tracking_number = track_match.group(1).strip() if track_match else None

        # 2. Store name
        store_name = "GLS Parcel Shop"
        # Often in "ya te espera en \n PS GLS DIS SUPREMOS BARBERSHOP" or "Datos del Parcel Shop \n PS GLS..."
        store_match = re.search(r'ya te espera en\s*[:\n]?\s*([^\.\n]+)', plain_text, re.IGNORECASE)
        if store_match:
            store_name = store_match.group(1).strip()
        else:
            ps_match = re.search(r'Datos del Parcel Shop\s*[:\n]?\s*([^\n]+)', plain_text, re.IGNORECASE)
            if ps_match:
                store_name = ps_match.group(1).strip()
            else:
                sub_match = re.search(r'en\s+(PS\s+GLS[^\n]+)', subject, re.IGNORECASE)
                if sub_match:
                    store_name = sub_match.group(1).strip()

        # 3. Address
        address = ""
        # In GLS emails:
        # Datos del Parcel Shop
        # PS GLS DIS SUPREMOS BARBERSHOP
        # AVENIDA GASPAR AGUILAR, 29, NAN
        # 46007
        # ,
        # VALENCIA
        addr_block_match = re.search(
            r'Datos del Parcel Shop\s*\n+[^\n]+\s*\n+([^\n]+)\s*\n+(\d{5})\s*\n*,\s*\n*([^\n]+)',
            plain_text,
            re.IGNORECASE
        )
        if addr_block_match:
            street = addr_block_match.group(1).strip()
            # Clean up trailing artifact like ", NAN"
            street = re.sub(r',\s*NAN\s*$', '', street, flags=re.IGNORECASE).strip()
            postal = addr_block_match.group(2).strip()
            city = addr_block_match.group(3).strip()
            address = f"{street}, {postal} {city}"
        else:
            # Fallback pattern for street & postal code
            street_match = re.search(r'([A-Za-zÁÉÍÓÚáéíóúñÑ\s]+,\s*\d+[^,\n]*)\s*\n+(\d{5})', plain_text)
            if street_match:
                address = f"{street_match.group(1).strip()}, {street_match.group(2).strip()}"

        # 4. Deadline
        deadline = None
        dead_match = re.search(r'Tienes hasta el\s*[:\n]?\s*(\d{2}/\d{2}/\d{4})', plain_text, re.IGNORECASE)
        if dead_match:
            deadline = dead_match.group(1).strip()

        # 5. PIN / Pickup code
        pickup_code = None
        pin_match = re.search(r'este c[oó]digo PIN\s*[:\n]?\s*(\d+)', plain_text, re.IGNORECASE)
        if pin_match:
            pickup_code = pin_match.group(1).strip()

        # 6. QR Code URL
        qr_url = None
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if 'qr.gls-spain.es' in src or 'barcode' in src.lower() or 'qr' in src.lower():
                # Avoid social media or tracking pixel
                if 'social' not in src.lower() and 'open.aspx' not in src.lower():
                    qr_url = src
                    break

        # 7. Merchant
        merchant = "GLS"
        merchant_match = re.search(r'Tu env[ií]o de\s*[:\n]?\s*([^\n]+?)\s*\n+con n[°º] de seguimiento', plain_text, re.IGNORECASE)
        if merchant_match:
            merchant = merchant_match.group(1).strip()

        return ShipmentInfo.create(
            courier="GLS",
            store_name=store_name,
            address=address or "See Google Maps",
            merchant=merchant,
            tracking_number=tracking_number,
            pickup_code=pickup_code,
            deadline=deadline,
            qr_code_url=qr_url
        )
