import streamlit as st
import pandas as pd

st.set_page_config(page_title="Resource Monitor", layout="wide")
st.title("📊 Resource Monitoring and Control App")

st.sidebar.header("Upload JIRA Excel File")
uploaded_file = st.sidebar.file_uploader("Choose an Excel file", type=["xlsx"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        st.success("✅ Data loaded successfully!")
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"❌ Error reading file: {e}")
else:
    st.info("📥 Please upload a JIRA Excel file to begin.")