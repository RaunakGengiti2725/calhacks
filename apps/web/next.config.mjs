/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Mol* ships large ESM modules; let Next transpile it for the App Router.
  transpilePackages: ["molstar"],
  webpack: (config) => {
    // Mol* references these Node built-ins in code paths the browser never hits.
    config.resolve.fallback = { ...config.resolve.fallback, fs: false, path: false };
    return config;
  },
};

export default nextConfig;
