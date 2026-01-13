/** @type {import('next').NextConfig} */
const nextConfig = {
  // 关闭 React 严格模式，防止 Live2D 模型在开发环境下加载两次
  reactStrictMode: false,
};

export default nextConfig;