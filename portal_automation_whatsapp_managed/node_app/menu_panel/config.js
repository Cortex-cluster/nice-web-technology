const fs = require("fs");
const path = require("path");
const dotenv = require("dotenv");

function parseInteger(value, fallbackValue) {
  const parsed = Number.parseInt(String(value || ""), 10);
  return Number.isNaN(parsed) ? fallbackValue : parsed;
}

function loadConfig() {
  const nodeRoot = path.resolve(__dirname, "..");
  const baseEnvPath = path.join(nodeRoot, ".env");
  const panelEnvPath = path.join(nodeRoot, ".env.menu-panel");

  dotenv.config({ path: baseEnvPath });
  if (fs.existsSync(panelEnvPath)) {
    dotenv.config({ path: panelEnvPath, override: true });
  }

  return {
    authorizedWhatsAppNumber: process.env.AUTHORIZED_WHATSAPP_NUMBER || "",
    authorizedWhatsAppId: String(process.env.AUTHORIZED_WHATSAPP_ID || "").trim().toLowerCase(),
    pythonBackendUrl: process.env.PYTHON_BACKEND_URL || "http://127.0.0.1:8001",
    port: parseInteger(process.env.PORT, 3001),
    whatsappSessionDir: process.env.WHATSAPP_SESSION_DIR || ".wwebjs_auth_menu_panel",
    flowStateTtlMs: parseInteger(process.env.FLOW_STATE_TTL_SECONDS, 900) * 1000,
    requestTimeoutMs: parseInteger(process.env.BACKEND_TIMEOUT_MS, 90000),
  };
}

module.exports = {
  loadConfig,
};
