const fs = require("fs");
const path = require("path");

const LOG_DIR = path.resolve(__dirname, "..", "..", "logs");
const WHATSAPP_LOG = path.join(LOG_DIR, "whatsapp.log");
const BACKEND_LOG = path.join(LOG_DIR, "backend.log");
const ERROR_LOG = path.join(LOG_DIR, "errors.log");

function ensureLogFiles() {
  fs.mkdirSync(LOG_DIR, { recursive: true });
  [WHATSAPP_LOG, BACKEND_LOG, ERROR_LOG].forEach((targetPath) => {
    if (!fs.existsSync(targetPath)) {
      fs.writeFileSync(targetPath, "", "utf8");
    }
  });
}

function formatContext(context) {
  if (!context || Object.keys(context).length === 0) {
    return "";
  }

  try {
    return ` | context=${JSON.stringify(context)}`;
  } catch (_error) {
    return "";
  }
}

function writeLine(targetPath, level, scope, message, context = {}) {
  ensureLogFiles();
  const line = `${new Date().toISOString()} | ${level} | ${scope} | ${message}${formatContext(context)}\n`;
  fs.appendFileSync(targetPath, line, "utf8");
}

function logWhatsAppInfo(scope, message, context = {}) {
  writeLine(WHATSAPP_LOG, "INFO", scope, message, context);
}

function logWhatsAppWarn(scope, message, context = {}) {
  writeLine(WHATSAPP_LOG, "WARN", scope, message, context);
}

function logWhatsAppError(scope, message, error, context = {}) {
  const mergedContext = {
    ...context,
    error: error instanceof Error ? error.message : String(error || ""),
  };
  writeLine(WHATSAPP_LOG, "ERROR", scope, message, mergedContext);
  writeLine(ERROR_LOG, "ERROR", scope, message, mergedContext);
}

function logBackendRelay(scope, message, context = {}) {
  writeLine(BACKEND_LOG, "INFO", scope, message, context);
}

module.exports = {
  ensureLogFiles,
  logBackendRelay,
  logWhatsAppError,
  logWhatsAppInfo,
  logWhatsAppWarn,
};
