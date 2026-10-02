import requests
import os
import tempfile
import time
from typing import Optional
from .base import BaseNotifier
from extractors.base import ShipmentInfo

class WhatsAppBridgeNotifier(BaseNotifier):
    def __init__(self, bridge_url: str, target_jid: str):
        self.bridge_url = bridge_url.rstrip('/')
        self.target_jid = target_jid

    def is_bridge_ready(self) -> bool:
        try:
            res = requests.get(f"{self.bridge_url}/status", timeout=5)
            if res.status_code == 200:
                data = res.json()
                return data.get("connected", False)
            return False
        except Exception:
            return False

    def list_groups(self) -> list:
        try:
            res = requests.get(f"{self.bridge_url}/groups", timeout=10)
            if res.status_code == 200:
                return res.json().get("groups", [])
            return []
        except Exception as e:
            print(f"Error fetching WhatsApp groups: {e}")
            return []

    def send(self, info: ShipmentInfo) -> bool:
        message_text = info.format_whatsapp_message()
        payload = {
            "target": self.target_jid,
            "message": message_text
        }

        # If we have a QR code image URL, download it to ensure clean delivery
        temp_img_file = None
        if info.qr_code_url:
            try:
                img_res = requests.get(
                    info.qr_code_url,
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=10
                )
                if img_res.status_code == 200 and len(img_res.content) > 100:
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                        f.write(img_res.content)
                        temp_img_file = f.name
                    payload["imagePath"] = temp_img_file
            except Exception as e:
                print(f"Warning: Failed to pre-download QR image, using URL fallback: {e}")
                payload["imageUrl"] = info.qr_code_url

        for attempt in range(1, 4):
            try:
                res = requests.post(f"{self.bridge_url}/send", json=payload, timeout=20)
                if res.status_code == 200 and res.json().get("success"):
                    print(f"✅ Notification sent to WhatsApp target ({self.target_jid})")
                    return True
                else:
                    print(f"⚠️ Attempt {attempt}: Bridge returned {res.status_code} - {res.text}. Retrying in 3s...")
                    time.sleep(3)
            except Exception as e:
                print(f"⚠️ Attempt {attempt}: Error connecting to bridge: {e}. Retrying in 3s...")
                time.sleep(3)
            finally:
                if temp_img_file and os.path.exists(temp_img_file):
                    try:
                        os.remove(temp_img_file)
                    except Exception:
                        pass
        return False
