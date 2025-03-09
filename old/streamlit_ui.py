import streamlit as st
import requests
import time
import pandas as pd
import plotly.express as px

# Initialize session state for storing history
if 'history' not in st.session_state:
    st.session_state.history = pd.DataFrame(
        columns=["timestamp", "odds_t1", "odds_t2", "probability_t1", "probability_t2", "margin"])

# Streamlit App
st.title("Live Odds and Probability Tracker")

# Endpoint URL
URL = "http://192.168.68.104:5000/odds"


# Function to fetch data
def fetch_data():
    try:
        response = requests.get(URL)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None


# Real-time update interval
update_interval = st.slider("Update Interval (seconds)", 1, 10, 2)

# Live data fetching
placeholder = st.empty()

while True:
    data = fetch_data()
    if data:
        margin = (data["probability_t1"] + data["probability_t2"] - 1) * 100

        new_row = pd.DataFrame([{
            "timestamp": pd.to_datetime(data["timestamp"], unit='s'),
            "odds_t1": float(data["odds_t1"]),
            "odds_t2": float(data["odds_t2"]),
            "probability_t1": data["probability_t1"] * 100,
            "probability_t2": data["probability_t2"] * 100,
            "margin": margin
        }])

        st.session_state.history = pd.concat([st.session_state.history, new_row], ignore_index=True)

        # Plot Odds with Dual Axis
        fig_odds = px.line(st.session_state.history, x="timestamp", y=["odds_t1", "odds_t2"],
                           title="Odds Over Time", labels={"value": "Odds", "variable": "Teams"})

        # Plot Probability as Stacked Area Chart
        fig_prob = px.area(st.session_state.history, x="timestamp", y=["probability_t1", "probability_t2"],
                           title="Probability Over Time (Stacked)",
                           labels={"value": "Probability (%)", "variable": "Teams"},
                           line_group=None)

        # Display graphs and metrics
        with placeholder.container():
            st.metric(label="Bookmaker Margin", value=f"{margin:.2f}%")
            st.plotly_chart(fig_odds, use_container_width=True)
            st.plotly_chart(fig_prob, use_container_width=True)

        time.sleep(update_interval)
