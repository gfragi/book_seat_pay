import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime

# ---------- CONFIG ----------
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
DATA_FILE = DATA_DIR / "payments.csv"
INTEREST_FILE = DATA_DIR / "interest.csv"

TICKET_PRICE = 10  # euros per seat
MAX_SEATS = 85

PAYMENT_DEADLINE = "2025-12-20"   # YYYY-MM-DD (αν χρειαστείς ημερομηνιακές συγκρίσεις)
PAYMENT_DEADLINE_LABEL = "20 Δεκεμβρίου 2025"

ADMIN_PASSWORD = "syllogos2025"   # απλός κωδικός για admin view


# ---------- HELPERS ----------

def load_data() -> pd.DataFrame:
    if DATA_FILE.exists():
        return pd.read_csv(DATA_FILE, dtype={"payment_code": str})
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
                "payment_status",  # pending / paid
            ]
        )
        df.to_csv(DATA_FILE, index=False)
        return df


def save_data(df: pd.DataFrame):
    df.to_csv(DATA_FILE, index=False)


def generate_payment_code(df: pd.DataFrame) -> str:
    next_number = len(df) + 1
    return f"EVT-{next_number:03d}"


def compute_seats_used(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    return int(df["total_tickets"].sum())


def load_interest() -> pd.DataFrame:
    """
    Περιμένουμε CSV με στήλες:
    - Timestamp
    - Email address
    - Ονοματεπώνυμο γονέα/κηδεμόνα
    - Τμήμα παιδιού/παιδιών
    - Αριθμός παιδικών εισιτηρίων
    - Αριθμός συνοδών ενηλίκων
    """
    if not INTEREST_FILE.exists():
        return pd.DataFrame()

    df = pd.read_csv(INTEREST_FILE)

    col_map = {
        "Timestamp": "timestamp",
        "Email address": "email",
        "Ονοματεπώνυμο γονέα/κηδεμόνα": "parent_name",
        "Τμήμα παιδιού/παιδιών": "child_class",
        "Αριθμός παιδικών εισιτηρίων": "child_tickets",
        "Αριθμός συνοδών ενηλίκων": "adult_tickets",
    }
    df = df.rename(columns=col_map)

    if "child_tickets" in df.columns and "adult_tickets" in df.columns:
        df["child_tickets"] = df["child_tickets"].astype(int)
        df["adult_tickets"] = df["adult_tickets"].astype(int)
        df["total_tickets"] = df["child_tickets"] + df["adult_tickets"]

    return df


def get_interest_for_email(interest_df: pd.DataFrame, email: str):
    if interest_df.empty:
        return None
    mask = interest_df["email"].str.lower() == email.lower()
    if not mask.any():
        return None
    return interest_df[mask].iloc[0]


def get_booking_for_email(df: pd.DataFrame, email: str):
    if df.empty:
        return None
    mask = df["email"].str.lower() == email.lower()
    if not mask.any():
        return None
    # υποθέτουμε μία κράτηση ανά email
    return df[mask].iloc[0], df[mask].index[0]


# ---------- STREAMLIT APP ----------

st.set_page_config(page_title="Θεατρική Παράσταση - Κρατήσεις", page_icon="🎭")

st.title("🎭 Κρατήσεις & Πληρωμές για τη Θεατρική Παράσταση")

df = load_data()
interest_df = load_interest()

seats_used = compute_seats_used(df)
seats_left = MAX_SEATS - seats_used

st.sidebar.header("Πλοήγηση")
mode = st.sidebar.radio(
    "Επιλέξτε λειτουργία:",
    ["Γονείς - Δήλωση & Πληρωμή", "Διαχειριστής - Έλεγχος & Καταχώριση Πληρωμών"],
)

# ---------- MODE 1: PARENTS ----------
if mode == "Γονείς - Δήλωση & Πληρωμή":
    st.subheader("Φόρμα συμμετοχής γονέα")

    with st.expander("ℹ️ Πληροφορίες για θέσεις & προθεσμία πληρωμής", expanded=True):
        st.write(f"- Διαθέσιμες θέσεις αυτή τη στιγμή: **{seats_left}** από {MAX_SEATS}.")
        st.write(
            f"- Για να είναι **εξασφαλισμένη** η θέση σας, "
            f"η πληρωμή πρέπει να ολοκληρωθεί μέχρι: **{PAYMENT_DEADLINE_LABEL}**."
        )
        st.caption(
            "Μετά την ημερομηνία αυτή, ενδέχεται να ακυρωθούν κρατήσεις χωρίς πληρωμή, "
            "ώστε να δοθούν οι θέσεις σε άλλους ενδιαφερόμενους."
        )

    if seats_left <= 0:
        st.error(
            "Δυστυχώς δεν υπάρχουν διαθέσιμες θέσεις. "
            "Επικοινωνήστε με τον Σύλλογο για ενημέρωση."
        )
        st.stop()

    st.info("Για λόγους προστασίας δεδομένων, χρειάζεται πρώτα να συμπληρώσετε το email σας.")

    email = st.text_input("Email (όπως το δηλώσατε στη φόρμα ενδιαφέροντος)")

    if not email:
        st.stop()

    # βρίσκουμε αρχική δήλωση ενδιαφέροντος (αν υπάρχει)
    interest_row = get_interest_for_email(interest_df, email)
    if interest_row is not None:
        st.success(
            "Βρέθηκε η αρχική σας δήλωση ενδιαφέροντος από τη φόρμα.\n\n"
            f"- Γονέας: **{interest_row['parent_name']}**\n"
            f"- Τμήμα παιδιού: **{interest_row['child_class']}**\n"
            f"- Παιδικά εισιτήρια: **{int(interest_row['child_tickets'])}**\n"
            f"- Ενήλικες συνοδοί: **{int(interest_row['adult_tickets'])}**\n"
            f"- Σύνολο εισιτηρίων: **{int(interest_row['total_tickets'])}**"
        )
        max_tickets_allowed = int(interest_row["total_tickets"])
    else:
        st.warning(
            "Δεν βρέθηκε αρχική δήλωση ενδιαφέροντος με αυτό το email.\n"
            "Αν πιστεύετε ότι είναι λάθος, ελέγξτε την ορθογραφία του email "
            "ή επικοινωνήστε με τον Σύλλογο."
        )
        # μπορείς εδώ να αποφασίσεις αν θα επιτρέπεις νέα κράτηση ή όχι
        max_tickets_allowed = None  # χωρίς όριο από interest

    # βρίσκουμε αν έχει ήδη κάνει κράτηση
    booking_row, booking_idx = get_booking_for_email(df, email) if not df.empty else (None, None)

    if booking_row is not None:
        st.info(
            "Υπάρχει ήδη καταχωρημένη κράτηση με αυτό το email.\n\n"
            f"- Τρέχων αριθμός παιδικών εισιτηρίων: **{int(booking_row['child_tickets'])}**\n"
            f"- Τρέχων αριθμός ενηλίκων: **{int(booking_row['adult_tickets'])}**\n"
            f"- Σύνολο εισιτηρίων: **{int(booking_row['total_tickets'])}**\n"
            f"- Κατάσταση πληρωμής: **{booking_row['payment_status']}**"
        )

        if booking_row["payment_status"] == "paid":
            st.error(
                "Η κράτησή σας έχει ήδη μαρκαριστεί ως πληρωμένη. "
                "Για αλλαγές, επικοινωνήστε με τον Σύλλογο."
            )
            st.stop()

        # προ-συμπλήρωση πεδίων με την υπάρχουσα κράτηση
        default_parent_name = booking_row["parent_name"]
        default_child_class = booking_row["child_class"]
        default_child_tickets = int(booking_row["child_tickets"])
        default_adult_tickets = int(booking_row["adult_tickets"])
        default_payment_method = booking_row["payment_method"]
        existing_payment_code = booking_row["payment_code"]
        previous_total = int(booking_row["total_tickets"])
    else:
        # νέα κράτηση
        default_parent_name = interest_row["parent_name"] if interest_row is not None else ""
        default_child_class = interest_row["child_class"] if interest_row is not None else "Γ"
        default_child_tickets = int(interest_row["child_tickets"]) if interest_row is not None else 1
        default_adult_tickets = int(interest_row["adult_tickets"]) if interest_row is not None else 1
        default_payment_method = "IRIS"
        existing_payment_code = None
        previous_total = 0

    with st.form("parent_form"):
        parent_name = st.text_input("Ονοματεπώνυμο γονέα/κηδεμόνα", value=default_parent_name)
        child_class = st.selectbox(
            "Τμήμα παιδιού",
            options=["Α", "Β", "Γ", "Δ"],
            index=["Α", "Β", "Γ", "Δ"].index(default_child_class) if default_child_class in ["Α", "Β", "Γ", "Δ"] else 2
        )

        col1, col2 = st.columns(2)
        with col1:
            child_tickets = st.number_input(
                "Αριθμός παιδικών εισιτηρίων", min_value=0, value=default_child_tickets, step=1
            )
        with col2:
            adult_tickets = st.number_input(
                "Αριθμός συνοδών ενηλίκων", min_value=0, value=default_adult_tickets, step=1
            )

        payment_method = st.radio(
            "Τρόπος πληρωμής",
            options=["IRIS", "Revolut", "Μετρητά"],
            index=["IRIS", "Revolut", "Μετρητά"].index(default_payment_method)
            if default_payment_method in ["IRIS", "Revolut", "Μετρητά"] else 0,
            horizontal=True,
        )

        total_tickets = child_tickets + adult_tickets
        total_amount = total_tickets * TICKET_PRICE

        if total_tickets == 0:
            st.warning("Πρέπει να δηλώσετε τουλάχιστον 1 εισιτήριο.")
        else:
            st.write(f"🔢 Συνολικός αριθμός εισιτηρίων: **{total_tickets}**")
            st.write(f"💶 Ποσό πληρωμής: **{total_amount} €** ({TICKET_PRICE} €/άτομο)")

        submitted = st.form_submit_button("Αποθήκευση & Λήψη κωδικού πληρωμής")

    if submitted:
        if not parent_name or not email:
            st.error("Συμπληρώστε ονοματεπώνυμο και email.")
            st.stop()

        if total_tickets == 0:
            st.error("Πρέπει να δηλώσετε τουλάχιστον 1 εισιτήριο.")
            st.stop()

        # Έλεγχος να μην ξεπερνά την αρχική δήλωση ενδιαφέροντος
        if max_tickets_allowed is not None and total_tickets > max_tickets_allowed:
            st.error(
                f"Δε μπορείτε να κλείσετε περισσότερα εισιτήρια "
                f"({total_tickets}) από όσα είχατε δηλώσει αρχικά ({max_tickets_allowed})."
            )
            st.stop()

        # Έλεγχος συνολικών θέσεων με βάση την αλλαγή
        df = load_data()
        seats_used_now = compute_seats_used(df)

        if booking_row is not None:
            # αναπροσαρμογή: αφαιρούμε την παλιά κράτηση, βάζουμε τη νέα
            seats_used_after = seats_used_now - previous_total + total_tickets
        else:
            seats_used_after = seats_used_now + total_tickets

        if seats_used_after > MAX_SEATS:
            available = MAX_SEATS - (seats_used_now - previous_total)
            st.error(
                f"Δεν υπάρχουν αρκετές διαθέσιμες θέσεις για την αλλαγή αυτή. "
                f"Διαθέσιμες θέσεις: {max(available, 0)}."
            )
            st.stop()

        # Δημιουργία ή ενημέρωση εγγραφής
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if booking_row is not None:
            payment_code = existing_payment_code
            df.loc[booking_idx, "timestamp"] = now
            df.loc[booking_idx, "parent_name"] = parent_name.strip()
            df.loc[booking_idx, "email"] = email.strip()
            df.loc[booking_idx, "child_class"] = child_class
            df.loc[booking_idx, "child_tickets"] = int(child_tickets)
            df.loc[booking_idx, "adult_tickets"] = int(adult_tickets)
            df.loc[booking_idx, "total_tickets"] = int(total_tickets)
            df.loc[booking_idx, "total_amount"] = float(total_amount)
            df.loc[booking_idx, "payment_method"] = payment_method
            # status παραμένει "pending" (ή ό,τι ήταν) – δεν το κάνουμε paid εδώ
            payment_status = df.loc[booking_idx, "payment_status"]
        else:
            payment_code = generate_payment_code(df)
            payment_status = "pending"
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
                "payment_status": payment_status,
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        save_data(df)

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

            Μετά την επιβεβαίωση της πληρωμής από τον Σύλλογο,
            η κράτησή σας θα θεωρείται **οριστική**.
            """
        )

        if payment_method == "Μετρητά":
            st.info(
                "Για πληρωμή με μετρητά, δώστε το ποσό σε μέλος του Συλλόγου "
                f"και αναφέρετε τον κωδικό `{payment_code}`."
            )

# ---------- MODE 2: ADMIN ----------
else:
    st.subheader("Πίνακας διαχείρισης (μόνο για Δ.Σ.)")

    admin_code = st.text_input("Κωδικός διαχειριστή", type="password")
    if admin_code != ADMIN_PASSWORD:
        st.warning("Συμπληρώστε τον σωστό κωδικό για να δείτε τα στοιχεία.")
        st.stop()

    seats_used = compute_seats_used(df)
    seats_left = MAX_SEATS - seats_used
    paid_seats = int(df[df["payment_status"] == "paid"]["total_tickets"].sum()) if not df.empty else 0
    pending_seats = seats_used - paid_seats

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Συνολικές θέσεις", MAX_SEATS)
    c2.metric("Δηλωμένες θέσεις (σύνολο)", seats_used)
    c3.metric("Επιβεβαιωμένες (paid)", paid_seats)
    c4.metric("Διαθέσιμες", seats_left)

    st.markdown(
        f"🔔 Προθεσμία πληρωμής για να θεωρούνται οι θέσεις εξασφαλισμένες: "
        f"**{PAYMENT_DEADLINE_LABEL}**."
    )

    st.markdown("---")
    st.markdown("### Αναζήτηση & Ενημέρωση Πληρωμών")

    status_filter = st.selectbox(
        "Φίλτρο κατάστασης",
        options=["Όλες", "pending", "paid"],
        index=0,
    )

    df_view = df.copy()
    if status_filter != "Όλες":
        df_view = df_view[df_view["payment_status"] == status_filter]

    search_term = st.text_input("Αναζήτηση (email ή όνομα γονέα ή κωδικός πληρωμής)")
    if search_term:
        mask = (
            df_view["email"].str.contains(search_term, case=False, na=False)
            | df_view["parent_name"].str.contains(search_term, case=False, na=False)
            | df_view["payment_code"].astype(str).str.contains(search_term, case=False, na=False)
        )
        df_view = df_view[mask]

    st.dataframe(
        df_view.sort_values("timestamp", ascending=False),
        use_container_width=True,
    )

    st.markdown("---")
    st.markdown("### Μαρκάρισμα πληρωμής ως εξοφλημένης")

    col_code, col_btn = st.columns([2, 1])
    with col_code:
        code_to_mark = st.text_input("Κωδικός πληρωμής για ενημέρωση (π.χ. EVT-003)")
    with col_btn:
        if st.button("Μαρκάρισμα ως 'paid'"):
            if not code_to_mark:
                st.error("Συμπληρώστε κωδικό πληρωμής.")
            else:
                df = load_data()
                mask = df["payment_code"].astype(str) == code_to_mark.strip()
                if not mask.any():
                    st.error("Δεν βρέθηκε εγγραφή με αυτόν τον κωδικό.")
                else:
                    df.loc[mask, "payment_status"] = "paid"
                    save_data(df)
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
