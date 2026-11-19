
import re

from dataclasses import dataclass, field

from .schemas import NumericalDiscrepancy


NUMBER = r"\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?"

METRIC_LABELS = [
    "accuracy",
    "precision",
    "recall",
    "sensitivity",
    "specificity",
    "f1 score",
    "error rate",
    "detection rate",
    "survival rate",
    "mortality rate",
    "risk reduction",
    "efficacy",
]

PERCENT_PATTERN = re.compile(
    rf"(?<![\w.])(?P<value>{NUMBER})\s*"
    r"(?P<unit>%|percent(?:age)?)(?![A-Za-z])",
    re.IGNORECASE,
)

SAMPLE_PATTERN = re.compile(
    rf"(?<![\w.])(?P<value>{NUMBER})\s+"
    r"(?P<label>participants|patients|subjects|samples|records|cases)\b",
    re.IGNORECASE,
)

SAMPLE_PREFIX_PATTERN = re.compile(
    rf"\b(?:sample\s+size(?:\s+of)?|n\s*=)\s*"
    rf"(?P<value>{NUMBER})",
    re.IGNORECASE,
)

DURATION_PATTERN = re.compile(
    rf"(?<![\w.])(?P<value>{NUMBER})\s*"
    r"(?P<unit>days?|weeks?|months?|years?|hours?|minutes?)\b",
    re.IGNORECASE,
)

MEASUREMENT_PATTERN = re.compile(
    rf"(?<![\w.])(?P<value>{NUMBER})\s*"
    r"(?P<unit>mmHg|mg/dL|mmol/L|mcg|μg|"
    r"mg|ml|mL|kg|cm|mm|bpm|°C|°F|"
    r"grams?|liters?|metres?|meters?)\b",
    re.IGNORECASE,
)


@dataclass
class NumericMention:
    value: float
    unit: str
    category: str
    label: str = ""

    def key(self):
        return (
            self.category,
            self.unit.lower(),
            self.label.lower(),
        )


@dataclass
class NumericExtraction:
    mentions: list[NumericMention] = field(default_factory=list)


def _parse_value(raw: str) -> float:
    return float(raw.replace(",", ""))


def _find_metric_label(context: str) -> str:
    lowered = context.lower()

    for label in METRIC_LABELS:
        if label in lowered:
            return label

    return ""


def extract_numeric_mentions(text: str) -> NumericExtraction:
    """
    Extract supported scientific numerical mentions.

    This is a screening tool, not a complete scientific
    natural-language understanding system.
    """

    result = NumericExtraction()

    if not text:
        return result

    occupied_spans = []

    # 1. Percentages and performance metrics
    for match in PERCENT_PATTERN.finditer(text):

        start = max(0, match.start() - 45)
        end = min(len(text), match.end() + 45)

        context = text[start:end]

        label = _find_metric_label(context) or "general"

        result.mentions.append(
            NumericMention(
                value=_parse_value(match.group("value")),
                unit="%",
                category="percentage",
                label=label,
            )
        )

        occupied_spans.append(match.span())

    # 2. Sample sizes
    for match in SAMPLE_PATTERN.finditer(text):

        result.mentions.append(
            NumericMention(
                value=_parse_value(match.group("value")),
                unit="count",
                category="sample_size",
                label=match.group("label").lower(),
            )
        )

        occupied_spans.append(match.span())

    for match in SAMPLE_PREFIX_PATTERN.finditer(text):

        result.mentions.append(
            NumericMention(
                value=_parse_value(match.group("value")),
                unit="count",
                category="sample_size",
                label="unspecified",
            )
        )

        occupied_spans.append(match.span())

    # 3. Study durations
    for match in DURATION_PATTERN.finditer(text):

        result.mentions.append(
            NumericMention(
                value=_parse_value(match.group("value")),
                unit=match.group("unit").lower(),
                category="duration",
            )
        )

        occupied_spans.append(match.span())

    # 4. Scientific measurements
    for match in MEASUREMENT_PATTERN.finditer(text):

        result.mentions.append(
            NumericMention(
                value=_parse_value(match.group("value")),
                unit=match.group("unit").lower(),
                category="measurement",
            )
        )

        occupied_spans.append(match.span())

    return result


def compare_claim_to_evidence(
    claim_text: str,
    evidence_text: str,
) -> list[NumericalDiscrepancy]:
    """
    Compare numerical mentions in a claim and one
    individual evidence passage.

    Only unambiguous one-to-one category/unit matches
    are reported as candidate discrepancies.
    """

    claim_data = extract_numeric_mentions(claim_text)
    evidence_data = extract_numeric_mentions(evidence_text)

    claim_groups: dict[tuple, set] = {}
    evidence_groups: dict[tuple, set] = {}

    for item in claim_data.mentions:
        claim_groups.setdefault(item.key(), set()).add(item.value)

    for item in evidence_data.mentions:
        evidence_groups.setdefault(item.key(), set()).add(item.value)

    discrepancies = []

    for key in claim_groups.keys() & evidence_groups.keys():

        claim_values = claim_groups[key]
        evidence_values = evidence_groups[key]

        # Avoid arbitrary matching when either side
        # contains multiple different values.
        if len(claim_values) != 1 or len(evidence_values) != 1:
            continue

        claim_value = next(iter(claim_values))
        evidence_value = next(iter(evidence_values))

        if claim_value == evidence_value:
            continue

        category, unit, label = key

        description = (
            f"Claim reports {claim_value:g}{unit}, while the "
            f"evidence reports {evidence_value:g}{unit}."
        )

        if label and label != "general":
            description += f" Metric: {label}."

        description += (
            " Check study context, population, methodology "
            "and measurement definitions."
        )

        discrepancies.append(
            NumericalDiscrepancy(
                claim_value=str(claim_value),
                evidence_value=str(evidence_value),
                unit=unit,
                description=description,
            )
        )

    return discrepancies
