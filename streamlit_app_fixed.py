import streamlit as st
import pandas as pd
from datetime import date, timedelta

st.set_page_config(page_title="התקציב שלי", page_icon="💰", layout="wide")
st.markdown("""<style>
html, body, [class*="css"] { direction: rtl; text-align: right; }
[data-testid="stMetric"] { direction: rtl; }
.block-container { max-width: 1100px; }
</style>""", unsafe_allow_html=True)

DEFAULTS = {
    "income": 28500.0,
    "mortgage": 9800.0,
    "kindergarten": 4000.0,
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
    "חשבונות ותקשורת",
    "קניות",
    "בילויים",
    "דיור/עירייה",
    "חיסכון",
    "אחר",
]

CATEGORY_COLORS = {
    "מזון וסופר": "#2E86DE",
    "מסעדות ואוכל בחוץ": "#FF8C42",
    "רכב ודלק": "#16A085",
    "חניה וכבישי אגרה": "#8E44AD",
    "ילדים וגן": "#E056FD",
    "בריאות ופארם": "#E74C3C",
    "חשבונות ותקשורת": "#3498DB",
    "קניות": "#F1C40F",
    "בילויים": "#9B59B6",
    "דיור/עירייה": "#795548",
    "חיסכון": "#27AE60",
    "אחר": "#7F8C8D",
}

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
        (["בזק", "פרטנר", "סלקום", "הוט", "נטפליקס", "spotify", "apple"], "חשבונות ותקשורת"),
        (["סופר-פארם", "סופר פארם", "בית מרקחת", "פארם"], "בריאות ופארם"),
        (["מסעד", "קפה", "ארומה", "מקדונלד", "וולט", "wolt", "תן ביס"], "מסעדות ואוכל בחוץ"),
        (["גן ילדים", "צהרון", "קייטנה"], "ילדים וגן"),
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

st.title("💰 התקציב שלי")
st.caption("מעלים את קובץ האשראי, מתקנים קטגוריות במידת הצורך ומקבלים תמונת מצב למחזור 10–10.")

with st.sidebar:
    st.header("הגדרות חודשיות")
    income = st.number_input("הכנסות", min_value=0.0, value=DEFAULTS["income"], step=100.0)
    mortgage = st.number_input("משכנתא", min_value=0.0, value=DEFAULTS["mortgage"], step=100.0)
    kindergarten = st.number_input("גן / צ׳קים", min_value=0.0, value=DEFAULTS["kindergarten"], step=100.0)
    savings_goal = st.number_input("יעד חיסכון", min_value=0.0, value=DEFAULTS["savings_goal"], step=100.0)
    st.info("המחזור מוגדר מה־10 בחודש עד ה־9 בחודש הבא.")

today = date.today()
start, end = cycle_bounds(today, DEFAULTS["cycle_day"])
available = income - mortgage - kindergarten - savings_goal

st.markdown(
    f"<h3 dir='rtl'>מחזור נוכחי: <span dir='ltr'>{start:%d.%m.%Y} ← {end:%d.%m.%Y}</span></h3>",
    unsafe_allow_html=True,
)
st.write(f"מסגרת לשאר ההוצאות אחרי משכנתא, גן ויעד חיסכון: **₪{available:,.0f}**")

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
st.caption("אפשר ללחוץ על הקטגוריה בכל שורה ולבחור קטגוריה אחרת. כל החישובים והגרפים למטה יתעדכנו מיד.")

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

consumer = cyc[cyc["קטגוריה"] != "חיסכון"].copy()
round_savings = cyc[cyc["קטגוריה"] == "חיסכון"]["סכום"].sum()
spend = consumer["סכום"].sum()
remaining = available - spend
days_left = max((end - today).days + 1, 1)
daily = max(remaining / days_left, 0)
elapsed = max((today - start).days + 1, 1)
pace = spend / elapsed
projected_spend = spend + pace * max((end - today).days, 0)
projected_saving = income - mortgage - kindergarten - projected_spend

if remaining < 0:
    status = "🔴 אדום"
    msg = f"⛔ עצור הוצאות לא חיוניות. חרגת ממסגרת ההוצאות ב־₪{abs(remaining):,.0f}."
elif projected_saving >= savings_goal:
    status = "🟢 ירוק"
    msg = f"✅ אתה במסלול טוב. ניתן להוציא עד כ־₪{daily:,.0f} ליום ועדיין לשמור על יעד החיסכון."
elif projected_saving >= 0:
    status = "🟠 כתום"
    msg = f"⚠️ כדאי להאט. המסגרת שנותרה היא כ־₪{daily:,.0f} ליום, ויעד החיסכון עלול להיפגע."
else:
    status = "🔴 אדום"
    msg = "⛔ עצור כרגע הוצאות לא חיוניות. בקצב הנוכחי צפויה חריגה מהתקציב."

st.divider()
st.subheader("📊 תמונת מצב עד ה־10")

days_remaining = max((end - today).days + 1, 0)
today_budget = max(daily, 0)

c1, c2, c3, c4 = st.columns(4)
c1.metric("💳 הוצאת עד עכשיו", f"₪{spend:,.0f}")
c2.metric(
    "💰 נשאר עד סוף המחזור",
    f"₪{max(remaining, 0):,.0f}",
    delta=f"חריגה ₪{abs(remaining):,.0f}" if remaining < 0 else None,
    delta_color="inverse",
)
c3.metric("📅 ימים שנותרו", f"{days_remaining}")
c4.metric("🎯 מותר להוציא היום", f"₪{today_budget:,.0f}")

st.markdown(
    f"""
    <div style="padding:18px;border-radius:14px;margin-top:12px;margin-bottom:14px;
        background:rgba(120,120,120,0.08);font-size:18px;">
        <b>יעד החיסכון שלך:</b> ₪{savings_goal:,.0f}
        &nbsp;&nbsp; | &nbsp;&nbsp;
        <b>תחזית חיסכון בסוף המחזור:</b> ₪{projected_saving:,.0f}
    </div>
    """,
    unsafe_allow_html=True,
)

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
        .reset_index(drop=True)
    )

    total = float(cats["סכום"].sum())
    max_amount = float(cats["סכום"].max()) if len(cats) else 1

    # גרף HTML מותאם לעברית.
    # השם והסכום נמצאים בשורה נפרדת מעל הפס ולכן שום טקסט לא נחתך.
    rows_html = ""

    for _, row in cats.iterrows():
        category = str(row["קטגוריה"])
        amount = float(row["סכום"])
        pct = (amount / total * 100) if total else 0
        width = max((amount / max_amount * 100), 2.5)
        color = CATEGORY_COLORS.get(category, "#7F8C8D")

        rows_html += f"""
        <div class="budget-row">
            <div class="budget-row-head">
                <span class="budget-category">{category}</span>
                <span class="budget-amount">₪{amount:,.0f}</span>
            </div>

            <div class="budget-track">
                <div class="budget-bar"
                     style="width:{width:.1f}%; background:{color};">
                </div>
            </div>

            <div class="budget-percent">{pct:.1f}% מהוצאות האשראי</div>
        </div>
        """

    st.markdown(
        f"""
        <style>
        .budget-chart {{
            direction: rtl;
            width: 100%;
            padding: 10px 4px 4px 4px;
            box-sizing: border-box;
        }}

        .budget-row {{
            direction: rtl;
            margin: 0 0 24px 0;
        }}

        .budget-row-head {{
            direction: rtl;
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            gap: 20px;
            margin-bottom: 7px;
        }}

        .budget-category {{
            font-size: 20px;
            font-weight: 800;
            color: #202124;
            line-height: 1.35;
            text-align: right;
        }}

        .budget-amount {{
            direction: ltr;
            unicode-bidi: isolate;
            white-space: nowrap;
            font-size: 20px;
            font-weight: 800;
            color: #202124;
            text-align: left;
        }}

        .budget-track {{
            direction: rtl;
            width: 100%;
            height: 25px;
            background: rgba(120,120,120,0.13);
            border-radius: 9px;
            overflow: hidden;
        }}

        .budget-bar {{
            height: 100%;
            min-width: 8px;
            border-radius: 9px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.10);
        }}

        .budget-percent {{
            direction: rtl;
            text-align: right;
            margin-top: 5px;
            font-size: 13px;
            font-weight: 600;
            color: #666;
        }}

        @media (max-width: 700px) {{
            .budget-category,
            .budget-amount {{
                font-size: 17px;
            }}
            .budget-row {{
                margin-bottom: 20px;
            }}
        }}
        </style>

        <div class="budget-chart">
            {rows_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

    summary = cats.copy()
    summary["אחוז"] = ((summary["סכום"] / total * 100) if total else 0).round(1)
    summary["סכום"] = summary["סכום"].round(2)

    with st.expander("📋 הצג טבלת פירוט"):
        st.dataframe(
            summary[["קטגוריה", "סכום", "אחוז"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "קטגוריה": st.column_config.TextColumn("קטגוריה"),
                "סכום": st.column_config.NumberColumn("סכום", format="₪ %.2f"),
                "אחוז": st.column_config.NumberColumn("אחוז מההוצאות", format="%.1f%%"),
            },
        )
else:
    st.info("לא נמצאו הוצאות אשראי להצגה במחזור הנוכחי.")

if round_savings:
    st.caption(f"'עגול לחיסכון' שזוהה במחזור: ₪{round_savings:,.2f}")

st.caption("הערה: שינוי קטגוריה במסך משפיע מיד על החישובים. בגרסה זו השינוי הידני נשמר במהלך העבודה הנוכחית; בהעלאה חדשה יבוצע שוב הסיווג האוטומטי.")
