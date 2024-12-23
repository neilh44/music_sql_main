/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'https://valet-server-kx48471r3-neilh44s-projects.vercel.app/:path*' // Replace with your actual backend URL
      }
    ]
  },
  // Add other Next.js config options as needed
  reactStrictMode: true,
}

module.exports = nextConfig