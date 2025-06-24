import os
import time
import requests
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# === Telegram 配置 ===
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID  = os.environ["TELEGRAM_CHAT_ID"]
# === 所有日期 + 酒店需求 ===
CHECKLIST = [
    ("07-10-2025", "Village Inn at Apgar"),
    ("07-11-2025", "Rising Sun Motor Inn"),
    ("07-12-2025", "Rising Sun Motor Inn"),
    ("07-13-2025", "Many Glacier Hotel"),
    ("07-14-2025", "Many Glacier Hotel"),
]

NIGHTS = 1  # 每次 stay 一个晚上

def send_telegram_message(message: str):
    """发送 Telegram 消息"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        requests.post(url, data=payload, timeout=10)
        print("📨 Telegram sent.")
    except Exception as e:
        print(f"❌ Failed to send Telegram message: {e}")

def open_with_retry(driver, url, retries=3, wait_sec=5):
    """尝试多次 driver.get，并等待 URL 跳转成功"""
    for attempt in range(1, retries+1):
        try:
            driver.get(url)
            # 等待 URL 包含 lodging-search，最多等 10 秒
            WebDriverWait(driver, 20).until(
                EC.url_contains("lodging-search")
            )
            return True
        except Exception as e:
            print(f"⚠️ Navigation attempt {attempt} failed: {e}")
            time.sleep(wait_sec)
    return False

def check_all_dates():
    """遍历 CHECKLIST，检查每个酒店的可订状态并发 Telegram 通知"""
    options = uc.ChromeOptions()
    # 基本配置
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    # 页面加载策略：DOM ready 即返回
    options.page_load_strategy = "eager"

    driver = uc.Chrome(options=options)
    found_any = False

    for date, hotel in CHECKLIST:
        print(f"\n🔍 Checking: {hotel} on {date}")
        url = (
            "https://secure.glaciernationalparklodges.com/booking/lodging-search"
            f"?destination=ALL&adults=1&children=0&dateFrom={date}&nights={NIGHTS}"
        )

        # 打开并重试
        ok = open_with_retry(driver, url)
        if not ok:
            print(f"❌ 无法打开页面 {url}，跳过")
            continue

        # 再智能等待：确保至少一个 .product-card 出现
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "section.product-card"))
            )
        except Exception:
            print("⚠️ 页面可能加载不完整，直接解析当前内容…")

        soup = BeautifulSoup(driver.page_source, "html.parser")

        for card in soup.select("section.product-card"):
            title_tag = card.select_one("div.product-card__title-top span")
            if not title_tag:
                continue
            name = title_tag.get_text(strip=True)
            print(f"  ▶️ Detected card title: {name}")
            if hotel.lower() not in name.lower():
                continue

            avail_tag = card.select_one("div.availability-message")
            status = avail_tag.get_text(strip=True) if avail_tag else "Unknown"
            print(f"    ‼️ Availability status: {status}")

            if status.lower() not in ("sold out", "closed"):
                msg = f"✅ Room FOUND for {hotel} on {date}! 状态：{status}\n{url}"
                print(msg)
                send_telegram_message(msg)
                found_any = True
            else:
                print(f"❌ {hotel} on {date} 状态：{status}")
            break
        else:
            print(f"⚠️ 在页面上未能定位到 {hotel}")

    # driver.quit()
    if not found_any:
        print("😢 No available rooms found for any of the dates.")

if __name__ == "__main__":
    print(f"\n🧪 Cron is working at {datetime.now()}")
    send_telegram_message("Cron is working at " + str(datetime.now()))
    check_all_dates()
