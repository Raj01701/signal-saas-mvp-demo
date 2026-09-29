import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // sharp (LGPL libvips) is removed via pnpm overrides; charts are SVG anyway.
  images: { unoptimized: true },
};

export default nextConfig;
