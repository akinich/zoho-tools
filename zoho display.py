import streamlit as st
import requests
import pandas as pd

st.title("📦 Zoho Books Item Fetcher")

# Load Zoho credentials securely
zoho = st.secrets["zoho"]
client_id = zoho["client_id"]
client_secret = zoho["client_secret"]
refresh_token = zoho["refresh_token"]
organization_id = zoho["organization_id"]
base_url = zoho["base_url"]

# Step 1: Refresh the access token
st.write("🔄 Refreshing access token...")

token_url = "https://accounts.zoho.com/oauth/v2/token"
params = {
    "refresh_token": refresh_token,
    "client_id": client_id,
    "client_secret": client_secret,
    "grant_type": "refresh_token"
}

response = requests.post(token_url, params=params)
if response.status_code == 200:
    access_token = response.json().get("access_token")
    st.success("✅ Access token refreshed successfully!")
else:
    st.error(f"Error refreshing token: {response.text}")
    st.stop()

# Step 2: Fetch first 20 items
headers = {
    "Authorization": f"Zoho-oauthtoken {access_token}"
}

items_url = f"{base_url}/items"
params = {"organization_id": organization_id, "per_page": 20}

st.write("📦 Fetching first 20 items from Zoho Books...")
res = requests.get(items_url, headers=headers, params=params)

if res.status_code == 200:
    data = res.json().get("items", [])
    if not data:
        st.warning("No items found.")
    else:
        df = pd.DataFrame(data)
        st.dataframe(df)
else:
    st.error(f"Error fetching items: {res.text}")
