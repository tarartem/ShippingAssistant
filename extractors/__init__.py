from typing import Optional
from bs4 import BeautifulSoup
from .base import ShipmentInfo
from .inpost import InPostExtractor
from .seur import SeurExtractor
from .vinted_go import VintedGoExtractor
from .generic import GenericExtractor
import email.header

# InPost and SEUR take priority because their notifications are often relayed via Vinted
ALL_EXTRACTORS = [
    InPostExtractor,
    SeurExtractor,
    VintedGoExtractor,
    GenericExtractor
]

def decode_mime_words(raw_header: str) -> str:
    if not raw_header:
        return ""
    decoded_fragments = email.header.decode_header(raw_header)
    result = []
    for fragment, encoding in decoded_fragments:
        if isinstance(fragment, bytes):
            result.append(fragment.decode(encoding or "utf-8", errors="ignore"))
        else:
            result.append(str(fragment))
    return "".join(result)

def extract_shipment(raw_subject: str, raw_sender: str, html: str, text: str = "") -> Optional[ShipmentInfo]:
    subject = decode_mime_words(raw_subject)
    sender = decode_mime_words(raw_sender)

    if not text and html:
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text('\n', strip=True)

    for extractor in ALL_EXTRACTORS:
        if extractor.can_handle(subject, sender, html, text):
            info = extractor.extract(subject, sender, html, text)
            if info:
                return info
    return None
