// Shared API plumbing (underscore-prefixed files are not routed by Vercel).
import { createClient } from "@supabase/supabase-js";

let client;
// Service-role client: bypasses RLS, so every query below must scope by the caller's workspace.
export function db() {
  client ??= createClient(process.env.SUPABASE_URL, process.env.SUPABASE_SERVICE_ROLE_KEY, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
  return client;
}

export class HttpError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

// Supabase returns { data, error } instead of throwing.
export async function unwrap(query) {
  const { data, error } = await query;
  if (error) throw error;
  return data;
}

export function positiveId(value) {
  const id = Number(value);
  if (!Number.isSafeInteger(id) || id <= 0) throw new HttpError(400, "A valid id is required");
  return id;
}

// Resolves the signed-in caller from the Bearer token and loads their workspace membership.
async function authenticate(req) {
  const token = /^Bearer (.+)$/.exec(req.headers.authorization ?? "")?.[1];
  if (!token) throw new HttpError(401, "Sign in required");
  const { data, error } = await db().auth.getUser(token);
  if (error || !data.user) throw new HttpError(401, "Your session has expired. Sign in again.");
  const member = await unwrap(db().from("members").select("*").eq("user_id", data.user.id).maybeSingle());
  if (!member) throw new HttpError(403, "No workspace is linked to this account");
  if (!member.active) throw new HttpError(403, "Your access to this workspace has been disabled");
  return { user: data.user, member };
}

function readBody(req) {
  if (req.body && typeof req.body === "object") return req.body;
  try { return JSON.parse(req.body || "{}"); } catch { return {}; }
}

// Builds a handler from per-method functions; each gets { req, res, body, user, member }.
export function route(methods, { requireAuth = true } = {}) {
  return async (req, res) => {
    const handle = methods[req.method];
    if (!handle) return res.status(405).json({ error: "Method not allowed" });
    try {
      const caller = requireAuth ? await authenticate(req) : {};
      await handle({ req, res, body: readBody(req), ...caller });
    } catch (err) {
      if (err instanceof HttpError) return res.status(err.status).json({ error: err.message });
      console.error(err);
      res.status(500).json({ error: "Something went wrong. Please try again." });
    }
  };
}

export const toSubmission = (row) => ({
  id: row.id, title: row.title, by: row.requester, votes: row.votes, status: row.status, createdAt: row.created_at,
});

export const toMember = (row, userId) => ({
  id: row.id, name: row.name, email: row.email, role: row.role, active: row.active, isYou: row.user_id === userId,
});
