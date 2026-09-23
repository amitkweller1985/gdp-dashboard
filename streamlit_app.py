# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from datetime import date, timedelta

st.set_page_config(page_title="התקציב שלי", page_icon="💰", layout="wide")

st.markdown("""
<style>
.block-container { max-width: 1100px; padding-top: 1.5rem; }
@media (min-width: 769px) {
    html, body, [data-testid="stAppViewContainer"] { direction: rtl; }
}
h1, h2, h3, p { text-align: right; }
.cycle-box { direction: rtl; text-align: right; font-weight: 700; margin: 1rem 0; }
@media (max-width: 768px) {
    .block-container { max-width: 100%; padding: 1rem 0.75rem 4rem; }
    h1 { font-size: 2.1rem !important; line-height: 1.2 !important; }
    h2 { font-size: 1.55rem !important; line-height: 1.25 !important; }
    h3 { font-size: 1.25rem !important; line-height: 1.3 !important; }
    .cycle-box { font-size: 1.15rem; line-height: 1.6; }
}
</style>
""", unsafe_allow_html=True)

DEFAULTS = {"income":28500.0,"mortgage":9800.0,"kindergarten":4000.0,
"personal_training":1200.0,"cleaner":800.0,"savings_goal":2000.0,"cycle_day":10}

CATEGORIES = ["מזון וסופר","מסעדות ואוכל בחוץ","רכב ודלק","חניה וכבישי אגרה",
"ילדים וגן","בריאות ופארם","חשבונות","תקשורת","קניות","בילויים","דיור/עירייה",
"טיפולי קוסמטיקה ומספרה","תשלום לא מתוכנן","חיסכון","אחר"]

def cycle_bounds(today,d=10):
    if today.day>=d:
        start=date(today.year,today.month,d)
        nxt=date(today.year+1,1,d) if today.month==12 else date(today.year,today.month+1,d)
    else:
        start=date(today.year-1,12,d) if today.month==1 else date(today.year,today.month-1,d)
        nxt=date(today.year,today.month,d)
    return start,nxt-timedelta(days=1)

def find_col(cols,wanted):
    return next((c for c in cols if str(c).strip()==wanted),None)

def auto_category(merchant):
    s=str(merchant or "").lower()
    rules=[
        (["עגול לחס"],"חיסכון"),
        (["שופרסל","רמי לוי","ויקטורי","קרפור","סופר","כל - בו","כל-בו"],"מזון וסופר"),
        (["פנגו","סלופארק","כביש 6"],"חניה וכבישי אגרה"),
        (["דלק","סונול","פז","דור אלון","טן"],"רכב ודלק"),
        (["עיריית","ארנונה"],"דיור/עירייה"),
        (["מכבי חיפה","סינמה","יס פלאנט","תיאטרון"],"בילויים"),
        (["בזק","פרטנר","סלקום","הוט","012","013","019"],"תקשורת"),
        (["חשמל","חברת החשמל","מים","מי ","גז","אמישראגז","פזגז"],"חשבונות"),
        (["נטפליקס","netflix","spotify","apple"],"תקשורת"),
        (["סופר-פארם","סופר פארם","בית מרקחת","פארם"],"בריאות ופארם"),
        (["מסעד","קפה","ארומה","מקדונלד","וולט","wolt","תן ביס"],"מסעדות ואוכל בחוץ"),
        (["גן ילדים","צהרון","קייטנה"],"ילדים וגן"),
        (["מספרה","ספר ","קוסמט","לק ג'ל","לק גל","מניקור","פדיקור"],"טיפולי קוסמטיקה ומספרה"),
        (["זארה","h&m","איקאה","ikea","קסטרו","פוקס"],"קניות")]
    for keys,cat in rules:
        if any(k.lower() in s for k in keys): return cat
    return "אחר"

def parse_file(upload):
    df=pd.read_excel(upload)
    merchant=find_col(df.columns,"בית עסק"); txdate=find_col(df.columns,"תאריך עסקה"); amount=find_col(df.columns,"סכום החיוב")
    if not all([merchant,txdate,amount]):
        raise ValueError("לא זוהה פורמט הקובץ. נדרשות העמודות: בית עסק, תאריך עסקה, סכום החיוב.")
    out=pd.DataFrame()
    out["בית עסק"]=df[merchant].astype(str).str.strip()
    out["תאריך"]=pd.to_datetime(df[txdate],errors="coerce",dayfirst=True)
    out["סכום"]=pd.to_numeric(df[amount],errors="coerce")
    out=out.dropna(subset=["תאריך","סכום"])
    out=out[(out["בית עסק"]!="בית עסק")&(out["בית עסק"]!="nan")]
    out=out.drop_duplicates(subset=["בית עסק","תאריך","סכום"])
    out["קטגוריה"]=out["בית עסק"].map(auto_category)
    return out

st.title("💰 התקציב שלי")
st.caption("מעלים את קובץ האשראי, מתקנים קטגוריות ומוסיפים חיובים צפויים לפני שהם נכנסים לאשראי.")

with st.sidebar:
    st.header("הגדרות חודשיות")
    income=st.number_input("הכנסות",min_value=0.0,value=DEFAULTS["income"],step=100.0)
    mortgage=st.number_input("משכנתא",min_value=0.0,value=DEFAULTS["mortgage"],step=100.0)
    kindergarten=st.number_input("גן / צ׳קים",min_value=0.0,value=DEFAULTS["kindergarten"],step=100.0)
    personal_training=st.number_input("אימונים אישיים",min_value=0.0,value=DEFAULTS["personal_training"],step=100.0)
    cleaner=st.number_input("מנקה",min_value=0.0,value=DEFAULTS["cleaner"],step=100.0)
    cash_spend=st.number_input("💵 הוצאות מזומן במחזור",min_value=0.0,value=0.0,step=50.0)
    savings_goal=st.number_input("יעד חיסכון",min_value=0.0,value=DEFAULTS["savings_goal"],step=100.0)
    st.info("המחזור מוגדר מה־10 בחודש עד ה־9 בחודש הבא.")

today=date.today(); start,end=cycle_bounds(today,DEFAULTS["cycle_day"])
available=income-mortgage-kindergarten-personal_training-cleaner-savings_goal

st.markdown(f"""<div class="cycle-box" dir="rtl">מחזור נוכחי:
<span style="white-space:nowrap;" dir="ltr">{start:%d.%m.%Y} – {end:%d.%m.%Y}</span></div>""",unsafe_allow_html=True)
st.markdown(f"מסגרת לשאר ההוצאות אחרי משכנתא, גן, אימונים אישיים, מנקה ויעד חיסכון: **₪{available:,.0f}**")
st.markdown(f"**הוצאות קבועות:** משכנתא ₪{mortgage:,.0f} · גן / צ׳קים ₪{kindergarten:,.0f} · אימונים אישיים ₪{personal_training:,.0f} · מנקה ₪{cleaner:,.0f} · **סה״כ ₪{mortgage+kindergarten+personal_training+cleaner:,.0f}**")

upload=st.file_uploader("העלה את קובץ האשראי העדכני",type=["xlsx","xls"])
if upload is None:
    st.info("בחר קובץ Excel כדי להתחיל."); st.stop()
try: df=parse_file(upload)
except Exception as e:
    st.error(str(e)); st.stop()

cyc=df[(df["תאריך"].dt.date>=start)&(df["תאריך"].dt.date<=end)].copy()

st.divider(); st.subheader("✏️ תיקון קטגוריות")
st.caption("לחץ על הקטגוריה בכל שורה כדי לשנות אותה. החישובים מתעדכנים מיד.")
if len(cyc):
    edit_df=cyc[["תאריך","בית עסק","סכום","קטגוריה"]].copy(); edit_df["תאריך"]=edit_df["תאריך"].dt.date
    edited=st.data_editor(edit_df,use_container_width=True,hide_index=True,disabled=["תאריך","בית עסק","סכום"],
        column_config={"תאריך":st.column_config.DateColumn("תאריך",format="DD/MM/YYYY"),
        "בית עסק":st.column_config.TextColumn("בית עסק"),
        "סכום":st.column_config.NumberColumn("סכום",format="₪ %.2f"),
        "קטגוריה":st.column_config.SelectboxColumn("קטגוריה",options=CATEGORIES,required=True)},key="category_editor")
    cyc["קטגוריה"]=edited["קטגוריה"].values
else: st.info("לא נמצאו עסקאות במחזור הנוכחי.")

st.divider(); st.subheader("📝 חיובים צפויים")
st.caption("כאן אפשר להכניס ידנית חשמל, מים, ארנונה וכל חיוב שעדיין לא הופיע באשראי. הוסף או מחק שורות ישירות בטבלה.")
if "expected_charges" not in st.session_state:
    st.session_state.expected_charges=pd.DataFrame({"תיאור":pd.Series(dtype="str"),"סכום":pd.Series(dtype="float"),"קטגוריה":pd.Series(dtype="str")})

expected_edit=st.data_editor(st.session_state.expected_charges,num_rows="dynamic",use_container_width=True,hide_index=True,
    column_config={"תיאור":st.column_config.TextColumn("תיאור החיוב"),
    "סכום":st.column_config.NumberColumn("סכום צפוי",min_value=0.0,step=10.0,format="₪ %.2f"),
    "קטגוריה":st.column_config.SelectboxColumn("קטגוריה",options=CATEGORIES)},key="expected_editor")

expected=expected_edit.copy()
expected["סכום"]=pd.to_numeric(expected["סכום"],errors="coerce").fillna(0.0)
expected=expected[expected["סכום"]>0].copy()
expected["קטגוריה"]=expected["קטגוריה"].fillna("חשבונות")
st.session_state.expected_charges=expected.reset_index(drop=True)

expected_spend=expected.loc[expected["קטגוריה"]!="חיסכון","סכום"].sum()
expected_savings=expected.loc[expected["קטגוריה"]=="חיסכון","סכום"].sum()
consumer=cyc[cyc["קטגוריה"]!="חיסכון"].copy()
round_savings=cyc[cyc["קטגוריה"]=="חיסכון"]["סכום"].sum()
credit_spend=consumer["סכום"].sum()
actual_spend=credit_spend+cash_spend
spend=actual_spend+expected_spend
remaining=available-spend
days_left=max((end-today).days+1,1); daily=max(remaining/days_left,0)
elapsed=max((today-start).days+1,1); pace=actual_spend/elapsed
projected_spend=actual_spend+expected_spend+pace*max((end-today).days,0)
projected_saving=income-mortgage-kindergarten-personal_training-cleaner-projected_spend

if remaining<0:
    status="🔴 אדום"; msg=f"⛔ חרגת ממסגרת ההוצאות ב־₪{abs(remaining):,.0f}, כולל החיובים הצפויים."
elif projected_saving>=savings_goal:
    status="🟢 ירוק"; msg=f"✅ אתה במסלול טוב. לאחר החיובים הצפויים ניתן להוציא עד כ־₪{daily:,.0f} ליום ועדיין לשמור על יעד החיסכון."
elif projected_saving>=0:
    status="🟠 כתום"; msg=f"⚠️ כדאי להאט. לאחר החיובים הצפויים המסגרת שנותרה היא כ־₪{daily:,.0f} ליום."
else:
    status="🔴 אדום"; msg="⛔ בקצב הנוכחי, ובהתחשב בחיובים הצפויים, צפויה חריגה מהתקציב."

st.divider(); st.subheader("📊 תמונת מצב")
st.caption(f"אשראי: ₪{credit_spend:,.0f} · מזומן: ₪{cash_spend:,.0f} · חיובים צפויים: ₪{expected_spend:,.0f}")
days_remaining=max((end-today).days+1,0)
c1,c2,c3,c4=st.columns(4)
c1.metric("💳 הוצאות כולל חיובים צפויים",f"₪{spend:,.0f}")
c2.metric("💰 נשאר עד סוף המחזור",f"₪{max(remaining,0):,.0f}",delta=f"חריגה ₪{abs(remaining):,.0f}" if remaining<0 else None,delta_color="inverse")
c3.metric("📅 ימים שנותרו",f"{days_remaining}")
c4.metric("🎯 מותר להוציא היום",f"₪{max(daily,0):,.0f}")
st.markdown(f"**יעד חיסכון:** ₪{savings_goal:,.0f}  
**תחזית חיסכון בסוף המחזור:** ₪{projected_saving:,.0f}")
st.header(status)
if status.startswith("🟢"): st.success(msg)
elif status.startswith("🟠"): st.warning(msg)
else: st.error(msg)

st.divider(); st.subheader("📊 הוצאות לפי קטגוריה")
parts=[]
if len(consumer): parts.append(consumer[["קטגוריה","סכום"]].copy())
if len(expected):
    ep=expected[expected["קטגוריה"]!="חיסכון"][["קטגוריה","סכום"]].copy()
    if len(ep): parts.append(ep)
if parts:
    cat_source=pd.concat(parts,ignore_index=True)
    cats=cat_source.groupby("קטגוריה",as_index=False)["סכום"].sum().sort_values("סכום",ascending=False)
    max_amount=cats["סכום"].max() if len(cats) else 1; cat_total=cats["סכום"].sum()
    for _,row in cats.iterrows():
        pct=(row["סכום"]/cat_total*100) if cat_total else 0
        st.markdown(f"**{row['קטגוריה']}** — ₪{row['סכום']:,.0f} ({pct:.1f}%)")
        st.progress(min(float(row["סכום"]/max_amount),1.0))
    with st.expander("פירוט סכומים לפי קטגוריה"):
        summary=cats.copy()
        summary["אחוז מההוצאות"]=(summary["סכום"]/cat_total*100).round(1) if cat_total else 0
        st.dataframe(summary,use_container_width=True,hide_index=True,column_config={
            "קטגוריה":st.column_config.TextColumn("קטגוריה"),
            "סכום":st.column_config.NumberColumn("סכום",format="₪ %.2f"),
            "אחוז מההוצאות":st.column_config.NumberColumn("אחוז",format="%.1f%%")})
else: st.info("לא נמצאו הוצאות להצגה.")

if round_savings or expected_savings:
    st.caption(f"חיסכון שזוהה/הוזן במחזור: ₪{round_savings+expected_savings:,.2f}")
st.caption("המנקה מוגדרת כהוצאה חודשית קבועה של ₪800. חיובים צפויים נכללים בתקציב מיד, עוד לפני שהם מופיעים בקובץ האשראי.")
