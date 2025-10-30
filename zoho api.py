import streamlit as st
import requests

st.title("Zoho Books Token Generator")

st.write("Paste your Zoho **grant token** below (expires in 10 minutes):")

grant_token = st.text_input("Grant Token")
client_id = st.text_input("Client ID")
client_secret = st.text_input("Client Secret")
redirect_uri = st.text_input("Redirect URI", "https://www.zoho.com/books")  # can be anything valid

if st.button("Generate Tokens"):
    if not all([grant_token, client_id, client_secret]):
        st.error("Please enter all details.")
    else:
        token_url = "https://accounts.zoho.in/oauth/v2/token"
        params = {
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "code": grant_token,
        }
        st.write("🔄 Exchanging grant token for access token...")
        response = requests.post(token_url, params=params)
        data = response.json()

        if "access_token" in data:
            st.success("✅ Token generated successfully!")
            st.write("**Access Token:**", data["access_token"])
            st.write("**Refresh Token:**", data.get("refresh_token"))
            st.write("**Expires In:**", data.get("expires_in", "Unknown"), "seconds")
        else:
            st.error("❌ Token generation failed!")
            st.json(data)
