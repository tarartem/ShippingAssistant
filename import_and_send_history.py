import imaplib
import ssl
import certifi
import email
import time
import sqlite3
from typing import List, Tuple
import config
from database import init_db, mark_processed
from extractors import extract_shipment, decode_mime_words
from notifiers import WhatsAppBridgeNotifier

def main():
    print("==========================================================")
    print("📦 IMPORTING & SENDING 3 MONTHS SHIPMENT ARRIVALS")
    print("==========================================================")
    
    init_db()
    # Reset DB to ensure fresh 3-month synchronization
    with sqlite3.connect(config.os.path.join(config.os.path.dirname(__file__), "processed_emails.db")) as conn:
        conn.execute("DELETE FROM processed_shipments")
        conn.commit()
    print("🧹 Reset processed shipments database for fresh 3-month import.")

    wa = WhatsAppBridgeNotifier(
        bridge_url=config.WHATSAPP_BRIDGE_URL,
        target_jid=config.WHATSAPP_TARGET_GROUP
    )

    if not wa.is_bridge_ready():
        print("❌ Error: WhatsApp Bridge is not connected!")
        return

    ctx = ssl.create_default_context(cafile=certifi.where())
    mail = imaplib.IMAP4_SSL(config.GMAIL_IMAP_SERVER, port=config.GMAIL_IMAP_PORT, ssl_context=ctx)
    mail.login(config.GMAIL_USER, config.GMAIL_APP_PASSWORD)
    mail.select("INBOX", readonly=True)

    queries = [
        '(SUBJECT "liberar espacio")',
        '(SUBJECT "entregado en tu punto")',
        '(SUBJECT "ya puedes recoger")'
    ]

    candidate_ids = set()
    for q in queries:
        status, data = mail.search(None, q)
        if status == "OK" and data[0]:
            for m in data[0].split():
                candidate_ids.add(int(m))

    sorted_ids = sorted(list(candidate_ids))
    print(f"🔍 Found {len(sorted_ids)} candidate arrival emails. Analyzing & extracting...")

    unique_shipments = []
    seen_trackings = set()

    for mid in sorted_ids:
        status, data = mail.fetch(str(mid), "(RFC822)")
        if status != "OK" or not data or not data[0]:
            continue

        msg = email.message_from_bytes(data[0][1])
        subj = decode_mime_words(msg.get("Subject", ""))
        sender = decode_mime_words(msg.get("From", ""))

        html = ""
        text = ""
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/html" and not html:
                html = part.get_payload(decode=True).decode("utf-8", errors="ignore")
            elif ct == "text/plain" and not text:
                text = part.get_payload(decode=True).decode("utf-8", errors="ignore")

        info = extract_shipment(subj, sender, html, text)
        if info:
            track_key = info.tracking_number or f"{info.store_name}_{info.pickup_code}"
            if track_key in seen_trackings:
                # Duplicate email for same shipment
                continue
            seen_trackings.add(track_key)
            unique_shipments.append((str(mid), subj, info))

    print(f"✨ Found {len(unique_shipments)} unique package arrival notifications to send.\n")

    for idx, (mid, subj, info) in enumerate(unique_shipments, 1):
        print(f"[{idx}/{len(unique_shipments)}] Sending: {info.store_name} ({info.courier})")
        print(info.format_whatsapp_message())
        print(f"Has QR Image: {bool(info.qr_code_url)}")
        
        sent = wa.send(info)
        if sent:
            mark_processed(
                email_id=mid,
                subject=subj,
                courier=info.courier,
                tracking_number=info.tracking_number,
                pickup_code=info.pickup_code
            )
            print("✅ Sent to WhatsApp successfully.\n")
        else:
            print("❌ Failed to send.\n")

        # 2-second rate-limit pause between messages
        time.sleep(2)

    mail.logout()
    print("🎉 Finished importing and sending all historical package arrival notifications!")

if __name__ == "__main__":
    main()
