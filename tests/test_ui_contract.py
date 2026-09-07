from pathlib import Path

import pandas as pd

from app.stations import display_district_name, display_station_name
from app.ui import _human_category, _table_rows


def test_dashboard_contract_has_filters_and_full_station_table():
    ui = (Path(__file__).parents[1] / "app/ui.py").read_text()
    assert "Data freshness" in ui
    assert "Color meaning" in ui
    assert "all_stations = pd.DataFrame(map_rows)" in ui
    assert "Inspect a station" not in ui
    assert "Rows per page" in ui


def test_chat_branding_and_document_flow_contract():
    ui = (Path(__file__).parents[1] / "app/ui.py").read_text()
    assert '"assets" / "napas-jakarta-air-icon.png"' in ui
    assert "st.image(brand_icon, width=52)" in ui
    assert "page_icon = str(ICON_PATH)" in ui
    assert "st.chat_message(role, avatar=" not in ui
    assert "with st.container():\n        question = st.chat_input(placeholder)" in ui
    assert "st.iframe(" in ui
    assert 'st.session_state.pending_prompt = {"question": question' in ui
    assert 'st.session_state.pop("pending_prompt", None)' in ui
    assert "scrollIntoView" not in ui
    assert (
        "Response interrupted before completion" in ui
        or "Response interrupted before completion"
        in (Path(__file__).parents[1] / "app/provider.py").read_text()
    )


def test_display_names_remove_feed_prefixes_but_keep_public_name():
    assert (
        display_station_name("DKI_PM25_64 SMPN 88 Jakarta (ROOFTOP)") == "SMPN 88 Jakarta (Rooftop)"
    )
    assert display_station_name("LCS-03 Hutan Kota Srengseng") == "Hutan Kota Srengseng"
    assert display_station_name("DKI1 Bundaran HI") == "Bundaran HI"
    assert display_district_name("Kota Adm. Jakarta Pusat") == "Jakarta Pusat"


def test_table_rows_have_continuing_numbers_and_human_categories():
    frame = pd.DataFrame(
        {
            "station": ["A", "B", "C"],
            "district": ["Jakarta Pusat"] * 3,
            "ispu": [30, 40, 50],
            "category": [_human_category("Sedang")] * 3,
            "concentration": [10.0, 20.0, 30.0],
            "observed_at": ["2026-09-07T11:00:00+07:00"] * 3,
            "source": ["https://udara.jakarta.go.id/"] * 3,
        }
    )
    table = _table_rows(frame, 1, 3, pd, include_source=True)
    assert table["No."].tolist() == [2, 3]
    assert table["Category"].tolist() == ["Moderate", "Moderate"]
    assert table["Observed (WIB)"].iloc[0] == "07 Sep 2026, 11:00 WIB"
