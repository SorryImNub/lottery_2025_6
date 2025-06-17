import discord
import random
import json
import os
import re
from collections import defaultdict
from dotenv import load_dotenv

from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "I am alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

SAVE_FILE = 'records.json'

# loot_table：value, label, count
loot_table = [
    {"label": "<:nomal_container:1384384819173003424>伝説迷彩コンテナ", "value": 0, "count": 1},
    {"label": "<:nomal_container:1384384819173003424>付属品コンテナ", "value": 0, "count": 1},
    {"label": "<:gold:1384363479439249528>500", "value": 500, "count": 20},
    {"label": "<:gold:1384363479439249528>650", "value": 650, "count": 1},
    {"label": "<:gold:1384363479439249528>750", "value": 750, "count": 1},
    {"label": "<:gold:1384363479439249528>1000", "value": 1000, "count": 1},
    {"label": "<:gold:1384363479439249528>1500", "value": 1500, "count": 1},
    {"label": "<:gold:1384363479439249528>2000", "value": 2000, "count": 1},
    {"label": "<:gold:1384363479439249528>3000", "value": 3000, "count": 1},
    {"label": "<:gold:1384363479439249528>3750", "value": 3750, "count": 1},
    {"label": "<:massive8:1384384363034054747>Tier8マッシブコンテナ", "value": 4121, "count": 1},
    {"label": "<:Tier10:1384385135830372412>最強の捕食者証券(Tier10)", "value": 7500, "count": 1}
]

# -------------------------
# JSONの読み書き
# -------------------------
def load_records():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_records(data):
    with open(SAVE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

user_records = load_records()  # 起動時に読み込む

# -------------------------
# 抽選
# -------------------------
def sort_result_entries(result):
    gold_items = []
    others = []

    for entry in result:
        # カスタム絵文字から数値を抽出
        match = re.search(r'<:gold:\d+>(\d+)', entry)
        if match:
            value = int(match.group(1))
            gold_items.append((value, entry))
        else:
            others.append(entry)

    gold_items.sort()
    return [entry for _, entry in gold_items] + others


def rare_draw():
    roll = random.random()
    if roll < 0.0001:
        return "<:1_:1384384404318584832>"
    elif roll < 0.0003:
        return "<:2_:1384384416318492682>"
    elif roll < 0.0005:
        return "<:3_:1384384433704013995>"
    return None

def rare_draw2():
    roll = random.random()
    if roll < 1/31:
        return "<:11:1384397788929982548>"
    return None

def draw_once():
    pool = []
    for item in loot_table:
        pool.extend([item] * item["count"])
    result = random.choice(pool)
    rare = rare_draw()
    rare2 = rare_draw2()
    return result, rare, rare2

# -------------------------
# メッセージ
# -------------------------
@client.event
async def on_ready():
    print(f'Bot起動完了: {client.user.name}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    content = message.content.strip()
    user_key = str(message.author.id)

    if content == '!!!':
        if user_key in user_records:
            del user_records[user_key]
            save_records(user_records)
            await message.channel.send(f"{message.author.display_name}さんの記録をリセットしました。")
        else:
            await message.channel.send("まだ記録がありません。")
        return

    if content == '!':
        results = []
        total_gold = 0

        for _ in range(10):
            result, rare, rare2 = draw_once()
            
            label = result["label"]
            value = result["value"]
            user_records.setdefault(user_key, {}).setdefault(label, 0)
            user_records[user_key][label] += 1
            if rare2:
                user_records.setdefault(user_key, {}).setdefault(rare2, 0)
                user_records[user_key][rare2] += 1
                label = label + " " + rare2
            if rare:
                user_records.setdefault(user_key, {}).setdefault(rare, 0)
                user_records[user_key][rare] += 1
                label = label + " " + rare
            results.append(label)
            total_gold += value

        save_records(user_records)

        # 累積結果の表示
        summary = f"\n{message.author.display_name}さんの累積結果：\n"
        record = user_records[user_key]
        total_count = sum(record.values())

        total_gold_record = 0
        for k, v in record.items():
            # ゴールドなら数値で加算（絵文字以外のラベルもあるので注意）
            if any(str(g["label"]) == k for g in loot_table):
                value = next((g["value"] for g in loot_table if g["label"] == k), 0)
                total_gold_record += value * v

        for k, v in record.items():
            rate = v / total_count * 100
            summary += f"{k}：{v}回（{rate:.2f}%）\n"

        yen_spent = (total_count // 10) * 3200
        summary += "----------------- \n"
        summary += f"累計支出：{yen_spent}円\n"
        summary += f"期待値：<:gold:1384363479439249528>{total_gold_record} \n"
        
        # 単価と損得判定
        if total_gold_record > 0:
            unit_price = total_gold_record/yen_spent
            status = "得" if unit_price >= 5.0 else "損"
            summary += f"ゴールド係数：{unit_price:.2f}  → {status}"
        else:
            summary += "<:gold:1384363479439249528>が出ていないため単価判定不可"
        results = sort_result_entries(results)
        await message.channel.send(f"{message.author.display_name}さんの結果（10回分）：\n" + "\n".join(results))
        await message.channel.send(f"-----------------{summary}\n ----------------- \n コマンド一覧:   ! → ガチャ10回   !!! → 記録リセット")

keep_alive()
client.run(TOKEN)
