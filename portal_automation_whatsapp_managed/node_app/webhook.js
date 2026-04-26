const express = require("express");

function createHealthServer({ port, getState }) {
  const app = express();

  app.get("/health", (_req, res) => {
    res.json({
      ok: true,
      service: "nicewebtechonoolyautomate-node",
      ...getState(),
    });
  });

  return app.listen(port, () => {
    console.log(`[node] Health endpoint listening on http://127.0.0.1:${port}/health`);
  });
}

module.exports = {
  createHealthServer,
};
