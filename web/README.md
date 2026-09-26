# Napas Jakarta web workspace

This directory is the additive Next.js + React + TypeScript replacement
workspace for Napas Jakarta. The `/` route is intentionally one spatial,
conversational surface: Ask Napas stays beside the Jakarta map, and station,
trend, comparison, and source results appear as contextual components.

The product brief and surface targets live at
[`../docs/product-design.md`](../docs/product-design.md). Mobile is currently a
basic fallback only; the approved targets are a 24-inch desktop reference and
a 14-inch laptop reference.

## Getting started

Install and run the browser workspace:

```bash
npm ci
npm run dev -- --hostname 127.0.0.1 --port 3200
```

Useful checks:

```bash
npm run typecheck
npm run build
```

The preview map uses MapLibre with the configurable OpenFreeMap Liberty style;
station coordinates and readings are clearly labelled illustrative fixtures
until the live geospatial contract is connected. Set
`NEXT_PUBLIC_MAP_STYLE_URL` to replace the preview style, and set
`NAPAS_API_ORIGIN` to the FastAPI origin when exercising the typed current
air-quality tool. Configure the model through `NAPAS_AGENT_MODEL` and the Eve
provider credentials required by the selected model.

Start by editing `agent/instructions.md` to define the agent's identity, purpose, tone, and response guidelines. Configure its model and runtime behavior in `agent/agent.ts`.

Add capabilities under `agent/`, including tools, connections, channels, skills, subagents, and schedules. eve reloads your changes as you work.

## Eve development

This app was bootstrapped with [`eve init`](https://eve.dev/docs/reference/cli#eve-init).
The agent identity is in `agent/instructions.md`, the model/runtime wiring is in
`agent/agent.ts`, and Napas-specific capabilities live under `agent/tools/`.
The generated `/s` routes remain Eve's session utility surface; `/` is the
Napas product surface.

## Learn more

To learn more about eve, explore these resources:

- [eve documentation](https://eve.dev/docs) — learn about eve's features and authoring APIs.
- [Build an Agent tutorial](https://eve.dev/docs/tutorial/first-agent) — build and deploy an agent step by step.
- [eve on GitHub](https://github.com/vercel/eve) — view the source and contribute.

## Deploy on Vercel

Deploy your agent to [Vercel](https://vercel.com) from the project root:

```bash
eve deploy
```

`eve deploy` links a Vercel project if needed and deploys the agent to production. See the [eve deployment documentation](https://eve.dev/docs/guides/deployment/vercel) for authentication, environment variables, and deployment options.
