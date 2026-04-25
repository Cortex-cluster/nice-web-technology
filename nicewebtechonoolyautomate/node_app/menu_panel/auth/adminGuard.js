function normalizeWhatsAppNumber(rawValue) {
  return String(rawValue || "").replace(/\D/g, "");
}

function normalizeWhatsAppId(rawValue) {
  return String(rawValue || "").trim().toLowerCase();
}

function extractSenderNumber(messageFrom) {
  return normalizeWhatsAppId(messageFrom).split("@")[0].replace(/\D/g, "");
}

function isAuthorizedSender({ messageFrom, authorizedNumber, authorizedId }) {
  const normalizedId = normalizeWhatsAppId(messageFrom);
  const senderNumber = extractSenderNumber(messageFrom);
  return Boolean(normalizedId)
    && Boolean(authorizedNumber)
    && Boolean(authorizedId)
    && normalizedId === normalizeWhatsAppId(authorizedId)
    && senderNumber === normalizeWhatsAppNumber(authorizedNumber);
}

module.exports = {
  extractSenderNumber,
  isAuthorizedSender,
  normalizeWhatsAppId,
  normalizeWhatsAppNumber,
};
