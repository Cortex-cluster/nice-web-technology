const path = require("path");
const qrcode = require("qrcode-terminal");
const { Client, LocalAuth } = require("whatsapp-web.js");
const { logWhatsAppError, logWhatsAppInfo, logWhatsAppWarn } = require("../logging");

function createWhatsAppClient(sessionDir) {
  return new Client({
    authStrategy: new LocalAuth({
      dataPath: path.resolve(__dirname, "..", "..", sessionDir),
    }),
    puppeteer: {
      headless: true,
      args: ["--no-sandbox", "--disable-setuid-sandbox"],
    },
  });
}

function registerWhatsAppLogging(client) {
  client.on("qr", (qr) => {
    logWhatsAppInfo("auth.qr", "Scan the QR code with the authorized admin WhatsApp account.");
    qrcode.generate(qr, { small: true });
  });

  client.on("authenticated", () => {
    logWhatsAppInfo("auth.authenticated", "WhatsApp session authenticated.");
  });

  client.on("ready", () => {
    logWhatsAppInfo("auth.ready", "WhatsApp client is ready.");
  });

  client.on("auth_failure", (message) => {
    logWhatsAppError("auth.failure", "WhatsApp authentication failure.", new Error(String(message || "Unknown auth failure.")));
  });

  client.on("disconnected", (reason) => {
    logWhatsAppWarn("auth.disconnected", "WhatsApp client disconnected.", { reason });
  });
}

module.exports = {
  createWhatsAppClient,
  registerWhatsAppLogging,
};
