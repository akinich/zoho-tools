import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime
from supabase import create_client

# ---------------- CONFIG ----------------
st.title("🧾 Zoho Books ↔ Supabase Sync")
st.caption("Incremental sync with audit logging and progress tracking")

# Load from Streamlit Secrets
zoho_org_id = st.secrets["zoho"]["organization_id"]
access_token = st.secrets["zoho"]["access_token"]
supabase_url = st.secrets["supabase"]["url"]
supabase_key = st.secrets["supabase"]["anon_key"]

# Initialize Supabase client
supabase = create_client(supabase_url, supabase_key)

# ---------------- FETCH ZOHO ITEMS ----------------
def fetch_all_zoho_items():
    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
    all_items = []
    page = 1
    max_pages = 20  # prevent infinite loops
    progress = st.progress(0)
    status_text = st.empty()
    start_time = time.time()

    while True:
        status_text.text(f"Fetching Zoho items... Page {page}")
        res = requests.get(
            f"https://books.zoho.com/api/v3/items?organization_id={zoho_org_id}&page={page}",
            headers=headers,
        )
        data = res.json()
        if "items" not in data:
            st.error(data)
            break
        items = data["items"]
        all_items.extend(items)

        # update progress bar
        progress.progress(min(page / max_pages, 1.0))
        if len(items) < 200:
            break
        page += 1
        if page > max_pages:
            break

    elapsed = time.time() - start_time
    status_text.text(f"Fetched {len(all_items)} items in {elapsed:.1f} seconds ✅")
    return all_items


# ---------------- SYNC LOGIC ----------------
def sync_items():
    st.info("🔄 Starting incremental sync...")
    start_time = time.time()

    zoho_items = fetch_all_zoho_items()
    zoho_df = pd.DataFrame(zoho_items)

    # Fetch existing data from Supabase
    existing = supabase.table("items_core").select("*").execute().data
    existing_df = pd.DataFrame(existing) if existing else pd.DataFrame()

    new_items, updated_items, deleted_items = [], [], []

    # Convert to dict keyed by item_id
    zoho_map = {item["item_id"]: item for item in zoho_items}
    existing_map = {item["item_id"]: item for item in existing} if existing else {}

    total_ops = len(zoho_items) + len(existing_map)
    progress = st.progress(0)
    ops_done = 0

    # Detect additions and updates
    for item_id, item in zoho_map.items():
        if item_id not in existing_map:
            new_items.append(item)
        else:
            existing_item = existing_map[item_id]
            if any(item.get(k) != existing_item.get(k) for k in item.keys()):
                updated_items.append(item)
        ops_done += 1
        progress.progress(min(ops_done / total_ops, 1.0))

    # Detect deletions
    for item_id in existing_map.keys():
        if item_id not in zoho_map:
            deleted_items.append(existing_map[item_id])
        ops_done += 1
        progress.progress(min(ops_done / total_ops, 1.0))

    # Apply changes
    if new_items:
        supabase.table("items_core").upsert(new_items).execute()
    if updated_items:
        supabase.table("items_core").upsert(updated_items).execute()
    if deleted_items:
        for d in deleted_items:
            supabase.table("items_core").delete().eq("item_id", d["item_id"]).execute()

    # Log changes
    now = datetime.utcnow().isoformat()
    audit_logs = []
    for i in new_items:
        audit_logs.append({"change_type": "INSERT", "item_id": i["item_id"], "changed_at": now})
    for i in updated_items:
        audit_logs.append({"change_type": "UPDATE", "item_id": i["item_id"], "changed_at": now})
    for i in deleted_items:
        audit_logs.append({"change_type": "DELETE", "item_id": i["item_id"], "changed_at": now})

    if audit_logs:
        supabase.table("audit_change_log").insert(audit_logs).execute()

    # Update metadata
    supabase.table("sync_metadata").upsert(
        {
            "table_name": "items_core",
            "last_synced_at": now,
            "inserted_count": len(new_items),
            "updated_count": len(updated_items),
            "deleted_count": len(deleted_items),
        }
    ).execute()

    total_time = time.time() - start_time
    st.success(
        f"✅ Sync Complete in {total_time:.1f}s! | Inserted: {len(new_items)} | Updated: {len(updated_items)} | Deleted: {len(deleted_items)}"
    )


# ---------------- STREAMLIT UI ----------------
if st.button("🔁 Run Incremental Sync"):
    sync_items()

st.divider()

st.subheader("📋 Current items from Supabase")
data = supabase.table("items_core").select("*").limit(100).execute().data
if data:
    st.dataframe(pd.DataFrame(data))
else:
    st.warning("No items found in Supabase yet.")

st.subheader("🧠 Audit Log (last 10 changes)")
logs = supabase.table("audit_change_log").select("*").order("changed_at", desc=True).limit(10).execute().data
if logs:
    st.dataframe(pd.DataFrame(logs))
else:
    st.caption("No changes logged yet.")
