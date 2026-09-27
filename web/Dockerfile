FROM node:24-slim AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:24-slim AS runner

WORKDIR /app
ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0

# next start serves the public app; the entrypoint starts the compiled Eve
# runtime beside it and proxies /eve/* over the private loopback port.
COPY --from=build /app/.next ./.next
COPY --from=build /app/.output ./.output
COPY --from=build /app/public ./public
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/package.json ./package.json
COPY --from=build /app/next.config.ts ./next.config.ts
COPY --from=build /app/agent ./agent
COPY --from=build /app/scripts ./scripts
RUN chmod +x ./scripts/start-production.sh

EXPOSE 3000
CMD ["./scripts/start-production.sh"]
