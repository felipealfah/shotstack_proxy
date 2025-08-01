/** @type {import('next').NextConfig} */
const nextConfig = {
  serverExternalPackages: ['@supabase/supabase-js'],
  images: {
    domains: ['storage.googleapis.com'],
    unoptimized: false
  },
  typescript: {
    ignoreBuildErrors: false
  },
  eslint: {
    ignoreDuringBuilds: false
  },
  // Enable standalone output for Docker
  output: 'standalone'
}

module.exports = nextConfig