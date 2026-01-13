/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    // 覆盖 src 目录下所有文件 (包括 app 和 components)
    "./src/**/*.{js,ts,jsx,tsx,mdx}",

    // 以防万一你没有用 src 目录，把根目录的也加上
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};