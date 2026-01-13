import Waifu from "@/components/Waifu";

export default function Home() {
  return (
    <main className="min-h-screen bg-pink-50">
      {/* 只渲染 Waifu 组件，没有任何多余的标题或输入框 */}
      <Waifu />
    </main>
  );
}