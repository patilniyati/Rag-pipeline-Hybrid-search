import html

import streamlit as st

CSS = """


<style>
:root {
  --navy: #101D2C;
  --teal: #238C87;
  --sky: #8CCFE5;
  --beige: #E8DCC5;
  --muted: #B3C3CC;
}

/* Background */
.stApp {
  background-color: var(--navy);
  background-image:
    radial-gradient(
      650px circle at 12% 8%,
      rgba(35,140,135,.25),
      transparent 60%
    ),
    radial-gradient(
      550px circle at 88% 28%,
      rgba(140,207,229,.17),
      transparent 60%
    ),
    radial-gradient(
      700px circle at 50% 100%,
      rgba(232,220,197,.09),
      transparent 60%
    );
  background-attachment: fixed;
  color: var(--beige);
}

[data-testid="stHeader"] {
  background: transparent;
}

.block-container {
  padding-top: 2rem;
  max-width: 1200px;
}

/* Sidebar */
[data-testid="stSidebar"] {
  background: rgba(16,29,44,.72);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  border-right: 1px solid rgba(140,207,229,.14);
}

/* Inputs */
.stTextInput input,
.stTextArea textarea {
  background: rgba(255,255,255,.07) !important;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(140,207,229,.22) !important;
  border-radius: 12px !important;
  color: var(--beige) !important;
  padding: 12px 14px !important;
}

.stTextInput input:focus,
.stTextArea textarea:focus {
  border-color: var(--sky) !important;
  box-shadow: 0 0 0 3px rgba(140,207,229,.18) !important;
}

/* Ask form */
[data-testid="stForm"] {
  background: rgba(255,255,255,.055);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(140,207,229,.17);
  border-radius: 16px;
  padding: 1.2rem;
}

/* Buttons */
.stButton > button,
[data-testid="stFormSubmitButton"] > button {
  background: linear-gradient(
    135deg,
    var(--teal),
    #347D9D
  );
  color: #FFFFFF;
  border: 1px solid rgba(140,207,229,.25);
  border-radius: 12px;
  padding: .55rem 1.4rem;
  font-weight: 600;
  transition: all .2s ease;
}

.stButton > button:hover,
[data-testid="stFormSubmitButton"] > button:hover {
  background: var(--sky);
  color: var(--navy);
  border-color: var(--sky);
}

/* Metrics */
[data-testid="stMetric"] {
  background: rgba(255,255,255,.07);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border: 1px solid rgba(140,207,229,.16);
  border-radius: 14px;
  padding: 14px 16px;
}

[data-testid="stMetricValue"] {
  color: var(--beige);
}

[data-testid="stMetricLabel"] {
  color: var(--muted);
}

/* Glass cards */
.glass {
  background: rgba(255,255,255,.065);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(140,207,229,.17);
  border-radius: 14px;
  padding: 14px 18px;
  margin: 10px 0;
  box-shadow: 0 8px 28px rgba(0,0,0,.18);
}

.glass.cited {
  border-left: 4px solid var(--teal);
}

.glass .title {
  color: var(--beige);
  font-weight: 600;
  font-size: 1.02rem;
}

.glass .meta {
  color: var(--muted);
  font-size: .8rem;
  margin: 2px 0 8px;
}

.glass pre {
  white-space: pre-wrap;
  margin: 0;
  color: #D6E3E9;
  font-size: .85rem;
  font-family: inherit;
}

.glass a {
  color: var(--sky);
}

/* Hero */
.hero {
  text-align: center;
  padding: 2.2rem 0 1.2rem;
}

.hero h1 {
  font-size: 2.8rem;
  font-weight: 700;
  margin: 0;
  background: linear-gradient(
    135deg,
    var(--beige),
    var(--sky) 55%,
    var(--teal)
  );
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.hero p {
  color: var(--muted);
  font-size: 1.05rem;
  margin: .5rem 0 0;
}

/* Chat messages */
[data-testid="stChatMessage"] {
  background: rgba(255,255,255,.06);
  backdrop-filter: blur(14px);
  border: 1px solid rgba(140,207,229,.16);
  border-radius: 14px;
}

/* Dividers */
hr {
  border-color: rgba(140,207,229,.16);
}

/* Links */
a {
  color: var(--sky);
}

/* Scrollbar */
::-webkit-scrollbar {
  width: 6px;
}

::-webkit-scrollbar-thumb {
  background: var(--teal);
  border-radius: 10px;
}
</style>
"""


def inject():
    st.markdown(CSS, unsafe_allow_html=True)


def card(title: str, meta: str = "", body: str = "", cited: bool = False, anchor: str = ""):
    """All text is escaped: document text must never be rendered as HTML."""
    box_id = f' id="{html.escape(anchor)}"' if anchor else ""
    cls = "glass cited" if cited else "glass"
    meta_html = f'<div class="meta">{html.escape(meta)}</div>' if meta else ""
    body_html = f"<pre>{html.escape(body)}</pre>" if body else ""
    st.markdown(f'<div class="{cls}"{box_id}><div class="title">{html.escape(title)}</div>'
                f"{meta_html}{body_html}</div>", unsafe_allow_html=True)

def hero(name: str, tagline: str):
    st.markdown(f'<div class="hero"><h1>{html.escape(name)}</h1>'
                f'<p>{html.escape(tagline)}</p></div>', unsafe_allow_html=True)