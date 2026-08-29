import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime

# ==========================================
# CONFIG – REPLACE THESE TWO VALUES
# ==========================================
SUPABASE_URL = "YOUR_SUPABASE_URL"
SUPABASE_KEY = "YOUR_SUPABASE_ANON_KEY"

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

RATING_OPTIONS = [
    "",
    "Very Satisfied",
    "Satisfied",
    "Neutral",
    "Dissatisfied",
    "Very Dissatisfied",
]

PHONE_TYPES = ["", "Mobile", "Home", "WhatsApp", "LINE"]

FEEDBACK_FIELDS = [
    ("feedback_accommodation_quality", "Overall accommodation quality"),
    ("feedback_room_cleanliness", "Room cleanliness and condition"),
    ("feedback_interaction_communication", "Interaction and communication with host family"),
    ("feedback_friendliness", "Friendliness of host family"),
    ("feedback_meal_quality_portion", "Quality and portion of meals"),
    ("feedback_meals_dietary", "Meals meeting personal/dietary needs"),
    ("feedback_safety_convenience", "Safety and convenience of accommodation"),
]


def safe(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value)


@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


supabase = get_supabase()


@st.cache_data(ttl=30)
def load_registrations():
    response = supabase.table("registrations").select("*").order("created_at", desc=True).execute()
    data = response.data
    if not data:
        return pd.DataFrame()
    return pd.DataFrame(data)


df = load_registrations()

if df.empty:
    st.info("No registrations found yet.")
    st.stop()

with st.sidebar:
    st.header("Filters")
    search = st.text_input("Search (name, passport, phone, email, host family)", "")

    status_options = ["All"] + sorted([s for s in df["status"].dropna().unique().tolist()])
    status_filter = st.selectbox("Status", status_options)

    if st.button("🔄 Refresh data"):
        st.cache_data.clear()
        st.rerun()

filtered = df.copy()

if search:
    q = search.lower()
    cols = [
        "surname", "first_name", "passport_number",
        "guardian_tel", "guardian_email", "host_family_name",
        "host_phone", "host_email"
    ]
    mask = False
    for col in cols:
        if col in filtered.columns:
            mask = mask | filtered[col].fillna("").astype(str).str.lower().str.contains(q)
    filtered = filtered[mask]

if status_filter != "All":
    filtered = filtered[filtered["status"] == status_filter]

st.write(f"**{len(filtered)}** record(s) shown")

csv = filtered.to_csv(index=False).encode("utf-8")
st.download_button(
    label="⬇️ Download CSV",
    data=csv,
    file_name=f"ambex_registrations_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
    mime="text/csv",
    use_container_width=True
)

st.divider()

if filtered.empty:
    st.warning("No records match your filters.")
else:
    for _, row in filtered.iterrows():
        record_id = row["id"]
        course_label = safe(row.get("course_type"))[:30]
        title = f"{safe(row.get('surname'))} {safe(row.get('first_name'))}  |  {safe(row.get('status'))}  |  {course_label}"

        with st.expander(title):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Date of Birth:** {safe(row.get('date_of_birth')) or '—'}")
                st.markdown(f"**Passport:** {safe(row.get('passport_number')) or '—'}")
                st.markdown(f"**Gender:** {safe(row.get('gender')) or '—'}")
                st.markdown(f"**Nationality:** {safe(row.get('nationality')) or '—'}")
            with col2:
                st.markdown(f"**Course:** {safe(row.get('course_type')) or '—'}")
                st.markdown(f"**Start:** {safe(row.get('course_start_date')) or '—'}")
                st.markdown(f"**End:** {safe(row.get('course_end_date')) or '—'}")
                st.markdown(f"**Duration:** {safe(row.get('duration_weeks')) or '—'} weeks")

            st.markdown(f"**Address:** {safe(row.get('home_address_english')) or '—'}")
            st.markdown(f"**Allergies:** {safe(row.get('allergies')) or 'None'}")

            st.markdown("---")
            st.markdown("**Guardian**")
            st.markdown(f"{safe(row.get('guardian_name')) or '—'}  |  {safe(row.get('guardian_tel')) or '—'}")
            st.markdown(f"{safe(row.get('guardian_email')) or '—'}  |  LINE: {safe(row.get('guardian_line_id')) or '—'}")
            st.markdown(f"Speaks English: {safe(row.get('guardian_speaks_english')) or '—'}")

            st.markdown("---")
            st.subheader("Host family")

            host_name = st.text_input("Host family name", value=safe(row.get("host_family_name")), key=f"hn_{record_id}")
            host_phone_type = st.selectbox(
                "Phone type",
                PHONE_TYPES,
                index=PHONE_TYPES.index(safe(row.get("host_phone_type"))) if safe(row.get("host_phone_type")) in PHONE_TYPES else 0,
                key=f"hpt_{record_id}"
            )
            host_phone = st.text_input("Host phone", value=safe(row.get("host_phone")), key=f"hp_{record_id}")
            host_email = st.text_input("Host email", value=safe(row.get("host_email")), key=f"he_{record_id}")
            host_l1 = st.text_input("Address line 1", value=safe(row.get("host_address_line1")), key=f"ha1_{record_id}")
            host_l2 = st.text_input("Address line 2", value=safe(row.get("host_address_line2")), key=f"ha2_{record_id}")
            host_l3 = st.text_input("Address line 3", value=safe(row.get("host_address_line3")), key=f"ha3_{record_id}")
            host_l4 = st.text_input("Address line 4", value=safe(row.get("host_address_line4")), key=f"ha4_{record_id}")
            host_pc = st.text_input("Postcode", value=safe(row.get("host_postcode")), key=f"hpc_{record_id}")

            st.markdown("---")
            st.subheader("Student feedback")

            feedback_values = {}
            for field_key, label in FEEDBACK_FIELDS:
                current = safe(row.get(field_key))
                feedback_values[field_key] = st.selectbox(
                    label,
                    RATING_OPTIONS,
                    index=RATING_OPTIONS.index(current) if current in RATING_OPTIONS else 0,
                    key=f"{field_key}_{record_id}"
                )

            feedback_comments = st.text_area(
                "Comments",
                value=safe(row.get("feedback_comments")),
                key=f"fc_{record_id}"
            )

            st.markdown("---")
            current_status = safe(row.get("status")) or "Draft"
            status_choices = ["Draft", "Submitted", "Confirmed", "Cancelled"]
            new_status = st.selectbox(
                "Change status",
                status_choices,
                index=status_choices.index(current_status) if current_status in status_choices else 0,
                key=f"status_{record_id}"
            )

            if st.button("Save host family, feedback & status", key=f"save_{record_id}", use_container_width=True):
                payload = {
                    "host_family_name": host_name.strip() or None,
                    "host_phone_type": host_phone_type or None,
                    "host_phone": host_phone.strip() or None,
                    "host_email": host_email.strip() or None,
                    "host_address_line1": host_l1.strip() or None,
                    "host_address_line2": host_l2.strip() or None,
                    "host_address_line3": host_l3.strip() or None,
                    "host_address_line4": host_l4.strip() or None,
                    "host_postcode": host_pc.strip() or None,
                    "feedback_comments": feedback_comments.strip() or None,
                    "status": new_status,
                    "updated_at": datetime.utcnow().isoformat(),
                }
                payload.update({k: (v or None) for k, v in feedback_values.items()})

                try:
                    supabase.table("registrations").update(payload).eq("id", record_id).execute()
                    st.success("Saved")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Update failed: {e}")

            st.caption(f"Created: {safe(row.get('created_at')) or '—'}  |  Updated: {safe(row.get('updated_at')) or '—'}")
