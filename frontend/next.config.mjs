/** @type {import('next').NextConfig} */
const isGhPages = process.env.DEPLOY_TARGET === 'gh-pages';
const basePath = isGhPages ? '/Prototype-2' : '';

const nextConfig = {
  output: isGhPages ? 'export' : undefined,
  basePath: basePath,
  assetPrefix: isGhPages ? '/Prototype-2/' : undefined,
  images: {
    unoptimized: true,
  },
  env: {
    NEXT_PUBLIC_BASE_PATH: basePath,
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  },
};

export default nextConfig;
