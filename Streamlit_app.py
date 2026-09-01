import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, date as date_cls, timedelta

SUPABASE_URL = "https://bwhkccfwzsvjtsaqvhyy.supabase.co"
SUPABASE_KEY = "sb_publishable_LdjLR-FIesLKwuqtQzHDpg_C-OIdGgg"

st.set_page_config(
    page_title="Daddy English Administration",
    page_icon="📋",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.title("Daddy English Administration")
st.caption("Mobile-friendly registration admin")

def get_app_password():
    try:
        return st.secrets["APP_PASSWORD"]
    except Exception:
        return "Matthew"

def check_password():
    if st.session_state.get("password_ok"):
        return True

    st.text_input("Password", type="password", key="admin_password")
    if st.button("Log in"):
        if st.session_state.get("admin_password") == get_app_password():
            st.session_state["password_ok"] = True
            st.rerun()
        else:
            st.error("Incorrect password")
    return False

if not check_password():
    st.stop()

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

tab_regs, tab_flights, tab_courses, tab_trips = st.tabs(
    ["Update & Amend Registrations", "Setup Flights", "Setup Courses", "Setup Trips"]
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
        st.error("Could not load flight options.")
        st.caption(str(e))
        flights = []

    st.subheader("Existing options")
    if flights:
        view = pd.DataFrame(flights)
        for col in ["outbound_date", "return_date"]:
            if col in view.columns:
                view[col] = view[col].apply(fmt_date)
        st.dataframe(view, use_container_width=True)

        labels = [
            f"{fmt_date(f.get('outbound_date'))} → {fmt_date(f.get('return_date'))} ({str(f.get('id'))[:8]})"
            for f in flights
        ]
        choice = st.selectbox("Deactivate an option", ["-"] + labels, key="flight_deactivate")
        if choice != "-" and st.button("Deactivate selected option"):
            selected = flights[labels.index(choice)]
            supabase.table("flight_options").update({"is_active": False}).eq("id", selected["id"]).execute()
            st.success("Option deactivated")
            st.rerun()
    else:
        st.info("No standard flight options yet. Add one above.")

with tab_trips:
    st.subheader("Setup Trips")
    st.caption("Weekend trips are Saturday and Sunday. You can generate them from course dates and also add extra trips before or after.")

    TRANSPORT_OPTIONS = ["Coach", "Mini Bus", "Train", "Taxi"]
    TRIP_TYPES = ["Anglo", "AMBEX"]
    STATUS_OPTIONS = ["Offered", "Confirmed"]
    DEPOSIT_STATUS_OPTIONS = ["Unpaid", "Paid"]

    try:
        active_courses = supabase.table("course_date_options").select("*").eq("is_active", True).order("start_date").execute().data or []
    except Exception as e:
        st.error("Could not load course groups.")
        st.caption(str(e))
        active_courses = []

    def overlapping_courses(trip_date):
        matches = []
        for c in active_courses:
            try:
                start = datetime.strptime(str(c.get("start_date"))[:10], "%Y-%m-%d").date()
                end = datetime.strptime(str(c.get("end_date"))[:10], "%Y-%m-%d").date()
            except Exception:
                continue
            if start <= trip_date <= end:
                matches.append(c)
        return matches

    def group_label(c):
        name = c.get("label") or "Unnamed group"
        return f"{name} ({fmt_date(c.get('start_date'))} to {fmt_date(c.get('end_date'))})"

    st.markdown("### Generate weekend trips from courses")
    extra_before = st.number_input("Extra weekends before courses", min_value=0, max_value=12, value=0, key="trip_before")
    extra_after = st.number_input("Extra weekends after courses", min_value=0, max_value=12, value=0, key="trip_after")

    if st.button("Generate Saturday & Sunday trips"):
        try:
            existing = supabase.table("trips").select("trip_date,trip_type").execute().data or []
            existing_keys = {(str(r.get("trip_date"))[:10], r.get("trip_type")) for r in existing}

            all_dates = set()
            if active_courses:
                min_start = min(datetime.strptime(str(c["start_date"])[:10], "%Y-%m-%d").date() for c in active_courses)
                max_end = max(datetime.strptime(str(c["end_date"])[:10], "%Y-%m-%d").date() for c in active_courses)
                window_start = min_start - timedelta(weeks=int(extra_before))
                window_end = max_end + timedelta(weeks=int(extra_after))
                d = window_start
                while d <= window_end:
                    if d.weekday() in (5, 6):
                        all_dates.add(d)
                    d += timedelta(days=1)

            created = 0
            for trip_date in sorted(all_dates):
                day_name = "Saturday" if trip_date.weekday() == 5 else "Sunday"
                for trip_type in TRIP_TYPES:
                    key = (trip_date.isoformat(), trip_type)
                    if key in existing_keys:
                        continue
                    transport = "Coach" if trip_type == "Anglo" else None
                    inserted = supabase.table("trips").insert({
                        "trip_date": trip_date.isoformat(),
                        "day_name": day_name,
                        "trip_type": trip_type,
                        "transportation": transport,
                        "is_active": True,
                    }).execute().data
                    if inserted:
                        trip_id = inserted[0]["id"]
                        for c in overlapping_courses(trip_date):
                            supabase.table("trip_groups").insert({
                                "trip_id": trip_id,
                                "course_date_option_id": c["id"],
                            }).execute()
                        created += 1
            st.success(f"Created {created} trip row(s)")
            st.rerun()
        except Exception as e:
            st.error("Could not generate trips.")
            st.caption(str(e))

    st.markdown("### Add a trip")
    new_date = st.date_input("Date", key="new_trip_date")
    st.caption(new_date.strftime("%d-%b-%Y"))
    new_day = "Saturday" if new_date.weekday() == 5 else "Sunday" if new_date.weekday() == 6 else new_date.strftime("%A")
    st.write(f"Day: **{new_day}**")

    new_type = st.selectbox("Trip Type", TRIP_TYPES, key="new_trip_type")
    new_desc = st.text_input("Description", key="new_trip_desc")

    default_transport = "Coach" if new_type == "Anglo" else TRANSPORT_OPTIONS[0]
    transport_choice = st.selectbox(
        "Transportation",
        TRANSPORT_OPTIONS,
        index=TRANSPORT_OPTIONS.index(default_transport) if default_transport in TRANSPORT_OPTIONS else 0,
        key=f"new_trip_transport_{new_type}"
    )
    transport_custom = st.text_input("Or type a different transportation", key="new_trip_transport_custom")
    new_transport = transport_custom.strip() or transport_choice

    ambex_status = None
    ambex_offer = None
    ambex_ref = None
    ambex_cost_plus = None
    ambex_cost_under = None
    deposit_status = None
    deposit_amount = None
    deposit_due = None
    selected_group_ids = []

    if new_type == "AMBEX":
        st.markdown("**AMBEX details**")
        ambex_status = st.selectbox("Status", STATUS_OPTIONS, key="new_trip_status")
        ambex_offer = st.text_input("Offer From", key="new_trip_offer")
        group_options = overlapping_courses(new_date) or active_courses
        group_labels = {group_label(c): c["id"] for c in group_options}
        selected_labels = st.multiselect(
            "Group Name (overlapping course groups are listed first)",
            options=list(group_labels.keys()),
            default=[group_label(c) for c in overlapping_courses(new_date)],
            key="new_trip_groups"
        )
        selected_group_ids = [group_labels[l] for l in selected_labels]
        ambex_ref = st.text_input("Booking Reference", key="new_trip_ref")
        ambex_cost_plus = st.number_input("Cost for 15+", min_value=0.0, step=1.0, key="new_trip_cost_plus")
        ambex_cost_under = st.number_input("Cost for under 15", min_value=0.0, step=1.0, key="new_trip_cost_under")
        deposit_status = st.selectbox("Deposit Status", DEPOSIT_STATUS_OPTIONS, key="new_trip_deposit_status")
        deposit_amount = st.number_input("Deposit Amount", min_value=0.0, step=1.0, key="new_trip_deposit_amount")
        deposit_due = st.date_input("Deposit Date Due", key="new_trip_deposit_due")
        st.caption(deposit_due.strftime("%d-%b-%Y"))

    if st.button("Save trip"):
        try:
            inserted = supabase.table("trips").insert({
                "trip_date": new_date.isoformat(),
                "day_name": new_day,
                "trip_type": new_type,
                "description": new_desc.strip() or None,
                "transportation": new_transport,
                "status": ambex_status if new_type == "AMBEX" else None,
                "offer_from": ambex_offer.strip() if ambex_offer else None,
                "booking_reference": ambex_ref.strip() if ambex_ref else None,
                "cost_15_plus": ambex_cost_plus if new_type == "AMBEX" else None,
                "cost_under_15": ambex_cost_under if new_type == "AMBEX" else None,
                "deposit_status": deposit_status if new_type == "AMBEX" else None,
                "deposit_amount": deposit_amount if new_type == "AMBEX" else None,
                "deposit_date_due": deposit_due.isoformat() if new_type == "AMBEX" and deposit_due else None,
                "is_active": True,
            }).execute().data
            if inserted and selected_group_ids:
                for gid in selected_group_ids:
                    supabase.table("trip_groups").insert({
                        "trip_id": inserted[0]["id"],
                        "course_date_option_id": gid,
                    }).execute()
            st.success("Trip saved")
            st.rerun()
        except Exception as e:
            st.error("Could not save trip.")
            st.caption(str(e))

    st.markdown("### Existing trips")
    try:
        trips = supabase.table("trips").select("*").order("trip_date").execute().data or []
    except Exception as e:
        st.error("Could not load trips.")
        st.caption(str(e))
        trips = []

    if trips:
        view = pd.DataFrame(trips)
        if "trip_date" in view.columns:
            view["trip_date"] = view["trip_date"].apply(fmt_date)
        if "deposit_date_due" in view.columns:
            view["deposit_date_due"] = view["deposit_date_due"].apply(fmt_date)
        st.dataframe(view, use_container_width=True)
    else:
        st.info("No trips yet. Generate weekends or add one above.")

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
