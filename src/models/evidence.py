"""
Evidence models for Stage 4-5 - LLM extraction and quote verification.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class SubRequirementEvidence(BaseModel):
    """Evidence for a single sub-requirement within a node"""

    requirement: str = Field(..., description="The sub-requirement being evaluated")
    satisfied: bool = Field(..., description="Whether this sub-requirement was met")
    quote: Optional[str] = Field(
        None, description="Exact verbatim quote from transcript (null if not satisfied)"
    )
    timestamp: Optional[float] = Field(
        None, description="When the quote was spoken (seconds)"
    )
    speaker: Optional[str] = Field(None, description="Who spoke: 'AGENT' or 'PATIENT'")
    confidence: str = Field(..., description="Confidence level: 'high' or 'low'")
    reasoning: str = Field(..., description="Why this requirement was/wasn't met")


class ExtractedEvidence(BaseModel):
    """Raw evidence extracted by LLM for a node (Stage 4)"""

    node_id: str = Field(..., description="ID of the node this evidence is for")
    sub_requirements: List[SubRequirementEvidence] = Field(
        default_factory=list, description="Evidence for each sub-requirement"
    )
    node_satisfied: bool = Field(
        ...,
        description="LLM's opinion on whether node was satisfied (NOT USED in final verdict)",
    )
    node_confidence: str = Field(..., description="Overall confidence: 'high' or 'low'")
    primary_evidence_quote: Optional[str] = Field(
        None, description="Main quote demonstrating node satisfaction"
    )
    primary_evidence_timestamp: Optional[float] = Field(
        None, description="Timestamp of primary evidence"
    )


class VerifiedQuote(BaseModel):
    """Quote after 3-check verification firewall (Stage 5)"""

    quote: str = Field(..., description="The quote text")
    verified: bool = Field(
        ..., description="Whether quote passed all verification checks"
    )
    speaker_match: bool = Field(
        ..., description="Whether speaker matches expected role"
    )
    timestamp_match: bool = Field(
        ..., description="Whether timestamp is within 1 second tolerance"
    )
    corrected_timestamp: Optional[float] = Field(
        None, description="Corrected timestamp from actual turn (if original was off)"
    )
    turn_index: int = Field(
        ..., description="Index of turn where quote was found (-1 if not found)"
    )
    hallucination: bool = Field(
        ..., description="Whether quote doesn't exist in transcript (hallucinated)"
    )

    @property
    def failed_checks(self) -> List[str]:
        """Get list of failed verification checks"""
        failures = []
        if self.hallucination:
            failures.append("Quote not found in transcript")
        if not self.speaker_match:
            failures.append("Wrong speaker")
        if not self.timestamp_match:
            failures.append("Timestamp mismatch")
        return failures


class ViolationCode(str):
    """Violation codes"""

    V01_REQUIRED_NODE_NOT_FOUND = "V-01"
    V02_INVALID_EDGE_TRAVERSAL = "V-02"
    V03_ORDER_VIOLATION = "V-03"
    V04_REQUIRED_FIELD_NOT_COLLECTED = "V-04"
    V05_INCORRECT_BRANCH = "V-05"
    V06_UNAUTHORIZED_STEP = "V-06"


class Violation(BaseModel):
    """A compliance violation detected during verification"""

    code: str = Field(..., description="Violation code (V-01 through V-06)")
    severity: str = Field(..., description="Severity: 'critical' or 'minor'")
    description: str = Field(..., description="Human-readable description of violation")
    node_id: Optional[str] = Field(
        None, description="Node where violation occurred (if applicable)"
    )
    edge: Optional[str] = Field(
        None, description="Edge that was violated (e.g., '1->4')"
    )
    timestamp: Optional[float] = Field(
        None, description="When violation occurred (seconds)"
    )


class NodeVerdict(BaseModel):
    """Deterministic pass/fail verdict for a single node (Stage 6)"""

    node_id: str = Field(..., description="ID of the node")
    satisfied: bool = Field(..., description="Whether node requirements were met")
    violations: List[Violation] = Field(
        default_factory=list, description="Violations detected for this node"
    )
    requires_human_review: bool = Field(
        default=False,
        description="Whether this node requires human review (low confidence)",
    )
    verified_timestamp: Optional[float] = Field(
        None, description="Timestamp when node was executed (from verified quotes)"
    )
    verified_quotes: List[str] = Field(
        default_factory=list,
        description="Quotes that passed verification for this node",
    )
    failed_quotes: List[str] = Field(
        default_factory=list,
        description="Quotes that failed verification (hallucinations)",
    )


class ComplianceMetrics(BaseModel):
    """Metrics calculated per logic.md Stage 8"""

    node_completion_rate: float = Field(
        ..., ge=0.0, le=1.0, description="Satisfied nodes / total nodes"
    )
    critical_node_pass: bool = Field(
        ..., description="Whether START and all END nodes were satisfied"
    )
    edge_accuracy: float = Field(
        ..., ge=0.0, le=1.0, description="Valid transitions / total transitions"
    )
    valid_path_matched: bool = Field(
        ..., description="Whether execution sequence matches a valid path"
    )
    order_violation: bool = Field(
        ..., description="Whether any order violations occurred"
    )
    first_deviation_point: Optional[float] = Field(
        None, description="Timestamp of first critical violation (seconds)"
    )
    low_confidence_count: int = Field(
        ..., ge=0, description="Number of nodes requiring human review"
    )
    unauthorized_steps: int = Field(
        ..., ge=0, description="Number of unauthorized step violations"
    )
    sub_requirement_coverage: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Sub-requirements satisfied / total sub-requirements",
    )


class ComplianceResult(BaseModel):
    """Binary PASS/FAIL compliance result (Stage 9)"""

    id: str = Field(..., description="Unique identifier for this verification")
    workflow_name: Optional[str] = Field(None, description="Name of workflow verified")
    verdict: str = Field(..., description="Binary verdict: 'PASS' or 'FAIL'")
    violations: List[Violation] = Field(
        default_factory=list, description="All violations detected"
    )
    metrics: ComplianceMetrics = Field(..., description="Compliance metrics")
    actual_sequence: List[str] = Field(
        default_factory=list,
        description="Actual execution sequence (node IDs in timestamp order)",
    )
    required_sequence: List[str] = Field(
        default_factory=list,
        description="Required sequence from closest matching valid path",
    )
    requires_human_review: bool = Field(
        default=False, description="Whether any nodes require human review"
    )
    node_verdicts: List[NodeVerdict] = Field(
        default_factory=list, description="Verdict for each node"
    )
    summary: Optional[str] = Field(None, description="Human-readable summary")

    def is_pass(self) -> bool:
        """
        Determine if verification passed per logic.md Stage 9.

        PASS requires ALL THREE:
        1. Zero critical violations
        2. valid_path_matched == True
        3. critical_node_pass == True
        """
        critical_violations = [v for v in self.violations if v.severity == "critical"]

        return (
            len(critical_violations) == 0
            and self.metrics.valid_path_matched
            and self.metrics.critical_node_pass
        )

    def get_critical_violations(self) -> List[Violation]:
        """Get all critical severity violations"""
        return [v for v in self.violations if v.severity == "critical"]

    def get_violations_by_code(self, code: str) -> List[Violation]:
        """Get violations matching a specific code"""
        return [v for v in self.violations if v.code == code]

    def get_nodes_requiring_review(self) -> List[NodeVerdict]:
        """Get all node verdicts that require human review"""
        return [nv for nv in self.node_verdicts if nv.requires_human_review]
