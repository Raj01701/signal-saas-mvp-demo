# Jyotish web app

The Next.js (App Router) front end for the Jyotish platform. The professional astrologer
workbench comes first (milestone M7), then the consumer experience (milestone M11).

```bash
pnpm install
pnpm dev          # http://localhost:3000
pnpm lint && pnpm typecheck && pnpm test && pnpm build
```

`sharp` (LGPL libvips) is removed through `pnpm-workspace.yaml` overrides, and images are
served unoptimised, so that every shipped dependency stays permissively licensed.
