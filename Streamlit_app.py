import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime

# ==========================================
# CONFIG – REPLACE THESE TWO VALUES
# ==========================================
SUPABASE_URL = "https://bwhkccfwzsvjtsaqvhyy.supabase.co"
SUPABASE_KEY = "sb_publishable_LdjLR-FIesLKwuqtQzHDpg_C-OIdGgg"   # Publishable key

# ==========================================
# PAGE SETUP
# ==========================================
st.set_page_config(
    page_title="AMBEX Support",
    page_icon="📋",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.title("AMBEX Support")
st.caption("Mobile-friendly registration admin")

# ==========================================
# SUPABASE CONNECTION
# ==========================================
@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase()

# ==========================================
# LOAD DATA
# ==========================================
@st.cache_data(ttl=30)
def load_registrations():
    response = supabase.table("registrations").select("*").order("created_at", desc=True).execute()
    data = response.data
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    return df

df = load_registrations()

if df.empty:
    st.info("No registrations found yet.")
    st.stop()

# ==========================================
# SIDEBAR FILTERS / SEARCH
# ==========================================
with st.sidebar:
    st.header("Filters")
    search = st.text_input("Search (name, passport, phone, email)", "")
    
    status_options = ["All"] + sorted(df["status"].dropna().unique().tolist())
    status_filter = st.selectbox("Status", status_options)

    if st.button("🔄 Refresh data"):
        st.cache_data.clear()
        st.rerun()

# Apply filters
filtered = df.copy()

if search:
    search_lower = search.lower()
    mask = (
        filtered["surname"].fillna("").str.lower().str.contains(search_lower) |
        filtered["first_name"].fillna("").str.lower().str.contains(search_lower) |
        filtered["passport_number"].fillna("").str.lower().str.contains(search_lower) |
        filtered["guardian_tel"].fillna("").str.lower().str.contains(search_lower) |
        filtered["guardian_email"].fillna("").str.lower().str.contains(search_lower)
    )
    filtered = filtered[mask]

if status_filter != "All":
    filtered = filtered[filtered["status"] == status_filter]

st.write(f"**{len(filtered)}** record(s) shown")

# ==========================================
# EXPORT CSV
# ==========================================
csv = filtered.to_csv(index=False).encode("utf-8")
st.download_button(
    label="⬇️ Download CSV",
    data=csv,
    file_name=f"ambex_registrations_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
    mime="text/csv",
    use_container_width=True
)

st.divider()

# ==========================================
# LIST + DETAIL VIEW
# ==========================================
if filtered.empty:
    st.warning("No records match your filters.")
else:
    # Show a compact list
    for idx, row in filtered.iterrows():
        course_label = str(row.get("course_type") or "")[:30]
        with st.expander(f"{row.get('surname', '')} {row.get('first_name', '')}  |  {row.get('status', '')}  |  {course_label}"):
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Date of Birth:** {row.get('date_of_birth', '—')}")
                st.markdown(f"**Passport:** {row.get('passport_number', '—')}")
                st.markdown(f"**Gender:** {row.get('gender', '—')}")
                st.markdown(f"**Nationality:** {row.get('nationality', '—')}")
            with col2:
                st.markdown(f"**Course:** {row.get('course_type', '—')}")
                st.markdown(f"**Start:** {row.get('course_start_date', '—')}")
                st.markdown(f"**End:** {row.get('course_end_date', '—')}")
                st.markdown(f"**Duration:** {row.get('duration_weeks', '—')} weeks")

            st.markdown(f"**Address:** {row.get('home_address_english', '—')}")
            st.markdown(f"**Allergies:** {row.get('allergies', '—') or 'None'}")

            st.markdown("---")
            st.markdown("**Guardian**")
            st.markdown(f"{row.get('guardian_name', '—')}  |  {row.get('guardian_tel', '—')}")
            st.markdown(f"{row.get('guardian_email', '—')}  |  LINE: {row.get('guardian_line_id', '—')}")
            st.markdown(f"Speaks English: {row.get('guardian_speaks_english', '—')}")

            st.markdown("---")
            st.caption(f"Created: {row.get('created_at', '—')}  |  Updated: {row.get('updated_at', '—')}")

            # Status change
            current_status = row["status"]
            new_status = st.selectbox(
                "Change status",
                ["Draft", "Submitted", "Confirmed", "Cancelled"],
                index=["Draft", "Submitted", "Confirmed", "Cancelled"].index(current_status) if current_status in ["Draft", "Submitted", "Confirmed", "Cancelled"] else 0,
                key=f"status_{row['id']}"
            )

            if new_status != current_status:
                if st.button("Update Status", key=f"btn_{row['id']}", use_container_width=True):
                    try:
                        supabase.table("registrations").update({
                            "status": new_status,
                            "updated_at": datetime.utcnow().isoformat()
                        }).eq("id", row["id"]).execute()
                        st.success(f"Status updated to {new_status}")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Update failed: {e}")
