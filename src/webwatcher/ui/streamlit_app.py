import os
from typing import Any

import httpx
import pandas as pd
import streamlit as st

DEFAULT_API_BASE = os.getenv("WEBWATCH_API_BASE_URL", "http://127.0.0.1:8080/api/v1")


def _client() -> httpx.Client:
    return httpx.Client(timeout=20)


def _request(method: str, url: str, payload: dict[str, Any] | None = None, params: dict[str, Any] | None = None) -> tuple[bool, Any]:
    with _client() as client:
        try:
            response = client.request(method, url, json=payload, params=params)
        except Exception as exc:
            return False, f"Request failed: {exc}"
    if response.status_code >= 400:
        return False, f"{response.status_code}: {response.text}"
    try:
        return True, response.json()
    except Exception:
        return True, response.text


def _get(base: str, path: str, params: dict[str, Any] | None = None) -> tuple[bool, Any]:
    return _request("GET", f"{base}{path}", params=params)


def _post(base: str, path: str, payload: dict[str, Any]) -> tuple[bool, Any]:
    return _request("POST", f"{base}{path}", payload=payload)


def _load_companies(base: str) -> list[dict[str, Any]]:
    ok, data = _get(base, "/companies")
    if not ok:
        st.error(data)
        return []
    return data if isinstance(data, list) else []


def _render_dataframe(items: list[dict[str, Any]], empty_label: str = "No data.") -> None:
    if not items:
        st.info(empty_label)
        return
    st.dataframe(pd.DataFrame(items), use_container_width=True, hide_index=True)


def render() -> None:
    st.set_page_config(page_title="Webwatcher UI", layout="wide")
    st.title("Webwatcher")
    st.caption("Simple operations UI for company onboarding, scans, and change review.")

    st.sidebar.header("Connection")
    api_base = st.sidebar.text_input("API Base URL", value=DEFAULT_API_BASE)
    health_btn = st.sidebar.button("Check Health")
    if health_btn:
        ok, data = _get(api_base, "/health")
        if ok:
            st.sidebar.success(f"Healthy: {data}")
        else:
            st.sidebar.error(str(data))

    companies = _load_companies(api_base)
    company_map = {f"{c['id']} - {c['name']}": c["id"] for c in companies}

    tab_overview, tab_add, tab_trigger, tab_status, tab_changes, tab_compare = st.tabs(
        ["Overview", "Add Company", "Trigger Scan", "Scan Status", "Changes", "Compare Snapshots"]
    )

    with tab_overview:
        st.subheader("Companies")
        _render_dataframe(companies, "No companies yet. Add one in the next tab.")

    with tab_add:
        st.subheader("Add Company")
        with st.form("add_company_form", clear_on_submit=False):
            name = st.text_input("Name", placeholder="Acme Ltd")
            base_url = st.text_input("Base URL", placeholder="https://example.com")
            ir_url = st.text_input("IR URL (optional)", placeholder="https://example.com/investors")
            scan_interval = st.number_input("Scan Interval (minutes)", min_value=30, max_value=720, value=90)
            submitted = st.form_submit_button("Create Company")
        if submitted:
            payload = {
                "name": name.strip(),
                "base_url": base_url.strip(),
                "scan_interval_minutes": int(scan_interval),
            }
            if ir_url.strip():
                payload["ir_url"] = ir_url.strip()
            ok, data = _post(api_base, "/companies", payload)
            if ok:
                st.success(f"Created company #{data['id']}")
            else:
                st.error(str(data))

    with tab_trigger:
        st.subheader("Trigger Manual Scan")
        if not company_map:
            st.info("Add a company first.")
        else:
            selected = st.selectbox("Company", list(company_map.keys()), key="trigger_company")
            if st.button("Trigger Scan", type="primary"):
                company_id = company_map[selected]
                ok, data = _post(api_base, f"/monitor/trigger/{company_id}", {})
                if ok:
                    st.success(f"Scan queued for company_id={company_id}")
                    st.json(data)
                else:
                    st.error(str(data))

    with tab_status:
        st.subheader("Scan Run Status")
        if not company_map:
            st.info("Add a company first.")
        else:
            selected = st.selectbox("Company", list(company_map.keys()), key="status_company")
            limit = st.slider("Rows", min_value=5, max_value=100, value=20, step=5)
            if st.button("Load Status"):
                company_id = company_map[selected]
                ok, data = _get(api_base, f"/monitor/status/{company_id}", params={"limit": limit})
                if ok and isinstance(data, list):
                    _render_dataframe(data, "No scan runs found.")
                else:
                    st.error(str(data))

    with tab_changes:
        st.subheader("Detected Changes")
        selected_label = st.selectbox(
            "Company Filter",
            options=["All"] + list(company_map.keys()),
            key="changes_company",
        )
        severity = st.selectbox("Severity", ["All", "Minor", "Moderate", "Significant", "Critical"])
        limit = st.slider("Rows ", min_value=5, max_value=200, value=50, step=5)
        if st.button("Load Changes"):
            params: dict[str, Any] = {"limit": limit}
            if selected_label != "All":
                params["company_id"] = company_map[selected_label]
            if severity != "All":
                params["severity"] = severity
            ok, data = _get(api_base, "/changes", params=params)
            if ok and isinstance(data, list):
                _render_dataframe(data, "No changes found.")
            else:
                st.error(str(data))

    with tab_compare:
        st.subheader("Compare Snapshot Sections")
        col1, col2 = st.columns(2)
        with col1:
            from_snapshot_id = st.number_input("From Snapshot ID", min_value=1, value=1, step=1)
        with col2:
            to_snapshot_id = st.number_input("To Snapshot ID", min_value=1, value=2, step=1)
        if st.button("Compare"):
            ok, data = _get(
                api_base,
                "/changes/compare",
                params={"from_snapshot_id": int(from_snapshot_id), "to_snapshot_id": int(to_snapshot_id)},
            )
            if ok:
                st.json(data)
            else:
                st.error(str(data))


if __name__ == "__main__":
    render()

