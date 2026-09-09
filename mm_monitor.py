import os
import json
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://mmtoyshop.com"
HOME_URL = "https://mmtoyshop.com/"
STATE_FILE = "mm_seen_products.json"

NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")

KEYWORDS = ("BX-", "UX-", "CX-")

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

def get_products():
product_urls = [
    "https://mmtoyshop.com/item/Shopee6a3bdc2987154",
    "https://mmtoyshop.com/item/Shopee6a3c8d32c819b",
    "https://mmtoyshop.com/item/Shopee6a3bdb8f6b386",
    "https://mmtoyshop.com/item/shopee6a3bdbb22415e",
    "https://mmtoyshop.com/item/shopee6a3bdb4fe2bcb",
    "https://mmtoyshop.com/item/Shopee6a3bdd0e115bf",
    "https://mmtoyshop.com/item/shopee6a3bdc09bb86a",
    "https://mmtoyshop.com/item/Shopee6a3bdbf9a7679",
    "https://mmtoyshop.com/item/shopee6a3bdc1b2db19",
    "https://mmtoyshop.com/item/shopee6a3bdba399773",
]
    

    products = {}

    for url in product_urls:
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            text = " ".join(soup.stripped_strings)

            match = re.search(
                r"(?:BX|UX|CX)-\d+[^\n]{0,120}",
                text,
                re.IGNORECASE
            )

            if not match:
                continue

            name = re.sub(r"\s+", " ", match.group(0)).strip()

            price_match = re.search(r"NT\$\s*[\d,]+", text)
            price = price_match.group(0) if price_match else "價格未取得"

            stock_match = re.search(r"商品庫存[:：]\s*(\d+)", text)
            stock = stock_match.group(1) if stock_match else "未知"

            products[url] = {
                "name": name,
                "price": price,
                "stock": stock,
                "url": url,
            }

        except Exception as e:
            print("讀取商品失敗：", url, e)

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

    print(f"目前找到 {len(products)} 個 M.M小舖 BX/UX/CX 商品")

    previous = load_seen()

    # 第一次只建立基準
    if previous is None or len(previous) == 0:
        save_seen(current_urls)

        send_notification(
            "M.M小舖 Monitor",
            f"監控啟動成功，目前記錄 {len(products)} 個 BX / UX / CX 商品。",
            HOME_URL,
        )
        return

    previous_urls = set(previous)
    new_urls = sorted(current_urls - previous_urls)

    if new_urls:
        print(f"發現 {len(new_urls)} 個新商品")

        for url in new_urls:
            product = products[url]
            name = product["name"]

            print("新品：", name)

            send_notification(
                "M.M小舖 新商品上架",
                name,
                url,
            )
    else:
        print("本次沒有發現新商品")

    save_seen(current_urls)


if __name__ == "__main__":
    main()
