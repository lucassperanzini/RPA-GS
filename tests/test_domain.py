import pytest

from firms_monitor.domain import CompositeFilter, ConfidenceFilter, MinFrpFilter, RiskClassifier, RiskLevel


@pytest.mark.parametrize(
    ("frp", "expected"),
    [
        (0, RiskLevel.BAIXO),
        (9.99, RiskLevel.BAIXO),
        (10, RiskLevel.MEDIO),
        (49.9, RiskLevel.MEDIO),
        (50, RiskLevel.ALTO),
        (99.9, RiskLevel.ALTO),
        (100, RiskLevel.CRITICO),
        (1500, RiskLevel.CRITICO),
        (-1, RiskLevel.BAIXO),
    ],
)
def test_classifier_default_thresholds(make_hotspot, frp, expected):
    classifier = RiskClassifier.from_thresholds(10, 50, 100)
    assert classifier.classify(make_hotspot(frp=frp)) is expected


def test_classifier_rejects_invalid_thresholds():
    with pytest.raises(ValueError):
        RiskClassifier.from_thresholds(50, 10, 100)


def test_risk_level_from_name_accepts_accents():
    assert RiskLevel.from_name("crítico") is RiskLevel.CRITICO
    assert RiskLevel.from_name("Médio") is RiskLevel.MEDIO
    with pytest.raises(ValueError):
        RiskLevel.from_name("extremo")


@pytest.mark.parametrize(
    ("confidence", "accepted"),
    [("l", False), ("n", True), ("h", True), ("10", False), ("30", True), ("95", True)],
)
def test_confidence_filter(make_hotspot, confidence, accepted):
    assert ConfidenceFilter(min_numeric_confidence=30).accepts(make_hotspot(confidence=confidence)) is accepted


def test_composite_filter_requires_all(make_hotspot):
    f = CompositeFilter([ConfidenceFilter(), MinFrpFilter(1.0)])
    assert f.accepts(make_hotspot(frp=2, confidence="h"))
    assert not f.accepts(make_hotspot(frp=0.5, confidence="h"))
    assert not f.accepts(make_hotspot(frp=200, confidence="l"))
