import { db, route, unwrap } from "./_lib.js";
import { ORDER, counts, topVoted } from "../logic.js";

export default route({
  async GET({ res, member }) {
    const rows = await unwrap(db().from("submissions").select("id, title, votes, status").eq("workspace_id", member.workspace_id));
    const { total, ...byStatus } = counts(rows);
    res.status(200).json({ total, byStatus, order: ORDER, topVoted: topVoted(rows, 5) });
  },
});
