import os
import json
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

URL = "https://shop.funbox.com.tw/categories/takaratomy/beyblade"
STATE_FILE = "seen_products.json"

NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}" if NTFY_TOPIC else ""

KEYWORDS = ("BX-", "UX-", "CX-")

headers = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) "
        "AppleWebKit/605.1.15 Version/18.0 Mobile/15E148 Safari/604.1"
    ),
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}

def send_notification(title, message, link):
    if not NTFY_URL:
        print("NTFY_TOPIC 尚未設定")
        return

    response = requests.post(
        NTFY_URL,
        data=message.encode("utf-8"),
        headers={
            "Title":"Funbox Monitor",
            "Priority": "high",
            "Tags": "bell",
            "Click": link,
        },
        timeout=20,
    )
    response.raise_for_status()


def get_products():
    response = requests.get(URL, headers=headers, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    products = {}

    for tag in soup.find_all("a", href=True):
        text = " ".join(tag.stripped_strings).strip()
        href = tag.get("href", "")

        if not text:
            continue

        if not any(keyword.lower() in text.lower() for keyword in KEYWORDS):
            continue

        full_url = urljoin(URL, href)

        # 只保留 Funbox 商品網址，排除選單/分類文字
        if "shop.funbox.com.tw" not in full_url:
            continue

        # 清理過長文字
        text = re.sub(r"\s+", " ", text)
        if len(text) > 180:
            text = text[:180]

        products[full_url] = text

    return products


def load_seen():
    if not os.path.exists(STATE_FILE):
        return None

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_seen(urls):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(urls), f, ensure_ascii=False, indent=2)


def main():
    products = get_products()
    current_urls = set(products.keys())

    print(f"目前找到 {len(products)} 個 BX/UX/CX 商品")

    previous = load_seen()

    # 第一次執行：建立基準
    if previous is None:
        save_seen(current_urls)

        send_notification(
            "✅ Funbox 監控啟動成功",
            f"已開始監控 Funbox 戰鬥陀螺，目前辨識到 {len(products)} 個 BX / UX / CX 商品。",
            URL,
        )
        return

    previous_urls = set(previous)
    new_urls = current_urls - previous_urls

    for product_url in new_urls:
        name = products.get(product_url, "Funbox 戰鬥陀螺新品")

        print("發現新品：", name)

        send_notification(
            "🔔 Funbox 即時上架",
            name,
            product_url,
        )

    save_seen(current_urls)

    if not new_urls:
        print("本次沒有發現新商品")


if __name__ == "__main__":
    main()
