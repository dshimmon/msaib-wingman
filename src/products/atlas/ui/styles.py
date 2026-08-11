"""Atlas-scoped responsive Streamlit styles."""

ATLAS_STYLES = """
<style>
:root {
  --atlas-ink: #16253a;
  --atlas-muted: #526278;
  --atlas-navy: #12345b;
  --atlas-blue: #1464a5;
  --atlas-sky: #eaf4fb;
  --atlas-cloud: #f5f8fb;
  --atlas-line: #cbd7e3;
  --atlas-success: #17633a;
  --atlas-warning: #7a4d00;
  --atlas-danger: #a1262f;
  --atlas-radius: 0.9rem;
}

[data-testid="stAppViewContainer"] {
  background: linear-gradient(180deg, #f7fafc 0%, #ffffff 18rem);
  color: var(--atlas-ink);
}

[data-testid="stMainBlockContainer"] {
  max-width: 1180px;
  padding-top: 2rem;
  padding-bottom: 5rem;
}

[data-testid="stSidebar"] {
  border-right: 1px solid var(--atlas-line);
  background: #f4f8fc;
}

[data-testid="stSidebar"] [role="radiogroup"] label p,
[data-testid="stSidebar"] [data-testid="stAlert"] p,
[data-testid="stMetricLabel"] p,
[data-testid="stMetricValue"] {
  color: var(--atlas-ink) !important;
  opacity: 1 !important;
}

[data-testid="stSidebar"] [role="radiogroup"] label {
  min-height: 2.5rem;
}

.atlas-brand {
  border-radius: var(--atlas-radius);
  background: linear-gradient(145deg, #12345b, #185888);
  color: #ffffff;
  padding: 1rem;
  margin-bottom: 1rem;
}

.atlas-brand__eyebrow,
.atlas-eyebrow {
  font-size: 0.76rem;
  font-weight: 750;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.atlas-brand__name {
  font-size: 1.35rem;
  font-weight: 760;
  line-height: 1.2;
  margin-top: 0.2rem;
}

.atlas-hero {
  border: 1px solid var(--atlas-line);
  border-radius: 1.15rem;
  background: linear-gradient(135deg, #ffffff 5%, #eaf4fb 100%);
  padding: clamp(1.15rem, 3vw, 2rem);
  margin: 0 0 1.25rem;
  box-shadow: 0 12px 34px rgba(18, 52, 91, 0.08);
}

.atlas-hero h1 {
  color: var(--atlas-navy);
  font-size: clamp(2rem, 5vw, 3.3rem);
  line-height: 1.05;
  margin: 0.25rem 0 0.65rem;
}

.atlas-hero p {
  color: var(--atlas-muted);
  font-size: 1.02rem;
  line-height: 1.6;
  margin: 0;
  max-width: 48rem;
}

.atlas-status {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  border: 1px solid var(--atlas-line);
  border-radius: 999px;
  color: var(--atlas-ink);
  background: #ffffff;
  font-size: 0.78rem;
  font-weight: 700;
  line-height: 1;
  padding: 0.4rem 0.65rem;
  margin-right: 0.35rem;
  margin-bottom: 0.35rem;
}

.atlas-status--success { border-color: #82bb9b; color: var(--atlas-success); }
.atlas-status--warning { border-color: #ddb96d; color: var(--atlas-warning); }
.atlas-status--danger { border-color: #e2a0a6; color: var(--atlas-danger); }
.atlas-status--neutral { color: var(--atlas-muted); }

.atlas-kicker {
  color: var(--atlas-blue);
  font-weight: 700;
  margin-bottom: 0.25rem;
}

.atlas-provenance {
  border-left: 4px solid var(--atlas-blue);
  color: var(--atlas-muted);
  padding: 0.2rem 0 0.2rem 0.85rem;
  margin: 0.5rem 0 1rem;
}

.stButton > button,
.stDownloadButton > button,
[data-testid="stLinkButton"] a {
  border-radius: 0.65rem;
  min-height: 2.65rem;
  font-weight: 680;
}

.stButton > button[kind="primary"],
.stDownloadButton > button[kind="primary"],
[data-testid="stLinkButton"] a[kind="primary"] {
  background: var(--atlas-navy);
  border-color: var(--atlas-navy);
  color: #ffffff;
}

.stButton > button[kind="primary"]:hover,
.stDownloadButton > button[kind="primary"]:hover,
[data-testid="stLinkButton"] a[kind="primary"]:hover {
  background: #0b2747;
  border-color: #0b2747;
  color: #ffffff;
}

.stButton > button[kind="secondary"],
.stDownloadButton > button[kind="secondary"] {
  background: #ffffff;
  border-color: #58708a;
  color: var(--atlas-navy);
}

.stButton > button[kind="secondary"]:hover,
.stDownloadButton > button[kind="secondary"]:hover {
  background: var(--atlas-sky);
  border-color: var(--atlas-navy);
  color: var(--atlas-navy);
}

.stButton > button:focus-visible,
.stDownloadButton > button:focus-visible,
[data-testid="stLinkButton"] a:focus-visible,
input:focus-visible,
textarea:focus-visible,
[role="radio"]:focus-visible {
  outline: 3px solid #ffbf47 !important;
  outline-offset: 2px !important;
}

@media (max-width: 1024px) {
  [data-testid="stMainBlockContainer"] {
    padding-left: 1.35rem;
    padding-right: 1.35rem;
  }
  [data-testid="stHorizontalBlock"] {
    flex-wrap: wrap;
  }
}

@media (max-width: 640px) {
  [data-testid="stMainBlockContainer"] {
    padding: 4.5rem 0.85rem 4rem;
  }
  .atlas-hero {
    border-radius: 0.85rem;
    padding: 1.1rem;
  }
  [data-testid="stHorizontalBlock"] {
    gap: 0.75rem;
  }
  [data-testid="column"] {
    flex: 1 1 100% !important;
    width: 100% !important;
  }
  .stButton > button,
  .stDownloadButton > button,
  [data-testid="stLinkButton"] a {
    width: 100%;
  }
}
</style>
"""


def apply_atlas_styles():
    import streamlit as st

    st.markdown(ATLAS_STYLES, unsafe_allow_html=True)
