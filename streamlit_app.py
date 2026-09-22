import streamlit as st
import pandas as pd
from datetime import date, timedelta

st.set_page_config(page_title="התקציב שלי", page_icon="💰", layout="wide")
st.markdown("""<style>
html, body, [class*="css"] { direction: rtl; text-align: right; }
[data-testid="stMetric"] { direction: rtl; }
.block-container { max-width: 1100px; }
</style>""", unsafe_allow_html=True)

DEFAULTS = {"income":28500.0,"mortgage":9800.0,"kindergarten":4000.0,"savings_goal":2000.0,"cycle_day":10}

def cycle_bounds(today, d=10):
    if today.day >= d:
        start=date(today.year,today.month,d)
        nxt=date(today.year+1,1,d) if today.month==12 else date(today.year,today.month+1,d)
    else:
        start=date(today.year-1,12,d) if today.month==1 else date(today.year,today.month-1,d)
        nxt=date(today.year,today.month,d)
    return start, nxt-timedelta(days=1)

def find_col(cols,wanted):
    return next((c for c in cols if str(c).strip()==wanted),None)

def auto_category(merchant):
    s=str(merchant or "").lower()
    rules=[
        (["עגול לחס"],"חיסכון"),
        (["שופרסל","רמי לוי","ויקטורי","קרפור","סופר","כל - בו","כל-בו"],"מזון וסופר"),
        (["פנגו","סלופארק","דלק","סונול","פז","דור אלון","כביש 6"],"רכב ותחבורה"),
        (["עיריית"],"דיור/עירייה"),
        (["מכבי חיפה","סינמה","יס פלאנט"],"בילויים"),
        (["בזק","פרטנר","סלקום","הוט","נטפליקס","spotify","apple"],"תקשורת ומנויים"),
        (["סופר-פארם","סופר פארם","בית מרקחת"],"בריאות"),
        (["מסעד","קפה","ארומה","מקדונלד","וולט","תן ביס"],"מסעדות"),
    ]
    for keys,cat in rules:
        if any(k.lower() in s for k in keys): return cat
    return "אחר"

def parse_file(upload):
    df=pd.read_excel(upload)
    merchant=find_col(df.columns,"בית עסק")
    txdate=find_col(df.columns,"תאריך עסקה")
    amount=find_col(df.columns,"סכום החיוב")
    if not all([merchant,txdate,amount]):
        raise ValueError("לא זוהה פורמט הקובץ. נדרשות העמודות: בית עסק, תאריך עסקה, סכום החיוב.")
    out=pd.DataFrame()
    out["בית עסק"]=df[merchant].astype(str).str.strip()
    out["תאריך"]=pd.to_datetime(df[txdate],errors="coerce",dayfirst=True)
    out["סכום"]=pd.to_numeric(df[amount],errors="coerce")
    out=out.dropna(subset=["תאריך","סכום"])
    out=out[(out["בית עסק"]!="בית עסק")&(out["בית עסק"]!="nan")]
    out["קטגוריה"]=out["בית עסק"].map(auto_category)
    return out.drop_duplicates(subset=["בית עסק","תאריך","סכום"])

st.title("💰 התקציב שלי")
st.caption("מעלים את קובץ האשראי העדכני ומקבלים תמונת מצב למחזור שמתחיל ב־10 בחודש ומסתיים ב־9 בחודש הבא.")

with st.sidebar:
    st.header("הגדרות חודשיות")
    income=st.number_input("הכנסות",min_value=0.0,value=DEFAULTS["income"],step=100.0)
    mortgage=st.number_input("משכנתא",min_value=0.0,value=DEFAULTS["mortgage"],step=100.0)
    kindergarten=st.number_input("גן / צ׳קים",min_value=0.0,value=DEFAULTS["kindergarten"],step=100.0)
    savings_goal=st.number_input("יעד חיסכון",min_value=0.0,value=DEFAULTS["savings_goal"],step=100.0)
    st.info("המחזור מוגדר מה־10 בחודש עד ה־9 בחודש הבא.")

today=date.today()
start,end=cycle_bounds(today,DEFAULTS["cycle_day"])
available=income-mortgage-kindergarten-savings_goal

st.markdown(f"<h3 dir='rtl'>מחזור נוכחי: <span dir='ltr'>{start:%d.%m.%Y} ← {end:%d.%m.%Y}</span></h3>",unsafe_allow_html=True)
st.write(f"מסגרת לשאר ההוצאות אחרי משכנתא, גן ויעד חיסכון: **₪{available:,.0f}**")

upload=st.file_uploader("העלה את קובץ האשראי העדכני",type=["xlsx","xls"])
if upload is None:
    st.info("בחר קובץ Excel. האפליקציה מנתחת אותו בזיכרון לצורך החישוב; גרסה זו אינה זקוקה למסד נתונים.")
    st.stop()

try:
    df=parse_file(upload)
except Exception as e:
    st.error(str(e)); st.stop()

cyc=df[(df["תאריך"].dt.date>=start)&(df["תאריך"].dt.date<=end)].copy()
consumer=cyc[cyc["קטגוריה"]!="חיסכון"].copy()
round_savings=cyc[cyc["קטגוריה"]=="חיסכון"]["סכום"].sum()
spend=consumer["סכום"].sum()
remaining=available-spend
days_left=max((end-today).days+1,1)
daily=max(remaining/days_left,0)
elapsed=max((today-start).days+1,1)
pace=spend/elapsed
projected_spend=spend+pace*max((end-today).days,0)
projected_saving=income-mortgage-kindergarten-projected_spend

if remaining<0:
    status="🔴 אדום"
    msg=f"⛔ עצור הוצאות לא חיוניות. חרגת ממסגרת ההוצאות ב־₪{abs(remaining):,.0f}. התמקד מעכשיו רק בהוצאות הכרחיות."
elif projected_saving>=savings_goal:
    status="🟢 ירוק"
    msg=f"✅ אתה במסלול טוב. ניתן להוציא עד כ־₪{daily:,.0f} ליום עד סוף המחזור ועדיין להישאר במסגרת ששומרת על יעד חיסכון של ₪{savings_goal:,.0f}."
elif projected_saving>=0:
    status="🟠 כתום"
    msg=f"⚠️ כדאי להאט. המסגרת שנותרה מאפשרת עד כ־₪{daily:,.0f} ליום, אבל בקצב הנוכחי יעד החיסכון עלול להיפגע. הימנע כרגע מהוצאות גדולות ולא חיוניות."
else:
    status="🔴 אדום"
    msg="⛔ עצור כרגע הוצאות לא חיוניות. בקצב ההוצאה הנוכחי התחזית מצביעה על חריגה מהתקציב עד סוף המחזור."

st.header(status)
c1,c2,c3,c4=st.columns(4)
c1.metric("נשאר להוציא",f"₪{max(remaining,0):,.0f}",delta=f"חריגה ₪{abs(remaining):,.0f}" if remaining<0 else None,delta_color="inverse")
c2.metric("מותר ליום",f"₪{daily:,.0f}")
c3.metric("הוצאות אשראי",f"₪{spend:,.0f}")
c4.metric("תחזית חיסכון",f"₪{projected_saving:,.0f}")

if status.startswith("🟢"): st.success(msg)
elif status.startswith("🟠"): st.warning(msg)
else: st.error(msg)

st.divider()
st.subheader("הוצאות לפי קטגוריה")
if len(consumer):
    cats=consumer.groupby("קטגוריה",as_index=False)["סכום"].sum().sort_values("סכום",ascending=False)
    st.bar_chart(cats.set_index("קטגוריה"))
    view=consumer[["תאריך","בית עסק","סכום","קטגוריה"]].sort_values("תאריך",ascending=False)
    view["תאריך"]=view["תאריך"].dt.strftime("%d/%m/%Y")
    st.dataframe(view,use_container_width=True,hide_index=True)
else:
    st.info("לא נמצאו עסקאות אשראי במחזור הנוכחי.")

if round_savings:
    st.caption(f"'עגול לחיסכון' שזוהה במחזור: ₪{round_savings:,.2f}")
st.caption("הערה: התחזית מבוססת על קצב ההוצאה עד היום ואינה התחייבות לתוצאה בפועל.")
