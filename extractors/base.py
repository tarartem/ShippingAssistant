import urllib.parse
from dataclasses import dataclass
from typing import Optional

STORE_EMOJI_MAP = {
    "herbolario": "🌿",
    "psicotronica": "🌿",
    "coaliment": "🇺🇾",
    "fruteria": "👳‍♂️",
    "frutería": "👳‍♂️"
}

def enrich_store_name(name: str) -> str:
    lower = name.lower()
    for keyword, emoji in STORE_EMOJI_MAP.items():
        if keyword in lower:
            # If emoji not already present, append it
            if emoji not in name:
                return f"{name.strip()} {emoji}"
            return name.strip()
    return name.strip()

@dataclass
class ShipmentInfo:
    courier: str
    store_name: str
    address: str
    maps_url: str
    merchant: str = "Vinted"
    pickup_code: Optional[str] = None
    tracking_number: Optional[str] = None
    deadline: Optional[str] = None
    qr_code_url: Optional[str] = None
    qr_code_path: Optional[str] = None
    recipient_name: Optional[str] = None
    item_details: Optional[str] = None

    @classmethod
    def create(cls, courier: str, store_name: str, address: str, merchant: str = "Vinted", **kwargs):
        clean_addr = address.strip()
        # For Google Maps query, use the clean store name without emojis
        query = f"{store_name.strip()}, {clean_addr}".replace('\n', ' ')
        encoded_query = urllib.parse.quote_plus(query)
        maps_url = f"https://www.google.com/maps/search/?api=1&query={encoded_query}"
        
        # Enriched store name with custom emojis
        decorated_store = enrich_store_name(store_name)

        return cls(courier=courier, store_name=decorated_store, address=clean_addr, maps_url=maps_url, merchant=merchant, **kwargs)

    def format_whatsapp_message(self) -> str:
        """
        Short, clean payload:
        *Package has arrived to <Store Name> <Emoji>*

        🔑 *Pickup code:* <Code>
        📍 *Address:* [<Address>](<Maps Link>)
        🏪 *Merchant:* <Merchant>
        """
        lines = [
            f"*Package has arrived to {self.store_name}*",
            ""
        ]
        
        if self.pickup_code:
            lines.append(f"🔑 *Pickup code:* *{self.pickup_code}*")
            
        lines.append(f"📍 *Address:* [{self.address}]({self.maps_url})")
        
        merchant_name = self.merchant or self.courier
        lines.append(f"🏪 *Merchant:* {merchant_name}")

        return "\n".join(lines)
