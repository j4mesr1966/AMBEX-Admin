import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, date as date_cls

SUPABASE_URL = "https://bwhkccfwzsvjtsaqvhyy.supabase.co"
SUPABASE_KEY = "sb_publishable_LdjLR-FIesLKwuqtQzHDpg_C-OIdGgg"

st.set_page_config(
    page_title="AMBEX Support",
    page_icon="📋",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.title("AMBEX Support")
st.caption("Mobile-friendly registration admin")

RATING_OPTIONS = ["", "Very Satisfied", "Satisfied", "Neutral", "Dissatisfied", "Very Dissatisfied"]
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


def fmt_date(value):
    text = safe(value)[:10]
    if not text:
        return "—"
    try:
        return datetime.strptime(text, "%Y-%m-%d").strftime("%d-%b-%Y")
    except Exception:
        return text


@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


supabase = get_supabase()

tab_regs, tab_flights, tab_courses = st.tabs(
    ["Registrations", "Standard Flight Options", "Default Course Dates"]
)
with tab_flights:
    st.subheader("Add a standard flight option")
    fo_out = st.date_input("Flight Out Date")
    fo_out_no = st.text_input("Outbound flight number")
    fo_ret = st.date_input("Associated Flight Return Date")
    fo_ret_no = st.text_input("Return flight number")
    fo_label = st.text_input("Label (optional)")

    if st.button("Save flight option"):
        try:
            supabase.table("flight_options").insert({
                "outbound_date": fo_out.isoformat(),
                "outbound_flight_number": fo_out_no.strip() or None,
                "return_date": fo_ret.isoformat(),
                "return_flight_number": fo_ret_no.strip() or None,
                "label": fo_label.strip() or None,
                "is_active": True,
            }).execute()
            st.success("Flight option saved")
            st.rerun()
        except Exception as e:
            st.error("Could not save flight option. Check that the flight_options table exists.")
            st.caption(str(e))

    try:
        flights = supabase.table("flight_options").select("*").order("outbound_date").execute().data or []
    except Exception as e:
        st.error("Could not load flight options. Check that the flight_options table exists and RLS allows select.")
        st.caption(str(e))
        flights = []

    try:
        flights = supabase.table("flight_options").select("*").order("outbound_date").execute().data or []
    except Exception as e:
        st.error("Could not load flight options. Check that the flight_options table exists and RLS allows select.")
        st.caption(str(e))
        flights = []    
        
    st.subheader("Existing options")
        
    if flights:
        view = pd.DataFrame(flights)
        for col in ["outbound_date", "return_date"]:
            if col in view.columns:
                view[col] = view[col].apply(fmt_date)
        st.dataframe(view, use_container_width=True)

        st.markdown("**Deactivate an option**")
        labels = [f"{fmt_date(f.get('outbound_date'))} → {fmt_date(f.get('return_date'))} ({f.get('id')[:8]})" for f in flights]
        choice = st.selectbox("Select option", ["-"] + labels)
        if choice != "-" and st.button("Deactivate selected option"):
            selected = flights[labels.index(choice)]
            supabase.table("flight_options").update({"is_active": False}).eq("id", selected["id"]).execute()
            st.success("Option deactivated")
            st.rerun()
    else:
        st.info("No standard flight options yet. Add one above.")

    st.subheader("Add a default course date")
    st.caption("End date is calculated as the Saturday at the end of the duration, and can be overridden.")

    cd_label = st.text_input("Label (optional)", key="cd_label")
    cd_start = st.date_input("Course Start Date", key="cd_start")
    cd_weeks = st.number_input("Duration (weeks)", min_value=1, max_value=12, value=4, key="cd_weeks")

    calculated_end = date_cls.fromordinal(cd_start.toordinal() + (int(cd_weeks) * 7) - 3)

    cd_end = st.date_input(
        "Course End Date (overridable)",
        value=calculated_end,
        key=f"cd_end_{cd_start}_{int(cd_weeks)}"
    )
    st.caption(f"Calculated Saturday: {calculated_end.strftime('%d-%b-%Y')}")

    if st.button("Save course date option"):
        try:
            supabase.table("course_date_options").insert({
                "label": cd_label.strip() or None,
                "start_date": cd_start.isoformat(),
                "duration_weeks": int(cd_weeks),
                "end_date": cd_end.isoformat(),
                "is_active": True,
            }).execute()
            st.success("Course date option saved")
            st.rerun()
        except Exception as e:
            st.error("Could not save course date option. Check that course_date_options exists.")
            st.caption(str(e))

    try:
        course_dates = supabase.table("course_date_options").select("*").order("start_date").execute().data or []
    except Exception as e:
        st.error("Could not load course date options.")
        st.caption(str(e))
        course_dates = []

    st.subheader("Existing course dates")
    if course_dates:
        view = pd.DataFrame(course_dates)
        for col in ["start_date", "end_date"]:
            if col in view.columns:
                view[col] = view[col].apply(fmt_date)
        st.dataframe(view, use_container_width=True)

        labels = [
            f"{fmt_date(c.get('start_date'))} → {fmt_date(c.get('end_date'))} ({c.get('duration_weeks')} wks)"
            for c in course_dates
        ]
        choice = st.selectbox("Deactivate an option", ["-"] + labels, key="cd_deactivate")
        if choice != "-" and st.button("Deactivate selected course date"):
            selected = course_dates[labels.index(choice)]
            supabase.table("course_date_options").update({"is_active": False}).eq("id", selected["id"]).execute()
            st.success("Course date option deactivated")
            st.rerun()
    else:
        st.info("No default course dates yet. Add one above.")

with tab_courses:
    st.subheader("Add a default course date")
    st.caption("End date is calculated as the Saturday at the end of the duration, and can be overridden.")

    cd_label = st.text_input("Label (optional)", key="cd_label")
    cd_start = st.date_input("Course Start Date", key="cd_start")
    cd_weeks = st.number_input("Duration (weeks)", min_value=1, max_value=12, value=4, key="cd_weeks")

    calculated_end = date_cls.fromordinal(cd_start.toordinal() + (int(cd_weeks) * 7) - 3)

    cd_end = st.date_input(
        "Course End Date (overridable)",
        value=calculated_end,
        key=f"cd_end_{cd_start}_{int(cd_weeks)}"
    )
    st.caption(f"Calculated Saturday: {calculated_end.strftime('%d-%b-%Y')}")

    if st.button("Save course date option"):
        try:
            supabase.table("course_date_options").insert({
                "label": cd_label.strip() or None,
                "start_date": cd_start.isoformat(),
                "duration_weeks": int(cd_weeks),
                "end_date": cd_end.isoformat(),
                "is_active": True,
            }).execute()
            st.success("Course date option saved")
            st.rerun()
        except Exception as e:
            st.error("Could not save course date option.")
            st.caption(str(e))

    try:
        course_dates = supabase.table("course_date_options").select("*").order("start_date").execute().data or []
    except Exception as e:
        st.error("Could not load course date options.")
        st.caption(str(e))
        course_dates = []

    st.subheader("Existing course dates")
    if course_dates:
        view = pd.DataFrame(course_dates)
        for col in ["start_date", "end_date"]:
            if col in view.columns:
                view[col] = view[col].apply(fmt_date)
        st.dataframe(view, use_container_width=True)
    else:
        st.info("No default course dates yet. Add one above.")

with tab_regs:
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
    else:
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
            cols = ["surname", "first_name", "passport_number", "guardian_tel", "guardian_email", "host_family_name", "host_phone", "host_email"]
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
                title = f"{safe(row.get('surname'))} {safe(row.get('first_name'))}  |  {safe(row.get('status'))}  |  {safe(row.get('course_type'))[:30]}"
                with st.expander(title):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Date of Birth:** {fmt_date(row.get('date_of_birth'))}")
                        st.markdown(f"**Passport:** {safe(row.get('passport_number')) or '—'}")
                        st.markdown(f"**Gender:** {safe(row.get('gender')) or '—'}")
                        st.markdown(f"**Nationality:** {safe(row.get('nationality')) or '—'}")
                    with col2:
                        st.markdown(f"**Course:** {safe(row.get('course_type')) or '—'}")
                        st.markdown(f"**Course Start Date:** {fmt_date(row.get('course_start_date'))}")
                        st.markdown(f"**Course End Date:** {fmt_date(row.get('course_end_date'))}")
                        st.markdown(f"**Duration:** {safe(row.get('duration_weeks')) or '—'} weeks")

                    st.markdown(f"**Address:** {safe(row.get('home_address_english')) or '—'}")
                    st.markdown(f"**Allergies:** {safe(row.get('allergies')) or 'None'}")
                    st.markdown(f"**Flight out:** {fmt_date(row.get('flight_out_date'))}  |  **Return:** {fmt_date(row.get('flight_return_date'))}")
                    st.markdown(f"**Arrangement:** {safe(row.get('flight_arrangement')) or '—'}")

                    st.markdown("---")
                    st.markdown("**Guardian**")
                    st.markdown(f"{safe(row.get('guardian_name')) or '—'}  |  {safe(row.get('guardian_tel')) or '—'}")
                    st.markdown(f"{safe(row.get('guardian_email')) or '—'}  |  LINE: {safe(row.get('guardian_line_id')) or '—'}")

                    st.markdown("---")
                    st.subheader("Host family")
                    host_name = st.text_input("Host family name", value=safe(row.get("host_family_name")), key=f"hn_{record_id}")
                    host_phone_type = st.selectbox(
                        "Phone type", PHONE_TYPES,
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
                            label, RATING_OPTIONS,
                            index=RATING_OPTIONS.index(current) if current in RATING_OPTIONS else 0,
                            key=f"{field_key}_{record_id}"
                        )
                    feedback_comments = st.text_area("Comments", value=safe(row.get("feedback_comments")), key=f"fc_{record_id}")

                    current_status = safe(row.get("status")) or "Draft"
                    status_choices = ["Draft", "Submitted", "Confirmed", "Cancelled"]
                    new_status = st.selectbox(
                        "Change status", status_choices,
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
