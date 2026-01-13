import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css"; // 🚨 核心：必须要有这一行，否则 Tailwind 完全不生效！

// 使用 Next.js 14 标准字体 Inter
const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Pastel*Chat",
  description: "Chat with Maruyama Aya",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      {/* 将字体类名应用到 body */}
      <body className={inter.className}>{children}</body>
    </html>
  );
}