const { cors } = require("./_data");
module.exports = (req, res) => {
  cors(res);
  if (req.method === "OPTIONS") return res.status(204).end();
  res.status(200).json({ ok: true, service: "signal-api", time: new Date().toISOString() });
};
