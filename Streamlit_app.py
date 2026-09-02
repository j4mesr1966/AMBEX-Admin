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
TRANSPORT_OPTIONS = ["Coach", "Mini Bus", "Train", "Taxi"]
TRIP_TYPES = ["Anglo", "AMBEX"]
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
        st.dataframe(view, use_container_width=True)
        labels = [
            f"{fmt_date(c.get('start_date'))} → {fmt_date(c.get('end_date'))} ({c.get('duration_weeks')} wks)"
            for c in course_dates
        ]
        choice = st.selectbox("Deactivate an option", ["-"] + labels, key="course_deactivate")
        if choice != "-" and st.button("Deactivate selected course date"):
            selected = course_dates[labels.index(choice)]
            supabase.table("course_date_options").update({"is_active": False}).eq("id", selected["id"]).execute()
            st.success("Course date option deactivated")
            st.rerun()
    else:
        st.info("No default course dates yet. Add one above.")

with tab_trips:
    st.subheader("Setup Trips")
    st.caption("Generate creates Anglo trips on Saturdays and AMBEX trips on Sundays. You can still add either type on either day manually.")

    try:
        active_courses = supabase.table("course_date_options").select("*").eq("is_active", True).order("start_date").execute().data or []
    except Exception as e:
        st.error("Could not load course groups.")
        st.caption(str(e))
        active_courses = []

    def overlapping_courses(trip_date):
        matches = []
        for c in active_courses:
            start = parse_iso_date(c.get("start_date"))
            end = parse_iso_date(c.get("end_date"))
            if start and end and start <= trip_date <= end:
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
                min_start = min(parse_iso_date(c["start_date"]) for c in active_courses if parse_iso_date(c.get("start_date")))
                max_end = max(parse_iso_date(c["end_date"]) for c in active_courses if parse_iso_date(c.get("end_date")))
                window_start = min_start - timedelta(weeks=int(extra_before))
                window_end = max_end + timedelta(weeks=int(extra_after))
                d = window_start
                while d <= window_end:
                    if d.weekday() in (5, 6):
                        all_dates.add(d)
                    d += timedelta(days=1)

            created = 0
            for trip_date in sorted(all_dates):
                if trip_date.weekday() == 5:
                    day_name = "Saturday"
                    trip_type = "Anglo"
                else:
                    day_name = "Sunday"
                    trip_type = "AMBEX"

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
        index=TRANSPORT_OPTIONS.index(default_transport),
        key=f"new_trip_transport_{new_type}"
    )
    transport_custom = st.text_input("Or type a different transportation", key="new_trip_transport_custom")
    new_transport = transport_custom.strip() or transport_choice

    ambex_status = ambex_offer = ambex_ref = None
    ambex_cost_plus = ambex_cost_under = None
    deposit_status = deposit_amount = deposit_due = None
    selected_group_ids = []

    if new_type == "AMBEX":
        st.markdown("**AMBEX details**")
        ambex_status = st.selectbox("Status", STATUS_OPTIONS, key="new_trip_status")
        ambex_offer = st.text_input("Offer From", key="new_trip_offer")
        group_options = overlapping_courses(new_date) or active_courses
        group_labels = {group_label(c): c["id"] for c in group_options}
        selected_labels = st.multiselect(
            "Group Name",
            options=list(group_labels.keys()),
            default=[group_label(c) for c in overlapping_courses(new_date)],
            key="new_trip_groups"
        )
        selected_group_ids = [group_labels[l] for l in selected_labels if l in group_labels]
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

    if not trips:
        st.info("No trips yet. Generate weekends or add one above.")
    else:
        display_cols = [
            "day_name", "trip_date", "trip_type", "description", "transportation",
            "status", "offer_from", "booking_reference", "cost_15_plus", "cost_under_15",
            "deposit_status", "deposit_amount", "deposit_date_due", "is_active", "id"
        ]
        view = pd.DataFrame(trips)
        for col in display_cols:
            if col not in view.columns:
                view[col] = None
        view = view[display_cols]

        st.caption("Edit cells in the table, then click Save table changes. Id is on the far right.")
        edited = st.data_editor(
            view,
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": st.column_config.TextColumn("Id", disabled=True),
                "trip_date": st.column_config.TextColumn("Date"),
                "day_name": st.column_config.TextColumn("Day"),
                "trip_type": st.column_config.SelectboxColumn("Trip Type", options=["Anglo", "AMBEX"]),
                "transportation": st.column_config.SelectboxColumn("Transportation", options=TRANSPORT_OPTIONS),
                "status": st.column_config.SelectboxColumn("Status", options=["", "Offered", "Confirmed"]),
                "deposit_status": st.column_config.SelectboxColumn("Deposit Status", options=["", "Unpaid", "Paid"]),
                "is_active": st.column_config.CheckboxColumn("Active"),
            },
            num_rows="fixed",
            key="trips_editor"
        )

        if st.button("Save table changes"):
            try:
                for _, r in edited.iterrows():
                    supabase.table("trips").update({
                        "day_name": r.get("day_name") or None,
                        "trip_date": str(r.get("trip_date"))[:10] if r.get("trip_date") else None,
                        "trip_type": r.get("trip_type") or None,
                        "description": r.get("description") or None,
                        "transportation": r.get("transportation") or None,
                        "status": r.get("status") or None,
                        "offer_from": r.get("offer_from") or None,
                        "booking_reference": r.get("booking_reference") or None,
                        "cost_15_plus": r.get("cost_15_plus") if pd.notna(r.get("cost_15_plus")) else None,
                        "cost_under_15": r.get("cost_under_15") if pd.notna(r.get("cost_under_15")) else None,
                        "deposit_status": r.get("deposit_status") or None,
                        "deposit_amount": r.get("deposit_amount") if pd.notna(r.get("deposit_amount")) else None,
                        "deposit_date_due": str(r.get("deposit_date_due"))[:10] if r.get("deposit_date_due") else None,
                        "is_active": bool(r.get("is_active")),
                        "updated_at": datetime.utcnow().isoformat(),
                    }).eq("id", r.get("id")).execute()
                st.success("Table changes saved")
                st.rerun()
            except Exception as e:
                st.error("Could not save table changes.")
                st.caption(str(e))

        st.markdown("### Edit window")
        trip_labels = [
            f"{fmt_date(t.get('trip_date'))} | {t.get('day_name')} | {t.get('trip_type')} | {str(t.get('id'))[:8]}"
            for t in trips
        ]
        picked = st.selectbox("Open a trip to edit", ["-"] + trip_labels, key="trip_edit_pick")
        if picked != "-":
            t = trips[trip_labels.index(picked)]
            st.text_input("Id", value=str(t.get("id")), disabled=True, key="edit_trip_id")
            current_date = parse_iso_date(t.get("trip_date")) or date_cls.today()
            edit_date = st.date_input("Date", value=current_date, key="edit_trip_date")
            st.caption(edit_date.strftime("%d-%b-%Y"))
            edit_day = "Saturday" if edit_date.weekday() == 5 else "Sunday" if edit_date.weekday() == 6 else edit_date.strftime("%A")
            st.write(f"Day: **{edit_day}**")
            edit_type = st.selectbox(
                "Trip Type",
                TRIP_TYPES,
                index=0 if t.get("trip_type") == "Anglo" else 1,
                key="edit_trip_type"
            )
            edit_desc = st.text_input("Description", value=safe(t.get("description")), key="edit_trip_desc")
            current_transport = safe(t.get("transportation")) or "Coach"
            transport_opts = TRANSPORT_OPTIONS[:]
            if current_transport not in transport_opts:
                transport_opts = [current_transport] + transport_opts
            edit_transport = st.selectbox(
                "Transportation",
                transport_opts,
                index=transport_opts.index(current_transport),
                key="edit_trip_transport"
            )
            edit_transport_custom = st.text_input("Or type a different transportation", key="edit_trip_transport_custom")
            edit_transport = edit_transport_custom.strip() or edit_transport

            edit_status = edit_offer = edit_ref = None
            edit_cost_plus = edit_cost_under = None
            edit_dep_status = edit_dep_amount = edit_dep_due = None
            if edit_type == "AMBEX":
                st.markdown("**AMBEX details**")
                edit_status = st.selectbox(
                    "Status",
                    STATUS_OPTIONS,
                    index=STATUS_OPTIONS.index(t.get("status")) if t.get("status") in STATUS_OPTIONS else 0,
                    key="edit_trip_status"
                )
                edit_offer = st.text_input("Offer From", value=safe(t.get("offer_from")), key="edit_trip_offer")
                edit_ref = st.text_input("Booking Reference", value=safe(t.get("booking_reference")), key="edit_trip_ref")
                edit_cost_plus = st.number_input("Cost for 15+", value=float(t.get("cost_15_plus") or 0), key="edit_trip_cost_plus")
                edit_cost_under = st.number_input("Cost for under 15", value=float(t.get("cost_under_15") or 0), key="edit_trip_cost_under")
                edit_dep_status = st.selectbox(
                    "Deposit Status",
                    DEPOSIT_STATUS_OPTIONS,
                    index=DEPOSIT_STATUS_OPTIONS.index(t.get("deposit_status")) if t.get("deposit_status") in DEPOSIT_STATUS_OPTIONS else 0,
                    key="edit_trip_dep_status"
                )
                edit_dep_amount = st.number_input("Deposit Amount", value=float(t.get("deposit_amount") or 0), key="edit_trip_dep_amount")
                due_val = parse_iso_date(t.get("deposit_date_due")) or edit_date
                edit_dep_due = st.date_input("Deposit Date Due", value=due_val, key="edit_trip_dep_due")
                st.caption(edit_dep_due.strftime("%d-%b-%Y"))

            if st.button("Save edit window"):
                try:
                    supabase.table("trips").update({
                        "trip_date": edit_date.isoformat(),
                        "day_name": edit_day,
                        "trip_type": edit_type,
                        "description": edit_desc.strip() or None,
                        "transportation": edit_transport,
                        "status": edit_status if edit_type == "AMBEX" else None,
                        "offer_from": (edit_offer or "").strip() or None if edit_type == "AMBEX" else None,
                        "booking_reference": (edit_ref or "").strip() or None if edit_type == "AMBEX" else None,
                        "cost_15_plus": edit_cost_plus if edit_type == "AMBEX" else None,
                        "cost_under_15": edit_cost_under if edit_type == "AMBEX" else None,
                        "deposit_status": edit_dep_status if edit_type == "AMBEX" else None,
                        "deposit_amount": edit_dep_amount if edit_type == "AMBEX" else None,
                        "deposit_date_due": edit_dep_due.isoformat() if edit_type == "AMBEX" and edit_dep_due else None,
                        "updated_at": datetime.utcnow().isoformat(),
                    }).eq("id", t.get("id")).execute()
                    st.success("Trip updated")
                    st.rerun()
                except Exception as e:
                    st.error("Could not save this trip.")
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
    else:
        pickup_l1 = st.text_input("Pickup address line 1", key="taxi_pick_l1")
        pickup_l2 = st.text_input("Pickup address line 2", key="taxi_pick_l2")
        pickup_l3 = st.text_input("Pickup address line 3", key="taxi_pick_l3")
        pickup_pc = st.text_input("Pickup postcode", key="taxi_pick_pc")

    if pickup_school == "Yes":
        st.text_input("Pickup address line 1", value=pickup_l1, disabled=True, key="taxi_pick_l1_disp")
        st.text_input("Pickup address line 2", value=pickup_l2, disabled=True, key="taxi_pick_l2_disp")
        st.text_input("Pickup address line 3", value=pickup_l3, disabled=True, key="taxi_pick_l3_disp")
        st.text_input("Pickup postcode", value=pickup_pc, disabled=True, key="taxi_pick_pc_disp")

    dropoff_school = st.radio("Dropoff to school", ["No", "Yes"], horizontal=True, key="taxi_drop_school")
    if dropoff_school == "Yes":
        drop_l1, drop_l2, drop_l3, drop_pc = SCHOOL_L1, SCHOOL_L2, SCHOOL_L3, SCHOOL_PC
    else:
        drop_l1 = st.text_input("Dropoff address line 1", key="taxi_drop_l1")
        drop_l2 = st.text_input("Dropoff address line 2", key="taxi_drop_l2")
        drop_l3 = st.text_input("Dropoff address line 3", key="taxi_drop_l3")
        drop_pc = st.text_input("Dropoff postcode", key="taxi_drop_pc")

    if dropoff_school == "Yes":
        st.text_input("Dropoff address line 1", value=drop_l1, disabled=True, key="taxi_drop_l1_disp")
        st.text_input("Dropoff address line 2", value=drop_l2, disabled=True, key="taxi_drop_l2_disp")
        st.text_input("Dropoff address line 3", value=drop_l3, disabled=True, key="taxi_drop_l3_disp")
        st.text_input("Dropoff postcode", value=drop_pc, disabled=True, key="taxi_drop_pc_disp")

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
                "booking_date": taxi_date.isoformat(),
                "booking_time": taxi_time.strftime("%H:%M"),
                "main_passenger": main_passenger.strip() or None,
                "passenger_contact": passenger_contact.strip() or None,
                "number_of_passengers": int(pax_count),
                "status": taxi_status,
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
            st.error("Could not save taxi booking. Check that taxi_bookings exists.")
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
        st.dataframe(view, use_container_width=True)
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
