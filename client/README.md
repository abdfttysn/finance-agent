# WhatsApp Monitor Client

A Node.js agent that monitors WhatsApp group chats for specific trigger keywords. When a match is detected, the agent logs it, saves the details as a JSON file in a shared directory (for a worker to consume later), and optionally calls a webhook.

## Prerequisites

- Node.js (v18 or higher recommended. Currently using v22.18.0)
- NPM (v9 or higher recommended)

## Installation

1. Open your terminal.
2. Navigate to the `client` directory:
   ```bash
   cd client
   ```
3. Install dependencies:
   ```bash
   npm install
   ```

## Configuration

Edit `config.json` to customize the behavior of the agent:

```json
{
  "keywords": [
    "bayar",
    "transfer",
    "invoice",
    "tagihan",
    "approve",
    "bukti",
    "dana"
  ],
  "monitorAllGroups": true,
  "targetGroups": [],
  "webhookUrl": "",
  "triggersDir": "../shared/triggers",
  "triggerOnDirectMessage": true,
  "triggerOnMention": true,
  "triggerOnKeywords": true
}
```

### Configuration Options:
- **`keywords`**: An array of case-insensitive keywords that trigger the agent when found in a message.
- **`monitorAllGroups`**: Set to `true` to listen to all WhatsApp groups you are in. Set to `false` to restrict monitoring.
- **`targetGroups`**: If `monitorAllGroups` is `false`, populate this with group JIDs (e.g., `120363123456789012@g.us`) or matching substring group names you wish to monitor.
- **`webhookUrl`**: Optional. A POST endpoint to notify when a keyword is matched.
- **`triggersDir`**: Directory path where matched messages are written as JSON files.
- **`triggerOnDirectMessage`**: If `true`, any private chat (DM/japri) sent to the bot will trigger the AI directly without requiring keywords.
- **`triggerOnMention`**: If `true`, mentioning the bot's number in a group chat will trigger the AI directly.
- **`triggerOnKeywords`**: If `true`, keywords found in group chats will continue to trigger the AI.

## Running the Agent

Start the agent:
```bash
npm start
```

### Authentication:
1. On the first startup, a QR code will print in the console.
2. Open WhatsApp on your phone -> Go to **Linked Devices** -> tap **Link a Device**.
3. Scan the QR code in your terminal.
4. Once scanned, authentication credentials are saved in the `auth_info_baileys/` folder so you won't need to scan it again on subsequent restarts.

## Trigger Event Format

Matched messages are saved as JSON files in the `triggersDir` folder:

```json
{
  "id": "3EB0ABC1234567890DEF",
  "timestamp": "2026-06-25T08:15:30.000Z",
  "keyword": "tagihan",
  "group": {
    "jid": "120363000000000000@g.us",
    "name": "Finance Team"
  },
  "sender": {
    "jid": "628123456789@s.whatsapp.net",
    "name": "Budi"
  },
  "message": "Tolong bayarkan tagihan ini secepatnya ya.",
  "processed": false
}
```
These files can then be processed by the worker component in the future.
