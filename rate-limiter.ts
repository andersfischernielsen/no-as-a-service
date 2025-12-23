export const rateLimiter = () => {
  const capacity = 120;
  const refill = 120 / 60;
  const ttl = 10 * 60_000;

  const ips = new Map<string, { tokens: number; last: number }>();

  const get = (key: string) => {
    const now = Date.now();
    let bucket = ips.get(key);

    if (!bucket) {
      bucket = { tokens: capacity, last: now };
      ips.set(key, bucket);
    }

    const elapsed = (now - bucket.last) / 1000;
    if (elapsed > 0) {
      bucket.tokens = Math.min(capacity, bucket.tokens + elapsed * refill);
      bucket.last = now;
    }

    if (bucket.tokens >= 1) {
      bucket.tokens -= 1;
      return true;
    }

    return false;
  };

  const sweep = () => {
    const cutoff = Date.now() - ttl;
    for (const [ip, info] of ips) {
      if (info.last < cutoff) ips.delete(ip);
    }
  };

  setInterval(sweep, ttl).unref?.();

  return { get };
};
