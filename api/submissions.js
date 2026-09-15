import { HttpError, db, positiveId, route, toSubmission, unwrap } from "./_lib.js";
import { nextStatus, parseSubmission, permissions } from "../logic.js";

const table = () => db().from("submissions");

function requireRole(member, ability) {
  if (!permissions(member.role)[ability]) {
    throw new HttpError(403, ability === "manage" ? "Only owners and admins can do that" : "Viewers have read-only access");
  }
}

export default route({
  async GET({ res, member }) {
    const rows = await unwrap(table().select("*").eq("workspace_id", member.workspace_id).order("created_at", { ascending: false }));
    res.status(200).json({ submissions: rows.map(toSubmission) });
  },

  async POST({ res, body, user, member }) {
    requireRole(member, "write");
    const { value, error } = parseSubmission(body);
    if (error) throw new HttpError(400, error);
    const row = await unwrap(table()
      .insert({ ...value, workspace_id: member.workspace_id, created_by: user.id })
      .select().single());
    res.status(201).json({ submission: toSubmission(row) });
  },

  async PATCH({ res, body, member }) {
    const id = positiveId(body.id);

    if (body.op === "upvote") {
      requireRole(member, "write");
      const [row] = await unwrap(db().rpc("upvote_submission", { p_workspace: member.workspace_id, p_id: id }));
      if (!row) throw new HttpError(404, "Request not found");
      return res.status(200).json({ submission: toSubmission(row) });
    }

    if (body.op === "advance") {
      requireRole(member, "manage");
      const current = await unwrap(table().select("status").eq("id", id).eq("workspace_id", member.workspace_id).maybeSingle());
      if (!current) throw new HttpError(404, "Request not found");
      // Conditional on the status we read, so a concurrent change isn't silently skipped past.
      const row = await unwrap(table()
        .update({ status: nextStatus(current.status) })
        .eq("id", id).eq("workspace_id", member.workspace_id).eq("status", current.status)
        .select().maybeSingle());
      if (!row) throw new HttpError(409, "Someone else just changed this request. Refresh and try again.");
      return res.status(200).json({ submission: toSubmission(row) });
    }

    throw new HttpError(400, "Unknown operation");
  },

  async DELETE({ res, body, member }) {
    requireRole(member, "manage");
    const id = positiveId(body.id);
    const rows = await unwrap(table().delete().eq("id", id).eq("workspace_id", member.workspace_id).select("id"));
    if (!rows.length) throw new HttpError(404, "Request not found");
    res.status(200).json({ id, deleted: true });
  },
});
