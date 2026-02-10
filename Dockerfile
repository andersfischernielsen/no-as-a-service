FROM oven/bun

USER bun
WORKDIR /api
COPY package.json /api
RUN bun install

COPY index.ts rate-limiter.ts reasons.json /api

EXPOSE 3000
ENTRYPOINT [ "bun", "run", "/api/index.ts" ]
