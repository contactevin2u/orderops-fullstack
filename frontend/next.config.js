/** @type {import('next').NextConfig} */
const API_BASE =
  (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/+$/, "") ||
  "https://orderops-api-v1.onrender.com"; // fallback for local

module.exports = {
  reactStrictMode: true,
  images: {
    remotePatterns: [{ protocol: 'https', hostname: '**' }],
  },
  async rewrites() {
    // Proxy path you can use for local dev if you prefer: /_api/* -> API_BASE/*
    return [{ source: "/_api/:path*", destination: `${API_BASE}/:path*` }];
  },
};
