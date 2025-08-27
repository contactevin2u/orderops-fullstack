/** @type {import('next').NextConfig} */
const API_BASE =
  (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/+$/, "") ||
  "https://orderops-api-v1.onrender.com"; // fallback for local

module.exports = {
  reactStrictMode: true,
  images: {
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
    remotePatterns: [
      { protocol: 'https', hostname: '**' },
      { protocol: 'http', hostname: '**' },
    ],
  },
  async rewrites() {
    // Proxy path you can use for local dev if you prefer: /_api/* -> API_BASE/*
    return [
      { source: "/_api/:path*", destination: `${API_BASE}/:path*` },
      { source: "/static/uploads/:path*", destination: `${API_BASE}/static/uploads/:path*` },
    ];
  },
};
