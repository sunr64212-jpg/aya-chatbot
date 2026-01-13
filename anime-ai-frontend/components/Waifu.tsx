"use client";
import React, { useEffect, useRef, useState } from "react";

interface ChatMessage {
  role: "user" | "ai";
  content: string;
}

const Waifu = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [model, setModel] = useState<any>(null);
  const [inputMsg, setInputMsg] = useState("");
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const [bubbleText, setBubbleText] = useState("丸之山上缤纷彩！我是丸山彩！请多指教！( > < )");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatHistory]);

  useEffect(() => {
    if ((window as any).isLive2DInitialized) return;
    (window as any).isLive2DInitialized = true;

    const initLive2D = async () => {
      try {
        await Promise.all([
          new Promise<void>((resolve) => {
            if ((window as any).Live2DCubismCore) return resolve();
            const script = document.createElement("script");
            script.src = "/live2d/live2dcubismcore.min.js";
            script.onload = () => resolve();
            document.body.appendChild(script);
          }),
          new Promise<void>((resolve, reject) => {
             if ((window as any).Live2D) return resolve();
             const script = document.createElement("script");
             script.src = "/live2d/live2d.min.js";
             script.onload = () => resolve();
             script.onerror = () => reject(new Error("找不到 /live2d/live2d.min.js"));
             document.body.appendChild(script);
          })
        ]);

        const PIXI = await import("pixi.js");
        (window as any).PIXI = PIXI;
        const { Live2DModel } = await import("pixi-live2d-display");
        Live2DModel.registerTicker(PIXI.Ticker as any);

        if (!canvasRef.current) return;

        const app = new PIXI.Application({
          view: canvasRef.current,
          transparent: true,
          autoStart: true,
          width: 500,
          height: 700,
        });

        const modelUrl = "/models/aya/model.json";
        const live2dModel = await Live2DModel.from(modelUrl);
        live2dModel.autoInteract = false;
        app.stage.addChild(live2dModel);

        live2dModel.scale.set(0.25);
        live2dModel.x = 0;
        live2dModel.y = 50;

        setModel(live2dModel);

      } catch (error) {
        console.error("❌ 模型加载失败:", error);
      }
    };

    initLive2D();
  }, []);

// 修改 handleSend 函数，在发送请求时带上 chatHistory
  const handleSend = async () => {
    if (!inputMsg.trim()) return;

    const userText = inputMsg;
    // 先更新本地显示
    const newHistory = [...chatHistory, { role: "user" as const, content: userText }];
    setChatHistory(newHistory);
    setInputMsg("");
    setIsThinking(true);

    try {
      // 关键修改：将 history 一并发送给后端
      // 我们只发最近的 6 条记录，避免 Token 爆炸，也足够让 AI 理解上下文
      const contextHistory = newHistory.slice(-6);

      const response = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            message: userText,
            history: contextHistory // 新增字段
        }),
      });

      const data = await response.json();
      const aiText = data.text || "呜呜...听不到你在说什么...";
      const emotion = data.emotion || "idle";

      setChatHistory(prev => [...prev, { role: "ai", content: aiText }]);
      setBubbleText(aiText);
      setIsThinking(false);
      triggerMotion(emotion);

    } catch (error) {
      console.error("API Error:", error);
      setBubbleText("后端连接失败了... ( > < )");
      setIsThinking(false);
    }
  };

  const triggerMotion = (emotion: string) => {
    if (!model) return;
    try {
        const expressionMap: any = {
            "smile": "f01", "cry": "f04", "shy": "f02", "anger": "f03"
        };
        const expName = expressionMap[emotion] || "f01";
        model.expression(expName);
    } catch (e) { console.warn("表情触发失败", e); }
  };

  return (
    // 布局改为 Flex 容器
    <div className="flex w-full h-screen bg-pink-50 overflow-hidden font-sans">

      {/* --- 左侧区域：模型 (占宽 35%) --- */}
      <div className="relative w-[35%] h-full flex items-end justify-center">
        {/* PIXI 画布 */}
        <div className="absolute bottom-0 left-0">
            <canvas ref={canvasRef} />
        </div>

        {/* 气泡 (调整位置使其在模型头上) */}
        <div className="absolute top-1/4 right-10 bg-white p-5 rounded-3xl shadow-lg border-2 border-pink-200 max-w-[240px] animate-bounce-slow z-10">
            <p className="text-pink-600 font-bold text-sm mb-1">丸山彩</p>
            <p className="text-gray-700 text-sm leading-relaxed">
              {isThinking ? "正在检索记忆..." : bubbleText}
            </p>
             <div className="absolute bottom-0 -left-2 w-4 h-4 bg-white border-b-2 border-l-2 border-pink-200 transform rotate-45"></div>
        </div>
      </div>

      {/* --- 右侧区域：大聊天框 (占宽 65%) --- */}
      <div className="flex-1 h-full p-10 flex items-center justify-center">

        {/* 聊天卡片容器 */}
        <div className="w-full max-w-4xl h-[85vh] bg-white/90 backdrop-blur-sm rounded-[3rem] shadow-2xl flex flex-col border-4 border-white ring-4 ring-pink-100 overflow-hidden">

          {/* 顶部标题栏 */}
          <div className="p-6 bg-gradient-to-r from-pink-400 to-pink-300 flex justify-between items-center shadow-md shrink-0">
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse shadow-[0_0_10px_#4ade80]"></div>
              <h1 className="text-white font-bold text-2xl tracking-wide">Pastel*Chat</h1>
            </div>
            <div className="flex gap-2">
                 <span className="text-pink-500 text-xs bg-white/90 px-3 py-1 rounded-full font-bold shadow-sm">
                    {isThinking ? "Connecting..." : "Online"}
                 </span>
            </div>
          </div>

          {/* 消息列表 */}
          <div className="flex-1 overflow-y-auto p-8 space-y-6 bg-gray-50/50">
            {chatHistory.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center text-gray-400 space-y-4">
                 <div className="text-6xl opacity-20">🌸</div>
                 <p>Aya只能解答自己知道的事情哦！（仅限二次元）</p>
              </div>
            )}

            {chatHistory.map((msg, index) => (
              <div key={index} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[80%] px-6 py-4 rounded-3xl text-lg shadow-sm leading-relaxed ${
                    msg.role === "user" 
                      ? "bg-pink-500 text-white rounded-tr-none shadow-pink-200" 
                      : "bg-white text-gray-800 border border-gray-100 rounded-tl-none shadow-gray-100"
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* 底部输入区 */}
          <div className="p-6 bg-white border-t border-gray-100 shrink-0">
            <div className="flex gap-4 items-center">
              <input
                type="text"
                value={inputMsg}
                onChange={(e) => setInputMsg(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSend()}
                placeholder="发送消息..."
                className="flex-1 px-6 py-4 rounded-full border-2 border-pink-100 focus:border-pink-400 focus:outline-none bg-pink-50/50 text-lg transition-all focus:shadow-inner"
                disabled={isThinking}
              />
              <button
                onClick={handleSend}
                disabled={isThinking}
                className={`px-8 py-4 rounded-full font-bold text-white text-lg shadow-lg transition-all active:scale-95 hover:shadow-xl ${
                  isThinking ? "bg-gray-300 cursor-not-allowed" : "bg-gradient-to-r from-pink-400 to-pink-500 hover:from-pink-500 hover:to-pink-600"
                }`}
              >
                发送
              </button>
            </div>
          </div>

        </div>
      </div>

    </div>
  );
};

export default Waifu;