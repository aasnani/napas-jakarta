from __future__ import annotations

import re


def classify(question: str) -> str:
    """Conservative route classifier with an explicit out-of-domain gate."""
    q = question.lower()
    # In a condensed turn, the follow-up's explicit intent should override
    # the earlier topic; the earlier text remains available for entities.
    focus = q.rsplit("follow-up:", 1)[-1].strip()
    if "follow-up:" in q:
        if any(
            term in focus
            for term in (
                "when was it good",
                "last time it was good",
                "most recently good",
                "kapan terakhir baik",
                "terakhir kali baik",
                "kapan kualitas udara baik",
                "terakhir baik",
            )
        ):
            return "most_recent_category"
        if any(
            term in focus
            for term in ("regulation", "regulations", "rules", "authority", "who guidance")
        ):
            return "regulation_current"
        if any(
            term in focus
            for term in ("source", "sources", "cause", "causes", "polluted", "transport")
        ):
            return "pollution_causes"
        if any(term in focus for term in ("erp", "lez", "low emission", "enacted", "status")):
            return "policy_history"
        if any(
            term in focus
            for term in ("high-rise", "high rise", "rooftop", "street-canyon", "safe floor")
        ):
            return "vertical_exposure"
        if any(
            term in focus
            for term in (
                "exercise",
                "child",
                "children",
                "pregnancy",
                "mask",
                "symptom",
                "exposure",
                "filtration",
            )
        ):
            return (
                "safety_abstention"
                if "symptom" in focus or "medical" in focus
                else "exposure_reduction"
            )
        if any(
            term in focus
            for term in ("current", "latest", "today", "north", "south", "east", "west", "there")
        ):
            return (
                "historical_tool"
                if any(term in focus for term in ("compare", "difference", "versus"))
                else "latest_measurements"
            )
    domain_terms = (
        "jakarta",
        "udara",
        "air quality",
        "kualitas",
        "polusi",
        "pollution",
        "ispu",
        "pm2.5",
        "pm25",
        "pollutant",
        "stasiun",
        "station",
        "who",
        "guideline",
        "regulation",
        "aturan",
        "health",
        "kesehatan",
    )
    unrelated_terms = (
        "recipe",
        "resep",
        "bitcoin",
        "stock market",
        "saham",
        "football",
        "soccer",
        "movie",
        "film",
        "horoscope",
        "cuaca",
        "weather forecast",
        "programming",
        "python code",
        "password",
        "joke",
        "lelucon",
    )
    if any(term in q for term in unrelated_terms) and not any(term in q for term in domain_terms):
        return "out_of_domain"
    if any(
        word in q
        for word in (
            "diagnose",
            "diagnosis",
            "disease",
            "symptoms",
            "medical help",
            "sakit saya",
            "individual outcome",
            "predict my",
            "medical advice",
        )
    ):
        return "safety_abstention"
    if any(
        term in q
        for term in (
            "reduce my emissions",
            "reduce pollution myself",
            "my contribution",
            "public transport",
            "vehicle maintenance",
            "avoid open burning",
            "open burning",
            "what can residents",
            "what can a jakarta resident",
            "resident do",
            "help reduce",
            "mengurangi emisi",
            "kontribusi saya",
        )
    ):
        return "individual_emission_reduction"
    if any(
        term in q
        for term in (
            "why are regulations not working",
            "why regulations are not working",
            "why regulation is not working",
            "not worked",
            "not working",
            "failed to improve",
            "not produced sufficient improvement",
            "why is enforcement weak",
            "why has enforcement",
            "implementation gap",
            "implementation gaps",
            "enforcement gap",
            "enforcement gaps",
            "weak enforcement",
            "poor enforcement",
            "compliance rate",
            "inspection coverage",
            "sanction",
            "penegakan",
            "implementasi",
            "kepatuhan",
            "pengawasan",
            "fragmented authority",
            "institutional fragmentation",
            "anggaran",
            "budget",
            "court order",
            "putusan pengadilan",
        )
    ):
        return "policy_implementation"
    if any(
        term in q
        for term in (
            "individual",
            "protect myself",
            "protect against",
            "for a child",
            "for children",
            "pregnancy",
            "exercise",
            "respirator",
            "air purifier",
            "mask",
            "masker",
            "melindungi",
            "paparan",
            "pembersih udara",
            "anak",
            "bad-air",
            "bad air",
            "pollution episode",
        )
    ):
        return "exposure_reduction"
    if any(
        term in q
        for term in (
            "reduce my emissions",
            "reduce pollution myself",
            "my contribution",
            "public transport",
            "avoid open burning",
            "vehicle maintenance",
            "mengurangi emisi",
            "kontribusi saya",
            "what can i do",
            "what can residents do",
            "what can a jakarta resident",
            "resident do",
            "help reduce",
            "report a violation",
            "report violations",
            "community monitoring",
            "public participation",
            "accountability",
            "citizen action",
            "open burning",
        )
    ):
        return "individual_emission_reduction"
    if any(
        term in q for term in ("what can we do", "how can we improve", "solutions", "interventions")
    ):
        return "improvement_strategies"
    if any(
        term in q
        for term in (
            "cause",
            "causes",
            "sources",
            "source of pollution",
            "why is the air",
            "penyebab",
            "sumber polusi",
            "mengapa polusi",
        )
    ):
        return "pollution_causes"
    categories = (
        "good", "baik", "moderate", "sedang", "unhealthy", "tidak sehat",
        "very unhealthy", "sangat tidak sehat", "hazardous", "berbahaya",
    )
    historical_markers = (
        "when was", "last time", "most recently", "latest", "how many",
        "count", "last week", "yesterday", "kapan terakhir", "terakhir kali",
        "berapa", "minggu lalu", "kemarin",
    )
    numeric_condition = re.search(
        r"\b(?:ispu|pm\s*2\.?5|pm25|pm10)\s*(?:below|under|above|over|<=|>=|<|>)\s*\d+(?:\.\d+)?"
        r"|\b(?:below|under|above|over|<=|>=|<|>)\s*(?:ispu|pm\s*2\.?5|pm25|pm10)\s*\d+(?:\.\d+)?",
        q,
    )
    if any(category in q for category in categories) and any(
        term in q for term in ("unhealthy day", "unhealthy days", "hari tidak sehat")
    ):
        return "historical_tool"
    if (any(category in q for category in categories) or numeric_condition) and any(
        marker in q for marker in historical_markers
    ):
        return "most_recent_category"
    if any(
        term in q
        for term in (
            "draft",
            "proposal",
            "not passed",
            "did not pass",
            "pending",
            "status now",
            "was it enacted",
            "is it currently enacted",
            "belum disahkan",
            "raperda",
            "erp",
            "pl2se",
            "low emission zone",
        )
    ):
        return "policy_history"
    if any(
        term in q
        for term in (
            "protect myself",
            "protect against",
            "reduce exposure",
            "respirator",
            "air purifier",
            "mask",
            "melindungi diri",
            "paparan",
        )
    ):
        return "exposure_reduction"
    if any(
        term in q
        for term in (
            "high-rise",
            "high rise",
            "highrise",
            "ground level",
            "floor height",
            "rooftop",
            "street-canyon",
            "safe floor",
            "lantai",
            "gedung tinggi",
            "tinggal di apartemen",
        )
    ):
        return "vertical_exposure"
    if any(
        term in q
        for term in (
            "improve air",
            "improve jakarta",
            "improve it",
            "ways to improve",
            "solutions",
            "what can we do",
            "mengurangi polusi",
            "perbaiki kualitas",
            "improvement",
            "improvements",
        )
    ):
        return "improvement_strategies"
    if any(
        term in q
        for term in (
            "regulations",
            "regulation",
            "law",
            "laws",
            "aturan",
            "peraturan",
            "hukum",
            "baku mutu",
            "legal",
            "rule",
            "currently in force",
            "in force",
            "vehicle emissions testing",
            "uji emisi",
        )
    ):
        return "regulation_current"
    if any(
        word in q
        for word in (
            "compare",
            "bandingkan",
            "rata-rata",
            "average",
            "trend",
            "historical",
            "unhealthy day",
            "unhealthy days",
            "hari tidak sehat",
            "highest",
            "tertinggi",
            "versus",
            " vs ",
            "last ",
            "yesterday",
            "minggu lalu",
            "kemarin",
        )
    ):
        return "historical_tool"
    if any(word in q for word in ("current", "latest", "sekarang", "terbaru", "today", "hari ini")):
        return "latest_measurements"
    if re.search(r"\b(ispu|pm\s*2\.5|pm25|guideline|standard|aturan|regulation)\b", q):
        return "document_rag"
    return "document_rag"
