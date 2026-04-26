const { Client, LocalAuth } = require("whatsapp-web.js");
const path = require("path");
const qrcode = require("qrcode-terminal");

function createWhatsAppClient(sessionDir) {
  return new Client({
    authStrategy: new LocalAuth({
      dataPath: path.resolve(sessionDir),
    }),
    puppeteer: {
      headless: true,
      args: ["--no-sandbox", "--disable-setuid-sandbox"],
    },
  });
}

function registerAuthLogging(client) {
  client.on("qr", (qr) => {
    console.log("[whatsapp] Scan the QR code below with the admin WhatsApp account:");
    qrcode.generate(qr, { small: true });
  });

  client.on("authenticated", () => {
    console.log("[whatsapp] Session authenticated.");
  });

  client.on("auth_failure", (message) => {
    console.error("[whatsapp] Authentication failed:", message);
  });

  client.on("ready", () => {
    console.log("[whatsapp] Client is ready.");
  });

  client.on("disconnected", (reason) => {
    console.warn("[whatsapp] Client disconnected:", reason);
  });
}

module.exports = {
  createWhatsAppClient,
  registerAuthLogging,
};
