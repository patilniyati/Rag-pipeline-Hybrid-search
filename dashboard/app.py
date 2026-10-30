import os
import re

import requests
import streamlit as st
import html as _html

from styles import card, inject
from styles import card, hero, inject

API_URL = os.getenv("API_URL", "http://localhost:8000")
HEADERS = {"X-API-Key": os.environ["API_KEY"]} if os.getenv("API_KEY") else {}
ICON = {"verified": "✅", "partial": "🟡", "unsupported": "❌", "uncited": "⚪"}

st.set_page_config(page_title="Subtext RAG", layout="wide")
inject()


def api(method, path, payload=None):
    try:
        r = requests.request(method, API_URL + path, json=payload, headers=HEADERS, timeout=300)
    except requests.RequestException as e:
        st.error(f"Cannot reach the API at {API_URL}: {e}")
        st.stop()
    if not r.ok:
        try:
            detail = r.json().get("detail", r.text)
        except ValueError:
            detail = r.text
        st.error(f"API error {r.status_code}: {detail}")
        st.stop()
    return r.json()


def fmt(v):
    return "–" if v is None else f"{v:.2f}"


def linkify(text):
    return re.sub(r"\[(\d+)\]", r"[[\1]](#source-\1)", text)      # [2] links to chunk 2

def linkify_html(text):
    safe = _html.escape(text)                      # escape first, then add our own links
    return re.sub(r"\[(\d+)\]", r'<a href="#source-\1">[\1]</a>', safe).replace("\n", "<br>")


# ---- sidebar
health = api("get", "/v1/health")
st.sidebar.title("Docs RAG")
if health["status"] != "ok":
    st.sidebar.warning("Some indexes are unreachable.")
strategy = st.sidebar.selectbox("Chunking strategy", list(health["strategies"]))
rerank = st.sidebar.checkbox("Apply reranker", value=True)
compare = st.sidebar.checkbox("Compare hybrid vs dense-only retrieval")
with st.sidebar.expander("Indexed documents"):
    docs = api("get", "/v1/documents?limit=200")
    st.caption(f"{docs['total']} documents")
    st.dataframe(docs["items"], hide_index=True)

# ---- ask (result kept in session_state, so toggling never re-calls the LLM)
hero("Welcome to Subtext!", "Ask anything about your documents and get answers with verified citations.")
with st.form("ask", border=False):
    question = st.text_input("Question", placeholder="Ask a question about your documents...",
                             label_visibility="collapsed")
    submitted = st.form_submit_button("Ask")

if submitted and question.strip():
    with st.spinner("Retrieving, generating and checking citations..."):
        st.session_state["result"] = api("post", "/v1/ask",
                                         {"question": question, "strategy": strategy})
    st.session_state.update(question=question, strategy=strategy)

res = st.session_state.get("result")
if not res:
    st.info("Ask a question to begin.")
    st.stop()

# ---- answer
st.markdown("### Answer")
if res["status"] == "answered":
    st.markdown(f'<div class="glass">{linkify_html(res["answer"])}</div>', unsafe_allow_html=True)
else:
    st.warning(res["answer"])
    st.write(res["not_found"])
    for f in res["found"]:
        st.caption(f"Closest: {f['source']} · {f['heading']} (relevance {f['relevance']})")
    if res["suggested_documents"]:
        st.write("Worth checking manually: " + ", ".join(res["suggested_documents"]))
st.caption(f"strategy `{res['strategy']}` · mode `{res['mode']}` · {res['latency_ms']} ms")

# ---- confidence by dimension
st.markdown("### Confidence")
c = res["confidence"]
for col, (label, key) in zip(st.columns(4), [("Retrieval", "retrieval"),
                                             ("Citation coverage", "citation_coverage"),
                                             ("Completeness", "completeness"),
                                             ("Composite", "composite")]):
    col.metric(label, fmt(c.get(key)))
    if c.get(key) is not None:
        col.progress(min(max(c[key], 0.0), 1.0))
if c.get("missing_parts"):
    st.caption("Not covered: " + "; ".join(c["missing_parts"]))

# ---- citation checks
if res["citations"]:
    st.markdown("### Citation checks")
    for item in res["citations"]:
        reasons = " · ".join(f"[{k['n']}] {k['verdict']}: {k.get('reason', '')}" for k in item["checks"])
        card(f"{ICON.get(item['status'], '⚪')} {item['status']}: {item['claim']}", reasons)

# ---- retrieved chunks, ranked
cited = {n for item in res["citations"] for n in item["cites"]}
st.markdown("### Retrieved chunks (ranked by relevance)")
for s in res["sources"]:
    where = f"page {s['page']} · " if s["page"] else ""
    meta = (f"{where}{s['heading']} · rerank {fmt(s['rerank_score'])} · fused {fmt(s['fused_score'])} · "
            f"dense #{s['dense_rank'] or '–'} · sparse #{s['sparse_rank'] or '–'}")
    card(f"[{s['n']}] {s['source']}" + ("  ·  cited" if s["n"] in cited else ""),
         meta, s["text"], cited=s["n"] in cited, anchor=f"source-{s['n']}")

# ---- hybrid vs dense-only (retrieval only, no LLM cost)
if compare:
    st.markdown("### Hybrid vs dense-only retrieval")
    key = (st.session_state["question"], st.session_state["strategy"], rerank)
    if st.session_state.get("cmp_key") != key:
        st.session_state["cmp"] = {
            m: api("post", "/v1/search", {"question": key[0], "strategy": key[1],
                                          "mode": m, "rerank": rerank})
            for m in ("hybrid", "dense")}
        st.session_state["cmp_key"] = key
    cmp = st.session_state["cmp"]
    ids = {m: {r["chunk_id"] for r in cmp[m]["results"]} for m in cmp}
    for col, m, other in zip(st.columns(2), ("hybrid", "dense"), ("dense", "hybrid")):
        col.markdown(f"**{m}** · {cmp[m]['latency_ms']} ms")
        for rank, r in enumerate(cmp[m]["results"], 1):
            tag = "" if r["chunk_id"] in ids[other] else "  🆕 only here"
            col.markdown(f"{rank}. `{r['source']}` {r['heading']}{tag}")
            col.caption(f"rerank {fmt(r['rerank_score'])} · dense #{r['dense_rank'] or '–'} "
                        f"· sparse #{r['sparse_rank'] or '–'}")
    st.caption(f"Overlap: {len(ids['hybrid'] & ids['dense'])} of {len(ids['hybrid'])} chunks")