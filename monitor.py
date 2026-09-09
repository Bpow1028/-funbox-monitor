import os
import json
import re
import requests

URL = "https://shop.funbox.com.tw/categories/takaratomy/beyblade"
STATE_FILE = "seen_products.json"

NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) "
        "AppleWebKit/605.1.15 Version/18.0 Mobile/15E148 Safari/604.1"
    ),
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}


def send_notification(title, message, link):
    if not NTFY_TOPIC:
        print("NTFY_TOPIC 尚未設定")
        return

    response = requests.post(
        "https://ntfy.sh",
        json={
            "topic": NTFY_TOPIC,
            "title": title,
            "message": message,
            "priority": 4,
            "tags": ["bell"],
            "click": link,
        },
        timeout=20,
    )
    response.raise_for_status()


def get_product_ids():
    response = requests.get(URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    html = response.text

    # Funbox 分類頁內嵌的商品 ID 為 8 位數，並以逗號分隔
    product_ids = re.findall(r"(?<!\d)([67]\d{7})(?=,)", html)

    return sorted(set(product_ids))


def load_seen():
    if not os.path.exists(STATE_FILE):
        return None

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_seen(product_ids):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(product_ids, f, ensure_ascii=False, indent=2)


def main():
    current = get_product_ids()

    print(f"目前找到 {len(current)} 個 Funbox 商品 ID")

    previous = load_seen()

    # 第一次執行只建立基準
    if previous is None or len(previous) == 0:
        save_seen(current)

        send_notification(
            "Funbox Monitor",
            f"監控啟動成功，目前辨識到 {len(current)} 個商品 ID。",
            URL,
        )
        return

    previous_set = set(previous)
    current_set = set(current)

    new_ids = current_set - previous_set

    if new_ids:
        for product_id in sorted(new_ids):
            print("發現新商品 ID：", product_id)

            send_notification(
                "Funbox 新商品上架",
                f"發現新的 Funbox 商品！商品 ID：{product_id}\n請立即查看戰鬥陀螺頁面。",
                URL,
            )
    else:
        print("本次沒有發現新商品")

    save_seen(current)


if __name__ == "__main__":
    main()
