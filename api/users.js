const { SEED_USERS, cors, body } = require("./_data");
const ROLES = ["Owner", "Admin", "Member", "Viewer"];

module.exports = (req, res) => {
  cors(res);
  if (req.method === "OPTIONS") return res.status(204).end();

  if (req.method === "GET") {
    return res.status(200).json({ users: SEED_USERS });
  }
  if (req.method === "POST") {
    const b = body(req);
    const name = String(b.name || "").trim();
    const email = String(b.email || "").trim();
    if (!name || !email) return res.status(400).json({ error: "name and email required" });
    const role = ROLES.includes(b.role) ? b.role : "Member";
    return res.status(201).json({ user: { id: Date.now(), name, email, role, active: true } });
  }
  if (req.method === "PATCH") {
    const b = body(req);
    if (b.id == null) return res.status(400).json({ error: "id required" });
    if (b.op === "role" && !ROLES.includes(b.role)) return res.status(400).json({ error: "invalid role" });
    if (!["toggle", "role"].includes(b.op)) return res.status(400).json({ error: "invalid op" });
    return res.status(200).json({ id: b.id, op: b.op, role: b.role, ok: true });
  }
  res.status(405).json({ error: "method not allowed" });
};
