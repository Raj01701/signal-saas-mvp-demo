import { HttpError, db, positiveId, route, toMember, unwrap } from "./_lib.js";
import { memberChangeError, parseInvite, permissions } from "../logic.js";

const table = () => db().from("members");
const UNIQUE_VIOLATION = "23505";

export default route({
  async GET({ res, user, member }) {
    const rows = await unwrap(table().select("*").eq("workspace_id", member.workspace_id).order("created_at"));
    res.status(200).json({ users: rows.map(row => toMember(row, user.id)) });
  },

  async POST({ res, body, user, member }) {
    if (!permissions(member.role).manage) throw new HttpError(403, "Only owners and admins can invite members");
    const { value, error } = parseInvite(body);
    if (error) throw new HttpError(400, error);
    const { data: row, error: dbError } = await table()
      .insert({ ...value, workspace_id: member.workspace_id })
      .select().single();
    if (dbError?.code === UNIQUE_VIOLATION) throw new HttpError(409, `${value.email} is already in this workspace`);
    if (dbError) throw dbError;
    res.status(201).json({ user: toMember(row, user.id) });
  },

  async PATCH({ res, body, user, member }) {
    const id = positiveId(body.id);
    const target = await unwrap(table().select("*").eq("id", id).eq("workspace_id", member.workspace_id).maybeSingle());
    if (!target) throw new HttpError(404, "Member not found");

    const change = { op: body.op, role: body.role };
    const refusal = memberChangeError(member, target, change);
    if (refusal) throw new HttpError(403, refusal);

    const patch = change.op === "role" ? { role: change.role } : { active: !target.active };
    const row = await unwrap(table().update(patch).eq("id", id).eq("workspace_id", member.workspace_id).select().single());
    res.status(200).json({ user: toMember(row, user.id) });
  },
});
