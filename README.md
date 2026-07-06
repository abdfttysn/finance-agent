## Development History & Troubleshooting

### Tools Installed
* **`@whiskeysockets/baileys`**: The core WhatsApp Web API integration library (WebSocket-based).
* **`qrcode-terminal`**: Used to generate and render the login QR code directly in the console.
* **`pino`**: A fast, low-overhead JSON logger required by Baileys.
* **`dotenv`**: Loaded environment variables for the application config.

### Completed Milestones
1. **Repository Setup**: Initialized Node.js environment and installed clean dependencies.
2. **WhatsApp Client Connection**: Configured connection handlers using multi-file auth state (`auth_info_baileys`) for session persistence.
3. **Webhook Integration**: Added automated event triggering to send matched messages to the FastAPI worker endpoint (`/process`).
4. **Automated Group Replies**: Extended the connection logic to receive responses from the worker and reply directly back to the triggering WhatsApp chat thread.

### Encountered Issues & Resolutions
* **Issue**: Connection loop failures on client startup (`Connection closed due to: Error: Connection Failure. Reconnecting: true`).
  * **Cause**: WhatsApp Web periodically updates its client protocol, causing static/outdated Baileys client versions to be rejected by the server.
  * **Resolution**: Replaced the default socket initialization with a dynamic check using `fetchLatestBaileysVersion()` from Baileys. The client now queries the latest WhatsApp Web version during boot, resolving reconnect loops automatically.