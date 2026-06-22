import streamlit as st
import sqlite3
import pandas as pd
import datetime
import matplotlib.pyplot as plt

st.set_page_config(page_title="钱袋袋", layout="wide")

st.title("💰 钱袋袋记账系统 ")

DB = "money.db"

# ======================
# 自动分类（不动）
# ======================
def auto_category(note):
    if not note:
        return "其他"

    note = note.lower()

    rules = {
        "餐饮": ["饭", "餐", "奶茶", "外卖", "咖啡", "吃", "火锅"],
        "交通": ["地铁", "公交", "打车", "滴滴", "车票"],
        "购物": ["淘宝", "京东", "拼多多", "买"],
        "住房": ["房租", "水电", "物业"],
        "娱乐": ["电影", "游戏", "ktv"],
        "工资": ["工资", "薪水", "奖金"]
    }

    for k, words in rules.items():
        if any(w in note for w in words):
            return k

    return "其他"

# ======================
# DB（不动）
# ======================
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            date TEXT,
            type TEXT,
            amount REAL,
            category TEXT,
            note TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ======================
# 数据读取
# ======================
def load_data():
    conn = sqlite3.connect(DB)
    df = pd.read_sql_query("SELECT * FROM records", conn)
    conn.close()

    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df

df = load_data()

# ======================
# 🚨 时间筛选系统（V7.5核心新增）
# ======================
st.sidebar.header("⏳ 时间筛选（全局）")

filter_type = st.sidebar.selectbox(
    "筛选方式",
    ["全部", "按年", "按月", "按日", "自定义"]
)

if not df.empty:

    if filter_type == "全部":
        df_view = df

    elif filter_type == "按年":
        year = st.sidebar.number_input("年份", value=datetime.date.today().year)
        df_view = df[df["date"].dt.year == year]

    elif filter_type == "按月":
        year = st.sidebar.number_input("年份", value=datetime.date.today().year)
        month = st.sidebar.number_input("月份", 1, 12, datetime.date.today().month)
        df_view = df[(df["date"].dt.year == year) & (df["date"].dt.month == month)]

    elif filter_type == "按日":
        day = st.sidebar.date_input("选择日期", datetime.date.today())
        df_view = df[df["date"].dt.date == day]

    else:
        start = st.sidebar.date_input("开始日期", datetime.date.today().replace(day=1))
        end = st.sidebar.date_input("结束日期", datetime.date.today())
        df_view = df[(df["date"] >= pd.to_datetime(start)) & (df["date"] <= pd.to_datetime(end))]
else:
    df_view = df

# ======================
# 新增记录（不动）
# ======================
st.subheader("➕ 新增记录")

col1, col2 = st.columns(2)

with col1:
    type_ = st.radio("类型", ["收入", "支出"])

with col2:
    amount = st.number_input("金额", min_value=0.0)

date = st.date_input("日期", datetime.date.today())
note = st.text_input("备注")

category = auto_category(note)
st.caption(f"🧠 自动分类：{category}")

if st.button("保存"):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        INSERT INTO records(date,type,amount,category,note)
        VALUES (?,?,?,?,?)
    """, (str(date), type_, float(amount), category, note))
    conn.commit()
    conn.close()
    st.rerun()

# ======================
# 📊 数据分析（新增时间筛选已生效）
# ======================
st.subheader("📊 数据分析")

if not df_view.empty:

    income = df_view[df_view["type"]=="收入"]["amount"].sum()
    expense = df_view[df_view["type"]=="支出"]["amount"].sum()

    colA, colB, colC = st.columns(3)
    colA.metric("收入", income)
    colB.metric("支出", expense)
    colC.metric("结余", income - expense)

# ======================
# 📈 收支趋势（时间筛选已生效）
# ======================
st.subheader("📈 收支趋势")

if not df_view.empty:

    trend = df_view.copy()
    trend["month"] = trend["date"].dt.to_period("M").astype(str)

    chart = trend.groupby(["month","type"])["amount"].sum().unstack().fillna(0)

    if "收入" not in chart.columns:
        chart["收入"] = 0
    if "支出" not in chart.columns:
        chart["支出"] = 0

    st.bar_chart(chart[["收入","支出"]])

# ======================
# 🍰 支出占比（时间筛选已生效）
# ======================
st.subheader("🍰 支出占比分析")

expense_df = df_view[df_view["type"] == "支出"]

if not expense_df.empty:

    pie_data = expense_df.groupby("category")["amount"].sum()

    fig, ax = plt.subplots(figsize=(1.7, 1.7))

    ax.pie(
        pie_data,
        labels=None,
        autopct="%1.0f%%",
        startangle=90,
        textprops={'fontsize': 8}
    )

    ax.legend(
        pie_data.index,
        loc="center left",
        bbox_to_anchor=(1, 0.5),
        fontsize=8
    )

    st.pyplot(fig)

# ======================
# 📋 明细（完全保留修改+删除）
# ======================
st.subheader("📋 明细")

if not df_view.empty:

    for _, row in df_view.sort_values("date", ascending=False).iterrows():

        rid = row["id"]

        col1, col2, col3, col4, col5, col6, col7 = st.columns([2,1,1,1,2,1,1])

        col1.write(str(row["date"].date()))
        col2.write(row["type"])
        col3.write(f"{row['amount']:.2f}")
        col4.write(row["category"])
        col5.write(row["note"])

        # 删除
        if col6.button("删除", key=f"del_{rid}"):

            conn = sqlite3.connect(DB)
            c = conn.cursor()
            c.execute("DELETE FROM records WHERE id=?", (rid,))
            conn.commit()
            conn.close()
            st.rerun()

        # 修改（保留逻辑）
        edit_key = f"edit_{rid}"

        if edit_key not in st.session_state:
            st.session_state[edit_key] = False

        if col7.button("修改", key=f"editbtn_{rid}"):

            st.session_state[edit_key] = not st.session_state[edit_key]
            st.rerun()

        if st.session_state.get(edit_key, False):

            st.info("编辑该条记录")

            new_date = st.date_input("日期", row["date"], key=f"d_{rid}")
            new_type = st.selectbox("类型", ["收入","支出"],
                                    index=0 if row["type"]=="收入" else 1,
                                    key=f"t_{rid}")
            new_amount = st.number_input("金额", value=float(row["amount"]), key=f"a_{rid}")
            new_category = st.text_input("分类", value=row["category"], key=f"c_{rid}")
            new_note = st.text_input("备注", value=row["note"], key=f"n_{rid}")

            if st.button("保存修改", key=f"s_{rid}"):

                conn = sqlite3.connect(DB)
                c = conn.cursor()
                c.execute("""
                    UPDATE records
                    SET date=?, type=?, amount=?, category=?, note=?
                    WHERE id=?
                """, (str(new_date), new_type, float(new_amount), new_category, new_note, rid))
                conn.commit()
                conn.close()

                st.session_state[edit_key] = False
                st.success("已更新")
                st.rerun()
