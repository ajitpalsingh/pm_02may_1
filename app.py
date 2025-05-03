import streamlit as st
import pandas as pd
import base64
from datetime import datetime, timedelta

st.set_page_config(page_title="Resource Monitoring App", layout="wide")
st.title("📊 Resource Monitoring and Availability Dashboard")

# --- Non-Availability Section ---
st.header("🛠️ Log or Edit Resource Non-Availability")

resources = ["Alice", "Bob", "Charlie", "Diana"]
user = st.selectbox("Select Resource", resources)

log_file = f"{user}_non_availability.csv"
try:
    df = pd.read_csv(log_file)
    df["Start"] = pd.to_datetime(df["Start"])
    df["End"] = pd.to_datetime(df["End"])
except FileNotFoundError:
    df = pd.DataFrame(columns=["Start", "End", "Reason"])

st.subheader("Current Non-Availability Log (Editable)")
edited_df = st.data_editor(
    df,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    key="editor"
)

if st.button("💾 Save Changes"):
    edited_df["Start"] = pd.to_datetime(edited_df["Start"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    edited_df["End"] = pd.to_datetime(edited_df["End"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    edited_df.to_csv(log_file, index=False)
    st.success("Changes saved successfully!")

# --- Placeholder for other modules ---
st.divider()
st.subheader("📌 Other modules (GPT, Reports, Utilization, etc.)")
st.markdown("⬅️ These are to be merged with existing GPT + Report generation features.")