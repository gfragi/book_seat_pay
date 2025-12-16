import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime, date

# ---------- CONFIG ----------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DATA_FILE = DATA_DIR / "payments.csv"
INTEREST_FILE = DATA_DIR / "interest.csv"

LOGO_FILE = BASE_DIR / "logo_syllogos.png"

EVENT_TITLE = "Ο κουρέας της Σεβίλλης"
EVENT_DATE_LABEL = "Κυριακή 18 Ιανουαρίου 2026, 11:00"
EVENT_LINK = "https://www.ticketservices.gr/event/o-koureas-tis-sevillis-theatro-poreia/?lang=el"

TICKET_PRICE = 10
MAX_SEATS = 85

PAYMENT_DEADLINE = date(2026, 12, 20)
PAYMENT_DEADLINE_LABEL = "20 Δεκεμβρίου 2026"

ADMIN_PASSWORD = "syllogos2025"


# ---------- HELPERS ----------
def validate_payments_csv(df: pd.DataFrame) -> tuple[bool, str]:
    required = [
        "timestamp","parent_name","email","child_class",
        "child_tickets","adult_tickets","total_tickets",
        "total_amount","payment_method","payment_code",
        "payment_status","category","priority_number"
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        return False, f"Λείπουν στήλες: {', '.join(missing)}"

    # basic cleanup / types
    for col in ["child_tickets","adult_tickets","total_tickets","priority_number"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    df["total_amount"] = pd.to_numeric(df["total_amount"], errors="coerce").fillna(0).astype(float)

    # normalize strings
    for col in ["parent_name","email","child_class","payment_method","payment_code","payment_status","category"]:
        df[col] = df[col].astype(str).fillna("").str.strip()

    return True, ""

def load_data() -> pd.DataFrame:
    if DATA_FILE.exists():
        df = pd.read_csv(DATA_FILE, dtype={"payment_code": str})
    else:
        df = pd.DataFrame(
            columns=[
                "timestamp",
                "parent_name",
                "email",
                "child_class",
                "child_tickets",
                "adult_tickets",
                "total_tickets",
                "total_amount",
                "payment_method",
                "payment_code",
                "payment_status",   # pending / paid / waitlist / cancelled
                "category",         # interest / waitlist
                "priority_number",  # σειρά προτεραιότητας (κυρίως για waitlist)
            ]
        )
        df.to_csv(DATA_FILE, index=False)

    # τύποι/στήλες
    for col in ["child_tickets", "adult_tickets", "total_tickets", "priority_number"]:
        if col in df.columns:
            df[col] = df[col].fillna(0).astype(int)
    if "total_amount" in df.columns:
        df["total_amount"] = df["total_amount"].fillna(0).astype(float)
    if "payment_status" not in df.columns:
        df["payment_status"] = "pending"
    if "category" not in df.columns:
        df["category"] = "interest"
    if "priority_number" not in df.columns:
        df["priority_number"] = 0

    return df


def save_data(df: pd.DataFrame):
    df.to_csv(DATA_FILE, index=False)


def generate_payment_code(df: pd.DataFrame) -> str:
    return f"EVT-{len(df) + 1:03d}"


def compute_seats_used(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    mask = df["category"] != "waitlist"
    return int(df.loc[mask, "total_tickets"].sum())


def load_interest() -> pd.DataFrame:
    if not INTEREST_FILE.exists():
        return pd.DataFrame()

    df = pd.read_csv(INTEREST_FILE)
    df = df.rename(
        columns={
            "Timestamp": "timestamp",
            "Email address": "email",
            "Ονοματεπώνυμο γονέα/κηδεμόνα": "parent_name",
            "Τμήμα παιδιού/παιδιών": "child_class",
            "Αριθμός παιδικών εισιτηρίων": "child_tickets",
            "Αριθμός συνοδών ενηλίκων": "adult_tickets",
        }
    )
    df["child_tickets"] = df["child_tickets"].astype(int)
    df["adult_tickets"] = df["adult_tickets"].astype(int)
    df["total_tickets"] = df["child_tickets"] + df["adult_tickets"]
    return df


def get_interest_for_email(interest_df: pd.DataFrame, email: str):
    if interest_df.empty:
        return None
    mask = interest_df["email"].str.lower() == email.lower().strip()
    if not mask.any():
        return None
    return interest_df[mask].iloc[0]


def get_booking_for_email(df: pd.DataFrame, email: str):
    if df.empty:
        return None, None
    mask = df["email"].str.lower() == email.lower().strip()
    if not mask.any():
        return None, None
    sub = df[mask]
    row = sub.iloc[0]
    idx = sub.index[0]
    return row, idx


def get_next_priority(df: pd.DataFrame) -> int:
    if df.empty:
        return 1
    existing = df[df["category"] == "waitlist"]["priority_number"]
    if existing.empty:
        return 1
    return int(existing.max()) + 1


# ---------- STREAMLIT UI ----------
st.set_page_config(page_title="Θεατρική Παράσταση - Κρατήσεις", page_icon="🎭")

# Header με logo + info
col_logo, col_text = st.columns([1, 3])
with col_logo:
    if LOGO_FILE.exists():
        st.image(str(LOGO_FILE), use_container_width=True)
with col_text:
    st.markdown("### Σύλλογος Γονέων & Κηδεμόνων 2ου Νηπιαγωγείου Παπάγου")
    st.markdown(f"# 🎭 {EVENT_TITLE}")
    st.markdown(
        f"**Ημερομηνία & ώρα:** {EVENT_DATE_LABEL}<br>"
        f"**Περισσότερες πληροφορίες:** "
        f"[{EVENT_TITLE}]({EVENT_LINK})",
        unsafe_allow_html=True,
    )

st.markdown("---")
# st.subheader("Κρατήσεις & Πληρωμές Εισιτηρίων")

df = load_data()
interest_df = load_interest()

priority_df = df[df["category"] != "waitlist"]
waitlist_df = df[df["category"] == "waitlist"]

paid_seats = int(priority_df[priority_df["payment_status"] == "paid"]["total_tickets"].sum()) if not priority_df.empty else 0
pending_seats = int(priority_df[priority_df["payment_status"] == "pending"]["total_tickets"].sum()) if not priority_df.empty else 0
waitlist_seats = int(waitlist_df["total_tickets"].sum()) if not waitlist_df.empty else 0

seats_used = paid_seats + pending_seats
seats_left = max(0, MAX_SEATS - seats_used)

st.sidebar.header("Πλοήγηση")
mode = st.sidebar.radio(
    "Επιλέξτε λειτουργία:",
    ["Γονείς - Δήλωση & Πληρωμή", "Διαχειριστής - Έλεγχος & Καταχώριση Πληρωμών"],
)

# ========== MODE 1: PARENTS ==========
if mode == "Γονείς - Δήλωση & Πληρωμή":
    st.subheader("Κρατήσεις Εισιτηρίων για Γονείς & Κηδεμόνες")

    # Dashboard
    c1, c2, c3 = st.columns(3)
    c1.metric("Πληρωμένες θέσεις", paid_seats)
    c2.metric("Σε εκκρεμότητα", pending_seats)
    c3.metric("Διαθέσιμες", seats_left)
    
    with st.expander("ℹ️ Τι σημαίνουν οι όροι;"):
        st.markdown(
            """
            **Πληρωμένη θέση:**  
            Έχει ολοκληρωθεί η πληρωμή και η κράτηση είναι οριστική.

            **Δεσμευμένη θέση:**  
            Η δήλωσή σας έχει καταχωρηθεί, αλλά δεν έχει γίνει ακόμη η πληρωμή.  
            Για να θεωρηθεί εξασφαλισμένη, πρέπει να πληρωθεί μέχρι την προθεσμία.

            **Διαθέσιμη θέση:**  
            Θέση που δεν έχει δεσμευτεί από κάποια δήλωση.

            **Λίστα αναμονής:**  
            Χρησιμοποιείται μόνο για όσους δεν είχαν δηλώσει αρχικά.  
            Μετά το τέλος της προθεσμίας πληρωμής, οι κενές θέσεις δίνονται στη λίστα αναμονής με σειρά προτεραιότητας.

            **Αλλαγή αριθμού εισιτηρίων:**  
            Επιτρέπεται μόνο **προς τα κάτω**, όχι προς τα πάνω, για λόγους ίσης μεταχείρισης.
            """
        )


    st.progress(seats_used / MAX_SEATS if MAX_SEATS > 0 else 0)
    st.caption(f"Δεσμευμένες θέσεις: {seats_used} / {MAX_SEATS}")
    if waitlist_seats > 0:
        st.caption(f"Ζητούμενες θέσεις σε λίστα αναμονής: {waitlist_seats}")

    with st.expander("ℹ️ Πληροφορίες για προθεσμία πληρωμής", expanded=True):
        st.write(
            f"- Για να είναι **εξασφαλισμένη** η θέση σας, η πληρωμή πρέπει "
            f"να ολοκληρωθεί μέχρι: **{PAYMENT_DEADLINE_LABEL}**."
        )
        st.caption(
            "Μετά την ημερομηνία αυτή, ενδέχεται να ακυρωθούν κρατήσεις χωρίς πληρωμή, "
            "ώστε οι θέσεις να διατεθούν σε γονείς από τη λίστα αναμονής."
        )

    st.info(
        "Για λόγους προστασίας δεδομένων, χρειάζεται πρώτα να συμπληρώσετε το email σας. "
        "Με αυτό θα δείτε μόνο τη δική σας δήλωση. Εκεί θα μπορείτε να την επεξεργαστείτε."
    )

    email = st.text_input("Email (όπως το δηλώσατε στη φόρμα ενδιαφέροντος, αν έχετε δηλώσει)")

    if email:
        interest_row = get_interest_for_email(interest_df, email)
        booking_row, booking_idx = get_booking_for_email(df, email)

        # Κατηγορία: interest ή waitlist
        if booking_row is not None:
            category = booking_row["category"]
        else:
            category = "interest" if interest_row is not None else "waitlist"

        # Already paid?
        if booking_row is not None and booking_row["payment_status"] == "paid" and category == "interest":
            st.error("Η κράτησή σας έχει ήδη μαρκαριστεί ως πληρωμένη. Για αλλαγές, επικοινωνήστε με τον Σύλλογο.")
        else:
            # Μήνυμα για interest / waitlist
            if category == "interest":
                if interest_row is not None:
                    st.success(
                        "Βρέθηκε η αρχική σας δήλωση ενδιαφέροντος από τη φόρμα.\n\n"
                        f"- Γονέας: **{interest_row['parent_name']}**\n"
                        f"- Τμήμα παιδιού: **{interest_row['child_class']}**\n"
                        f"- Παιδικά εισιτήρια: **{int(interest_row['child_tickets'])}**\n"
                        f"- Ενήλικες συνοδοί: **{int(interest_row['adult_tickets'])}**\n"
                        f"- Σύνολο εισιτηρίων: **{int(interest_row['total_tickets'])}**"
                    )
                else:
                    st.info("Έχετε ήδη καταχωρημένη κανονική κράτηση με αυτό το email.")
                max_tickets_allowed = int(interest_row["total_tickets"]) if interest_row is not None else None
            else:
                # waitlist
                if booking_row is not None:
                    prio = int(booking_row.get("priority_number", 0))
                    msg = (
                        "Έχετε ήδη δήλωση στη **λίστα αναμονής** με αυτό το email.\n\n"
                        f"- Παιδικά εισιτήρια: **{int(booking_row['child_tickets'])}**\n"
                        f"- Ενήλικες συνοδοί: **{int(booking_row['adult_tickets'])}**\n"
                        f"- Σύνολο εισιτηρίων: **{int(booking_row['total_tickets'])}**"
                    )
                    if prio > 0:
                        msg += f"\n- Αριθμός προτεραιότητας: **#{prio}**"
                    st.info(msg)
                else:
                    st.warning(
                        "Δεν βρέθηκε αρχική δήλωση ενδιαφέροντος με αυτό το email.\n"
                        "Μπορείτε όμως να δηλώσετε συμμετοχή στη **λίστα αναμονής**."
                    )
                max_tickets_allowed = None

            # Προεπιλογές φόρμας
            if booking_row is not None:
                default_parent = booking_row["parent_name"]
                default_class = booking_row["child_class"]
                default_child = int(booking_row["child_tickets"])
                default_adult = int(booking_row["adult_tickets"])
                default_method = (
                    booking_row["payment_method"] if isinstance(booking_row["payment_method"], str) else "IRIS"
                )
                existing_code = booking_row["payment_code"]
                existing_status = booking_row["payment_status"]
                existing_priority = int(booking_row.get("priority_number", 0))
                previous_total = int(booking_row["total_tickets"])
            else:
                if interest_row is not None:
                    default_parent = interest_row["parent_name"]
                    default_class = interest_row["child_class"]
                    default_child = int(interest_row["child_tickets"])
                    default_adult = int(interest_row["adult_tickets"])
                else:
                    default_parent = ""
                    default_class = "Γ"
                    default_child = 1
                    default_adult = 1
                default_method = "IRIS"
                existing_code = ""
                existing_status = "pending" if category == "interest" else "waitlist"
                existing_priority = 0
                previous_total = 0

            with st.form("parent_form"):
                parent_name = st.text_input("Ονοματεπώνυμο γονέα/κηδεμόνα", default_parent)
                child_class = st.selectbox(
                    "Τμήμα παιδιού",
                    ["Α", "Β", "Γ", "Δ"],
                    index=["Α", "Β", "Γ", "Δ"].index(default_class) if default_class in ["Α", "Β", "Γ", "Δ"] else 2,
                )
                col1, col2 = st.columns(2)
                child_tickets = col1.number_input("Παιδικά εισιτήρια", min_value=0, value=int(default_child), step=1)
                adult_tickets = col2.number_input("Ενήλικες συνοδοί", min_value=0, value=int(default_adult), step=1)

                total_tickets = child_tickets + adult_tickets
                total_amount = total_tickets * TICKET_PRICE

                if category == "interest":
                    payment_method = st.radio(
                        "Τρόπος πληρωμής",
                        ["IRIS", "Revolut", "Μετρητά"],
                        index=["IRIS", "Revolut", "Μετρητά"].index(default_method),
                        horizontal=True,
                    )
                else:
                    payment_method = ""

                if total_tickets > 0:
                    st.write(f"🔢 Σύνολο εισιτηρίων: **{total_tickets}**")
                    if category == "interest":
                        st.write(f"💶 Ποσό πληρωμής: **{total_amount} €** ({TICKET_PRICE} €/άτομο)")
                    else:
                        st.info(
                            "Η δήλωσή σας θα καταχωρηθεί στη **λίστα αναμονής**. "
                            "Δεν απαιτείται πληρωμή σε αυτή τη φάση."
                        )
                else:
                    st.warning("Πρέπει να δηλώσετε τουλάχιστον 1 εισιτήριο.")

                submitted = st.form_submit_button("Αποθήκευση δήλωσης")

            if submitted:
                if not parent_name or not email:
                    st.error("Συμπληρώστε ονοματεπώνυμο και email.")
                elif total_tickets == 0:
                    st.error("Πρέπει να δηλώσετε τουλάχιστον 1 εισιτήριο.")
                elif category == "interest" and max_tickets_allowed is not None and total_tickets > max_tickets_allowed:
                    st.error(
                        f"Δεν μπορείτε να κλείσετε περισσότερα εισιτήρια ({total_tickets}) "
                        f"από όσα είχατε δηλώσει αρχικά ({max_tickets_allowed})."
                    )
                else:
                    # Έλεγχος χωρητικότητας
                    df_current = load_data()
                    seats_used_now = compute_seats_used(df_current)
                    if category == "interest":
                        if booking_row is not None and booking_row["category"] == "interest":
                            seats_after = seats_used_now - previous_total + total_tickets
                        else:
                            seats_after = seats_used_now + total_tickets
                        if seats_after > MAX_SEATS:
                            available = MAX_SEATS - (seats_used_now - previous_total)
                            st.error(
                                f"Δεν υπάρχουν αρκετές διαθέσιμες θέσεις για την αλλαγή αυτή. "
                                f"Διαθέσιμες θέσεις: {max(available, 0)}."
                            )
                            # δεν συνεχίζουμε σε αυτήν την περίπτωση
                        else:
                            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            # ενημέρωση / δημιουργία εγγραφής
                            if booking_row is not None:
                                idx = booking_idx
                                df_current.loc[idx, "timestamp"] = now
                                df_current.loc[idx, "parent_name"] = parent_name.strip()
                                df_current.loc[idx, "email"] = email.strip()
                                df_current.loc[idx, "child_class"] = child_class
                                df_current.loc[idx, "child_tickets"] = int(child_tickets)
                                df_current.loc[idx, "adult_tickets"] = int(adult_tickets)
                                df_current.loc[idx, "total_tickets"] = int(total_tickets)
                                df_current.loc[idx, "category"] = category

                                priority_number = existing_priority
                                if not priority_number and category == "waitlist":
                                    priority_number = get_next_priority(df_current)
                                df_current.loc[idx, "priority_number"] = priority_number

                                payment_code = existing_code or generate_payment_code(df_current)
                                df_current.loc[idx, "payment_code"] = payment_code
                                df_current.loc[idx, "payment_method"] = payment_method
                                df_current.loc[idx, "total_amount"] = float(total_amount)
                                if existing_status == "waitlist":
                                    df_current.loc[idx, "payment_status"] = "pending"
                            else:
                                payment_code = generate_payment_code(df_current)
                                priority_number = 0
                                new_row = {
                                    "timestamp": now,
                                    "parent_name": parent_name.strip(),
                                    "email": email.strip(),
                                    "child_class": child_class,
                                    "child_tickets": int(child_tickets),
                                    "adult_tickets": int(adult_tickets),
                                    "total_tickets": int(total_tickets),
                                    "total_amount": float(total_amount),
                                    "payment_method": payment_method,
                                    "payment_code": payment_code,
                                    "payment_status": "pending",
                                    "category": category,
                                    "priority_number": priority_number,
                                }
                                df_current = pd.concat([df_current, pd.DataFrame([new_row])], ignore_index=True)

                            save_data(df_current)
                            st.success("Η κράτησή σας αποθηκεύτηκε με επιτυχία! ✅")
                            st.markdown(
                                f"""
                                ### 📌 Ο προσωπικός σας κωδικός πληρωμής

                                Χρησιμοποιήστε τον παρακάτω κωδικό **ΑΚΡΙΒΩΣ ΟΠΩΣ ΕΜΦΑΝΙΖΕΤΑΙ**
                                στο πεδίο *«Σχόλια/Αιτιολογία»* της πληρωμής σας (IRIS ή Revolut):

                                ## `{payment_code}`

                                - Ποσό προς πληρωμή: **{total_amount} €**
                                - Τρόπος πληρωμής: **{payment_method}**
                                - Προθεσμία πληρωμής: **{PAYMENT_DEADLINE_LABEL}**
                                """
                            )
                            if payment_method == "Μετρητά":
                                st.info(
                                    "Για πληρωμή με μετρητά, δώστε το ποσό σε μέλος του Συλλόγου "
                                    f"και αναφέρετε τον κωδικό `{payment_code}`."
                                )
                    else:
                        # waitlist: δεν δεσμεύει θέσεις, δεν χτυπάει MAX_SEATS
                        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        df_current = load_data()
                        if booking_row is not None:
                            idx = booking_idx
                            df_current.loc[idx, "timestamp"] = now
                            df_current.loc[idx, "parent_name"] = parent_name.strip()
                            df_current.loc[idx, "email"] = email.strip()
                            df_current.loc[idx, "child_class"] = child_class
                            df_current.loc[idx, "child_tickets"] = int(child_tickets)
                            df_current.loc[idx, "adult_tickets"] = int(adult_tickets)
                            df_current.loc[idx, "total_tickets"] = int(total_tickets)
                            df_current.loc[idx, "category"] = "waitlist"
                            priority_number = existing_priority or get_next_priority(df_current)
                            df_current.loc[idx, "priority_number"] = priority_number
                            df_current.loc[idx, "payment_status"] = "waitlist"
                            df_current.loc[idx, "payment_code"] = ""
                            df_current.loc[idx, "payment_method"] = ""
                            df_current.loc[idx, "total_amount"] = 0.0
                        else:
                            priority_number = get_next_priority(df_current)
                            new_row = {
                                "timestamp": now,
                                "parent_name": parent_name.strip(),
                                "email": email.strip(),
                                "child_class": child_class,
                                "child_tickets": int(child_tickets),
                                "adult_tickets": int(adult_tickets),
                                "total_tickets": int(total_tickets),
                                "total_amount": 0.0,
                                "payment_method": "",
                                "payment_code": "",
                                "payment_status": "waitlist",
                                "category": "waitlist",
                                "priority_number": priority_number,
                            }
                            df_current = pd.concat([df_current, pd.DataFrame([new_row])], ignore_index=True)

                        save_data(df_current)
                        st.success("Η δήλωσή σας στη λίστα αναμονής καταχωρήθηκε με επιτυχία! ✅")
                        st.info(f"Αριθμός προτεραιότητας στη λίστα αναμονής: **#{priority_number}**")

# ========== MODE 2: ADMIN ==========
elif mode == "Διαχειριστής - Έλεγχος & Καταχώριση Πληρωμών":
    st.subheader("Πίνακας διαχείρισης (μόνο για Δ.Σ.)")

    admin_code = st.text_input("Κωδικός διαχειριστή", type="password")
    if admin_code == ADMIN_PASSWORD:
        df = load_data()
        priority_df = df[df["category"] != "waitlist"]
        waitlist_df = df[df["category"] == "waitlist"]

        seats_used = compute_seats_used(df)
        seats_left = MAX_SEATS - seats_used

        paid_seats = int(priority_df[priority_df["payment_status"] == "paid"]["total_tickets"].sum()) if not priority_df.empty else 0
        pending_priority_seats = int(priority_df[priority_df["payment_status"] == "pending"]["total_tickets"].sum()) if not priority_df.empty else 0
        waitlist_seats = int(waitlist_df["total_tickets"].sum()) if not waitlist_df.empty else 0

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Συνολικές θέσεις", MAX_SEATS)
        c2.metric("Κανονικές κρατήσεις", seats_used)
        c3.metric("Πληρωμένες", paid_seats)
        c4.metric("Σε εκκρεμότητα", pending_priority_seats)
        c5.metric("Λίστα αναμονής", waitlist_seats)

        st.markdown(
            f"🔔 Προθεσμία πληρωμής για να θεωρούνται οι θέσεις εξασφαλισμένες: "
            f"**{PAYMENT_DEADLINE_LABEL}**."
        )

        st.markdown("---")
        st.markdown("### ♻️ Επαναφορά πληρωμών από backup CSV (Admin)")

        uploaded = st.file_uploader(
            "Ανέβασε payments backup CSV",
            type=["csv"],
            help="Προσοχή: Αυτό θα αντικαταστήσει πλήρως το τρέχον payments.csv."
        )

        col_a, col_b = st.columns([1, 2])
        with col_a:
            do_restore = st.button("Επαναφορά τώρα", type="primary", disabled=(uploaded is None))
        with col_b:
            st.caption("Χρησιμοποίησέ το μόνο αν χάθηκαν δεδομένα μετά από deploy/restart.")

        if do_restore and uploaded is not None:
            try:
                new_df = pd.read_csv(uploaded, dtype={"payment_code": str})
                ok, msg = validate_payments_csv(new_df)
                if not ok:
                    st.error(f"Μη έγκυρο αρχείο: {msg}")
                else:
                    # optional: make a safety backup of current file
                    if DATA_FILE.exists():
                        backup_name = DATA_DIR / f"payments_backup_before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                        DATA_FILE.replace(backup_name)

                    save_data(new_df)
                    st.success("✅ Η επαναφορά ολοκληρώθηκε. Κάνε refresh τη σελίδα για να δεις τα ενημερωμένα στοιχεία.")
            except Exception as e:
                st.error(f"Αποτυχία επαναφοράς: {e}")

        st.markdown("---")
        st.markdown("### Αναζήτηση & Φίλτρα")

        status_filter = st.selectbox(
            "Φίλτρο κατάστασης",
            ["Όλες", "pending", "paid", "waitlist"],
            index=0,
        )
        category_filter = st.selectbox(
            "Φίλτρο κατηγορίας",
            ["Όλες", "interest", "waitlist"],
            index=0,
        )

        df_view = df.copy()
        if status_filter != "Όλες":
            df_view = df_view[df_view["payment_status"] == status_filter]
        if category_filter != "Όλες":
            df_view = df_view[df_view["category"] == category_filter]

        search_term = st.text_input("Αναζήτηση (email, όνομα γονέα ή κωδικός πληρωμής)")
        if search_term:
            mask = (
                df_view["email"].str.contains(search_term, case=False, na=False)
                | df_view["parent_name"].str.contains(search_term, case=False, na=False)
                | df_view["payment_code"].astype(str).str.contains(search_term, case=False, na=False)
            )
            df_view = df_view[mask]

        if not df_view.empty:
            st.dataframe(
                df_view.sort_values("timestamp", ascending=False),
                use_container_width=True,
            )
        else:
            st.info("Δεν βρέθηκαν εγγραφές με τα τρέχοντα φίλτρα.")

        st.markdown("---")
        st.markdown("### Μαρκάρισμα πληρωμής ως εξοφλημένης")

        col_code, col_btn = st.columns([2, 1])
        with col_code:
            code_to_mark = st.text_input("Κωδικός πληρωμής (π.χ. EVT-003)")
        with col_btn:
            if st.button("Μαρκάρισμα ως 'paid'"):
                if not code_to_mark:
                    st.error("Συμπληρώστε κωδικό πληρωμής.")
                else:
                    df2 = load_data()
                    mask = df2["payment_code"].astype(str) == code_to_mark.strip()
                    if not mask.any():
                        st.error("Δεν βρέθηκε εγγραφή με αυτόν τον κωδικό.")
                    else:
                        if (df2.loc[mask, "category"] == "waitlist").any():
                            st.error("Ο κωδικός αντιστοιχεί σε εγγραφή λίστας αναμονής, όχι σε κανονική κράτηση.")
                        else:
                            df2.loc[mask, "payment_status"] = "paid"
                            save_data(df2)
                            st.success(f"Ο κωδικός {code_to_mark} μαρκαρίστηκε ως 'paid'.")

        st.markdown("---")
        st.markdown("### Εξαγωγή δεδομένων")

        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "📥 Λήψη όλων των δεδομένων σε CSV",
            data=csv,
            file_name="payments_export.csv",
            mime="text/csv",
        )

        if not waitlist_df.empty:
            st.markdown("---")
            st.markdown("### Λίστα αναμονής (με σειρά προτεραιότητας)")
            st.dataframe(
                waitlist_df.sort_values(
                    by=["priority_number", "timestamp"], ascending=[True, True]
                ),
                use_container_width=True,
            )
    else:
        st.warning("Συμπληρώστε τον σωστό κωδικό διαχειριστή για να δείτε τα στοιχεία.")

# ---------- FOOTER ----------
st.markdown("---")
st.caption(
    "Αυτή η πλατφόρμα κρατήσεων αναπτύχθηκε από " "[gfragi](https://github.com/gfragi) "
    "με χρήση Streamlit, "
    "[git repo](https://github.com/gfragi/book_seat_pay)."
)
