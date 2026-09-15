import { route } from "./_lib.js";

// Public client settings. The anon key is designed to be shipped to browsers; RLS denies it table access.
export default route({
  async GET({ res }) {
    res.setHeader("Cache-Control", "public, max-age=300");
    res.status(200).json({ supabaseUrl: process.env.SUPABASE_URL, supabaseAnonKey: process.env.SUPABASE_ANON_KEY });
  },
}, { requireAuth: false });
