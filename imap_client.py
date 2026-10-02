import imaplib
import ssl
import certifi
import email
from typing import List, Tuple, Optional
import config
from database import is_processed, mark_processed
from extractors import extract_shipment, decode_mime_words
from extractors.base import ShipmentInfo
from notifiers.base import BaseNotifier

class GmailShippingMonitor:
    def __init__(self, notifier: BaseNotifier):
        self.notifier = notifier
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())

    def connect(self) -> imaplib.IMAP4_SSL:
        mail = imaplib.IMAP4_SSL(
            config.GMAIL_IMAP_SERVER,
            port=config.GMAIL_IMAP_PORT,
            ssl_context=self.ssl_context
        )
        mail.login(config.GMAIL_USER, config.GMAIL_APP_PASSWORD)
        return mail

    def check_inbox(self, max_scan: int = 25) -> int:
        """
        Scans inbox for recent shipping emails, extracts pickup details,
        and sends notifications.
        Returns the count of new shipments processed.
        """
        processed_count = 0
        mail = None
        try:
            mail = self.connect()
            mail.select("INBOX")

            # Search ALL emails in the inbox to never miss emails read on mobile/desktop
            status, data = mail.search(None, "ALL")
            msg_ids = data[0].split()

            if not msg_ids:
                if config.DEBUG:
                    print("No candidate emails found.")
                return 0

            # Scan the most recent emails up to max_scan
            recent_ids = msg_ids[-max_scan:]
            if config.DEBUG:
                print(f"Scanning {len(recent_ids)} recent email(s)...")

            for mid_bytes in reversed(recent_ids):
                mid = mid_bytes.decode()
                
                # Check DB cache first (fast PostgreSQL index lookup)
                if is_processed(mid):
                    continue

                # Fetch RFC822
                status, msg_data = mail.fetch(mid, "(RFC822)")
                if status != "OK" or not msg_data or not msg_data[0]:
                    continue

                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                raw_subject = msg.get("Subject", "")
                raw_sender = msg.get("From", "")
                subject = decode_mime_words(raw_subject)
                sender = decode_mime_words(raw_sender)

                # Extract HTML and plain text
                html = ""
                text = ""
                for part in msg.walk():
                    ct = part.get_content_type()
                    disposition = str(part.get("Content-Disposition", ""))
                    if "attachment" in disposition:
                        continue
                    if ct == "text/html" and not html:
                        html = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                    elif ct == "text/plain" and not text:
                        text = part.get_payload(decode=True).decode("utf-8", errors="ignore")

                # Run programmatic extractors
                info: Optional[ShipmentInfo] = extract_shipment(raw_subject, raw_sender, html, text)
                if info:
                    print(f"✨ Detected pickup for {info.courier}: {info.store_name} (Email ID: {mid})")
                    sent = self.notifier.send(info)
                    if sent:
                        mark_processed(
                            email_id=mid,
                            subject=subject,
                            courier=info.courier,
                            tracking_number=info.tracking_number,
                            pickup_code=info.pickup_code
                        )
                        processed_count += 1
                        # Mark as seen on server
                        try:
                            mail.store(mid, "+FLAGS", "\\Seen")
                        except Exception:
                            pass
                else:
                    # Mark non-shipping email as checked so we don't re-download every cycle
                    mark_processed(
                        email_id=mid,
                        subject=subject[:100],
                        courier="SKIPPED"
                    )
                    if config.DEBUG:
                        print(f"Skipping non-pickup email: {subject[:60]} (ID {mid})")

        except Exception as e:
            print(f"Error during inbox check: {e}")
        finally:
            if mail:
                try:
                    mail.close()
                    mail.logout()
                except Exception:
                    pass

        return processed_count
