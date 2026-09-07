from app.evidence import compare_study_findings, get_source_apportionment


def test_source_apportionment_tool_preserves_limitations():
    findings = get_source_apportionment("PM2.5")
    assert findings
    assert all("limitations" in finding for finding in findings)
    assert all(finding["estimate"] is None or "estimate_unit" in finding for finding in findings)


def test_study_comparison_does_not_infer_ranking():
    result = compare_study_findings()
    assert result["count"] == 2
    assert "no cross-study causal ranking" in result["comparison_note"]
