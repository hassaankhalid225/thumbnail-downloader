/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  compress: true,

  // Required by the Docker runner stage — ships a self-contained server.js instead of
  // the whole node_modules tree.
  output: "standalone",

  // These three are barrel packages: a single named import pulls the whole index in.
  // react-icons/si alone exports ~3,000 components and we use eleven.
  experimental: {
    optimizePackageImports: ["framer-motion", "lucide-react", "react-icons/si"],
  },

  images: {
    remotePatterns: [
      { protocol: "https", hostname: "i.ytimg.com" },
      { protocol: "https", hostname: "i9.ytimg.com" },
      { protocol: "https", hostname: "*.ytimg.com" },
      { protocol: "https", hostname: "*.ggpht.com" },
      { protocol: "https", hostname: "*.cdninstagram.com" },
      { protocol: "https", hostname: "*.fbcdn.net" },
      { protocol: "https", hostname: "*.tiktokcdn.com" },
      { protocol: "https", hostname: "*.tiktokcdn-us.com" },
      { protocol: "https", hostname: "*.vimeocdn.com" },
      { protocol: "https", hostname: "*.jtvnw.net" },
      { protocol: "https", hostname: "*.twimg.com" },
      { protocol: "https", hostname: "*.dmcdn.net" },
      { protocol: "https", hostname: "*.redd.it" },
      { protocol: "https", hostname: "*.pinimg.com" },
      { protocol: "https", hostname: "*.licdn.com" },
      { protocol: "https", hostname: "*.rmbl.ws" },
    ],
    formats: ["image/avif", "image/webp"],
  },

  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ];
  },
};

export default nextConfig;
