# 📦 ShippingAssistant

Automated, **0-token**, **$0 cost** assistant that monitors Gmail for e-commerce shipment notices (Vinted Go, SEUR, InPost, GLS, etc.) and pushes pickup alerts with:
- Store / Pickup Point Name
- Address + Direct Google Maps Link
- Pickup PIN / Numeric Code
- QR Code Image
- Deadline & Tracking Number
to a dedicated **WhatsApp Family Group**.

---

## ⚡ Quick Start

### 1. Verify Email Extraction (Dry Run)
You can run a dry-run test right now against your real Gmail inbox:
```bash
python3 main.py --mode test-scan
```
This inspects recent shipping emails and prints the extracted information to the console without sending notifications or altering email status.

---

### 2. Connect Your WhatsApp

We use an open-source WhatsApp Web gateway powered by `@whiskeysockets/baileys` (MIT license, completely free, private, no third-party cloud vendors).

1. Start the WhatsApp bridge in a separate terminal:
   ```bash
   cd whatsapp_bridge
   node server.js
   ```
2. A QR code will display directly in your terminal.
3. Open WhatsApp on your phone:
   - Go to **Settings** $\rightarrow$ **Linked Devices** $\rightarrow$ **Link a Device**.
   - Scan the terminal QR code.
   - It will say `✅ WhatsApp successfully connected and authenticated!`
4. In another terminal, run:
   ```bash
   python3 check_whatsapp_groups.py
   ```
   This will list all your WhatsApp groups with their IDs (e.g. `120363023456789012@g.us`).
5. Copy your **Family Group ID** and paste it into `.env`:
   ```bash
   WHATSAPP_TARGET_GROUP=120363023456789012@g.us
   ```

---

### 3. Run the Assistant

- **Single Check** (e.g. via cron or scheduled task):
  ```bash
  python3 main.py --mode once
  ```

- **Continuous Background Daemon** (checks every 5 minutes):
  ```bash
  python3 main.py --mode daemon --interval 300
  ```

---

## 🛡️ Architecture & Token Efficiency

- **0 Tokens**: 100% deterministic Python extraction using BeautifulSoup and Regex.
- **Deduplication**: Uses SQLite (`processed_emails.db`) so no email or package is ever notified twice.
- **Privacy**: No intermediate cloud servers holding your email or chat data.
