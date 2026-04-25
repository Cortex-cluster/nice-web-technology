function normalizeWhatsAppNumber(rawValue) {
  return String(rawValue || "").replace(/\D/g, "");
}

function extractSenderNumber(messageFrom) {
  return String(messageFrom || "").split("@")[0].replace(/\D/g, "");
}

function isAuthorizedSender(messageFrom, authorizedNumber) {
  return extractSenderNumber(messageFrom) === normalizeWhatsAppNumber(authorizedNumber);
}

module.exports = {
  normalizeWhatsAppNumber,
  extractSenderNumber,
  isAuthorizedSender,
};
