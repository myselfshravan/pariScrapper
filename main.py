import logging
import time
import threading
import json
from flask import Flask, jsonify, request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = Flask(__name__)
latest_odds = {}
on_going_events = set()
lock = threading.Lock()


def setup_driver(headless=True):
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    if headless:
        chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.set_window_position(1920, -315)
    return driver


def get_market_items(driver):
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div[data-id="market-item"]'))
        )
        return driver.find_elements(By.CSS_SELECTOR, 'div[data-id="market-item"]')
    except Exception as e:
        logging.error(f"Error finding market items: {e}")
        return []


def get_market_title_by_index(driver, index=1):
    try:
        markets = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div[data-id="market-item"]'))
        )
        if 1 <= index <= len(markets):
            title_element = markets[index - 1].find_element(By.CSS_SELECTOR, 'div[role="button"]')
            return title_element.text.strip()
        else:
            logging.error("Invalid market index provided.")
            return None
    except Exception as e:
        logging.error(f"Error retrieving market title: {e}")
        return None


def extract_market_odds(driver, market_title):
    while True:
        try:
            # Locate all market items and find the one that matches the title
            markets = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div[data-id="market-item"]'))
            )
            target_market = None
            for market in markets:
                try:
                    title_element = market.find_element(By.CSS_SELECTOR, 'div[role="button"]')
                    if title_element.text.strip() == market_title:
                        target_market = market
                        break
                except (StaleElementReferenceException, NoSuchElementException):
                    continue

            if not target_market:
                logging.warning("Market not found, retrying...")
                time.sleep(2)
                continue

            odds_elements = target_market.find_elements(By.CSS_SELECTOR, 'span[data-id="animated-odds-value"]')
            odds_data = [odds.text.strip() for odds in odds_elements]
            return {"market_name": market_title, "odds": odds_data}
        except (StaleElementReferenceException, NoSuchElementException):
            logging.warning("Market element went stale or disappeared. Retrying...")
            time.sleep(2)
            continue
        except Exception as e:
            logging.error(f"Unexpected error extracting market data: {e}")
            return None


def compute_record(odds_data):
    try:
        odds_t1_str, odds_t2_str = odds_data["odds"]
        odds_t1 = float(odds_t1_str)
        odds_t2 = float(odds_t2_str)
        probability_t1 = 1 / odds_t1 if odds_t1 != 0 else None
        probability_t2 = 1 / odds_t2 if odds_t2 != 0 else None
    except Exception as e:
        logging.error("Invalid odds format. Expected two numeric odds as strings.", exc_info=e)
        return None

    record = {
        "timestamp": time.time(),
        "odds_t1": odds_t1_str,
        "odds_t2": odds_t2_str,
        "probability_t1": round(probability_t1, 4) if probability_t1 is not None else None,
        "probability_t2": round(probability_t2, 4) if probability_t2 is not None else None
    }
    return record


def monitor_odds(event):
    global latest_odds, on_going_events
    url = f"https://pari-matchin.com/en/events/{event}?tab=all"
    driver = setup_driver(headless=False)
    driver.get(url)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    market_title = get_market_title_by_index(driver, index=1)
    if not market_title:
        logging.error("Could not retrieve market title for index 1. Exiting monitor thread.")
        driver.quit()
        with lock:
            on_going_events.discard(event)
        return
    logging.info(f"Monitoring market: {market_title}")

    while True:
        odds_data = extract_market_odds(driver, market_title)
        if odds_data:
            record = compute_record(odds_data)
            if record:
                with lock:
                    latest_odds[event] = record
                logging.info(f"Updated odds for {event}: {record}")
        time.sleep(2)


@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Welcome to the Odds Monitoring API!"})


@app.route("/odds", methods=["GET"])
def get_odds():
    event = request.args.get("event")
    if not event:
        return jsonify({"error": "Event parameter is required."}), 400

    with lock:
        if event not in latest_odds:
            if event not in on_going_events:
                on_going_events.add(event)
                threading.Thread(target=monitor_odds, args=(event,), daemon=True).start()
            return jsonify({"message": "Fetching odds. Please try again in a few seconds."}), 202

    return jsonify(latest_odds[event])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
