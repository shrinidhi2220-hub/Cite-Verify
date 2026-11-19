
from enum import StrEnum


class Verdict(StrEnum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    POSSIBLY_OUTDATED = "POSSIBLY_OUTDATED"


class EvidenceStrength(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class SourceType(StrEnum):
    FULL_TEXT = "full_text"
    ABSTRACT = "abstract"
    METADATA_ONLY = "metadata_only"
    UNKNOWN = "unknown"


class RetrievalStatus(StrEnum):
    RESOLVED = "resolved"
    FULL_TEXT_AVAILABLE = "full_text_available"
    AMBIGUOUS = "ambiguous"
    NOT_FOUND = "not_found"
    METADATA_ONLY = "metadata_only"


class VerificationMethod(StrEnum):
    RULE_BASED = "rule_based"
    LLM_ASSISTED = "llm_assisted"
    HUMAN_REVIEW = "human_review"


class EvidenceQualityStatus(StrEnum):
    FULL_TEXT_AVAILABLE = "FULL_TEXT_AVAILABLE"
    ABSTRACT_ONLY = "ABSTRACT_ONLY"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    AMBIGUOUS_SOURCE = "AMBIGUOUS_SOURCE"


class EvidenceRelation(StrEnum):
    SUPPORTS = "supports"
    PARTIALLY_SUPPORTS = "partially_supports"
    CONTRADICTS = "contradicts"
    DOES_NOT_ESTABLISH = "does_not_establish"
    IRRELEVANT = "irrelevant"
    UNCERTAIN = "uncertain"