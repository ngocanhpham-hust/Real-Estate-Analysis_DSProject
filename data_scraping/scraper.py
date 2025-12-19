import time
import csv
import math
import random
import os

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec

from utils import extract_numeric, extract_coordinates

# ==========
# SETTINGS
# ==========
OUTPUT_CSV = "data/raw/batdongsan_com_vn.csv"

START_I = 439
END_I = 500
PAGE_SIZE = 20

DELAY_PAGE = (2.0, 5.0)
DELAY_DETAIL = (1.5, 4.0)
DELAY_SCROLL = (0.2, 0.6)

property_types_links = {
    "Căn hộ chung cư": "https://batdongsan.com.vn/ban-can-ho-chung-cu",
    "Nhà riêng": "https://batdongsan.com.vn/ban-nha-rieng",
    "Nhà biệt thự, liền kề": "https://batdongsan.com.vn/ban-nha-biet-thu-lien-ke",
    "Nhà mặt phố": "https://batdongsan.com.vn/ban-nha-mat-pho",
}

FIELDS = [
    "price","area","n_bedrooms","n_bathrooms","n_floors",
    "legal","interior","facing_direction","balcony_direction",
    "front_width","front_road_width","title",
    "latitude","longitude","verified",
    "location","location_details",
    "property_type","date_of_posting","url"
]

# ==========
# HELPERS
# ==========
def sleep_rand(a_b):
    time.sleep(random.uniform(a_b[0], a_b[1]))

def ensure_outdir():
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)

def build_driver():
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-notifications")
    options.add_argument("--no-first-run")
    options.add_argument("--no-service-autorun")
    options.add_argument("--password-store=basic")

    driver = uc.Chrome(options=options)
    return driver

def write_rows(rows):
    ensure_outdir()
    file_exists = os.path.exists(OUTPUT_CSV)
    with open(OUTPUT_CSV, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)

# ==========
# MAIN
# ==========
def main():
    driver = build_driver()

    try:
        keys = list(property_types_links.keys())

        for i in range(START_I, END_I):
            all_data = []

            current_type = keys[i % len(keys)]
            current_link = property_types_links[current_type]
            current_page_num = i // len(keys) + 1

            list_url = f"{current_link}/p{current_page_num}?sortValue=8"
            print(f"\n=== i={i} | type={current_type} | page={current_page_num} ===")

            driver.get(list_url)
            sleep_rand(DELAY_PAGE)

            if current_link not in driver.current_url:
                print("⚠️ Redirect detected, reload list page")
                driver.get(list_url)
                sleep_rand(DELAY_PAGE)

            WebDriverWait(driver, 60).until(
                ec.presence_of_element_located(
                    (By.CSS_SELECTOR, ".re__srp-total-count.js__srp-total-result")
                )
            )

            try:
                count_text = driver.find_element(
                    By.CSS_SELECTOR,
                    ".re__srp-total-count.js__srp-total-result #count-number"
                ).text
                num_results = int(extract_numeric(count_text))
            except:
                print("⚠️ Cannot read result count, skip")
                continue

            if math.ceil(num_results / PAGE_SIZE) < current_page_num:
                print("✅ No more pages")
                continue

            cards = driver.find_elements(By.CLASS_NAME, "re__card-info")
            if not cards:
                print("⚠️ No cards found")
                continue

            for j in range(min(PAGE_SIZE, len(cards))):
                new_line = {k: None for k in FIELDS}
                new_line["property_type"] = current_type

                cards = driver.find_elements(By.CLASS_NAME, "re__card-info")
                if j >= len(cards):
                    break

                page_result = cards[j]

                try:
                    new_line["location"] = page_result.find_elements(
                        By.CSS_SELECTOR, ".re__card-location > *"
                    )[1].text.strip()
                except:
                    pass

                try:
                    link_el = page_result.find_element(By.CLASS_NAME, "re__card-title")
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center'});", link_el
                    )
                    sleep_rand((0.3, 0.8))
                    link_el.click()
                except:
                    continue

                sleep_rand(DELAY_DETAIL)
                new_line["url"] = driver.current_url

                if current_link not in new_line["url"]:
                    print("⚠️ Invalid URL, skip")
                    driver.back()
                    sleep_rand((1.0, 2.0))
                    continue

                try:
                    new_line["title"] = driver.find_element(
                        By.CSS_SELECTOR,
                        ".re__pr-title.pr-title.js__pr-title"
                    ).text.strip()
                except:
                    pass

                try:
                    new_line["location_details"] = driver.find_element(
                        By.CSS_SELECTOR,
                        ".re__pr-short-description.js__pr-address"
                    ).text.strip()
                except:
                    pass

                try:
                    specs = driver.find_elements(
                        By.CLASS_NAME, "re__pr-specs-content-item"
                    )
                    for s in specs:
                        k = s.find_element(
                            By.CLASS_NAME, "re__pr-specs-content-item-title"
                        ).text.strip()
                        v = s.find_element(
                            By.CLASS_NAME, "re__pr-specs-content-item-value"
                        ).text.strip()

                        if k == "Khoảng giá": new_line["price"] = v
                        elif k == "Diện tích": new_line["area"] = v
                        elif k == "Số phòng ngủ": new_line["n_bedrooms"] = v
                        elif k == "Số phòng tắm, vệ sinh": new_line["n_bathrooms"] = v
                        elif k == "Số tầng": new_line["n_floors"] = v
                        elif k == "Pháp lý": new_line["legal"] = v
                        elif k == "Nội thất": new_line["interior"] = v
                        elif k == "Hướng nhà": new_line["facing_direction"] = v
                        elif k == "Hướng ban công": new_line["balcony_direction"] = v
                        elif k == "Mặt tiền": new_line["front_width"] = v
                        elif k == "Đường vào": new_line["front_road_width"] = v
                except:
                    pass

                try:
                    driver.find_element(By.CLASS_NAME, "re__pr-stick-listing-verified")
                    new_line["verified"] = 1
                except:
                    new_line["verified"] = 0

                for _ in range(8):
                    try:
                        map_box = driver.find_element(
                            By.CSS_SELECTOR,
                            ".re__section.re__pr-map.js__section.js__li-other .re__section-body"
                        )
                        iframe = map_box.find_element(By.TAG_NAME, "iframe")
                        src = iframe.get_attribute("data-src") or iframe.get_attribute("src")
                        lat, lon = extract_coordinates(src)
                        new_line["latitude"], new_line["longitude"] = lat, lon
                        break
                    except:
                        driver.execute_script("window.scrollBy(0, 550);")
                        sleep_rand(DELAY_SCROLL)

                try:
                    new_line["date_of_posting"] = driver.find_element(
                        By.CSS_SELECTOR,
                        ".re__pr-short-info.re__pr-config.js__pr-config > :nth-child(1) > .value"
                    ).text
                except:
                    pass

                all_data.append(new_line)
                print(f"  - got item {j+1}/{PAGE_SIZE}")

                driver.back()
                sleep_rand((1.2, 2.5))

            if all_data:
                write_rows(all_data)
                print(f"✅ wrote {len(all_data)} rows → {OUTPUT_CSV}")

            sleep_rand((3.0, 8.0))

    finally:
        driver.quit()
        print("Driver quit.")

if __name__ == "__main__":
    main()