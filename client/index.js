const { default: makeWASocket, useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion } = require('@whiskeysockets/baileys');
const pino = require('pino');
const qrcode = require('qrcode-terminal');
const fs = require('fs');
const path = require('path');

// Load configurations
let config = {
  keywords: [
    "#elingcash",
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
  triggersDir: "../shared/triggers",
  triggerOnDirectMessage: true,
  triggerOnMention: true,
  triggerOnKeywords: true
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

// Allow environment variable to override config values
if (process.env.WEBHOOK_URL) {
  config.webhookUrl = process.env.WEBHOOK_URL;
}

// Ensure triggers directory exists
const resolvedTriggersDir = path.resolve(__dirname, config.triggersDir);
if (!fs.existsSync(resolvedTriggersDir)) {
  fs.mkdirSync(resolvedTriggersDir, { recursive: true });
  console.log(`Created triggers directory at: ${resolvedTriggersDir}`);
}

// Group metadata cache
const groupCache = {};

// OTP Access Control variables
const otpSessionPath = path.resolve(__dirname, config.otpStoragePath || './otp_session.json');
let otpSession = {
  activeOtp: '',
  authorizedNumbers: []
};

function loadOtpSession() {
  if (fs.existsSync(otpSessionPath)) {
    try {
      otpSession = JSON.parse(fs.readFileSync(otpSessionPath, 'utf8'));
      if (!Array.isArray(otpSession.authorizedNumbers)) {
        otpSession.authorizedNumbers = [];
      }
    } catch (error) {
      console.error('Error reading otp_session.json, using defaults:', error.message);
    }
  }
}

function saveOtpSession() {
  try {
    fs.writeFileSync(otpSessionPath, JSON.stringify(otpSession, null, 2), 'utf8');
  } catch (error) {
    console.error('Error writing otp_session.json:', error.message);
  }
}

function generateOtp() {
  // Generate random 5-digit OTP
  return Math.floor(10000 + Math.random() * 90000).toString();
}

async function connectToWhatsApp() {
  if (config.requireOtpAccess) {
    loadOtpSession();
    otpSession.activeOtp = generateOtp();
    saveOtpSession();
    
    console.log('\n=======================================================');
    console.log('[SECURITY] OTP ACCESS CONTROL IS ENABLED!');
    console.log(`[SECURITY] ACTIVE OTP CODE: ${otpSession.activeOtp}`);
    console.log(`[SECURITY] Users must send "${config.otpCommandPrefix}${otpSession.activeOtp}" to register.`);
    console.log('=======================================================\n');
  }

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
      console.log('--- Configuration Settings ---');
      console.log(`- Webhook URL: ${config.webhookUrl}`);
      console.log(`- Triggers Directory: ${config.triggersDir}`);
      console.log(`- Monitor All Groups: ${config.monitorAllGroups}`);
      console.log(`- Target Groups: ${JSON.stringify(config.targetGroups)}`);
      console.log(`- Trigger On Direct Message: ${config.triggerOnDirectMessage}`);
      console.log(`- Trigger On Mention: ${config.triggerOnMention}`);
      console.log(`- Trigger On Keywords: ${config.triggerOnKeywords}`);
      if (config.triggerOnKeywords) {
        console.log(`Monitoring keywords: ${JSON.stringify(config.keywords)}`);
      }
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
        // Ignore status broadcasts
        if (chatJid === 'status@broadcast') continue;

        const isGroup = chatJid.endsWith('@g.us');

        let shouldTrigger = false;
        let triggerReason = '';
        let matchedKeyword = null;

        const text = getMessageText(msg.message);
        if (!text) continue;

        // OTP Access Control check
        if (config.requireOtpAccess) {
          const cleanText = text.trim();
          const senderJid = msg.key.participant || msg.key.remoteJid;

          // Check if it is an OTP registration attempt
          if (cleanText.toLowerCase().startsWith(config.otpCommandPrefix.toLowerCase())) {
            const enteredOtp = cleanText.substring(config.otpCommandPrefix.length).trim();
            loadOtpSession(); // Reload session to get latest data

            if (enteredOtp === otpSession.activeOtp) {
              if (!otpSession.authorizedNumbers.includes(senderJid)) {
                otpSession.authorizedNumbers.push(senderJid);
                saveOtpSession();
              }
              console.log(`[OTP SECURITY] Number registered successfully: ${senderJid}`);
              await sock.sendMessage(chatJid, { text: '✅ Nomor Anda berhasil terverifikasi! Anda sekarang dapat menggunakan AI asisten.' }, { quoted: msg });
            } else {
              console.log(`[OTP SECURITY] Invalid OTP attempt from ${senderJid}: "${enteredOtp}"`);
              await sock.sendMessage(chatJid, { text: '❌ Kode OTP salah atau kedaluwarsa.' }, { quoted: msg });
            }
            continue;
          }

          // Check if sender is authorized
          loadOtpSession();
          const isAuthorized = otpSession.authorizedNumbers.includes(senderJid);

          if (!isAuthorized) {
            const serverJid = sock.user ? sock.user.id.split(':')[0] + '@s.whatsapp.net' : null;
            const mentions = msg.message?.extendedTextMessage?.contextInfo?.mentionedJid || [];
            const isMentioned = serverJid && mentions.includes(serverJid);

            // Only reply to unauthorized messages if in DM or when bot is mentioned in group
            if (!isGroup || isMentioned) {
              console.log(`[OTP SECURITY] Unauthorized message blocked from ${senderJid}`);
              await sock.sendMessage(chatJid, { text: '🔒 Akses dibatasi. Nomor Anda belum terdaftar.\n\nSilakan daftarkan nomor Anda dengan mengirimkan format:\n`#otp:KODE` (Minta kode OTP aktif kepada Admin).' }, { quoted: msg });
            }
            continue;
          }
        }

        if (!isGroup) {
          // Direct Message (Japri)
          if (config.triggerOnDirectMessage) {
            shouldTrigger = true;
            triggerReason = 'direct_message';
          }
        } else {
          // Group Message

          // Apply group filters if configured to monitor only specific groups
          if (!config.monitorAllGroups && Array.isArray(config.targetGroups) && config.targetGroups.length > 0) {
            const isTarget = config.targetGroups.some(target =>
              target === chatJid || (groupCache[chatJid] && groupCache[chatJid].toLowerCase().includes(target.toLowerCase()))
            );
            if (!isTarget) continue;
          }

          // A. Check if bot is mentioned
          const serverJid = sock.user ? sock.user.id.split(':')[0] + '@s.whatsapp.net' : null;
          const mentions = msg.message?.extendedTextMessage?.contextInfo?.mentionedJid || [];
          const isMentioned = serverJid && mentions.includes(serverJid);

          if (isMentioned && config.triggerOnMention) {
            shouldTrigger = true;
            triggerReason = 'mention';
          }

          // B. Check for keywords if mention did not trigger
          if (!shouldTrigger && config.triggerOnKeywords && Array.isArray(config.keywords)) {
            const lowerText = text.toLowerCase();
            matchedKeyword = config.keywords.find(keyword =>
              lowerText.includes(keyword.toLowerCase())
            );
            if (matchedKeyword) {
              shouldTrigger = true;
              triggerReason = 'keyword';
            }
          }
        }

        if (!shouldTrigger) continue;

        const groupName = isGroup ? await getGroupSubject(chatJid) : 'Direct Message';
        const senderJid = msg.key.participant || msg.key.remoteJid;
        const senderName = msg.pushName || 'Unknown Sender';
        const timestamp = new Date(msg.messageTimestamp * 1000 || Date.now());

        console.log(`\n[TRIGGER MATCHED]`);
        console.log(`- Type: ${triggerReason.toUpperCase()}`);
        console.log(`- Chat: ${groupName} (${chatJid})`);
        console.log(`- Sender: ${senderName} (${senderJid})`);
        if (matchedKeyword) {
          console.log(`- Keyword: "${matchedKeyword}"`);
        }
        console.log(`- Time: ${timestamp.toISOString()}`);
        console.log(`- Message: "${text}"`);

        const triggerEvent = {
          id: msg.key.id,
          timestamp: timestamp.toISOString(),
          keyword: matchedKeyword || triggerReason,
          group: isGroup ? {
            jid: chatJid,
            name: groupName
          } : {
            jid: chatJid,
            name: 'Direct Message'
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

                // Update trigger file with response and token usage
                if (fs.existsSync(filePath)) {
                  try {
                    const currentData = JSON.parse(fs.readFileSync(filePath, 'utf8'));
                    currentData.processed = true;
                    currentData.response = resData.answer;
                    currentData.token_usage = resData.token_usage || { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 };

                    fs.writeFileSync(filePath, JSON.stringify(currentData, null, 2), 'utf8');
                    console.log(`[TOKEN HISTORY] Trigger file updated with token usage and response.`);
                    console.log(`- Prompt Tokens: ${currentData.token_usage.prompt_tokens}`);
                    console.log(`- Completion Tokens: ${currentData.token_usage.completion_tokens}`);
                    console.log(`- Total Tokens: ${currentData.token_usage.total_tokens}`);
                  } catch (updateErr) {
                    console.error('Failed to update trigger file with token usage:', updateErr.message);
                  }
                }
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
      } catch (err) {
        console.error('Error processing message:', err);
      }
    }
  });
}

connectToWhatsApp().catch(err => {
  console.error('Failed to start WhatsApp Connection:', err);
});
