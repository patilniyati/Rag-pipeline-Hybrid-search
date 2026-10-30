import html

import streamlit as st

CSS = """
<style>
.stApp {
  background-color: #0b1020;
  background-image:
    radial-gradient(600px circle at 12% 8%,  rgba(99,102,241,.35), transparent 60%),
    radial-gradient(520px circle at 88% 28%, rgba(236,72,153,.22), transparent 60%),
    radial-gradient(700px circle at 50% 100%, rgba(20,184,166,.20), transparent 60%);
  background-attachment: fixed;
}
[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2rem; max-width: 1200px; }

/* sidebar */
[data-testid="stSidebar"] {
  background: rgba(255,255,255,.04);
  backdrop-filter: blur(16px);
  border-right: 1px solid rgba(255,255,255,.08);
}

/* input boxes */
.stTextInput input, .stTextArea textarea {
  background: rgba(255,255,255,.07) !important;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255,255,255,.18) !important;
  border-radius: 12px !important;
  color: #fff !important;
  padding: 12px 14px !important;
}
.stTextInput input:focus { border-color: #818cf8 !important; box-shadow: 0 0 0 3px rgba(129,140,248,.25) !important; }

/* the ask form */
[data-testid="stForm"] {
  background: rgba(255,255,255,.05);
  backdrop-filter: blur(14px);
  border: 1px solid rgba(255,255,255,.12);
  border-radius: 16px;
  padding: 1.2rem;
}

/* buttons */
.stButton > button, [data-testid="stFormSubmitButton"] > button {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff; border: 0; border-radius: 12px; padding: .55rem 1.4rem; font-weight: 600;
}
.stButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover { filter: brightness(1.12); }

/* metric tiles */
[data-testid="stMetric"] {
  background: rgba(255,255,255,.06);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,.12);
  border-radius: 14px;
  padding: 14px 16px;
}

/* glass cards for answer, citations and chunks */
.glass {
  background: rgba(255,255,255,.06);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border: 1px solid rgba(255,255,255,.14);
  border-radius: 14px;
  padding: 14px 18px;
  margin: 10px 0;
  box-shadow: 0 8px 28px rgba(0,0,0,.28);
}
.glass.cited { border-left: 4px solid #34d399; }
.glass .title { font-weight: 600; font-size: 1.02rem; }
.glass .meta  { color: #9ca3af; font-size: .8rem; margin: 2px 0 8px; }
.glass pre    { white-space: pre-wrap; margin: 0; color: #d1d5db; font-size: .85rem; font-family: inherit; }
.glass a { color: #a5b4fc; }

.hero { text-align: center; padding: 2.2rem 0 1.2rem; }
.hero h1 {
  font-size: 2.8rem; font-weight: 700; margin: 0;
  background: linear-gradient(135deg, #c7d2fe, #818cf8 45%, #f0abfc);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.hero p { color: #9ca3af; font-size: 1.05rem; margin: .5rem 0 0; }
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