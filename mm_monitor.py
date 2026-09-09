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
    response = requests.get(HOME_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    products = {}

    for tag in soup.find_all("a", href=True):
        text = " ".join(tag.stripped_strings).strip()
        href = tag.get("href", "")

        if not text:
            continue

        if not any(k.lower() in text.lower() for k in KEYWORDS):
            continue

        full_url = urljoin(BASE_URL, href)

        if "/item/" not in full_url:
            continue

        text = re.sub(r"\s+", " ", text)

        products[full_url] = {
            "name": text,
            "url": full_url,
        }

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
