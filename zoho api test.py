import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Zoho Books Items Viewer", layout="wide")

st.title("📘 Zoho Books Items Viewer")

st.markdown("""
Use this app to connect to Zoho Books, exchange your grant token, and fetch all items.
> **Note:** Grant token is valid for only 10 minutes.
""")

# --- Input fields for credentials ---
with st.form("zoho_form"):
    client_id = st.text_input("Client ID", placeholder="Enter your Zoho client ID")
    client_secret = st.text_input("Client Secret", placeholder="Enter your Zoho client secret", type="password")
    redirect_uri = st.text_input("Redirect URI", placeholder="https://example.com")
    grant_token = st.text_input("Grant Token", placeholder="Paste your Zoho grant token")
    organization_id = st.text_input("Organization ID", placeholder="Enter your Zoho Books Organization ID")

    submitted = st.form_submit_button("Fetch Items")

if submitted:
    if not all([client_id, client_secret, redirect_uri, grant_token, organization_id]):
        st.error("⚠️ Please fill in all fields before submitting.")
    else:
        st.info("⏳ Exchanging grant token for access token...")

        token_url = "https://accounts.zoho.com/oauth/v2/token"
        params = {
            "code": grant_token,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }

        token_response = requests.post(token_url, params=params)
        st.write("🔍 Token response from Zoho:")
        st.json(token_response.json())

        if token_response.status_code == 200:
            tokens = token_response.json()
            access_token = tokens.get("access_token")
            refresh_token = tokens.get("refresh_token")

            st.success("✅ Token generated successfully!")
            st.code(f"Access Token: {access_token}\nRefresh Token: {refresh_token}", language="bash")

            st.info("📦 Fetching items from Zoho Books...")

            items_url = f"https://books.zoho.com/api/v3/items?organization_id={organization_id}"
            headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}

            items_response = requests.get(items_url, headers=headers)

            if items_response.status_code == 200:
                items_data = items_response.json().get("items", [])
                if items_data:
                    df = pd.DataFrame(items_data)
                    st.success(f"✅ Retrieved {len(df)} items from Zoho Books!")
                    st.dataframe(df)
                else:
                    st.warning("No items found in your organization.")
            else:
                st.error(f"Error fetching items: {items_response.text}")
        else:
            st.error(f"Error exchanging token: {token_response.text}")
