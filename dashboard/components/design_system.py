from __future__ import annotations

import streamlit as st


def render_institutional_design_system() -> None:
    st.markdown(
        """
        <style>
        .lotoia-institutional-shell {
            max-width: 1400px;
            margin: 0 auto;
        }
        .lotoia-section-spacer {
            margin-top: 0.85rem;
        }
        .lotoia-card-shell {
            border: 1px solid #dbe4ee;
            border-radius: 0.95rem;
            background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
            box-shadow: 0 12px 28px rgba(18, 52, 86, 0.06);
        }
        .lotoia-secondary-shell {
            border: 1px solid #e3ebf3;
            border-radius: 0.9rem;
            background: #fbfdff;
        }
        .lotoia-muted-label {
            font-size: 0.74rem;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            color: #6b7f93;
        }
        .lotoia-executive-title {
            color: #123456;
            font-weight: 800;
            line-height: 1.15;
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
        </style>
        """,
        unsafe_allow_html=True,
    )
