const { loadConfig } = require("./menu_panel/config");
const { isAuthorizedSender } = require("./menu_panel/auth/adminGuard");
const { AdminPanelController } = require("./menu_panel/controller/adminPanelController");
const {
  ensureLogFiles,
  logWhatsAppError,
  logWhatsAppInfo,
  logWhatsAppWarn,
} = require("./menu_panel/logging");
const { createHealthServer } = require("./menu_panel/server/healthServer");
const { PanelBackendClient } = require("./menu_panel/services/backendClient");
const { FlowStateStore } = require("./menu_panel/services/flowStateStore");
const {
  createWhatsAppClient,
  registerWhatsAppLogging,
} = require("./menu_panel/whatsapp/clientFactory");

const config = loadConfig();

ensureLogFiles();

let whatsappAuthenticated = false;

const client = createWhatsAppClient(config.whatsappSessionDir);
const backendClient = new PanelBackendClient({
  baseURL: config.pythonBackendUrl,
  timeoutMs: config.requestTimeoutMs,
});
const stateStore = new FlowStateStore({ ttlMs: config.flowStateTtlMs });
const controller = new AdminPanelController({
  backendClient,
  stateStore,
});

registerWhatsAppLogging(client);

if (!config.authorizedWhatsAppNumber || !config.authorizedWhatsAppId) {
  logWhatsAppWarn(
    "startup.auth",
    "AUTHORIZED_WHATSAPP_NUMBER or AUTHORIZED_WHATSAPP_ID is missing. Incoming messages will be ignored.",
    {
      hasAuthorizedNumber: Boolean(config.authorizedWhatsAppNumber),
      hasAuthorizedId: Boolean(config.authorizedWhatsAppId),
    }
  );
}

client.on("authenticated", () => {
  whatsappAuthenticated = true;
});

client.on("ready", () => {
  whatsappAuthenticated = true;
});

client.on("auth_failure", (message) => {
  whatsappAuthenticated = false;
  logWhatsAppError("auth.failure", "WhatsApp authentication failed.", new Error(String(message || "Unknown auth failure.")));
});

client.on("disconnected", (reason) => {
  whatsappAuthenticated = false;
  logWhatsAppWarn("auth.disconnected", "WhatsApp client disconnected.", { reason });
});

client.on("message", async (message) => {
  try {
    if (
      !isAuthorizedSender({
        messageFrom: message.from,
        authorizedNumber: config.authorizedWhatsAppNumber,
        authorizedId: config.authorizedWhatsAppId,
      })
    ) {
      logWhatsAppWarn("security.unauthorized", "Unauthorized WhatsApp access attempt ignored.", {
        from: message.from,
      });
      return;
    }

    logWhatsAppInfo("message.received", "Authorized admin message received.", {
      from: message.from,
      body: String(message.body || "").slice(0, 250),
    });

    await controller.handleMessage(message, {
      whatsappAuthenticated,
    });
  } catch (error) {
    logWhatsAppError("message.handler", "Admin panel message handling failed.", error, {
      from: message.from,
    });
    try {
      await message.reply(error.message || "Unexpected WhatsApp controller error. Please try again.");
    } catch (replyError) {
      logWhatsAppError("message.reply", "Failed to send error reply.", replyError, {
        from: message.from,
      });
    }
  }
});

createHealthServer({
  port: config.port,
  getState: () => ({
    whatsappAuthenticated,
    authorizedNumberConfigured: Boolean(config.authorizedWhatsAppNumber),
    authorizedIdConfigured: Boolean(config.authorizedWhatsAppId),
    pythonBackendUrl: config.pythonBackendUrl,
  }),
});

client.initialize().catch((error) => {
  logWhatsAppError("startup.initialize", "WhatsApp client initialization failed.", error);
  process.exitCode = 1;
});
