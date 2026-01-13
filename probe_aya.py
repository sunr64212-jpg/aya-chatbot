import requests
import time

# 目标：Pastel*Palettes 第一章 第一话
# Scenario ID: band4-001
# 目标结果：找到一个能返回 200 OK 的网址

BASE_URL = "https://bestdori.com/assets/jp/scenario/band/"

# 伪装成浏览器 (非常重要！防止被服务器拦截)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# 我们要测试的文件名变体
candidates = [
    "004_01.json",  # 变体1: 标准旧格式 (BandID_EpID)
    "band4-001.json",  # 变体2: 原始ID
    "band4_001.json",  # 变体3: 下划线替代连字符
    "004_001.json",  # 变体4: 3位章节号
    "004-01.json",  # 变体5: 连字符旧格式
    "band4_01.json"  # 变体6: 混合格式
]

print("🕵️‍♀️ 正在探测丸山彩的剧本真实地址...\n")

success_url = None

for filename in candidates:
    url = f"{BASE_URL}{filename}"
    print(f"尝试: {filename.ljust(20)}", end="")

    try:
        # 加上 headers 是关键
        res = requests.get(url, headers=HEADERS, timeout=5)

        if res.status_code == 200:
            print("✅ 成功！")
            success_url = filename
            # 打印前50个字符验证内容
            print(f"   -> 内容预览: {res.text[:50]}...")
            break
        else:
            print(f"❌ 失败 ({res.status_code})")
    except Exception as e:
        print(f"⚠️ 出错: {e}")

    time.sleep(0.5)

print("-" * 30)
if success_url:
    print(f"🎉 破解成功！正确的文件名格式是: {success_url}")
    print("请告诉我这个文件名，我来帮你修改主下载脚本。")
else:
    print("😭 全部失败。可能是 Base URL 不对，或者需要从 'main' 文件夹下载。")