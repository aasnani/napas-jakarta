from app.provenance import validate_source_manifest


def test_source_manifest_has_required_provenance_fields():
    result = validate_source_manifest()
    assert result["sources"] >= 11
    assert result["valid"] is True, result["missing"]
