from __future__ import annotations

import streamlit as st


def render_institutional_design_system() -> None:
    st.markdown(
        """
        <style>
        .lotoia-page-shell {
            width: 100%;
            max-width: 100%;
            margin: 0 auto;
        }
        .lotoia-institutional-shell {
            max-width: 1520px;
            margin: 0 auto;
            padding-left: 0.25rem;
            padding-right: 0.25rem;
        }
        .lotoia-section-spacer {
            margin-top: 1rem;
        }
        .lotoia-executive-section {
            margin-top: 1rem;
            margin-bottom: 1rem;
        }
        .lotoia-card-shell {
            border: 1px solid #d8e2ec;
            border-radius: 1rem;
            background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
            box-shadow: 0 14px 30px rgba(18, 52, 86, 0.07);
        }
        .lotoia-secondary-shell {
            border: 1px solid #e2eaf2;
            border-radius: 0.95rem;
            background: #fbfdff;
        }
        .lotoia-muted-label {
            font-size: 0.72rem;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            color: #6b7f93;
        }
        .lotoia-executive-title {
            color: #123456;
            font-weight: 800;
            line-height: 1.12;
            letter-spacing: -0.01em;
        }
        .lotoia-analytical-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.28rem 0.62rem;
            border-radius: 999px;
            border: 1px solid #d8e3ef;
            background: #f4f8fc;
            color: #183754;
            font-size: 0.82rem;
            font-weight: 700;
        }
        .lotoia-trend-pill {
            display: inline-flex;
            align-items: center;
            padding: 0.28rem 0.6rem;
            border-radius: 999px;
            background: #eef4fb;
            color: #24416a;
            font-size: 0.8rem;
            font-weight: 700;
        }
        .lotoia-runtime-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.36rem 0.72rem;
            border-radius: 999px;
            border: 1px solid #d8e3ef;
            background: #eef4fb;
            color: #123456;
            font-size: 0.85rem;
            font-weight: 700;
        }
        .lotoia-executive-kicker {
            font-size: 0.77rem;
            letter-spacing: 0.18em;
            text-transform: uppercase;
            color: #70849a;
            margin-bottom: 0.45rem;
        }
        .lotoia-executive-headline {
            font-size: clamp(1.75rem, 2.1vw, 2.4rem);
            font-weight: 850;
            line-height: 1.1;
            letter-spacing: -0.02em;
            color: #123456;
        }
        .lotoia-executive-copy {
            color: #4b5f74;
            line-height: 1.55;
            font-size: 0.96rem;
        }
        .lotoia-flow-panel {
            padding: 1rem 1.05rem;
        }
        .lotoia-signature-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
            gap: 0.55rem;
            margin: 0.35rem 0 0.75rem 0;
        }
        .lotoia-signature-pill {
            display: flex;
            align-items: center;
            gap: 0.55rem;
            padding: 0.45rem 0.7rem;
            border-radius: 0.85rem;
            border: 1px solid #d7e1ec;
            background: linear-gradient(180deg, #ffffff 0%, #f4f8fc 100%);
            box-shadow: 0 8px 18px rgba(18, 52, 86, 0.05);
            overflow: hidden;
        }
        .lotoia-signature-index {
            flex: 0 0 auto;
            width: 1.9rem;
            height: 1.9rem;
            border-radius: 999px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background: #123456;
            color: #ffffff;
            font-size: 0.72rem;
            font-weight: 800;
        }
        .lotoia-signature-text {
            font-size: 0.84rem;
            color: #20415f;
            font-weight: 700;
            overflow-wrap: anywhere;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
