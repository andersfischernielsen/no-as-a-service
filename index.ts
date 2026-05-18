import { rateLimiter } from "./rate-limiter.ts";
import reasons from "./reasons.json" with { type: "json" };
import { createServer } from "node:http";

const limiter = rateLimiter();
const error = JSON.stringify({
  error: "Too many requests, please try again later. (120 reqs/min/IP)",
});
const port = process.env.PORT ?? 3000;

const server = createServer((req, res) => {
  if (req.url !== "/no") {
    res.statusCode = 404;
    res.end();
    return;
  }

  const ip = req.socket.remoteAddress ?? "unknown";
  if (!limiter.get(ip)) {
    res.statusCode = 429;
    res.end(error);
    return;
  }

  const reason = reasons[Math.floor(Math.random() * reasons.length)];
  res.end(JSON.stringify({ reason }));
  return;
}).listen(port);

console.log(`No-as-a-Service is running on port ${port}`);

const shutdown = () => {
  server.close();
  process.exit(0);
};

process.on("SIGTERM", shutdown);
process.on("SIGINT", shutdown);
