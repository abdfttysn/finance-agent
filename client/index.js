const { default: makeWASocket, useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion } = require('@whiskeysockets/baileys');
const pino = require('pino');
const qrcode = require('qrcode-terminal');
const fs = require('fs');
const path = require('path');

// Load configurations
let config = {
  keywords: [
    "#finsight",
    "catat",
    "input",
    "tambah",
    "bayar",
    "transfer",
    "tagihan",
    "invoice",
    "approve",
    "bukti",
    "dana",
    "saldo",
    "rekening",
    "utang",
    "hutang",
    "cicilan",
    "kewajiban",
    "aset",
    "harta",
    "budget",
    "anggaran",
    "limit",
    "sisa",
    "laporan",
    "analisa",
    "analisis",
    "tren",
    "net worth",
    "runway",
    "kekayaan",
    "keuangan",
    "warning",
    "dashboard",
    "ringkasan",
    "pengeluaran",
    "pemasukan",
    "transaksi",
    "riwayat"
  ],
  monitorAllGroups: true,
  targetGroups: [],
  webhookUrl: "",
  triggersDir: "../shared/triggers"
};

const configPath = path.join(__dirname, 'config.json');
if (fs.existsSync(configPath)) {
  try {
    config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
    console.log('Configuration loaded successfully.');
  } catch (error) {
    console.error('Error reading config.json, using defaults:', error.message);
  }
}

// Ensure triggers directory exists
const resolvedTriggersDir = path.resolve(__dirname, config.triggersDir);
if (!fs.existsSync(resolvedTriggersDir)) {
  fs.mkdirSync(resolvedTriggersDir, { recursive: true });
  console.log(`Created triggers directory at: ${resolvedTriggersDir}`);
}

// Group metadata cache
const groupCache = {};

async function connectToWhatsApp() {
  console.log('Fetching latest WhatsApp Web version...');
  let version = [2, 3000, 1017531287]; // Fallback version
  let isLatest = false;
  try {
    const latest = await fetchLatestBaileysVersion();
    version = latest.version;
    isLatest = latest.isLatest;
    console.log(`Using WhatsApp Web v${version.join('.')}, isLatest: ${isLatest}`);
  } catch (error) {
    console.warn('Failed to fetch latest WhatsApp version, using fallback:', error.message);
  }

  console.log('Initializing WhatsApp connection...');

  // Create authentication folder inside the client directory
  const { state, saveCreds } = await useMultiFileAuthState(path.join(__dirname, 'auth_info_baileys'));

  const sock = makeWASocket({
    version,
    logger: pino({ level: 'silent' }), // Suppress detailed library logging
    printQRInTerminal: false,          // We will print QR code manually below for better control
    auth: state
  });

  // Save session credentials on updates
  sock.ev.on('creds.update', saveCreds);

  // Monitor connection status
  sock.ev.on('connection.update', async (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      console.log('\n--- SCAN THIS QR CODE WITH YOUR WHATSAPP TO CONNECT ---');
      qrcode.generate(qr, { small: true });
      console.log('-------------------------------------------------------\n');
    }

    if (connection === 'close') {
      const statusCode = lastDisconnect?.error?.output?.statusCode;
      const shouldReconnect = statusCode !== DisconnectReason.loggedOut;
      console.log(`Connection closed due to: ${lastDisconnect?.error || 'unknown reason'}. Reconnecting: ${shouldReconnect}`);
      if (shouldReconnect) {
        connectToWhatsApp();
      } else {
        console.log('Connection closed permanently because you logged out.');
      }
    } else if (connection === 'open') {
      console.log('\n========================================');
      console.log('WhatsApp Agent successfully CONNECTED!');
      console.log(`Monitoring keywords: ${JSON.stringify(config.keywords)}`);
      console.log('========================================\n');
    }
  });

  // Helper to extract message text
  function getMessageText(message) {
    if (!message) return '';
    return message.conversation ||
      message.extendedTextMessage?.text ||
      message.imageMessage?.caption ||
      message.videoMessage?.caption ||
      '';
  }

  // Helper to get group subject (name)
  async function getGroupSubject(jid) {
    if (!jid.endsWith('@g.us')) return 'Direct Message';
    if (groupCache[jid]) return groupCache[jid];

    try {
      const metadata = await sock.groupMetadata(jid);
      groupCache[jid] = metadata.subject;
      return metadata.subject;
    } catch (e) {
      // In case we can't fetch metadata immediately, return the JID
      return jid;
    }
  }

  // Handle incoming messages
  sock.ev.on('messages.upsert', async ({ messages, type }) => {
    // Only process new messages
    if (type !== 'notify') return;

    for (const msg of messages) {
      try {
        // Ignore messages sent by the agent itself
        if (msg.key.fromMe) continue;

        const chatJid = msg.key.remoteJid;
        const isGroup = chatJid.endsWith('@g.us');

        // We only monitor group chats
        if (!isGroup) continue;

        // Apply group filters if configured to monitor only specific groups
        if (!config.monitorAllGroups && Array.isArray(config.targetGroups) && config.targetGroups.length > 0) {
          const isTarget = config.targetGroups.some(target =>
            target === chatJid || (groupCache[chatJid] && groupCache[chatJid].toLowerCase().includes(target.toLowerCase()))
          );
          if (!isTarget) continue;
        }

        const text = getMessageText(msg.message);
        if (!text) continue;

        // Check for keywords
        const lowerText = text.toLowerCase();
        const matchedKeyword = config.keywords.find(keyword =>
          lowerText.includes(keyword.toLowerCase())
        );

        if (matchedKeyword) {
          const groupName = await getGroupSubject(chatJid);
          const senderJid = msg.key.participant || msg.key.remoteJid;
          const senderName = msg.pushName || 'Unknown Sender';
          const timestamp = new Date(msg.messageTimestamp * 1000 || Date.now());

          console.log(`\n[TRIGGER MATCHED]`);
          console.log(`- Group: ${groupName} (${chatJid})`);
          console.log(`- Sender: ${senderName} (${senderJid})`);
          console.log(`- Keyword: "${matchedKeyword}"`);
          console.log(`- Time: ${timestamp.toISOString()}`);
          console.log(`- Message: "${text}"`);

          const triggerEvent = {
            id: msg.key.id,
            timestamp: timestamp.toISOString(),
            keyword: matchedKeyword,
            group: {
              jid: chatJid,
              name: groupName
            },
            sender: {
              jid: senderJid,
              name: senderName
            },
            message: text,
            processed: false
          };

          // Save trigger event to triggers directory
          const filename = `trigger_${msg.key.id}_${timestamp.getTime()}.json`;
          const filePath = path.join(resolvedTriggersDir, filename);

          fs.writeFileSync(filePath, JSON.stringify(triggerEvent, null, 2));
          console.log(`Trigger saved to file: ${filePath}`);

          // Trigger webhook if URL is provided
          if (config.webhookUrl) {
            try {
              console.log(`Sending webhook request to ${config.webhookUrl}...`);
              const response = await fetch(config.webhookUrl, {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json'
                },
                body: JSON.stringify(triggerEvent)
              });

              if (response.ok) {
                console.log('Webhook triggered successfully.');
                const resData = await response.json();
                if (resData.success && resData.answer) {
                  console.log(`Sending answer back to WhatsApp: "${resData.answer}"`);
                  await sock.sendMessage(chatJid, { text: resData.answer }, { quoted: msg });
                } else {
                  console.warn('Webhook success flag was false or answer was empty.');
                }
              } else {
                console.warn(`Webhook responded with status: ${response.status}`);
              }
            } catch (webhookError) {
              console.error('Failed to trigger webhook:', webhookError.message);
            }
          }
        }
      } catch (err) {
        console.error('Error processing message:', err);
      }
    }
  });
}

connectToWhatsApp().catch(err => {
  console.error('Failed to start WhatsApp Connection:', err);
});
