import json
import re
from pathlib import Path


ROOT = Path(__file__).parents[1]
REGISTRY_PATH = ROOT / "web" / "lib" / "topics.json"


def load_registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def registered_source_ids() -> set[str]:
    source_text = (ROOT / "data" / "sources.yaml").read_text(encoding="utf-8")
    return set(re.findall(r"^- id: ([a-z0-9-]+)$", source_text, flags=re.MULTILINE))


def test_topic_registry_is_bilingual_and_source_grounded():
    registry = load_registry()
    source_ids = registered_source_ids()
    topics = [topic for group in registry["groups"] for topic in group["topics"]]

    assert len(registry["groups"]) >= 8
    assert len(topics) >= 16
    assert len({topic["id"] for topic in topics}) == len(topics)

    for group in registry["groups"]:
        assert group["label"]
        assert group["indonesian"]["label"]
        for topic in group["topics"]:
            assert topic["sourceIds"]
            assert set(topic["sourceIds"]).issubset(source_ids)
            assert topic["suggestedQuestion"]
            assert topic["indonesian"]["label"]
            assert topic["indonesian"]["suggestedQuestion"]


def test_pregnancy_topic_is_explicitly_review_gated():
    registry = load_registry()
    topics = [topic for group in registry["groups"] for topic in group["topics"]]
    pregnancy = next(topic for topic in topics if topic["id"] == "pregnancy-and-air")

    assert pregnancy["reviewStatus"] == "clinical-review-required"
