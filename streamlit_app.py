import streamlit as st
import pandas as pd
import gspread
from datetime import date, timedelta
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="התקציב שלי", page_icon="💰", layout="wide")

# RTL globally, but without forcing direction on every Streamlit element.
# The mobile rules prevent Hebrew text from collapsing into a one-letter-wide column.
st.markdown("""
<style>
/* Minimal responsive CSS.
   IMPORTANT: do not apply direction:rtl to html/body/div/span or Streamlit's
   internal flex containers; that caused the one-letter-wide vertical text. */
.block-container {
    max-width: 1100px;
    padding-top: 1.5rem;
}

/* במחשב: מחזירים את פריסת ה-RTL המקורית, כולל הסרגל בצד ימין.
   בטלפון לא כופים RTL על מבנה Streamlit כדי למנוע שבירת טקסט. */
@media (min-width: 769px) {
    html, body, [data-testid="stAppViewContainer"] {
        direction: rtl;
    }
}

/* יישור הטקסט בעברית */
h1, h2, h3, p {
    text-align: right;
}

/* The cycle line is our own element, so RTL is safe here */
.cycle-box {
    direction: rtl;
    text-align: right;
    font-weight: 700;
    margin: 1rem 0;
}

/* Phone: only spacing and font sizes. Let Streamlit handle responsiveness. */
@media (max-width: 768px) {
    .block-container {
        max-width: 100%;
        padding: 1rem 0.75rem 4rem;
    }

    h1 {
        font-size: 2.1rem !important;
        line-height: 1.2 !important;
    }

    h2 {
        font-size: 1.55rem !important;
        line-height: 1.25 !important;
    }

    h3 {
        font-size: 1.25rem !important;
        line-height: 1.3 !important;
    }

    .cycle-box {
        font-size: 1.15rem;
        line-height: 1.6;
    }
}
</style>
""", unsafe_allow_html=True)

DEFAULTS = {
    "income": 28500.0,
    "mortgage": 9800.0,
    "kindergarten": 4000.0,
    "personal_training": 1200.0,
    "savings_goal": 2000.0,
    "cycle_day": 10,
}

CATEGORIES = [
    "מזון וסופר",
    "מסעדות ואוכל בחוץ",
    "רכב ודלק",
    "חניה וכבישי אגרה",
    "ילדים וגן",
    "בריאות ופארם",
    "חשבונות",
    "תקשורת",
    "קניות",
    "בילויים",
    "דיור/עירייה",
    "טיפולי קוסמטיקה ומספרה",
    "תשלום לא מתוכנן",
    "חיסכון",
    "אחר",
]

def cycle_bounds(today, d=10):
    if today.day >= d:
        start = date(today.year, today.month, d)
        nxt = date(today.year + 1, 1, d) if today.month == 12 else date(today.year, today.month + 1, d)
    else:
        start = date(today.year - 1, 12, d) if today.month == 1 else date(today.year, today.month - 1, d)
        nxt = date(today.year, today.month, d)
    return start, nxt - timedelta(days=1)

def find_col(cols, wanted):
    return next((c for c in cols if str(c).strip() == wanted), None)

def auto_category(merchant):
    s = str(merchant or "").lower()
    rules = [
        (["עגול לחס"], "חיסכון"),
        (["שופרסל", "רמי לוי", "ויקטורי", "קרפור", "סופר", "כל - בו", "כל-בו"], "מזון וסופר"),
        (["פנגו", "סלופארק", "כביש 6"], "חניה וכבישי אגרה"),
        (["דלק", "סונול", "פז", "דור אלון", "טן"], "רכב ודלק"),
        (["עיריית", "ארנונה"], "דיור/עירייה"),
        (["מכבי חיפה", "סינמה", "יס פלאנט", "תיאטרון"], "בילויים"),
        (["בזק", "פרטנר", "סלקום", "הוט", "012", "013", "019"], "תקשורת"),
        (["חשמל", "חברת החשמל", "מים", "מי ", "גז", "אמישראגז", "פזגז"], "חשבונות"),
        (["נטפליקס", "netflix", "spotify", "apple"], "תקשורת"),
        (["סופר-פארם", "סופר פארם", "בית מרקחת", "פארם"], "בריאות ופארם"),
        (["מסעד", "קפה", "ארומה", "מקדונלד", "וולט", "wolt", "תן ביס"], "מסעדות ואוכל בחוץ"),
        (["גן ילדים", "צהרון", "קייטנה"], "ילדים וגן"),
        (["מספרה", "ספר ", "קוסמט", "לק ג'ל", "לק גל", "מניקור", "פדיקור"], "טיפולי קוסמטיקה ומספרה"),
        (["זארה", "h&m", "איקאה", "ikea", "קסטרו", "פוקס"], "קניות"),
    ]
    for keys, cat in rules:
        if any(k.lower() in s for k in keys):
            return cat
    return "אחר"

def parse_file(upload):
    df = pd.read_excel(upload)
    merchant = find_col(df.columns, "בית עסק")
    txdate = find_col(df.columns, "תאריך עסקה")
    amount = find_col(df.columns, "סכום החיוב")
    if not all([merchant, txdate, amount]):
        raise ValueError("לא זוהה פורמט הקובץ. נדרשות העמודות: בית עסק, תאריך עסקה, סכום החיוב.")

    out = pd.DataFrame()
    out["בית עסק"] = df[merchant].astype(str).str.strip()
    out["תאריך"] = pd.to_datetime(df[txdate], errors="coerce", dayfirst=True)
    out["סכום"] = pd.to_numeric(df[amount], errors="coerce")
    out = out.dropna(subset=["תאריך", "סכום"])
    out = out[(out["בית עסק"] != "בית עסק") & (out["בית עסק"] != "nan")]
    out = out.drop_duplicates(subset=["בית עסק", "תאריך", "סכום"])
    out["קטגוריה"] = out["בית עסק"].map(auto_category)
    return out

# שמירת הוצאות מזומן קבועה ב-Google Sheets.
SHEET_ID = "16789a4GZ54B31myr5YsHzCANah6mjOsy1WpEWqQH-Gw"
SHEET_HEADERS = ["תאריך", "תיאור", "סכום", "קטגוריה", "אמצעי תשלום", "מחזור"]

def cycle_key(start, end):
    return f"{start:%d/%m/%Y}-{end:%d/%m/%Y}"

@st.cache_resource
def get_cash_sheet():
    info = dict(st.secrets["gcp_service_account"])
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).sheet1
    if not sheet.row_values(1):
        sheet.append_row(SHEET_HEADERS, value_input_option="USER_ENTERED")
    return sheet

def load_cash_rows(start, end):
    records = get_cash_sheet().get_all_records()
    key = cycle_key(start, end)
    rows = []
    for sheet_row, rec in enumerate(records, start=2):
        if str(rec.get("מחזור", "")).strip() != key:
            continue
        try:
            tx_date = pd.to_datetime(rec.get("תאריך"), dayfirst=True).date()
            amount = float(str(rec.get("סכום", 0)).replace(",", ""))
        except Exception:
            continue
        rows.append({
            "_sheet_row": sheet_row,
            "תאריך": tx_date,
            "בית עסק": str(rec.get("תיאור", "")).strip(),
            "סכום": amount,
            "קטגוריה": str(rec.get("קטגוריה", "אחר")).strip() or "אחר",
        })
    return rows

def add_cash_row(tx_date, description, amount, category, start, end):
    get_cash_sheet().append_row(
        [tx_date.strftime("%d/%m/%Y"), description, float(amount),
         category, "מזומן", cycle_key(start, end)],
        value_input_option="USER_ENTERED",
    )

def delete_cash_row(sheet_row):
    get_cash_sheet().delete_rows(sheet_row)

st.title("💰 התקציב שלי")
st.caption("מעלים את קובץ האשראי, מתקנים קטגוריות במידת הצורך ומקבלים תמונת מצב למחזור 10–10.")

with st.sidebar:
    st.header("הגדרות חודשיות")
    income = st.number_input("הכנסות", min_value=0.0, value=DEFAULTS["income"], step=100.0)
    mortgage = st.number_input("משכנתא", min_value=0.0, value=DEFAULTS["mortgage"], step=100.0)
    kindergarten = st.number_input("גן / צ׳קים", min_value=0.0, value=DEFAULTS["kindergarten"], step=100.0)
    personal_training = st.number_input("אימונים אישיים", min_value=0.0, value=DEFAULTS["personal_training"], step=100.0)
    savings_goal = st.number_input("יעד חיסכון", min_value=0.0, value=DEFAULTS["savings_goal"], step=100.0)
    st.info("המחזור מוגדר מה־10 בחודש עד ה־9 בחודש הבא.")

today = date.today()
start, end = cycle_bounds(today, DEFAULTS["cycle_day"])
available = income - mortgage - kindergarten - personal_training - savings_goal



# A single responsive block instead of mixed RTL/LTR heading fragments.
st.markdown(
    f"""
    <div class="cycle-box" dir="rtl" style="font-weight:700; margin:1rem 0;">
        מחזור נוכחי:
        <span style="white-space:nowrap;" dir="ltr">{start:%d.%m.%Y} – {end:%d.%m.%Y}</span>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown(f"מסגרת לשאר ההוצאות אחרי משכנתא, גן, אימונים אישיים ויעד חיסכון: **₪{available:,.0f}**")

st.markdown(
    f"**הוצאות קבועות:** משכנתא ₪{mortgage:,.0f} · גן / צ׳קים ₪{kindergarten:,.0f} · "
    f"אימונים אישיים ₪{personal_training:,.0f} · **סה״כ ₪{mortgage + kindergarten + personal_training:,.0f}**"
)

upload = st.file_uploader("העלה את קובץ האשראי העדכני", type=["xlsx", "xls"])
if upload is None:
    st.info("בחר קובץ Excel כדי להתחיל.")
    st.stop()

try:
    df = parse_file(upload)
except Exception as e:
    st.error(str(e))
    st.stop()

cyc = df[(df["תאריך"].dt.date >= start) & (df["תאריך"].dt.date <= end)].copy()

st.divider()
st.subheader("✏️ תיקון קטגוריות")
st.caption("לחץ על הקטגוריה בכל שורה כדי לשנות אותה. החישובים מתעדכנים מיד.")

if len(cyc):
    edit_df = cyc[["תאריך", "בית עסק", "סכום", "קטגוריה"]].copy()
    edit_df["תאריך"] = edit_df["תאריך"].dt.date

    edited = st.data_editor(
        edit_df,
        use_container_width=True,
        hide_index=True,
        disabled=["תאריך", "בית עסק", "סכום"],
        column_config={
            "תאריך": st.column_config.DateColumn("תאריך", format="DD/MM/YYYY"),
            "בית עסק": st.column_config.TextColumn("בית עסק"),
            "סכום": st.column_config.NumberColumn("סכום", format="₪ %.2f"),
            "קטגוריה": st.column_config.SelectboxColumn("קטגוריה", options=CATEGORIES, required=True),
        },
        key="category_editor",
    )
    cyc["קטגוריה"] = edited["קטגוריה"].values
else:
    st.info("לא נמצאו עסקאות במחזור הנוכחי.")

st.divider()
st.subheader("💵 הוצאות במזומן")
st.caption(
    "הוצאות המזומן נשמרות ב-Google Sheets. בכל מחזור 10–9 מוצגות רק "
    "ההוצאות של אותו מחזור; מחזורים קודמים נשמרים בגיליון כהיסטוריה."
)

# כלי בדיקה פשוט לחיבור Google Sheets
with st.expander("🔧 בדיקת חיבור ל-Google Sheets"):
    if st.button("הפעל בדיקת חיבור", use_container_width=True):
        try:
            if "gcp_service_account" not in st.secrets:
                st.error("❌ שלב 1: לא נמצא [gcp_service_account] ב-Streamlit Secrets.")
            else:
                st.success("✅ שלב 1: Secrets נמצאו.")
                info = dict(st.secrets["gcp_service_account"])
                required_keys = ["project_id", "private_key", "client_email", "token_uri"]
                missing = [k for k in required_keys if not info.get(k)]
                if missing:
                    st.error("❌ חסרים ב-Secrets השדות: " + ", ".join(missing))
                else:
                    st.success("✅ שלב 2: השדות הדרושים נמצאו ב-Secrets.")
                    scopes = [
                        "https://www.googleapis.com/auth/spreadsheets",
                        "https://www.googleapis.com/auth/drive",
                    ]
                    creds = Credentials.from_service_account_info(info, scopes=scopes)
                    st.success("✅ שלב 3: פרטי Service Account נקראו בהצלחה.")
                    client = gspread.authorize(creds)
                    st.success("✅ שלב 4: ההתחברות ל-Google הצליחה.")
                    test_sheet = client.open_by_key(SHEET_ID).sheet1
                    st.success(f"✅ שלב 5: הגיליון נמצא ונפתח בהצלחה — {test_sheet.title}")
                    st.info("🎉 החיבור תקין. אפשר להזין הוצאות במזומן.")
        except Exception as e:
            st.error("❌ הבדיקה נעצרה בשלב שבו קיימת הבעיה.")
            st.code(f"{type(e).__name__}: {repr(str(e))}")

try:
    cash_rows = load_cash_rows(start, end)
    sheets_ok = True
except Exception as e:
    cash_rows = []
    sheets_ok = False
    st.error("לא הצלחתי להתחבר ל-Google Sheets. פתח את 'בדיקת חיבור ל-Google Sheets' ולחץ על הכפתור.")

if sheets_ok:
    with st.form("cash_expense_form", clear_on_submit=True):
        cash_date = st.date_input("תאריך ההוצאה", value=today, min_value=start, max_value=end)
        cash_description = st.text_input("תיאור ההוצאה", placeholder="לדוגמה: מכולת, מספרה, מתנה")
        cash_amount = st.number_input("סכום", min_value=0.0, value=0.0, step=10.0)
        cash_category = st.selectbox("קטגוריה", CATEGORIES, index=CATEGORIES.index("אחר"))
        add_cash = st.form_submit_button("➕ הוסף הוצאה במזומן", use_container_width=True)

        if add_cash:
            if not cash_description.strip():
                st.error("יש להזין תיאור להוצאה.")
            elif cash_amount <= 0:
                st.error("יש להזין סכום גדול מאפס.")
            else:
                try:
                    add_cash_row(cash_date, cash_description.strip(), cash_amount,
                                 cash_category, start, end)
                    st.success("ההוצאה נשמרה ב-Google Sheets.")
                    st.rerun()
                except Exception as e:
                    st.error(f"לא הצלחתי לשמור את ההוצאה: {e}")

    if cash_rows:
        cash_view = pd.DataFrame(cash_rows)
        st.markdown("**הוצאות מזומן במחזור הנוכחי**")
        st.dataframe(
            cash_view[["תאריך", "בית עסק", "סכום", "קטגוריה"]],
            use_container_width=True, hide_index=True,
            column_config={
                "תאריך": st.column_config.DateColumn("תאריך", format="DD/MM/YYYY"),
                "בית עסק": st.column_config.TextColumn("תיאור"),
                "סכום": st.column_config.NumberColumn("סכום", format="₪ %.2f"),
                "קטגוריה": st.column_config.TextColumn("קטגוריה"),
            },
        )

        remove_options = [
            f'{i + 1}. {x["תאריך"].strftime("%d/%m/%Y")} — {x["בית עסק"]} — ₪{x["סכום"]:,.2f}'
            for i, x in enumerate(cash_rows)
        ]
        remove_choice = st.selectbox("מחיקת הוצאה במזומן", ["בחר הוצאה למחיקה"] + remove_options)
        if st.button("🗑️ מחק הוצאה שנבחרה", use_container_width=True):
            if remove_choice != "בחר הוצאה למחיקה":
                idx = remove_options.index(remove_choice)
                try:
                    delete_cash_row(cash_rows[idx]["_sheet_row"])
                    st.rerun()
                except Exception as e:
                    st.error(f"לא הצלחתי למחוק את ההוצאה: {e}")

        cash_df = pd.DataFrame(cash_rows)
        cash_df["תאריך"] = pd.to_datetime(cash_df["תאריך"])
        cyc = pd.concat(
            [cyc, cash_df[["תאריך", "בית עסק", "סכום", "קטגוריה"]]],
            ignore_index=True,
        )
    else:
        st.info("עדיין לא הוזנו הוצאות במזומן במחזור הנוכחי.")

consumer = cyc[cyc["קטגוריה"] != "חיסכון"].copy()
round_savings = cyc[cyc["קטגוריה"] == "חיסכון"]["סכום"].sum()
spend = consumer["סכום"].sum()
remaining = available - spend
days_left = max((end - today).days + 1, 1)
daily = max(remaining / days_left, 0)
elapsed = max((today - start).days + 1, 1)
pace = spend / elapsed
projected_spend = spend + pace * max((end - today).days, 0)
projected_saving = income - mortgage - kindergarten - personal_training - projected_spend

if remaining < 0:
    status = "🔴 אדום"
    msg = f"⛔ חרגת ממסגרת ההוצאות ב־₪{abs(remaining):,.0f}."
elif projected_saving >= savings_goal:
    status = "🟢 ירוק"
    msg = f"✅ אתה במסלול טוב. ניתן להוציא עד כ־₪{daily:,.0f} ליום ועדיין לשמור על יעד החיסכון."
elif projected_saving >= 0:
    status = "🟠 כתום"
    msg = f"⚠️ כדאי להאט. המסגרת שנותרה היא כ־₪{daily:,.0f} ליום."
else:
    status = "🔴 אדום"
    msg = "⛔ בקצב הנוכחי צפויה חריגה מהתקציב."

st.divider()
st.subheader("📊 תמונת מצב")

days_remaining = max((end - today).days + 1, 0)

# Native Streamlit columns: CSS stacks them on mobile.
c1, c2, c3, c4 = st.columns(4)
c1.metric("💳 הוצאות עד עכשיו (אשראי + מזומן)", f"₪{spend:,.0f}")
c2.metric(
    "💰 נשאר עד סוף המחזור",
    f"₪{max(remaining, 0):,.0f}",
    delta=f"חריגה ₪{abs(remaining):,.0f}" if remaining < 0 else None,
    delta_color="inverse",
)
c3.metric("📅 ימים שנותרו", f"{days_remaining}")
c4.metric("🎯 מותר להוציא היום", f"₪{max(daily, 0):,.0f}")

st.markdown(f"**יעד חיסכון:** ₪{savings_goal:,.0f}  \n**תחזית חיסכון בסוף המחזור:** ₪{projected_saving:,.0f}")

st.header(status)
if status.startswith("🟢"):
    st.success(msg)
elif status.startswith("🟠"):
    st.warning(msg)
else:
    st.error(msg)

st.divider()
st.subheader("📊 הוצאות לפי קטגוריה")

if len(consumer):
    cats = (
        consumer.groupby("קטגוריה", as_index=False)["סכום"]
        .sum()
        .sort_values("סכום", ascending=False)
    )

    # Simple, robust mobile presentation. No custom HTML chart and no RTL axis problems.
    max_amount = cats["סכום"].max() if len(cats) else 1
    for _, row in cats.iterrows():
        pct = (row["סכום"] / spend * 100) if spend else 0
        st.markdown(f"**{row['קטגוריה']}** — ₪{row['סכום']:,.0f} ({pct:.1f}%)")
        st.progress(min(float(row["סכום"] / max_amount), 1.0))

    with st.expander("פירוט סכומים לפי קטגוריה"):
        summary = cats.copy()
        total = summary["סכום"].sum()
        summary["אחוז מההוצאות"] = (summary["סכום"] / total * 100).round(1) if total else 0
        st.dataframe(
            summary,
            use_container_width=True,
            hide_index=True,
            column_config={
                "קטגוריה": st.column_config.TextColumn("קטגוריה"),
                "סכום": st.column_config.NumberColumn("סכום", format="₪ %.2f"),
                "אחוז מההוצאות": st.column_config.NumberColumn("אחוז", format="%.1f%%"),
            },
        )
else:
    st.info("לא נמצאו הוצאות להצגה.")

if round_savings:
    st.caption(f"'עגול לחיסכון' שזוהה במחזור: ₪{round_savings:,.2f}")

st.caption("הוצאות המזומן נשמרות ב-Google Sheets. בתחילת מחזור חדש התצוגה מתאפסת, והמחזור הקודם נשמר כהיסטוריה בגיליון.")
