FROM node:24-bookworm-slim AS build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY tsconfig.json vitest.config.ts ./
COPY src ./src
COPY tests ./tests

RUN npm run build

FROM node:24-bookworm-slim AS runtime

WORKDIR /app

ENV NODE_ENV=production
ENV SQLITE_PATH=/data/automation-core.sqlite
ENV APP_HOST=0.0.0.0
ENV APP_PORT=3010

COPY --from=build /app/package.json /app/package-lock.json* ./
RUN npm install --omit=dev

COPY --from=build /app/dist ./dist

VOLUME ["/data"]
EXPOSE 3010

CMD ["node", "dist/server.js"]
