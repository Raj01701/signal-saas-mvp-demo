const { SEED_SUBS, cors } = require("./_data");
const ORDER = ["open", "prog", "shipped", "closed"];

module.exports = (req, res) => {
  cors(res);
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "GET") return res.status(405).json({ error: "method not allowed" });

  const c = { open: 0, prog: 0, shipped: 0, closed: 0 };
  for (const s of SEED_SUBS) if (c[s.status] != null) c[s.status]++;
  const top = [...SEED_SUBS].sort((a, b) => b.votes - a.votes).slice(0, 5)
    .map(s => ({ id: s.id, title: s.title, votes: s.votes, status: s.status }));

  res.status(200).json({ total: SEED_SUBS.length, byStatus: c, order: ORDER, topVoted: top });
};
