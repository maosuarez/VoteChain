// The browser only talks to this origin; /api/* is proxied to the VoteChain API (no CORS needed).
const API = process.env.VOTECHAIN_API_URL ?? "http://127.0.0.1:8000";

/** @type {import('next').NextConfig} */
export default {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API}/:path*` }];
  },
};
