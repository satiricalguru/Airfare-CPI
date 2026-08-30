/**
 * Universal asset path resolver supporting GitHub Pages subpath deployment (/Airfare-CPI)
 * and root domain deployments (Vercel, custom domain).
 */
export function getAssetPath(path) {
  if (!path) return "";
  if (path.startsWith("http://") || path.startsWith("https://") || path.startsWith("data:")) {
    return path;
  }
  const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  return `${basePath}${cleanPath}`;
}

export default getAssetPath;
