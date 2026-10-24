import streamlit as st
import pandas as pd
import requests
from supabase import create_client, Client
from datetime import datetime, date as date_cls, timedelta

SHEET_REFRESH_URL = "https://script.google.com/macros/s/AKfycbyvy4ax3fSugB4eaekhLrW4HUmKTloqzlo16Ix0K0YPV5n2XQlNOMOY1t9jHkHHlnxTEw/exec"

def refresh_sheet():
    try:
        requests.get(SHEET_REFRESH_URL, timeout=30)
    except Exception:
        pass

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
TRANSPORT_OPTIONS = ["Coach", "Mini Bus", "Train", "Taxi", "Other"]
STATUS_OPTIONS = ["Offered", "Confirmed"]
DEPOSIT_STATUS_OPTIONS = ["Unpaid", "Paid"]


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


def parse_iso_date(value):
    text = safe(value)[:10]
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except Exception:
        return None


@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


supabase = get_supabase()

tab_regs, tab_flights, tab_courses, tab_trips, tab_taxis = st.tabs(
    ["Update & Amend Registrations", "Setup Flights", "Setup Courses", "Setup Trips", "Book Taxi"]
)

with tab_flights:
    st.subheader("Add a standard flight option")
    today = date_cls.today()
    fo_out = st.date_input("Flight Out Date", value=today, min_value=today)
    fo_out_no = st.text_input("Outbound flight number")
    fo_ret = st.date_input(
        "Flight Return Date",
        value=fo_out + timedelta(days=1),
        min_value=fo_out + timedelta(days=1),
        key=f"fo_ret_{fo_out}"
    )
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
            st.error("Could not save flight option.")
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
        # Hide id from the editor (keep it in the dataframe for deletion matching)
        display_cols = [c for c in view.columns if c != "id"]
        edited = st.data_editor(
            view[display_cols],
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            key="flights_editor"
        )
        if st.button("Save flight changes"):
            try:
                # Rows that disappeared are deleted
                original_ids = set(view["id"].astype(str))
                # Map remaining rows back by position is unreliable after format; delete by matching on remaining count is hard.
                # Safer: show a simple delete list.
                st.warning("Use the delete list below for reliable removal. Table edits are display-only for now.")
            except Exception as e:
                st.error("Could not save flight changes.")
                st.caption(str(e))

        st.markdown("**Delete a flight option**")
        labels = [
            f"{fmt_date(f.get('outbound_date'))} → {fmt_date(f.get('return_date'))} | {f.get('outbound_flight_number') or ''} / {f.get('return_flight_number') or ''}"
            for f in flights
        ]
        choice = st.selectbox("Select option to delete", ["-"] + labels, key="flight_delete")
        if choice != "-" and st.button("Delete selected flight"):
            selected = flights[labels.index(choice)]
            supabase.table("flight_options").delete().eq("id", selected["id"]).execute()
            st.success("Flight option deleted")
            st.rerun()
    else:
        st.info("No standard flight options yet. Add one above.")

with tab_courses:
    st.subheader("Add a default course date")
    st.caption("End date is calculated as the Saturday at the end of the duration, and can be overridden.")

    cd_label = st.text_input("Group Name", key="course_date_label")
    cd_start = st.date_input("Course Start Date", key="course_date_start")
    cd_weeks = st.number_input("Duration (weeks)", min_value=1, max_value=12, value=4, key="course_date_weeks")
    calculated_end = date_cls.fromordinal(cd_start.toordinal() + (int(cd_weeks) * 7) - 3)
    cd_end = st.date_input(
        "Course End Date (overridable)",
        value=calculated_end,
        key=f"course_date_end_{cd_start}_{int(cd_weeks)}"
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
        display_cols = [c for c in view.columns if c not in ("id", "is_active")]
        st.data_editor(
            view[display_cols],
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            key="courses_editor"
        )
        st.markdown("**Delete a course date**")
        labels = [
            f"{safe(c.get('label')) or 'Unnamed'} | {fmt_date(c.get('start_date'))} → {fmt_date(c.get('end_date'))} ({c.get('duration_weeks')} wks)"
            for c in course_dates
        ]
        choice = st.selectbox("Select course date to delete", ["-"] + labels, key="course_delete")
        if choice != "-" and st.button("Delete selected course date"):
            selected = course_dates[labels.index(choice)]
            supabase.table("course_date_options").delete().eq("id", selected["id"]).execute()
            st.success("Course date deleted")
            st.rerun()
    else:
        st.info("No default course dates yet. Add one above.")

with tab_trips:
    st.subheader("Setup Trips")
    st.caption("Add individual trips. Non-Saturday / non-Sunday dates are flagged.")

    st.markdown("### Add a trip")
    new_date = st.date_input("Date", key="new_trip_date")
    st.caption(new_date.strftime("%d-%b-%Y"))
    new_day = "Saturday" if new_date.weekday() == 5 else "Sunday" if new_date.weekday() == 6 else new_date.strftime("%A")
    is_weekend = new_date.weekday() in (5, 6)
    if is_weekend:
        st.write(f"Day: **{new_day}**")
    else:
        st.error(f"Flagged: {new_day} is not a Saturday or Sunday")

    trip_provider = st.selectbox("Provider", ["Anglo", "Ambex"], key="new_trip_provider")
    trip_to = st.text_input("Trip to", key="new_trip_to")
    trip_price = st.number_input("Price", min_value=0.0, step=1.0, key="new_trip_price")

    if st.button("Save trip"):
        try:
            supabase.table("trips").insert({
                "trip_date": new_date.isoformat(),
                "day_name": new_day,
                "trip_type": trip_provider,
                "description": trip_to.strip() or None,
                "cost_15_plus": trip_price,
                "is_active": True,
            }).execute()
            st.success("Trip saved")
            st.rerun()
        except Exception as e:
            st.error("Could not save trip.")
            st.caption(str(e))

    st.markdown("### Trips")
    try:
        trips = supabase.table("trips").select("*").order("trip_date").execute().data or []
    except Exception as e:
        st.error("Could not load trips.")
        st.caption(str(e))
        trips = []

    if not trips:
        st.info("No trips yet. Add one above.")
    else:
        if st.button("Select all"):
            st.session_state["trips_force_select"] = True
            st.session_state["trips_editor_key"] = st.session_state.get("trips_editor_key", 0) + 1
            st.rerun()
        force_select = st.session_state.get("trips_force_select", False)
        editor_key = st.session_state.get("trips_editor_key", 0)

        rows = []
        for t in trips:
            d = parse_iso_date(t.get("trip_date"))
            day = t.get("day_name") or (d.strftime("%A") if d else "")
            flagged = "Yes" if d and d.weekday() not in (5, 6) else ""
            rows.append({
                "Select": force_select,
                "Day": day,
                "Date": fmt_date(t.get("trip_date")),
                "Flagged": flagged,
                "Provider": t.get("trip_type") or "",
                "Trip to": t.get("description") or "",
                "Price": t.get("cost_15_plus") or "",
                "id": str(t.get("id")),
            })
        view = pd.DataFrame(rows)
        edited = st.data_editor(
            view,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Select": st.column_config.CheckboxColumn("Select", default=False),
                "id": None,
            },
            disabled=["Day", "Date", "Flagged", "Provider", "Trip to", "Price", "id"],
            key=f"trips_editor_{editor_key}"
        )
        if st.button("Delete selected trips"):
            if force_select:
                to_delete = [str(t.get("id")) for t in trips]
            else:
                to_delete = edited.loc[edited["Select"] == True, "id"].tolist()
            if not to_delete:
                st.warning("Select at least one trip to delete.")
            else:
                try:
                    for tid in to_delete:
                        supabase.table("trips").delete().eq("id", tid).execute()
                    st.session_state["trips_force_select"] = False
                    st.session_state["trips_editor_key"] = st.session_state.get("trips_editor_key", 0) + 1
                    st.success(f"Deleted {len(to_delete)} trip(s)")
                    st.rerun()
                except Exception as e:
                    st.error("Could not delete trips.")
                    st.caption(str(e))

with tab_taxis:
    SCHOOL_L1 = "Anglo-Continental School of English"
    SCHOOL_L2 = "29-35 Wimborne Rd"
    SCHOOL_L3 = "Bournemouth"
    SCHOOL_PC = "BH2 6NA"

    st.subheader("Book Taxi")

    taxi_date = st.date_input("Date", key="taxi_date")
    st.caption(taxi_date.strftime("%d-%b-%Y"))
    taxi_time = st.time_input("Time", key="taxi_time")

    def next_job_number():
        stamp = datetime.now().strftime("%Y%m%d-%H%M")
        suffix = str(datetime.now().microsecond)[-4:]
        return f"TX-{stamp}-{suffix}"

    job_number = st.text_input("Job number", value=next_job_number(), key="taxi_job")
    taxi_status = st.selectbox(
        "Status",
        ["Booked", "Paid", "Invoice due", "Invoice paid"],
        key="taxi_status"
    )
    main_passenger = st.text_input("Main passenger", key="taxi_main")
    passenger_contact = st.text_input("Passenger contact number", key="taxi_pax_tel")
    pax_count = st.number_input("Number of passengers", min_value=1, max_value=20, value=1, key="taxi_pax_count")

    pickup_school = st.radio("Pickup from school", ["No", "Yes"], horizontal=True, key="taxi_pickup_school")
    if pickup_school == "Yes":
        pickup_l1, pickup_l2, pickup_l3, pickup_pc = SCHOOL_L1, SCHOOL_L2, SCHOOL_L3, SCHOOL_PC
        st.text_input("Pickup address line 1", value=pickup_l1, disabled=True, key="taxi_pick_l1_disp")
        st.text_input("Pickup address line 2", value=pickup_l2, disabled=True, key="taxi_pick_l2_disp")
        st.text_input("Pickup address line 3", value=pickup_l3, disabled=True, key="taxi_pick_l3_disp")
        st.text_input("Pickup postcode", value=pickup_pc, disabled=True, key="taxi_pick_pc_disp")
    else:
        pickup_l1 = st.text_input("Pickup address line 1", key="taxi_pick_l1")
        pickup_l2 = st.text_input("Pickup address line 2", key="taxi_pick_l2")
        pickup_l3 = st.text_input("Pickup address line 3", key="taxi_pick_l3")
        pickup_pc = st.text_input("Pickup postcode", key="taxi_pick_pc")

    dropoff_school = st.radio("Dropoff to school", ["No", "Yes"], horizontal=True, key="taxi_drop_school")
    if dropoff_school == "Yes":
        drop_l1, drop_l2, drop_l3, drop_pc = SCHOOL_L1, SCHOOL_L2, SCHOOL_L3, SCHOOL_PC
        st.text_input("Dropoff address line 1", value=drop_l1, disabled=True, key="taxi_drop_l1_disp")
        st.text_input("Dropoff address line 2", value=drop_l2, disabled=True, key="taxi_drop_l2_disp")
        st.text_input("Dropoff address line 3", value=drop_l3, disabled=True, key="taxi_drop_l3_disp")
        st.text_input("Dropoff postcode", value=drop_pc, disabled=True, key="taxi_drop_pc_disp")
    else:
        drop_l1 = st.text_input("Dropoff address line 1", key="taxi_drop_l1")
        drop_l2 = st.text_input("Dropoff address line 2", key="taxi_drop_l2")
        drop_l3 = st.text_input("Dropoff address line 3", key="taxi_drop_l3")
        drop_pc = st.text_input("Dropoff postcode", key="taxi_drop_pc")

    driver_name = st.text_input("Driver name", key="taxi_driver")
    driver_contact = st.text_input("Driver contact number", key="taxi_driver_tel")
    cost = st.number_input("Cost", min_value=0.0, step=0.5, key="taxi_cost")
    price_pp = st.number_input("Price per passenger", min_value=0.0, step=0.5, key="taxi_price_pp")
    total_price = float(price_pp) * int(pax_count)
    st.write(f"**Total Price:** £{total_price:.2f}")
    taxi_notes = st.text_area("Notes", key="taxi_notes")

    if st.button("Save taxi booking"):
        try:
            supabase.table("taxi_bookings").insert({
                "job_number": job_number.strip() or next_job_number(),
                "status": taxi_status,
                "booking_date": taxi_date.isoformat(),
                "booking_time": taxi_time.strftime("%H:%M"),
                "main_passenger": main_passenger.strip() or None,
                "passenger_contact": passenger_contact.strip() or None,
                "number_of_passengers": int(pax_count),
                "pickup_from_school": pickup_school == "Yes",
                "pickup_line1": pickup_l1.strip() if pickup_l1 else None,
                "pickup_line2": pickup_l2.strip() if pickup_l2 else None,
                "pickup_line3": pickup_l3.strip() if pickup_l3 else None,
                "pickup_postcode": pickup_pc.strip() if pickup_pc else None,
                "dropoff_to_school": dropoff_school == "Yes",
                "dropoff_line1": drop_l1.strip() if drop_l1 else None,
                "dropoff_line2": drop_l2.strip() if drop_l2 else None,
                "dropoff_line3": drop_l3.strip() if drop_l3 else None,
                "dropoff_postcode": drop_pc.strip() if drop_pc else None,
                "driver_name": driver_name.strip() or None,
                "driver_contact": driver_contact.strip() or None,
                "cost": cost,
                "price_per_passenger": price_pp,
                "total_price": total_price,
                "notes": taxi_notes.strip() or None,
            }).execute()
            st.success(f"Taxi booking saved ({job_number})")
            st.rerun()
        except Exception as e:
            st.error("Could not save taxi booking.")
            st.caption(str(e))

    st.markdown("### Existing taxi bookings")
    try:
        bookings = supabase.table("taxi_bookings").select("*").order("booking_date", desc=True).execute().data or []
    except Exception as e:
        st.error("Could not load taxi bookings.")
        st.caption(str(e))
        bookings = []

    if bookings:
        view = pd.DataFrame(bookings)
        if "booking_date" in view.columns:
            view["booking_date"] = view["booking_date"].apply(fmt_date)
        display_cols = [c for c in view.columns if c != "id"]
        st.data_editor(
            view[display_cols],
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            key="taxis_editor"
        )
    else:
        st.info("No taxi bookings yet.")

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

        def sheet_row(r):
            nat = safe(r.get("nationality"))
            nationality_out = "" if nat.lower() == "taiwanese" else nat
            return {
                "Timestamp": safe(r.get("submitted_at") or r.get("created_at") or r.get("updated_at")),
                "Male or Female?": safe(r.get("gender")),
                "Surname/family name of student (as on passport)": safe(r.get("surname")),
                "First name of student (as on passport)": safe(r.get("first_name")),
                "Nationality if NOT Taiwanese (leave blank if Taiwanese)": nationality_out,
                "Date of Birth (day/month/year) as on passport": fmt_date(r.get("date_of_birth")),
                "Student's age when starting their course": safe(r.get("age_at_start")),
                "Student's age when ending their course": safe(r.get("age_at_end")),
                "Over 18s student’s contact tel": safe(r.get("student_tel")),
                "Over 18s student’s email": safe(r.get("student_email")),
                "Student's passport number": safe(r.get("passport_number")),
                "Permission to request to go out without supervision (Age group 14-16)": safe(r.get("permission_unsupervised")),
                "Permission for Anglo to use photography/video, social media": safe(r.get("permission_anglo_media")),
                "Course Type": safe(r.get("course_type")),
                "If you chose Other for your course type, please specify": safe(r.get("course_other")),
                "Course Start Date": fmt_date(r.get("course_start_date")),
                "Course Duration (number of weeks)": safe(r.get("duration_weeks")),
                "Does the student require a host family?": safe(r.get("requires_host_family")),
                "Host family from date": fmt_date(r.get("host_family_from")),
                "Host family leave date": fmt_date(r.get("host_family_leave")),
                "Homestay pairing request": safe(r.get("homestay_pairing")),
                "Allergies": safe(r.get("allergies")),
                "Medical issues": safe(r.get("medical_issues")),
                "Special dietary requirements": safe(r.get("dietary_requirements")),
                "Prefer a host family with a pet?": safe(r.get("host_family_pet")),
                "Learning disabilities": safe(r.get("learning_disabilities")),
                "Medications": safe(r.get("medications")),
                "Any other remarks": safe(r.get("notes")),
                "First name of one parent or guardian": safe(r.get("guardian_name")),
                "Next of kin contact tel": safe(r.get("guardian_tel")),
                "Next of kin email": safe(r.get("guardian_email")),
                "Next of kin's relationship to student": safe(r.get("next_of_kin_relationship")),
                "Does next of kin speak English?": safe(r.get("guardian_speaks_english")),
                "Permission for AMBEX to take student out": safe(r.get("permission_ambex_outing")),
                "Contact parent's LINE name": safe(r.get("guardian_line_id")),
                "Join the Parent and Child Program?": safe(r.get("parent_child_program")),
                "Accompany the child but NOT join the program?": safe(r.get("accompany_not_program")),
                "Home address (in English)": safe(r.get("home_address_english")),
                "Notes": safe(r.get("notes")),
            }

        export_df = pd.DataFrame([sheet_row(r) for _, r in filtered.iterrows()])
        csv = export_df.to_csv(index=False).encode("utf-8")
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
                            refresh_sheet()
                            st.success("Saved")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Update failed: {e}")
