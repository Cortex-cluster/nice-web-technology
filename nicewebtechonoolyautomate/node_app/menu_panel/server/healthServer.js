const express = require("express");
const { logWhatsAppInfo } = require("../logging");

function createHealthServer({ port, getState }) {
  const app = express();

  app.get("/health", (_req, res) => {
    res.json({
      ok: true,
      service: "niceweb-admin-control-panel-node",
      ...getState(),
    });
  });

  return app.listen(port, () => {
    logWhatsAppInfo("health.start", "Health endpoint started.", {
      url: `http://127.0.0.1:${port}/health`,
    });
  });
}

module.exports = {
  createHealthServer,
};
