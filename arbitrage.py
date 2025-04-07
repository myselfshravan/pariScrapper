import requests
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def get_odds(event_url):
    try:
        response = requests.get(event_url)
        data = response.json()
        return float(data["odds_t1"]), float(data["odds_t2"])
    except Exception as e:
        logging.error(f"Error fetching data: {e}")
        return None, None


def check_arbitrage(initial_odds, current_odds):
    arb_condition = (1 / initial_odds) + (1 / current_odds)
    return arb_condition < 1, arb_condition


def notify_arbitrage(initial_bet, initial_odds, hedge_odds):
    logging.info(
        f"Arbitrage Opportunity Found! Initial Bet: {initial_bet} at {initial_odds}, Hedge Bet at {hedge_odds}")
    # You can integrate email, Telegram, or other notifications here


if __name__ == "__main__":
    EVENT_URL = "http://127.0.0.1:5000/odds?event=gujarat-titans-punjab-kings-12844553"
    CHECK_INTERVAL = 10
    initial_bet = 55
    initial_odds = float("1.64")
    logging.info(f"Tracking arbitrage for initial bet on {initial_bet} at {initial_odds}")

    while True:
        odds_t1, odds_t2 = get_odds(EVENT_URL)
        if odds_t1 and odds_t2:
            logging.info(f"Fetched Odds - Team 1: {odds_t1}, Team 2: {odds_t2}")

            current_odds = odds_t2 if initial_bet == "T1" else odds_t1
            is_arb, arb_value = check_arbitrage(initial_odds, current_odds)

            if is_arb:
                notify_arbitrage(initial_bet, initial_odds, current_odds)
                break  # Stop execution once arbitrage is found

        time.sleep(CHECK_INTERVAL)
