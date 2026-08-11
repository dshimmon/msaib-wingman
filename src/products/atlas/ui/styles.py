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
  --atlas-link: #0b5b95;
  --atlas-disabled: #667085;
  --atlas-disabled-surface: #e7edf3;
  --atlas-focus: #005ea8;
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

[data-testid="stMain"],
[data-testid="stSidebar"] {
  color: var(--atlas-ink);
}

[data-testid="stMain"] h1,
[data-testid="stMain"] h2,
[data-testid="stMain"] h3,
[data-testid="stMain"] h4,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
  color: var(--atlas-navy) !important;
  opacity: 1 !important;
}

[data-testid="stMain"] [data-testid="stMarkdown"] p,
[data-testid="stMain"] [data-testid="stMarkdownContainer"] p,
[data-testid="stMain"] [data-testid="stWidgetLabel"] p,
[data-testid="stMain"] label,
[data-testid="stSidebar"] [data-testid="stMarkdown"] p,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
[data-testid="stSidebar"] [role="radiogroup"] label p,
[data-testid="stSidebar"] label,
[data-testid="stAlert"] p,
[data-testid="stAlert"] [data-testid="stMarkdownContainer"] {
  color: var(--atlas-ink) !important;
  opacity: 1 !important;
}

[data-testid="stMain"] [data-testid="stCaptionContainer"],
[data-testid="stMain"] [data-testid="stCaptionContainer"] p,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p,
[data-testid="stMetricLabel"] p {
  color: var(--atlas-muted) !important;
  opacity: 1 !important;
}

[data-testid="stMetricValue"] {
  color: var(--atlas-navy) !important;
  opacity: 1 !important;
}

[data-testid="stMain"] a,
[data-testid="stSidebar"] a {
  color: var(--atlas-link);
  text-decoration-color: currentColor;
}

[data-testid="stMain"] a:hover,
[data-testid="stSidebar"] a:hover {
  color: #073b65;
  text-decoration: underline;
}

[data-testid="stSidebar"] [role="radiogroup"] label {
  min-height: 2.5rem;
}

[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stNumberInput"] input,
[data-testid="stChatInputTextArea"],
[data-testid="stChatInput"] textarea {
  background: #ffffff !important;
  color: var(--atlas-ink) !important;
  caret-color: var(--atlas-ink) !important;
  -webkit-text-fill-color: var(--atlas-ink) !important;
  opacity: 1 !important;
}

[data-testid="stTextInput"] input::placeholder,
[data-testid="stTextArea"] textarea::placeholder,
[data-testid="stNumberInput"] input::placeholder,
[data-testid="stChatInputTextArea"]::placeholder,
[data-testid="stChatInput"] textarea::placeholder {
  color: var(--atlas-muted) !important;
  -webkit-text-fill-color: var(--atlas-muted) !important;
  opacity: 1 !important;
}

[data-testid="stSelectbox"],
[data-testid="stMultiSelect"],
[data-testid="stFileUploader"],
[data-testid="stChatInput"] {
  color: var(--atlas-ink) !important;
}

[data-testid="stSelectbox"] [role="combobox"],
[data-testid="stMultiSelect"] [role="combobox"],
[data-testid="stFileUploader"] section,
[data-testid="stChatInput"] > div {
  background: #ffffff !important;
  color: var(--atlas-ink) !important;
}

[data-testid="stChatMessage"] {
  background: var(--atlas-cloud) !important;
  border: 1px solid var(--atlas-line);
  color: var(--atlas-ink) !important;
}

[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] {
  color: var(--atlas-ink) !important;
  opacity: 1 !important;
}

.atlas-brand {
  border-radius: var(--atlas-radius);
  background: linear-gradient(145deg, #12345b, #185888);
  color: #ffffff;
  padding: 1rem;
  margin-bottom: 1rem;
}

.atlas-brand,
.atlas-brand * {
  color: #ffffff !important;
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

[data-testid="stMain"] .atlas-hero h1 {
  color: var(--atlas-navy) !important;
  font-size: clamp(2rem, 5vw, 3.3rem);
  line-height: 1.05;
  margin: 0.25rem 0 0.65rem;
}

[data-testid="stMain"] .atlas-hero p {
  color: var(--atlas-muted) !important;
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

[data-testid="stButton"] > button,
[data-testid="stDownloadButton"] > button,
[data-testid="stLinkButton"] a {
  border-radius: 0.65rem;
  color: var(--atlas-navy);
  min-height: 2.65rem;
  font-weight: 680;
  opacity: 1;
}

[data-testid="stMain"] [data-testid^="stBaseButton-"] *,
[data-testid="stSidebar"] [data-testid^="stBaseButton-"] *,
[data-testid="stDownloadButton"] button *,
[data-testid="stLinkButton"] a * {
  color: inherit !important;
  opacity: 1 !important;
}

[data-testid="stButton"] > button[kind="secondary"],
[data-testid="stDownloadButton"] > button[kind="secondary"],
[data-testid="stMain"] [data-testid="stBaseButton-secondary"],
[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"],
[data-testid="stLinkButton"] a[kind="secondary"] {
  background: #ffffff;
  border-color: #58708a;
  color: var(--atlas-navy);
}

[data-testid="stButton"] > button[kind="secondary"]:hover,
[data-testid="stDownloadButton"] > button[kind="secondary"]:hover,
[data-testid="stMain"] [data-testid="stBaseButton-secondary"]:hover,
[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"]:hover,
[data-testid="stLinkButton"] a[kind="secondary"]:hover {
  background: var(--atlas-sky);
  border-color: var(--atlas-navy);
  color: var(--atlas-navy);
}

[data-testid="stButton"] > button[kind="primary"],
[data-testid="stDownloadButton"] > button[kind="primary"],
[data-testid="stMain"] [data-testid="stBaseButton-primary"],
[data-testid="stSidebar"] [data-testid="stBaseButton-primary"],
[data-testid="stLinkButton"] a[kind="primary"] {
  background: var(--atlas-navy);
  border-color: var(--atlas-navy);
  color: #ffffff !important;
}

[data-testid="stButton"] > button[kind="primary"]:hover,
[data-testid="stDownloadButton"] > button[kind="primary"]:hover,
[data-testid="stMain"] [data-testid="stBaseButton-primary"]:hover,
[data-testid="stSidebar"] [data-testid="stBaseButton-primary"]:hover,
[data-testid="stLinkButton"] a[kind="primary"]:hover {
  background: #0b2747;
  border-color: #0b2747;
  color: #ffffff !important;
}

[data-testid="stMain"] [data-testid="stBaseButton-primary"] *,
[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] *,
[data-testid="stLinkButton"] a[kind="primary"] * {
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
}

[data-testid="stMain"] [data-testid="stBaseButton-primary"] p,
[data-testid="stMain"] [data-testid="stBaseButton-primary"] span,
[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] p,
[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] span,
[data-testid="stLinkButton"] a[kind="primary"] p,
[data-testid="stLinkButton"] a[kind="primary"] span {
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
}

[data-testid="stMain"] button:disabled,
[data-testid="stSidebar"] button:disabled,
[data-testid="stMain"] input:disabled,
[data-testid="stMain"] textarea:disabled,
[data-testid="stMain"] [aria-disabled="true"],
[data-testid="stSidebar"] [aria-disabled="true"] {
  background: var(--atlas-disabled-surface) !important;
  border-color: #8796a8 !important;
  color: var(--atlas-disabled) !important;
  -webkit-text-fill-color: var(--atlas-disabled) !important;
  opacity: 1 !important;
}

[data-testid="stMain"] [data-testid="stBaseButton-primary"]:disabled,
[data-testid="stSidebar"] [data-testid="stBaseButton-primary"]:disabled {
  background: var(--atlas-disabled) !important;
  border-color: var(--atlas-disabled) !important;
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
}

[data-testid="stMain"] button:focus-visible,
[data-testid="stSidebar"] button:focus-visible,
[data-testid="stLinkButton"] a:focus-visible,
[data-testid="stMain"] a:focus-visible,
[data-testid="stSidebar"] a:focus-visible,
[data-testid="stMain"] input:focus-visible,
[data-testid="stSidebar"] input:focus-visible,
[data-testid="stMain"] textarea:focus-visible,
[data-testid="stSidebar"] textarea:focus-visible,
[data-testid="stMain"] [role="radio"]:focus-visible,
[data-testid="stSidebar"] [role="radio"]:focus-visible {
  outline: 3px solid #ffffff !important;
  outline-offset: 2px !important;
  box-shadow: 0 0 0 6px var(--atlas-focus) !important;
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
  [data-testid="stButton"] > button,
  [data-testid="stDownloadButton"] > button,
  [data-testid="stLinkButton"] a {
    width: 100%;
  }
}
</style>
"""


def apply_atlas_styles():
    import streamlit as st

    st.markdown(ATLAS_STYLES, unsafe_allow_html=True)
