import os
import time
import requests
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 从环境变量读取
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID  = os.environ["TELEGRAM_CHAT_ID"]

CHECKLIST = [
    ("07-10-2025", "Village Inn at Apgar"),
    ("07-11-2025", "Rising Sun Motor Inn"),
    ("07-12-2025", "Rising Sun Motor Inn"),
    ("07-13-2025", "Many Glacier Hotel"),
    ("07-14-2025", "Many Glacier Hotel"),
]
NIGHTS = 1

def send_telegram_message(msg: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=10)

def check_all_dates():
    options = uc.ChromeOptions()
    # 指定 runner 上的 chromium 路径
    options.binary_location = "/usr/bin/chromium-browser"
    options.add_argument("--headless=new")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    # 避免一些 CDN 资源加载失败
    options.add_argument("--disable-gpu")
    # DOMReady 即返回
    options.page_load_strategy = "eager"

    driver = uc.Chrome(options=options)
    found_any = False

    for date, hotel in CHECKLIST:
        url = (
            "https://secure.glaciernationalparklodges.com/booking/lodging-search"
            f"?destination=ALL&adults=1&children=0&dateFrom={date}&nights={NIGHTS}"
        )
        driver.get(url)

        try:
            # 等待：最少有 1 张卡片出现，最长 30 秒
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "section.product-card"))
            )
            # 再确保 JS 渲染完毕：等待卡片数量大于等于 1
            WebDriverWait(driver, 10).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, "section.product-card")) >= 1
            )
        except Exception:
            print(f"⚠️ [{date}] 卡片加载失败，继续尝试解析现有页面…")

        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("section.product-card")
        print(f"[{date}] 抓到 {len(cards)} 张卡片")

        for card in cards:
            title_tag = card.select_one("div.product-card__title-top span")
            if not title_tag:
                continue
            name = title_tag.get_text(strip=True)
            if hotel.lower() not in name.lower():
                continue

            avail = card.select_one("div.availability-message")
            status = avail.get_text(strip=True) if avail else "Unknown"
            print(f"  ▶️ {hotel} 状态：{status}")

            if status.lower() not in ("sold out", "closed"):
                msg = f"✅ {hotel} on {date} AVAILABLE! 状态：{status}\n{url}"
                send_telegram_message(msg)
                found_any = True
            break
        else:
            print(f"❌ 在页面上没找到 {hotel}")

    driver.quit()
    if not found_any:
        print("😢 本次所有日期均无可订房源")

if __name__ == "__main__":
    print(f"🧪 Cron at {datetime.now()}")
    check_all_dates()
