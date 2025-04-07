import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
from streamlit_autorefresh import st_autorefresh

# Auto-refresh the app every 2 seconds
st_autorefresh(interval=2000, limit=None, key="odds_refresh")

if "data" not in st.session_state:
    st.session_state["data"] = []

st.title("Real-Time Odds, Probabilities & Bookmakers Margin")


def compute_margin(odds_t1, odds_t2):
    try:
        o1, o2 = float(odds_t1), float(odds_t2)
        margin = (1 / o1 + 1 / o2 - 1) * 100
        return round(margin, 2)
    except Exception as e:
        st.error(f"Error computing margin: {e}")
        return None


# Fetch the latest odds from the Flask endpoint
try:
    response = requests.get("http://127.0.0.1:5000/odds?event=gujarat-titans-punjab-kings-12844553")
    if response.status_code == 200:
        new_record = response.json()
        if not st.session_state["data"] or new_record["timestamp"] != st.session_state["data"][-1]["timestamp"]:
            st.session_state["data"].append(new_record)
    else:
        st.error("Flask endpoint returned an error.")
except Exception as e:
    st.error(f"Error fetching odds: {e}")

if st.session_state["data"]:
    # Convert history to DataFrame for plotting and analysis
    df = pd.DataFrame(st.session_state["data"])
    df["datetime"] = pd.to_datetime(df["timestamp"], unit="s")
    df.sort_values("datetime", inplace=True)
    df.set_index("datetime", inplace=True)

    df["margin"] = df.apply(lambda row: compute_margin(row["odds_t1"], row["odds_t2"]), axis=1)

    # Create two columns for charts and stats
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Odds Over Time")
        # Plot odds as a line chart (converted to float)
        odds_df = df[["odds_t1", "odds_t2"]].astype(float)
        st.line_chart(odds_df)

        st.subheader("Full History")
        st.dataframe(df[["odds_t1", "odds_t2", "probability_t1", "probability_t2", "margin"]].astype(float))

    with col2:
        st.subheader("Latest Stats")
        latest = st.session_state["data"][-1]
        odds_t1 = latest["odds_t1"]
        odds_t2 = latest["odds_t2"]
        prob_t1 = float(latest["probability_t1"])
        prob_t2 = float(latest["probability_t2"])
        margin = compute_margin(odds_t1, odds_t2)

        st.markdown(f"""
        **Latest Odds:**  
        - **Team 1:** {odds_t1}  
        - **Team 2:** {odds_t2}  

        **Latest Probabilities:**  
        - **Team 1:** {prob_t1:.4f}  
        - **Team 2:** {prob_t2:.4f}  

        **Bookmakers Margin:** {margin}%
        """)

        # Pie chart for probability distribution
        fig, ax = plt.subplots()
        labels = ['Team 1', 'Team 2']
        # Convert probabilities to percentages for display
        sizes = [prob_t1 * 100, prob_t2 * 100]
        ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
        ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
        st.pyplot(fig)

        # Probability slider as a visual gauge (non-interactive)
        st.slider(
            "Probability Distribution",
            min_value=0.0,
            max_value=1.0,
            value=(prob_t1, prob_t2),
            step=0.01,
            disabled=True
        )
else:
    st.info("Awaiting data from the Flask endpoint...")
