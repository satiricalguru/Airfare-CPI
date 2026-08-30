/** @type {import('next').NextConfig} */
const isGhPages = process.env.DEPLOY_TARGET === 'gh-pages';
const basePath = isGhPages ? '/Airfare-CPI' : '';

const nextConfig = {
  output: isGhPages ? 'export' : undefined,
  basePath: basePath,
  assetPrefix: isGhPages ? '/Airfare-CPI/' : undefined,
  images: {
    unoptimized: true,
  },
  devIndicators: false,
  env: {
    NEXT_PUBLIC_BASE_PATH: basePath,
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  },
};

export default nextConfig;
