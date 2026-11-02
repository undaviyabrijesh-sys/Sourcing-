import datetime as dt
from pathlib import Path

import pandas as pd
import streamlit as st

DATA = Path(__file__).parent / "data"
SAVED = DATA / "shortlist.csv"

st.set_page_config(page_title="Sourcing Radar", page_icon="🔎", layout="wide")


@st.cache_data(ttl=300)
def load_csv(name):
    p = DATA / name
    return pd.read_csv(p).fillna("") if p.exists() else None


def load_saved():
    if SAVED.exists():
        return set(pd.read_csv(SAVED)["link"].astype(str))
    return set()


tenders = load_csv("tenders.csv")
suppliers = load_csv("suppliers_who_india.csv")
report = (DATA / "run_report.txt").read_text() if (DATA / "run_report.txt").exists() else None

st.title("🔎 Sourcing Radar")
st.caption("Pharma tenders (GeM) and Indian API suppliers (WHO prequalified)")

if "saved" not in st.session_state:
    st.session_state.saved = load_saved()

tab_t, tab_s, tab_u, tab_r = st.tabs(["Tenders", "Shortlist", "Suppliers", "Status"])


def prep(df):
    df = df.copy()
    df["ends_dt"] = pd.to_datetime(df["ends"], errors="coerce")
    today = pd.Timestamp(dt.date.today())
    df["days_left"] = (df["ends_dt"] - today).dt.days
    return df[df["ends_dt"].isna() | (df["days_left"] >= 0)]


with tab_t:
    if tenders is None:
        st.info("No tenders yet. Run the GitHub Action, then refresh.")
    else:
        df = prep(tenders)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Open tenders", len(df))
        c2.metric("Close in 3 days", int((df["days_left"] <= 3).sum()))
        c3.metric("Keywords", df["keyword"].nunique())
        c4.metric("Shortlisted", len(st.session_state.saved))

        f1, f2, f3 = st.columns([2, 2, 1])
        q = f1.text_input("Search", placeholder="item, buyer…")
        kws = f2.multiselect("Keyword", sorted(df["keyword"].unique()))
        soon = f3.checkbox("Closing ≤ 7d")

        if q:
            m = df.apply(lambda r: q.lower() in " ".join(map(str, r.values)).lower(), axis=1)
            df = df[m]
        if kws:
            df = df[df["keyword"].isin(kws)]
        if soon:
            df = df[df["days_left"] <= 7]

        df = df.sort_values("ends_dt", na_position="last")
        df.insert(0, "★", df["link"].astype(str).isin(st.session_state.saved))
        show = df[["★", "item", "buyer", "ends", "days_left", "keyword", "link"]]
        edited = st.data_editor(
            show,
            hide_index=True,
            use_container_width=True,
            disabled=["item", "buyer", "ends", "days_left", "keyword", "link"],
            column_config={
                "link": st.column_config.LinkColumn("GeM", display_text="Open"),
                "days_left": st.column_config.NumberColumn("Days left"),
            },
            key="tenders_editor",
        )
        picked = set(edited.loc[edited["★"], "link"].astype(str))
        shown = set(show["link"].astype(str))
        st.session_state.saved = (st.session_state.saved - shown) | picked
        st.download_button("Download filtered CSV", show.to_csv(index=False), "tenders_filtered.csv")

with tab_s:
    if tenders is None:
        st.info("No data yet.")
    else:
        sv = tenders[tenders["link"].astype(str).isin(st.session_state.saved)]
        st.write(f"{len(sv)} shortlisted")
        st.dataframe(
            sv[["item", "buyer", "ends", "keyword", "link"]],
            hide_index=True,
            use_container_width=True,
            column_config={"link": st.column_config.LinkColumn("GeM", display_text="Open")},
        )
        st.caption("The shortlist lasts for this session. To keep it permanently, commit data/shortlist.csv to the repo.")
        if len(sv):
            st.download_button("Download shortlist.csv", sv.to_csv(index=False), "shortlist.csv")

with tab_u:
    if suppliers is None:
        st.info("No suppliers yet. Run the GitHub Action, then refresh.")
    else:
        s = st.text_input("Search suppliers")
        d = suppliers
        if s:
            d = d[d.apply(lambda r: s.lower() in " ".join(map(str, r.values)).lower(), axis=1)]
        st.write(f"{len(d)} suppliers")
        st.dataframe(d, hide_index=True, use_container_width=True)

with tab_r:
    if report:
        st.code(report, language=None)
    else:
        st.info("No run report yet. Run the workflow in the Actions tab.")
    if st.button("Reload data"):
        st.cache_data.clear()
        st.rerun()
