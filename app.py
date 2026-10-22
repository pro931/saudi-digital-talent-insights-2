import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Saudi Digital Talent Insights", page_icon="📊", layout="wide")

COLORS = {"Male": "#2a6f97", "Female": "#c8553d", "Total": "#555555"}
ICT = "Communication and Information Technology"
EDU_ORDER = ["Upper secondary education", "Short-cycle tertiary education",
             "Bachelor’s or equivalent level", "Master’s or equivalent level",
             "Doctoral or equivalent level"]
EDU_LABELS = dict(zip(EDU_ORDER, ["Secondary", "Diploma", "Bachelor", "Master", "PhD"]))


@st.cache_data
def load_data():
    return pd.read_csv("labor_market_clean.csv")


df = load_data()


def get_table(keywords, **filters):
    d = df[df["Table_Title"].str.contains(keywords, regex=True)]
    for col, val in filters.items():
        d = d[d[col] == val]
    return d


def style(fig, height=420):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=50, b=10),
                      legend_title_text="", plot_bgcolor="rgba(0,0,0,0)",
                      hovermode="x unified")
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.2)")
    return fig


st.sidebar.header("Filters")
nationality = st.sidebar.selectbox("Nationality", ["Saudi", "Non Saudi", "Total"])
sexes = st.sidebar.multiselect("Sex", ["Male", "Female", "Total"], default=["Male", "Female", "Total"])
if not sexes:
    st.warning("اختاري جنس واحد على الأقل من القائمة الجانبية")
    st.stop()
st.sidebar.caption("Source: GASTAT – Labour Market Statistics, Q2 2022–2026")

st.title("📊 Saudi Digital Talent Insights")
st.caption(f"Labour market indicators · Nationality: **{nationality}**")

unemp_q = get_table("quarterly unemployment rate", Nationality=nationality, Sex="Total").sort_values("Category")
lfpr_q = get_table("quarterly labor force participation", Nationality=nationality, Sex="Total").sort_values("Category")
spec = get_table("unemployment rate for holders", Nationality=nationality)
wages = get_table("wages.*education", Nationality=nationality)

last_q, prev_q = unemp_q["Category"].iloc[-1], unemp_q["Category"].iloc[-5]
latest_year = int(spec["File_Year"].max())


def kpi(series_df, period, prev_period):
    s = series_df.set_index("Category")["Value"]
    return s.get(period), s.get(period) - s.get(prev_period)


k1, k2, k3, k4 = st.columns(4)
u, du = kpi(unemp_q, last_q, prev_q)
k1.metric(f"Unemployment rate ({last_q})", f"{u:.1f}%", f"{du:+.1f} pts YoY", delta_color="inverse")
p, dp = kpi(lfpr_q, last_q, prev_q)
k2.metric(f"Participation rate ({last_q})", f"{p:.1f}%", f"{dp:+.1f} pts YoY")
ict = spec[(spec["Category"] == ICT) & (spec["Sex"] == "Total")].set_index("File_Year")["Value"]
k3.metric(f"ICT graduates unemployment ({latest_year})", f"{ict[latest_year]:.1f}%",
          f"{ict[latest_year] - ict[latest_year - 1]:+.1f} pts YoY", delta_color="inverse")
bach = wages[(wages["Category"] == EDU_ORDER[2]) & (wages["Sex"] == "Total")].set_index("File_Year")["Value"]
k4.metric(f"Avg wage – Bachelor ({latest_year})", f"{bach[latest_year]:,.0f} SAR",
          f"{(bach[latest_year] / bach[latest_year - 1] - 1) * 100:+.1f}% YoY")

st.divider()

tab1, tab2, tab3, tab4 = st.tabs(["📈 Trends", "🎓 Fields of study", "💰 Wages", "🔎 Explore all tables"])

with tab1:
    metric = st.radio("Indicator", ["Unemployment rate", "Participation rate"], horizontal=True)
    kw = "quarterly unemployment rate" if metric == "Unemployment rate" else "quarterly labor force participation"
    d = get_table(kw, Nationality=nationality)
    d = d[d["Sex"].isin(sexes)].sort_values("Category")
    fig = px.line(d, x="Category", y="Value", color="Sex", markers=True, color_discrete_map=COLORS,
                  labels={"Category": "Quarter", "Value": "%"},
                  title=f"{metric} by quarter – {nationality}")
    st.plotly_chart(style(fig), use_container_width=True)

    gap = d.pivot_table(index="Category", columns="Sex", values="Value")
    if {"Male", "Female"} <= set(gap.columns):
        gap["Gap (F − M)"] = gap["Female"] - gap["Male"]
        fig = px.bar(gap.reset_index(), x="Category", y="Gap (F − M)",
                     title="Gender gap (Female − Male, percentage points)",
                     labels={"Category": "Quarter"}, color_discrete_sequence=["#c8553d"])
        st.plotly_chart(style(fig, 320), use_container_width=True)

with tab2:
    years = sorted(spec["File_Year"].unique())
    c1, c2 = st.columns([1, 2])
    with c1:
        year = st.select_slider("Year (Q2)", options=years, value=years[-1])
        sex_one = st.radio("Sex", ["Total", "Male", "Female"], horizontal=True, key="sex_spec")
    d = (spec[(spec["File_Year"] == year) & (spec["Sex"] == sex_one) &
              (spec["Category"] != "Unknown programs")].sort_values("Value"))
    d["Highlight"] = d["Category"].eq(ICT).map({True: "ICT", False: "Other"})
    fig = px.bar(d, x="Value", y="Category", orientation="h", color="Highlight", text_auto=".1f",
                 color_discrete_map={"ICT": "#c8553d", "Other": "#b0b7c0"},
                 labels={"Value": "Unemployment rate (%)", "Category": ""},
                 title=f"Unemployment by field of study – {nationality}, {sex_one}, Q2 {year}")
    fig.update_layout(showlegend=False)
    with c2:
        st.plotly_chart(style(fig, 460), use_container_width=True)

    fields = sorted(spec["Category"].unique())
    chosen = st.multiselect("Compare fields over time", fields,
                            default=[ICT, "Business, Management and Law", "Engineering, manufacturing and Building"])
    d = spec[spec["Category"].isin(chosen) & (spec["Sex"] == sex_one)].sort_values("File_Year")
    fig = px.line(d, x="File_Year", y="Value", color="Category", markers=True,
                  labels={"File_Year": "Year (Q2)", "Value": "%"},
                  title="Unemployment rate trend by field")
    fig.update_xaxes(dtick=1)
    st.plotly_chart(style(fig), use_container_width=True)

with tab3:
    years_w = sorted(wages["File_Year"].unique())
    year_w = st.select_slider("Year (Q2)", options=years_w, value=years_w[-1], key="year_w")
    d = wages[(wages["File_Year"] == year_w) & wages["Category"].isin(EDU_ORDER) & wages["Sex"].isin(sexes)].copy()
    d["Education"] = pd.Categorical(d["Category"].map(EDU_LABELS), list(EDU_LABELS.values()), ordered=True)
    d = d.sort_values("Education")
    fig = px.bar(d, x="Education", y="Value", color="Sex", barmode="group", color_discrete_map=COLORS,
                 text_auto=",.0f", labels={"Value": "SAR / month", "Education": ""},
                 title=f"Average monthly wage by education – {nationality}, Q2 {year_w}")
    st.plotly_chart(style(fig), use_container_width=True)

    d = wages[wages["Category"].isin(EDU_ORDER) & (wages["Sex"] == "Total")].copy()
    d["Education"] = d["Category"].map(EDU_LABELS)
    fig = px.line(d.sort_values("File_Year"), x="File_Year", y="Value", color="Education", markers=True,
                  labels={"File_Year": "Year (Q2)", "Value": "SAR / month"},
                  title="Average wage trend by education (Total)")
    fig.update_xaxes(dtick=1)
    st.plotly_chart(style(fig), use_container_width=True)

with tab4:
    st.caption("اختاري أي جدول من الـ 43 جدول وشوفي بياناته")
    titles = sorted(df["Table_Title"].unique())
    title = st.selectbox("Table", titles)
    d = df[(df["Table_Title"] == title) & (df["Nationality"] == nationality) & df["Sex"].isin(sexes)]
    if d.empty:
        available = ", ".join(df.loc[df["Table_Title"] == title, "Nationality"].unique())
        st.info(f"هذا الجدول متاح فقط لـ: {available} — غيّري الجنسية من القائمة الجانبية")
        st.stop()
    if d["Quarter"].isna().all():
        yrs = sorted(d["File_Year"].unique())
        y = st.select_slider("Year (Q2)", options=yrs, value=yrs[-1], key="year_x")
        d = d[d["File_Year"] == y]
    breakdowns = d["Column_Breakdown"].unique()
    if len(breakdowns) > 1:
        b = st.selectbox("Breakdown", breakdowns)
        d = d[d["Column_Breakdown"] == b]
    unit = d["Unit"].iloc[0] if len(d) else ""
    if len(d):
        is_ts = d["Quarter"].notna().all()
        if is_ts:
            fig = px.line(d.sort_values("Category"), x="Category", y="Value", color="Sex", markers=True,
                          color_discrete_map=COLORS, labels={"Category": "", "Value": unit})
        else:
            fig = px.bar(d, x="Value", y="Category", color="Sex", barmode="group", orientation="h",
                         color_discrete_map=COLORS, labels={"Category": "", "Value": unit})
            fig.update_layout(height=max(400, 30 * d["Category"].nunique()))
        st.plotly_chart(style(fig, fig.layout.height or 420), use_container_width=True)
        table = d.pivot_table(index="Category", columns="Sex", values="Value", sort=False)
        st.dataframe(table, use_container_width=True)
        st.download_button("⬇️ Download CSV", d.to_csv(index=False).encode("utf-8-sig"),
                           file_name="table.csv", mime="text/csv")
    else:
        st.info("ما فيه بيانات لهذا الاختيار")
