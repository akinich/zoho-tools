import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from supabase import create_client, Client

st.set_page_config(page_title="Zoho ↔ Supabase Sync", page_icon="🔄", layout="wide")

# ---------- CONFIG ----------
ZOHO_CLIENT_ID = st.secrets["ZOHO_CLIENT_ID"]
ZOHO_CLIENT_SECRET = st.secrets["ZOHO_CLIENT_SECRET"]
ZOHO_REFRESH_TOKEN = st.secrets["ZOHO_REFRESH_TOKEN"]
ZOHO_ORGANIZATION_ID = st.secrets["ZOHO_ORGANIZATION_ID"]
ZOHO_BASE_URL = st.secrets["ZOHO_BASE_URL"]

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ---------- ZOHO AUTH ----------
@st.cache_data(ttl=3000)
def get_access_token():
    """Exchange refresh token for access token"""
    token_url = "https://accounts.zoho.com/oauth/v2/token"
    payload = {
        "refresh_token": ZOHO_REFRESH_TOKEN,
        "client_id": ZOHO_CLIENT_ID,
        "client_secret": ZOHO_CLIENT_SECRET,
        "grant_type": "refresh_token"
    }
    r = requests.post(token_url, data=payload)
    if r.status_code == 200:
        return r.json().get("access_token")
    else:
        st.error(f"Auth error: {r.text}")
        return None

# ---------- ZOHO DATA FETCH ----------
def fetch_all_items():
    """Fetch all items from Zoho Books (auto-paginate)"""
    access_token = get_access_token()
    if not access_token:
        st.error("Access token not found.")
        return []

    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
    items = []
    page = 1

    while True:
        resp = requests.get(
            f"{ZOHO_BASE_URL}/items?organization_id={ZOHO_ORGANIZATION_ID}&page={page}",
            headers=headers
        )
        if resp.status_code != 200:
            st.error(f"Error fetching items: {resp.text}")
            break
        data = resp.json()
        page_items = data.get("items", [])
        if not page_items:
            break
        items.extend(page_items)
        if not data.get("page_context", {}).get("has_more_page"):
            break
        page += 1

    return items

# ---------- UPSERT TO SUPABASE ----------
def upsert_items(items):
    """Upsert Zoho items into Supabase"""
    for item in items:
        record = {
            "item_id": item.get("item_id"),
            "organization_id": ZOHO_ORGANIZATION_ID,
            "name": item.get("name"),
            "sku": item.get("sku"),
            "hsn_or_sac": item.get("hsn_or_sac"),
            "status": item.get("status"),
            "product_type": item.get("product_type"),
            "item_type": item.get("item_type"),
            "unit": item.get("unit"),
            "purchase_rate": item.get("purchase_rate"),
            "purchase_account_name": item.get("purchase_account_name"),
            "selling_rate": item.get("rate"),
            "selling_account_name": item.get("account_name"),
            "is_taxable": item.get("is_taxable"),
            "tax_percentage": item.get("tax_percentage"),
            "created_time": item.get("created_time"),
            "last_modified_time": item.get("last_modified_time"),
            "last_synced_at": datetime.utcnow().isoformat(),
            "raw_json": item
        }

        supabase.table("items_core").upsert(record).execute()

# ---------- UI ----------
st.title("📦 Zoho Books → Supabase Sync Dashboard")

if st.button("🔄 Refresh / Sync Now"):
    with st.spinner("Syncing data from Zoho Books..."):
        items = fetch_all_items()
        if items:
            upsert_items(items)
            st.success(f"✅ Synced {len(items)} items successfully!")

# ---------- DISPLAY DATA ----------
with st.spinner("Loading all items from Supabase..."):
    data = supabase.table("items_core").select("*").execute()
    df = pd.DataFrame(data.data)

if not df.empty:
    # Convert timestamp fields to datetime and sort
    if "last_modified_time" in df.columns:
        df["last_modified_time"] = pd.to_datetime(df["last_modified_time"], errors="coerce")
        df = df.sort_values(by="last_modified_time", ascending=False)
    st.dataframe(df, use_container_width=True)
else:
    st.info("No items found in Supabase yet.")
