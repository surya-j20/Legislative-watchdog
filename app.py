import streamlit as st
from supabase import create_client
from sentence_transformers import SentenceTransformer
import os

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Legislative Watchdog",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styling ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #0d0f12;
    color: #e8e4dc;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #13161b;
    border-right: 1px solid #1f2430;
}
section[data-testid="stSidebar"] * {
    color: #e8e4dc !important;
}

/* Header */
.watchdog-header {
    padding: 2rem 0 1.5rem 0;
    border-bottom: 1px solid #1f2430;
    margin-bottom: 2rem;
}
.watchdog-title {
    font-family: 'Playfair Display', serif;
    font-size: 2.6rem;
    font-weight: 700;
    color: #f0ebe0;
    letter-spacing: -0.5px;
    margin: 0;
    line-height: 1.1;
}
.watchdog-subtitle {
    font-size: 0.9rem;
    color: #6b7280;
    margin-top: 0.4rem;
    font-weight: 300;
    letter-spacing: 0.3px;
}

/* Search box */
.stTextInput > div > div > input {
    background-color: #13161b !important;
    border: 1px solid #2a2f3d !important;
    border-radius: 8px !important;
    color: #e8e4dc !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.95rem !important;
    padding: 0.7rem 1rem !important;
}
.stTextInput > div > div > input:focus {
    border-color: #c9a84c !important;
    box-shadow: 0 0 0 2px rgba(201,168,76,0.15) !important;
}

/* Bill card */
.bill-card {
    background: #13161b;
    border: 1px solid #1f2430;
    border-radius: 12px;
    padding: 1.5rem 1.8rem;
    margin-bottom: 1.2rem;
    transition: border-color 0.2s ease;
    position: relative;
    overflow: hidden;
}
.bill-card:hover {
    border-color: #c9a84c;
}
.bill-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 3px; height: 100%;
    background: linear-gradient(180deg, #c9a84c, #8b6914);
    opacity: 0;
    transition: opacity 0.2s;
}
.bill-card:hover::before {
    opacity: 1;
}

.bill-title {
    font-family: 'Playfair Display', serif;
    font-size: 1.15rem;
    font-weight: 600;
    color: #f0ebe0;
    margin-bottom: 0.5rem;
    line-height: 1.4;
}
.bill-meta {
    display: flex;
    gap: 1rem;
    align-items: center;
    margin-bottom: 0.9rem;
    flex-wrap: wrap;
}
.bill-stage {
    font-size: 0.75rem;
    font-weight: 500;
    color: #c9a84c;
    background: rgba(201,168,76,0.1);
    border: 1px solid rgba(201,168,76,0.25);
    padding: 0.2rem 0.65rem;
    border-radius: 20px;
    letter-spacing: 0.3px;
}
.bill-date {
    font-size: 0.78rem;
    color: #6b7280;
}
.bill-summary {
    font-size: 0.875rem;
    color: #9ca3af;
    line-height: 1.65;
    margin-bottom: 1rem;
    font-weight: 300;
}
.bill-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin-bottom: 0.9rem;
}
.bill-tag {
    font-size: 0.7rem;
    font-weight: 500;
    color: #6b8cba;
    background: rgba(107,140,186,0.1);
    border: 1px solid rgba(107,140,186,0.2);
    padding: 0.15rem 0.55rem;
    border-radius: 20px;
    letter-spacing: 0.4px;
    text-transform: uppercase;
}
.bill-pdf-link a {
    font-size: 0.8rem;
    color: #c9a84c;
    text-decoration: none;
    font-weight: 500;
    letter-spacing: 0.2px;
}
.bill-pdf-link a:hover {
    text-decoration: underline;
}

/* Stats bar */
.stats-bar {
    display: flex;
    gap: 2rem;
    padding: 0.9rem 1.2rem;
    background: #13161b;
    border: 1px solid #1f2430;
    border-radius: 8px;
    margin-bottom: 1.5rem;
}
.stat-item {
    text-align: center;
}
.stat-value {
    font-family: 'Playfair Display', serif;
    font-size: 1.4rem;
    font-weight: 700;
    color: #c9a84c;
}
.stat-label {
    font-size: 0.72rem;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.6px;
}

/* Selectbox and multiselect */
.stSelectbox > div > div,
.stMultiSelect > div > div {
    background-color: #13161b !important;
    border-color: #2a2f3d !important;
    color: #e8e4dc !important;
}

/* No results */
.no-results {
    text-align: center;
    padding: 3rem;
    color: #6b7280;
    font-size: 0.9rem;
}

/* Divider */
hr {
    border-color: #1f2430 !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0d0f12; }
::-webkit-scrollbar-thumb { background: #2a2f3d; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)


# ── Supabase client ─────────────────────────────────────────────────────────────
@st.cache_resource
def get_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(url, key)


@st.cache_resource
def get_model():
    return SentenceTransformer("all-MiniLM-L6-v2")


supabase = get_supabase()
model = get_model()


# ── Data helpers ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def get_all_tags():
    rows = supabase.table("uk_bills_main") \
        .select("industry_tags") \
        .not_.is_("industry_tags", None) \
        .execute()
    tags = set()
    for row in rows.data:
        if row["industry_tags"]:
            tags.update(row["industry_tags"])
    return sorted(tags)


@st.cache_data(ttl=300)
def get_all_stages():
    rows = supabase.table("uk_bills_main") \
        .select("current_stage") \
        .not_.is_("current_stage", None) \
        .execute()
    stages = sorted({r["current_stage"] for r in rows.data if r["current_stage"]})
    return stages


@st.cache_data(ttl=300)
def get_stats():
    total = supabase.table("uk_bills_main").select("bill_id", count="exact").execute()
    summarised = supabase.table("uk_bills_main").select("bill_id", count="exact") \
        .not_.is_("summary", None).execute()
    tagged = supabase.table("uk_bills_main").select("bill_id", count="exact") \
        .not_.is_("industry_tags", None).execute()
    return total.count or 0, summarised.count or 0, tagged.count or 0


def semantic_search(query: str, tag_filter: list, stage_filter: str, limit: int = 20):
    embedding = model.encode(query).tolist()
    result = supabase.rpc("search_bills", {
        "query_embedding": embedding,
        "match_count": 50
    }).execute()

    bills = result.data or []

    if tag_filter:
        bills = [
            b for b in bills
            if b.get("industry_tags") and any(t in b["industry_tags"] for t in tag_filter)
        ]
    if stage_filter and stage_filter != "All":
        bills = [b for b in bills if b.get("current_stage") == stage_filter]

    return bills[:limit]


def get_bills(tag_filter: list, stage_filter: str, limit: int = 30):
    query = supabase.table("uk_bills_main") \
        .select("bill_id, title, summary, current_stage, introduced_date, industry_tags, pdf_public_url") \
        .not_.is_("summary", None) \
        .order("bill_id", desc=True)

    if stage_filter and stage_filter != "All":
        query = query.eq("current_stage", stage_filter)

    result = query.limit(100).execute()
    bills = result.data or []

    if tag_filter:
        bills = [
            b for b in bills
            if b.get("industry_tags") and any(t in b["industry_tags"] for t in tag_filter)
        ]

    return bills[:limit]


# ── Render bill card ────────────────────────────────────────────────────────────
def render_bill(bill):
    title = bill.get("title") or "Untitled Bill"
    summary = bill.get("summary") or ""
    stage = bill.get("current_stage") or ""
    date = bill.get("introduced_date") or ""
    tags = bill.get("industry_tags") or []
    pdf_url = bill.get("pdf_public_url") or ""

    short_summary = summary[:400] + "..." if len(summary) > 400 else summary

    tags_html = "".join(f'<span class="bill-tag">{t.replace("_", " ")}</span>' for t in tags)
    pdf_html = f'<div class="bill-pdf-link"><a href="{pdf_url}" target="_blank">📄 View PDF →</a></div>' if pdf_url else ""
    stage_html = f'<span class="bill-stage">{stage}</span>' if stage else ""
    date_html = f'<span class="bill-date">{date}</span>' if date else ""

    st.markdown(f"""
    <div class="bill-card">
        <div class="bill-title">{title}</div>
        <div class="bill-meta">
            {stage_html}
            {date_html}
        </div>
        <div class="bill-summary">{short_summary}</div>
        <div class="bill-tags">{tags_html}</div>
        {pdf_html}
    </div>
    """, unsafe_allow_html=True)


# ── Sidebar ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding: 1rem 0 1.5rem 0; border-bottom: 1px solid #1f2430; margin-bottom: 1.5rem;">
        <div style="font-family: 'Playfair Display', serif; font-size: 1.1rem; color: #f0ebe0; font-weight: 600;">⚖️ Filters</div>
    </div>
    """, unsafe_allow_html=True)

    all_tags = get_all_tags()
    selected_tags = st.multiselect(
        "Industry Tags",
        options=all_tags,
        default=[],
        format_func=lambda x: x.replace("_", " ").title()
    )

    all_stages = ["All"] + get_all_stages()
    selected_stage = st.selectbox("Bill Stage", options=all_stages)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size: 0.72rem; color: #4b5563; text-transform: uppercase; letter-spacing: 0.6px;">
        Data refreshes every 5 minutes
    </div>
    """, unsafe_allow_html=True)


# ── Main ─────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="watchdog-header">
    <div class="watchdog-title">Legislative Watchdog</div>
    <div class="watchdog-subtitle">UK Parliament Bills — Plain English Summaries & Industry Intelligence</div>
</div>
""", unsafe_allow_html=True)

# Stats
total, summarised, tagged = get_stats()
st.markdown(f"""
<div class="stats-bar">
    <div class="stat-item">
        <div class="stat-value">{total}</div>
        <div class="stat-label">Bills Tracked</div>
    </div>
    <div class="stat-item">
        <div class="stat-value">{summarised}</div>
        <div class="stat-label">Summarised</div>
    </div>
    <div class="stat-item">
        <div class="stat-value">{tagged}</div>
        <div class="stat-label">Tagged</div>
    </div>
</div>
""", unsafe_allow_html=True)

# Search
search_query = st.text_input(
    "",
    placeholder="🔍  Search bills semantically — e.g. 'data privacy rules for businesses'",
    label_visibility="collapsed"
)

st.markdown("<br>", unsafe_allow_html=True)

# Results
if search_query.strip():
    with st.spinner("Searching..."):
        bills = semantic_search(search_query, selected_tags, selected_stage)
    st.markdown(f"<div style='font-size:0.8rem; color:#6b7280; margin-bottom:1rem;'>{len(bills)} results for <em>\"{search_query}\"</em></div>", unsafe_allow_html=True)
else:
    bills = get_bills(selected_tags, selected_stage)
    st.markdown(f"<div style='font-size:0.8rem; color:#6b7280; margin-bottom:1rem;'>Showing {len(bills)} most recent bills</div>", unsafe_allow_html=True)

if bills:
    for bill in bills:
        render_bill(bill)
else:
    st.markdown("""
    <div class="no-results">
        <div style="font-size: 2rem; margin-bottom: 0.5rem;">🔎</div>
        <div>No bills found matching your criteria.</div>
    </div>
    """, unsafe_allow_html=True)