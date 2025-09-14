import streamlit as st
from streamlit_autorefresh import st_autorefresh


import pandas as pd
import math
from pathlib import Path
from firebase_admin import credentials, firestore
import firebase_admin

from datetime import datetime as dt

import plotly.express as px

import os, json

# Set the title and favicon that appear in the Browser's tab bar.
st.set_page_config(
    page_title='GDP dashboard',
    page_icon=':earth_americas:', # This is an emoji shortcode. Could be a URL too.
)

# firebase_key = st.secrets['FIREBASE_KEY']

if not firebase_admin._apps:
    firebase_admin.initialize_app(credentials.Certificate(".streamlit/energy-manager-ed733-firebase-adminsdk-fbsvc-f4489abd7c.json"))
db = firestore.client()


# Data 
@st.cache_data
def load_data():
    docs = db.collection("kwh_price").stream()
    data = []
    for doc in docs:
        d = doc.to_dict()
        # Assume Firestore doc has fields: "timestamp" and "price"
        data.append({"timestamp": d["timestamp"], "price": d["price"]})
    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp")
    return df

df = load_data()



# --- UI CONTROLS ---
st.title("📈 Price Time Series from Firestore")


if df.empty:
    st.warning("No data available in Firestore yet.")
else:
    # Let user pick time range
    min_date, max_date = df["timestamp"].min(), df["timestamp"].max()
    st.sidebar.header("X-Axis Scale")
    start_date = st.sidebar.date_input(
        "Start", min_date.date(), min_value=min_date.date(), max_value=max_date.date()
    )
    end_date = st.sidebar.date_input(
        "End", max_date.date(), min_value=min_date.date(), max_value=max_date.date()
    )

    # Filter dataframe based on selection
    mask = (df["timestamp"].dt.date >= start_date) & (df["timestamp"].dt.date <= end_date)
    filtered_df = df.loc[mask]

    # Plot
    fig = px.line(filtered_df, x="timestamp", y="price", title="Price Development")
    fig.update_xaxes(rangeslider_visible=True)

    st.plotly_chart(fig, use_container_width=True)

# command sender
def send_command_to_db(command):
    # Data to store
    data = {
        "timestamp": dt.now(),
        "user_command": command
    }
    db.collection("user_commands").document(dt.now().strftime("%Y-%m-%d_%H:%M:%S")).set(data)


def get_latest_command():
    """Fetch the most recent command"""
    docs = (
        db.collection("user_commands")
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(1)
        .stream()
    )
    latest = None
    for doc in docs:
        latest = doc.to_dict().get("user_command", 0)
        # print(f"Latest command from DB: {latest}")
    return int(latest) if latest is not None else 0

# --- Streamlit UI ---
st.title("🔋 Battery Control")

# Auto-refresh every 10 seconds
refresh_interval = st.sidebar.number_input("Auto-refresh interval (sec)", 5, 60, 10)

st_autorefresh(interval=refresh_interval * 1000, key="refresh")

# Initialize session state from Firestore (first load only)
if "battery_state" not in st.session_state:
    st.session_state.battery_state = get_latest_command()

# Toggle bound to session state
toggle_state = st.toggle("Battery ON/OFF", value=st.session_state.battery_state == 1)

# Detect change -> update Firestore
new_state = 1 if toggle_state else 0
if new_state != st.session_state.battery_state:
    send_command_to_db(new_state)
    st.session_state.battery_state = new_state
    st.toast(f"Sent command: {new_state}")

# Always check Firestore for external changes (e.g. another user)
latest_command = get_latest_command()
if latest_command != st.session_state.battery_state:
    st.session_state.battery_state = latest_command
    st.experimental_rerun()




# def get_gdp_data():
#     """Grab GDP data from a CSV file.

#     This uses caching to avoid having to read the file every time. If we were
#     reading from an HTTP endpoint instead of a file, it's a good idea to set
#     a maximum age to the cache with the TTL argument: @st.cache_data(ttl='1d')
#     """

#     # Instead of a CSV on disk, you could read from an HTTP endpoint here too.
#     DATA_FILENAME = Path(__file__).parent/'data/gdp_data.csv'
#     raw_gdp_df = pd.read_csv(DATA_FILENAME)

#     MIN_YEAR = 1960
#     MAX_YEAR = 2022

#     # The data above has columns like:
#     # - Country Name
#     # - Country Code
#     # - [Stuff I don't care about]
#     # - GDP for 1960
#     # - GDP for 1961
#     # - GDP for 1962
#     # - ...
#     # - GDP for 2022
#     #
#     # ...but I want this instead:
#     # - Country Name
#     # - Country Code
#     # - Year
#     # - GDP
#     #
#     # So let's pivot all those year-columns into two: Year and GDP
#     gdp_df = raw_gdp_df.melt(
#         ['Country Code'],
#         [str(x) for x in range(MIN_YEAR, MAX_YEAR + 1)],
#         'Year',
#         'GDP',
#     )

#     # Convert years from string to integers
#     gdp_df['Year'] = pd.to_numeric(gdp_df['Year'])

#     return gdp_df

# gdp_df = get_gdp_data()

# # -----------------------------------------------------------------------------
# # Draw the actual page

# # Set the title that appears at the top of the page.
# '''
# # :earth_americas: GDP dashboard test of Raoul

# Browse GDP data from the [World Bank Open Data](https://data.worldbank.org/) website. As you'll
# notice, the data only goes to 2022 right now, and datapoints for certain years are often missing.
# But it's otherwise a great (and did I mention _free_?) source of data.
# '''

# # Add some spacing
# ''
# ''

# min_value = gdp_df['Year'].min()
# max_value = gdp_df['Year'].max()

# from_year, to_year = st.slider(
#     'Which years are you interested in?',
#     min_value=min_value,
#     max_value=max_value,
#     value=[min_value, max_value])

# countries = gdp_df['Country Code'].unique()

# if not len(countries):
#     st.warning("Select at least one country")

# selected_countries = st.multiselect(
#     'Which countries would you like to view?',
#     countries,
#     ['DEU', 'FRA', 'GBR', 'BRA', 'MEX', 'JPN'])

# ''
# ''
# ''

# # Filter the data
# filtered_gdp_df = gdp_df[
#     (gdp_df['Country Code'].isin(selected_countries))
#     & (gdp_df['Year'] <= to_year)
#     & (from_year <= gdp_df['Year'])
# ]

# st.header('GDP over time', divider='gray')

# ''

# st.line_chart(
#     filtered_gdp_df,
#     x='Year',
#     y='GDP',
#     color='Country Code',
# )

# ''
# ''


# first_year = gdp_df[gdp_df['Year'] == from_year]
# last_year = gdp_df[gdp_df['Year'] == to_year]

# st.header(f'GDP in {to_year}', divider='gray')

# ''

# cols = st.columns(4)

# for i, country in enumerate(selected_countries):
#     col = cols[i % len(cols)]

#     with col:
#         first_gdp = first_year[first_year['Country Code'] == country]['GDP'].iat[0] / 1000000000
#         last_gdp = last_year[last_year['Country Code'] == country]['GDP'].iat[0] / 1000000000

#         if math.isnan(first_gdp):
#             growth = 'n/a'
#             delta_color = 'off'
#         else:
#             growth = f'{last_gdp / first_gdp:,.2f}x'
#             delta_color = 'normal'

#         st.metric(
#             label=f'{country} GDP',
#             value=f'{last_gdp:,.0f}B',
#             delta=growth,
#             delta_color=delta_color
#         )
