import { db, route, toMember, unwrap } from "./_lib.js";

export default route({
  async GET({ res, user, member }) {
    const workspace = await unwrap(db().from("workspaces").select("id, name").eq("id", member.workspace_id).single());
    res.status(200).json({ member: toMember(member, user.id), workspace, isGuest: Boolean(user.is_anonymous) });
  },
});
