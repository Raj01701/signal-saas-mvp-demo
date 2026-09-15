const { SEED_SUBS, cors, body } = require("./_data");
const ORDER = ["open", "prog", "shipped", "closed"];

module.exports = (req, res) => {
  cors(res);
  if (req.method === "OPTIONS") return res.status(204).end();

  if (req.method === "GET") {
    return res.status(200).json({ submissions: SEED_SUBS });
  }
  if (req.method === "POST") {
    const b = body(req);
    const title = String(b.title || "").trim();
    if (!title) return res.status(400).json({ error: "title required" });
    const item = {
      id: Date.now(),
      title,
      by: String(b.by || "").trim() || "You",
      votes: 1,
      status: "open",
      createdAt: new Date().toISOString(),
    };
    return res.status(201).json({ submission: item });
  }
  if (req.method === "PATCH") {
    const b = body(req);
    if (b.id == null) return res.status(400).json({ error: "id required" });
    if (!["advance", "upvote"].includes(b.op)) return res.status(400).json({ error: "invalid op" });
    return res.status(200).json({ id: b.id, op: b.op, ok: true });
  }
  if (req.method === "DELETE") {
    const b = body(req);
    if (b.id == null) return res.status(400).json({ error: "id required" });
    return res.status(200).json({ id: b.id, deleted: true });
  }
  res.status(405).json({ error: "method not allowed" });
};

module.exports.ORDER = ORDER;
