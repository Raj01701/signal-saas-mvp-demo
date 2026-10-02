import type { NextConfig } from "next";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
// A path such as "/api" means the browser reaches the API through this site, which
// forwards those requests to API_PROXY_TARGET (used where only one port is public).
const proxied = apiUrl.startsWith("/");
const api = proxied ? "" : ` ${new URL(apiUrl).origin}`;
const production = process.env.NODE_ENV === "production";

/** The browser may load code and styles only from this site and talk only to the API. */
const contentSecurityPolicy = [
  "default-src 'self'",
  // Next.js inlines its bootstrap scripts; development also needs eval for fast refresh.
  `script-src 'self' 'unsafe-inline'${production ? "" : " 'unsafe-eval'"}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data:",
  "font-src 'self'",
  `connect-src 'self'${api}`,
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join("; ");

const nextConfig: NextConfig = {
  // sharp (LGPL libvips) is removed via pnpm overrides; charts are SVG anyway.
  images: { unoptimized: true },
  poweredByHeader: false,
  async rewrites() {
    const target = process.env.API_PROXY_TARGET;
    return proxied && target ? [{ source: `${apiUrl}/:path*`, destination: `${target}/:path*` }] : [];
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "Content-Security-Policy", value: contentSecurityPolicy },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=()" },
          { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains" },
        ],
      },
      {
        // The reminder service worker: always revalidated, and allowed only its own origin.
        source: "/sw.js",
        headers: [
          { key: "Content-Type", value: "application/javascript; charset=utf-8" },
          { key: "Cache-Control", value: "no-cache, no-store, must-revalidate" },
          { key: "Content-Security-Policy", value: "default-src 'self'; script-src 'self'" },
        ],
      },
    ];
  },
};

export default nextConfig;
