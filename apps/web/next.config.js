/** @type {import('next').NextConfig} */
const path = require('path')
const nextConfig = {
  output: 'standalone',
  // Work around Windows/OneDrive permission issues by moving .next in dev
  // In Docker production builds, use default .next directory
  distDir: process.env.NODE_ENV === 'production' ? '.next' : (process.env.NEXT_DIST_DIR || '/tmp/ll_next'),
  env: {
    NEXT_PUBLIC_WS_TOKEN: process.env.NEXT_PUBLIC_WS_TOKEN || 'MaroMaro',
    // Default off to reduce CPU; can be overridden or toggled at runtime via localStorage('LEDGERLOOP_REALTIME')
    NEXT_PUBLIC_ENABLE_REALTIME: process.env.NEXT_PUBLIC_ENABLE_REALTIME || '0',
  },
  webpack: (config, { dev }) => {
    if (dev) {
      // Reduce watcher load for WSL/OneDrive by ignoring large directories
      config.watchOptions = config.watchOptions || {}
      config.watchOptions.ignored = [
        '**/.venv/**',
        '**/logs/**',
        '**/artifacts/**',
        '**/apps/backend/**',
        '**/data/**',
      ]
    }
    return config
  },
  async redirects() {
    return [
      { source: '/analyze', destination: '/ai', permanent: false },
      // Redirect old standalone pages to new locations
      { source: '/analytics', destination: '/', permanent: true },
      { source: '/categories', destination: '/settings/categories', permanent: true },
      { source: '/rules', destination: '/settings/automation', permanent: true },
      { source: '/pulse', destination: '/settings/system', permanent: true },
      // Renamed pages
      { source: '/calendar', destination: '/bills', permanent: true },
      { source: '/recurring', destination: '/subscriptions', permanent: true },
    ]
  },
  async rewrites() {
    // Proxy all /api/* calls to the backend origin, preserving path.
    //
    // IMPORTANT:
    // - Client code should use NEXT_PUBLIC_API_BASE='/api' (same-origin).
    // - The backend origin must be configured separately for the Next server proxy,
    //   otherwise Docker builds may incorrectly proxy to the web container itself.
    const backendOrigin =
      process.env.LEDGERLOOP_BACKEND_ORIGIN ||
      (() => {
        const apiBase = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000/api'
        try {
          return new URL(apiBase).origin
        } catch (_) {
          return 'http://localhost:8000'
        }
      })()
    return [
      {
        source: '/api/:path*',
        destination: `${backendOrigin}/api/:path*`,
      },
    ]
  },
}

module.exports = nextConfig
