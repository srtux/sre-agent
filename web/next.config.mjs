const nextConfig = {
  output: 'standalone',
  serverExternalPackages: ['@copilotkit/runtime'],

  async rewrites() {
    return [
      {
        source: '/api/tools/:path*',
        destination: 'http://127.0.0.1:8000/api/tools/:path*',
      },
    ];
  },
  devIndicators: false,
};

export default nextConfig;
