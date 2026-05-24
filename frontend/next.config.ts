/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {},
  // Allow requests to the local FastAPI backend
  async rewrites() {
    return [
      {
        source: '/api/backend/:path*',
        destination: 'http://localhost:8000/api/v1/:path*',
      },
    ];
  },
  images: {
    remotePatterns: [],
  },
};

export default nextConfig;
