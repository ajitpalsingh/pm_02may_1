
import streamlit as st
import pandas as pd

st.title("Calendar Click Handler Fix Example")

clicked_date = st.text_input("Simulated clicked date input")

if clicked_date and isinstance(clicked_date, str):
    try:
        click_time = pd.to_datetime(clicked_date)
        st.success(f"Parsed date: {click_time}")
    except ValueError:
        st.warning("Could not parse the clicked date.")
        click_time = None
else:
    click_time = None

if click_time:
    st.write("Do something with the valid datetime:", click_time)
