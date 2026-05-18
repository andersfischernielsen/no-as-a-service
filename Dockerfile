FROM node:26-alpine

USER node
WORKDIR /api
COPY package.json /api
RUN npm install

COPY index.ts rate-limiter.ts reasons.json /api/

EXPOSE 3000
ENTRYPOINT [ "node", "/api/index.ts" ]
