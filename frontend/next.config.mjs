/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",          // static SPA, served by FastAPI on one origin
  images: { unoptimized: true },
};
export default nextConfig;
