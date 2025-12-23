import { rateLimiter } from "./rate-limiter";
import reasons from "./reasons.json";

const limiter = rateLimiter();
const error = "Too many requests, please try again later. (120 reqs/min/IP)";

const server = Bun.serve({
  port: process.env.PORT || 3000,
  routes: {
    "/no": (req, server) => {
      const ip = server.requestIP(req)?.address ?? "unknown";

      if (!limiter.get(ip)) {
        return Response.json({ error });
      }

      const reason = reasons[Math.floor(Math.random() * reasons.length)];
      return Response.json({ reason });
    },
  },
});

console.log(`No-as-a-Service is running on port ${server.port}`);
