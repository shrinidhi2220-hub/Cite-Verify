
from collections import Counter

from .enums import (
    SourceType,
    RetrievalStatus,
    EvidenceQualityStatus,
)

from .schemas import (
    VerificationRequest,
    EvidenceQualityResult,
    EvidenceIssue,
)


def assess_evidence_quality(
    request: VerificationRequest,
) -> EvidenceQualityResult:

    issues: list[EvidenceIssue] = []

    evidence_ids = [
        item.evidence_id for item in request.evidence
    ]

    counts = Counter(evidence_ids)

    duplicate_ids = sorted(
        evidence_id
        for evidence_id, count in counts.items()
        if count > 1
    )

    if duplicate_ids:
        issues.append(
            EvidenceIssue(
                code="duplicate_evidence_id",
                message=(
                    "Duplicate evidence IDs were detected. "
                    "All passages sharing those IDs are excluded."
                ),
                evidence_ids=duplicate_ids,
            )
        )

    # Ambiguous or unresolved sources cannot be trusted
    # for claim verification.
    if request.retrieval_status == RetrievalStatus.AMBIGUOUS:
        issues.append(
            EvidenceIssue(
                code="ambiguous_source",
                message="The research source identity is ambiguous.",
            )
        )

        return EvidenceQualityResult(
            status=EvidenceQualityStatus.AMBIGUOUS_SOURCE,
            duplicate_evidence_ids=duplicate_ids,
            issues=issues,
        )

    if request.retrieval_status == RetrievalStatus.NOT_FOUND:
        issues.append(
            EvidenceIssue(
                code="source_not_found",
                message="The cited research source was not found.",
            )
        )

        return EvidenceQualityResult(
            status=EvidenceQualityStatus.INSUFFICIENT_EVIDENCE,
            duplicate_evidence_ids=duplicate_ids,
            issues=issues,
        )

    # Do not treat metadata-only retrieval as research evidence.
    if request.retrieval_status == RetrievalStatus.METADATA_ONLY:
        issues.append(
            EvidenceIssue(
                code="retrieval_metadata_only",
                message=(
                    "Only publication metadata is available. "
                    "Research passages are required."
                ),
            )
        )

        metadata_ids = list(dict.fromkeys(
            evidence_id
            for evidence_id in evidence_ids
            if evidence_id not in duplicate_ids
        ))

        return EvidenceQualityResult(
            status=EvidenceQualityStatus.INSUFFICIENT_EVIDENCE,
            metadata_only_evidence_ids=metadata_ids,
            duplicate_evidence_ids=duplicate_ids,
            issues=issues,
        )

    usable_ids: list[str] = []
    full_text_ids: list[str] = []
    abstract_ids: list[str] = []
    metadata_ids: list[str] = []

    for item in request.evidence:

        # Exclude duplicate IDs completely.
        if item.evidence_id in duplicate_ids:
            continue

        if item.source_type == SourceType.FULL_TEXT:
            full_text_ids.append(item.evidence_id)
            usable_ids.append(item.evidence_id)

            if item.page_number is None and not item.section_name:
                issues.append(
                    EvidenceIssue(
                        code="evidence_location_missing",
                        message=(
                            "A full-text passage has no page "
                            "or section location."
                        ),
                        evidence_ids=[item.evidence_id],
                    )
                )

        elif item.source_type == SourceType.ABSTRACT:
            abstract_ids.append(item.evidence_id)
            usable_ids.append(item.evidence_id)

        elif item.source_type == SourceType.METADATA_ONLY:
            metadata_ids.append(item.evidence_id)

        else:
            issues.append(
                EvidenceIssue(
                    code="unknown_source_type",
                    message=(
                        "Evidence source type is unknown "
                        "and cannot be used for verification."
                    ),
                    evidence_ids=[item.evidence_id],
                )
            )

    if abstract_ids:
        issues.append(
            EvidenceIssue(
                code="abstract_only",
                message=(
                    "Abstract passages provide limited context. "
                    "Full-text review is preferable."
                ),
                evidence_ids=abstract_ids,
            )
        )

    if metadata_ids:
        issues.append(
            EvidenceIssue(
                code="metadata_only",
                message=(
                    "Metadata does not contain scientific "
                    "evidence passages."
                ),
                evidence_ids=metadata_ids,
            )
        )

    if full_text_ids:
        status = EvidenceQualityStatus.FULL_TEXT_AVAILABLE

    elif abstract_ids:
        status = EvidenceQualityStatus.ABSTRACT_ONLY

    else:
        status = EvidenceQualityStatus.INSUFFICIENT_EVIDENCE

        issues.append(
            EvidenceIssue(
                code="no_usable_evidence",
                message=(
                    "No readable full-text or abstract "
                    "evidence passages are available."
                ),
            )
        )

    return EvidenceQualityResult(
        status=status,
        usable_evidence_ids=usable_ids,
        full_text_evidence_ids=full_text_ids,
        abstract_evidence_ids=abstract_ids,
        metadata_only_evidence_ids=metadata_ids,
        duplicate_evidence_ids=duplicate_ids,
        issues=issues,
        human_review_required=True,
    )
