require("dotenv").config();

const { createWhatsAppClient, registerAuthLogging } = require("./auth");
const { isAuthorizedSender } = require("./commandRouter");
const { ConversationManager } = require("./handlers");
const { createHealthServer } = require("./webhook");

const AUTHORIZED_WHATSAPP_NUMBER = process.env.AUTHORIZED_WHATSAPP_NUMBER || "";
const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || "http://127.0.0.1:8000";
const PORT = Number.parseInt(process.env.PORT || "3000", 10);
const WHATSAPP_SESSION_DIR = process.env.WHATSAPP_SESSION_DIR || ".wwebjs_auth";

let whatsappAuthenticated = false;

const client = createWhatsAppClient(WHATSAPP_SESSION_DIR);
const manager = new ConversationManager(PYTHON_BACKEND_URL);

registerAuthLogging(client);

client.on("authenticated", () => {
  whatsappAuthenticated = true;
});

client.on("ready", () => {
  whatsappAuthenticated = true;
});

client.on("disconnected", () => {
  whatsappAuthenticated = false;
});

client.on("message", async (message) => {
  try {
    if (!isAuthorizedSender(message.from, AUTHORIZED_WHATSAPP_NUMBER)) {
      return;
    }
    await manager.handleMessage(message, whatsappAuthenticated);
  } catch (error) {
    console.error("[node] Message handling failed:", error.message);
    try {
      await message.reply(`Operation failed: ${error.response?.data?.detail || error.message}`);
    } catch (replyError) {
      console.error("[node] Failed to send error reply:", replyError.message);
    }
  }
});

createHealthServer({
  port: PORT,
  getState: () => ({
    whatsappAuthenticated,
    authorizedNumberConfigured: Boolean(AUTHORIZED_WHATSAPP_NUMBER),
    pythonBackendUrl: PYTHON_BACKEND_URL,
  }),
});

client.initialize().catch((error) => {
  console.error("[whatsapp] Initialization failed:", error);
  process.exitCode = 1;
});
