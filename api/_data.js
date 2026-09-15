// Shared seed data for the serverless API (underscore-prefixed files are not routed by Vercel).
const DAY = 86_400_000;
const iso = (d) => new Date(Date.now() - d * DAY).toISOString();

const SEED_SUBS = [
  { id: 1, title: "Slack notifications for new feedback", by: "Priya (Acme)", votes: 42, status: "prog", createdAt: iso(1) },
  { id: 2, title: "Export requests to CSV", by: "Daniel M.", votes: 28, status: "open", createdAt: iso(3) },
  { id: 3, title: "Dark mode for the dashboard", by: "Lucia R.", votes: 19, status: "shipped", createdAt: iso(6) },
  { id: 4, title: "Public roadmap page", by: "Tomás (Beta)", votes: 37, status: "open", createdAt: iso(9) },
  { id: 5, title: "Merge duplicate requests", by: "Priya (Acme)", votes: 15, status: "prog", createdAt: iso(12) },
  { id: 6, title: "Weekly digest email", by: "Sofia K.", votes: 23, status: "open", createdAt: iso(16) },
  { id: 7, title: "SSO / Google login", by: "Marco (Enterprise)", votes: 31, status: "closed", createdAt: iso(24) },
  { id: 8, title: "Tag & categorise submissions", by: "Daniel M.", votes: 12, status: "shipped", createdAt: iso(33) },
  { id: 9, title: "Mobile push notifications", by: "Aisha N.", votes: 26, status: "open", createdAt: iso(2) },
  { id: 10, title: "Bulk status updates", by: "Marco (Enterprise)", votes: 9, status: "prog", createdAt: iso(19) },
];

const SEED_USERS = [
  { id: 1, name: "Alex Rivera", email: "alex@startup.com", role: "Owner", active: true },
  { id: 2, name: "Priya Nair", email: "priya@acme.io", role: "Admin", active: true },
  { id: 3, name: "Daniel Moreno", email: "daniel@startup.com", role: "Member", active: true },
  { id: 4, name: "Lucia Rossi", email: "lucia@beta.co", role: "Viewer", active: false },
  { id: 5, name: "Sofia Kaur", email: "sofia@startup.com", role: "Member", active: true },
];

function cors(res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET,POST,PATCH,DELETE,OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
}
function body(req) {
  if (req.body && typeof req.body === "object") return req.body;
  try { return JSON.parse(req.body || "{}"); } catch { return {}; }
}

module.exports = { SEED_SUBS, SEED_USERS, cors, body };
