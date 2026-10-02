const { default: makeWASocket, useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion, Browsers } = require('@whiskeysockets/baileys');
const { usePostgresAuthState } = require('./postgres_auth');
const QRCode = require('qrcode');
const qrcodeTerminal = require('qrcode-terminal');
const express = require('express');
const pino = require('pino');
const fs = require('fs');
const path = require('path');

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 3000;
const AUTH_DIR = path.join(__dirname, 'auth_info');
const QR_FILE = path.join(__dirname, 'qr.png');

let sock = null;
let isConnected = false;
let qrDataUrl = null;
let currentQrRaw = null;

async function startWhatsApp() {
  let authResult;
  if (process.env.DATABASE_URL) {
    console.log('🐘 Connecting to PostgreSQL for persistent WhatsApp session...');
    authResult = await usePostgresAuthState(process.env.DATABASE_URL);
  } else {
    authResult = await useMultiFileAuthState(AUTH_DIR);
  }
  const { state, saveCreds } = authResult;
  const { version } = await fetchLatestBaileysVersion();

  sock = makeWASocket({
    version,
    logger: pino({ level: 'silent' }),
    printQRInTerminal: false,
    auth: state,
    browser: Browsers.macOS('Desktop'),
    syncFullHistory: false
  });

  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('connection.update', async (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      currentQrRaw = qr;
      console.log('\n======================================================');
      console.log('NEW LIVE QR CODE (WhatsApp > Settings > Linked Devices):');
      console.log('======================================================\n');
      qrcodeTerminal.generate(qr, { small: true });
      console.log('======================================================\n');
      
      try {
        qrDataUrl = await QRCode.toDataURL(qr, { width: 380, margin: 2 });
        await QRCode.toFile(QR_FILE, qr, { width: 380, margin: 2 });
      } catch (err) {
        console.error('Failed to encode QR image:', err);
      }
    }

    if (connection === 'close') {
      isConnected = false;
      const statusCode = lastDisconnect?.error?.output?.statusCode;
      const shouldReconnect = statusCode !== DisconnectReason.loggedOut;
      console.log(`WhatsApp connection closed (Status: ${statusCode}). Reconnecting: ${shouldReconnect}`);
      if (shouldReconnect) {
        setTimeout(startWhatsApp, 3000);
      }
    } else if (connection === 'open') {
      isConnected = true;
      qrDataUrl = null;
      currentQrRaw = null;
      if (fs.existsSync(QR_FILE)) {
        try { fs.unlinkSync(QR_FILE); } catch(e){}
      }
      console.log('🎉 WhatsApp successfully linked and authenticated!');
    }
  });

  // Automatically welcome new participants added to the group
  sock.ev.on('group-participants.update', async (update) => {
    const { id, participants, action } = update;
    if (action === 'add') {
      for (const participant of participants) {
        try {
          const userTag = `@${participant.split('@')[0]}`;
          const welcomeMsg = 
            `👋 ¡Bienvenido/a ${userTag} a *🌐 Fruteria Internacional 🍊*!\n` +
            `👋 Вітаємо ${userTag} у нашій групі сповіщень!\n\n` +
            `🇪🇸 Este grupo avisa automáticamente cuando llega un paquete de la familia listo para recoger.\n` +
            `🇺🇦 Ця група автоматично сповіщає, коли прибула посилка для сімʼї, готова до отримання.\n\n` +
            `📋 *En cada aviso / У кожному сповіщенні:*\n` +
            `• 📍 Punto de recogida y Google Maps / Назва пункту та посилання на мапу\n` +
            `• 🔑 Código PIN o QR / PIN-код або QR-код для отримання\n` +
            `• 🏪 Puntos habituales / Наші точки видачі:\n` +
            `   - 🇺🇾 *Supermercado Coaliment* (Calle Carcagente, 14)\n` +
            `   - 👳‍♂️ *Frutería Internacional* (Av. Gaspar Aguilar, 13)\n` +
            `   - 🌿 *Herbolario Estrella Psicotrónica* (Gaspar Aguilar, 25)\n\n` +
            `💡 _¿Pasas cerca? ¡Avisa y recógelo! / Хтось проходить поруч? Маякніть у групу та заберіть!_ 🏃💨`;

          await sock.sendMessage(id, {
            text: welcomeMsg,
            mentions: [participant]
          });
          console.log(`Sent welcome instructions to ${participant} in group ${id}`);
        } catch (err) {
          console.error('Failed to send welcome message:', err);
        }
      }
    }
  });
}

// Live interactive QR Page (auto-refreshes every 2 seconds until linked)
app.get('/qr', (req, res) => {
  if (isConnected) {
    return res.send(`
      <!DOCTYPE html>
      <html>
      <head><title>WhatsApp Connected</title><meta charset="utf-8"></head>
      <body style="font-family: -apple-system, sans-serif; text-align: center; padding: 50px;">
        <h1 style="color: #25D366;">✅ WhatsApp is Linked & Connected!</h1>
        <p>You can close this tab and return to the assistant.</p>
      </body>
      </html>
    `);
  }

  res.send(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>Link WhatsApp</title>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f0f2f5; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }
        .card { background: white; padding: 32px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); text-align: center; max-width: 420px; }
        h2 { margin-top: 0; color: #111b21; }
        p { color: #54656f; font-size: 14px; line-height: 1.5; }
        .qr-box { background: white; padding: 12px; border-radius: 12px; display: inline-block; margin: 16px 0; border: 1px solid #e9edef; }
        img { display: block; width: 280px; height: 280px; }
        .badge { background: #e7fce3; color: #008069; padding: 6px 12px; border-radius: 20px; font-size: 13px; font-weight: 500; display: inline-block; margin-bottom: 12px; }
      </style>
      <script>
        setInterval(async () => {
          try {
            const res = await fetch('/status');
            const data = await res.json();
            if (data.connected) {
              window.location.reload();
            } else {
              document.getElementById('qr-img').src = '/qr.png?t=' + Date.now();
            }
          } catch(e) {}
        }, 2000);
      </script>
    </head>
    <body>
      <div class="card">
        <div class="badge">Live Connection Ready</div>
        <h2>Link ShippingAssistant</h2>
        <p>1. Open WhatsApp on your phone<br>2. Tap <b>Settings</b> &rarr; <b>Linked Devices</b> &rarr; <b>Link a Device</b><br>3. Scan this QR code:</p>
        <div class="qr-box">
          <img id="qr-img" src="/qr.png?t=${Date.now()}" alt="QR Code" />
        </div>
        <p style="font-size: 12px; color: #8696a0;">This code updates live automatically. Point your camera now.</p>
      </div>
    </body>
    </html>
  `);
});

app.get('/qr.png', (req, res) => {
  if (fs.existsSync(QR_FILE)) {
    res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate, private');
    return res.sendFile(QR_FILE);
  }
  res.status(404).send('QR not generated yet');
});

// Health / Status endpoint
app.get('/status', (req, res) => {
  res.json({
    connected: isConnected,
    hasQR: !!currentQrRaw
  });
});

// List all groups to help user find family group ID
app.get('/groups', async (req, res) => {
  if (!sock || !isConnected) {
    return res.status(503).json({ error: 'WhatsApp is not connected yet.' });
  }

  try {
    const chats = await sock.groupFetchAllParticipating();
    const groups = Object.values(chats).map(g => ({
      id: g.id,
      subject: g.subject,
      participantsCount: g.participants?.length || 0
    }));
    res.json({ groups });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Send message (text and/or image) to a target (group or direct number)
app.post('/send', async (req, res) => {
  if (!sock || !isConnected) {
    return res.status(503).json({ error: 'WhatsApp is not connected yet.' });
  }

  const { target, message, imageUrl, imagePath } = req.body;
  if (!target) {
    return res.status(400).json({ error: 'Target JID (phone@s.whatsapp.net or group@g.us) is required.' });
  }

  try {
    let sendTarget = target.trim();
    if (!sendTarget.includes('@')) {
      sendTarget = `${sendTarget}@s.whatsapp.net`;
    }

    let result;
    if (imagePath && fs.existsSync(imagePath)) {
      const buffer = fs.readFileSync(imagePath);
      result = await sock.sendMessage(sendTarget, {
        image: buffer,
        caption: message || ''
      });
    } else if (imageUrl) {
      result = await sock.sendMessage(sendTarget, {
        image: { url: imageUrl },
        caption: message || ''
      });
    } else {
      result = await sock.sendMessage(sendTarget, {
        text: message
      });
    }

    res.json({ success: true, messageId: result?.key?.id });
  } catch (err) {
    console.error('Failed to send message:', err);
    res.status(500).json({ error: err.message });
  }
});

// Set group description
app.post('/set-description', async (req, res) => {
  if (!sock || !isConnected) {
    return res.status(503).json({ error: 'WhatsApp is not connected yet.' });
  }
  const { target, description } = req.body;
  if (!target || !description) {
    return res.status(400).json({ error: 'target and description are required.' });
  }
  try {
    await sock.groupUpdateDescription(target, description);
    res.json({ success: true });
  } catch (err) {
    console.error('Failed to update group description:', err);
    res.status(500).json({ error: err.message });
  }
});

startWhatsApp();

app.listen(PORT, () => {
  console.log(`🚀 WhatsApp Bridge running on http://127.0.0.1:${PORT}`);
});
