import json
import requests
import os
import time

# 1. 你的源文件
INDEX_FILE = 'bandstories.5.json'
# 2. 保存位置
OUTPUT_DIR = 'raw_scenarios'

# 丸山彩所属乐队 ID (Pastel*Palettes = 4)
TARGET_BAND_ID = 4

# Bestdori 剧本服务器地址
BASE_URL = "https://bestdori.com/assets/jp/scenario/band/"


def get_legacy_filename(scenario_id):
    """
    把 band4-001 转换成旧版格式 004_01
    """
    try:
        # 分割 "band4-001"
        parts = scenario_id.split('-')
        if len(parts) != 2:
            return None

        band_part = parts[0]  # band4
        ep_part = parts[1]  # 001

        # 提取数字
        band_num = band_part.replace('band', '')  # 4
        ep_num = int(ep_part)  # 1

        # 构造旧格式: 004_01.json
        # {:03d} 意思是补齐3位 (4 -> 004)
        # {:02d} 意思是补齐2位 (1 -> 01)
        return f"{int(band_num):03d}_{ep_num:02d}.json"
    except:
        return None


def download_scripts():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"📂 正在解析 {INDEX_FILE}...")

    download_list = []

    # 解析 JSON
    for chapter_key, chapter_data in data.items():
        if chapter_data.get('bandId') != TARGET_BAND_ID:
            continue

        chapter_title = chapter_data.get('mainTitle', ['未知章节'])[0]
        stories = chapter_data.get('stories', {})

        for story_key, story_info in stories.items():
            scenario_id = story_info.get('scenarioId')
            episode_title = story_info.get('title', ['未知'])[0]

            if scenario_id:
                download_list.append({
                    "id": scenario_id,
                    "title": episode_title
                })

    print(f"✅ 找到 {len(download_list)} 个剧本，开始智能下载...\n")

    success_count = 0

    for i, item in enumerate(download_list):
        scenario_id = item['id']
        title = item['title']

        # 构造两种可能的文件名
        # 1. 新格式: band4-001.json
        file_name_new = f"{scenario_id}.json"
        # 2. 旧格式: 004_01.json
        file_name_old = get_legacy_filename(scenario_id)

        # 默认保存为 scenario_id.json (方便后续处理统一)
        save_path = os.path.join(OUTPUT_DIR, file_name_new)

        if os.path.exists(save_path):
            print(f"[{i + 1}] ⏭️ 跳过: {title}")
            continue

        print(f"[{i + 1}] ⬇️ 尝试下载: {title} ({scenario_id})...", end="")

        # --- 第一次尝试：新文件名 ---
        url_new = f"{BASE_URL}{file_name_new}"
        try:
            res = requests.get(url_new)
            if res.status_code == 200:
                with open(save_path, 'wb') as f:
                    f.write(res.content)
                print(" ✅ (新格式)")
                success_count += 1
                time.sleep(0.5)
                continue  # 成功了就进入下一个循环
        except:
            pass

        # --- 第二次尝试：旧文件名 ---
        if file_name_old:
            url_old = f"{BASE_URL}{file_name_old}"
            try:
                res = requests.get(url_old)
                if res.status_code == 200:
                    with open(save_path, 'wb') as f:
                        f.write(res.content)
                    print(f" ✅ (旧格式: {file_name_old})")
                    success_count += 1
                    time.sleep(0.5)
                    continue
            except:
                pass

        print(" ❌ 均失败 (404)")

    print(f"\n🎉 下载完成！成功: {success_count}/{len(download_list)}")
    print("请运行清洗脚本 process_aya_memory.py 继续。")


if __name__ == '__main__':
    download_scripts()