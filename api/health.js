import { db, route } from "./_lib.js";

export default route({
  async GET({ res }) {
    const { error } = await db().from("workspaces").select("id").limit(1);
    res.status(error ? 503 : 200).json({ ok: !error, database: error ? "down" : "up", time: new Date().toISOString() });
  },
}, { requireAuth: false });
