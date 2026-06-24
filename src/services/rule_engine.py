"""
Rule engine for Stage 6 - deterministic node evaluation.
"""

from typing import List, Dict
from ..models import WorkflowGraph, Node, NodeType, Transcript
from ..models.evidence import (
    ExtractedEvidence,
    VerifiedQuote,
    Violation,
    ViolationCode,
    NodeVerdict,
)


class RuleEngine:
    """
    Deterministic node evaluation per logic.md Stage 6.

    The LLM's node_satisfied opinion is NEVER used.
    All verdicts are recomputed from verified evidence only.
    """

    def evaluate_node(
        self,
        node: Node,
        evidence: ExtractedEvidence,
        verified_quotes: Dict[str, VerifiedQuote],
        transcript: Transcript,
        workflow: WorkflowGraph,
    ) -> NodeVerdict:
        """
        Apply deterministic rules based on node type.

        Args:
            node: The workflow node to evaluate
            evidence: Raw evidence extracted by LLM
            verified_quotes: Map of {quote_text: VerifiedQuote}
            transcript: The conversation transcript
            workflow: The workflow graph (for context)

        Returns:
            NodeVerdict with satisfaction status and violations
        """
        violations = []
        requires_review = False

        # Check if any sub-requirement has low confidence
        low_confidence = any(sr.confidence == "low" for sr in evidence.sub_requirements)
        if low_confidence:
            requires_review = True

        # Check for failed quote verification (hallucinations)
        failed_quotes = []
        verified_quote_texts = []

        for sub_req in evidence.sub_requirements:
            if sub_req.quote:
                vq = verified_quotes.get(sub_req.quote)
                if vq and not vq.verified:
                    # Quote failed verification
                    failed_quotes.append(sub_req.quote)
                    violations.append(
                        Violation(
                            code=ViolationCode.V04_REQUIRED_FIELD_NOT_COLLECTED,
                            severity="critical",
                            description=f"Quote verification failed: '{sub_req.quote[:50]}...'",
                            node_id=node.id,
                            edge=None,
                            timestamp=sub_req.timestamp,
                        )
                    )
                elif vq and vq.verified:
                    verified_quote_texts.append(sub_req.quote)

        # Apply node-type-specific rules
        if node.type == NodeType.START:
            return self._evaluate_start_node(
                node,
                evidence,
                verified_quotes,
                transcript,
                violations,
                requires_review,
                verified_quote_texts,
                failed_quotes,
            )
        elif node.type == NodeType.END:
            return self._evaluate_end_node(
                node,
                evidence,
                verified_quotes,
                transcript,
                violations,
                requires_review,
                verified_quote_texts,
                failed_quotes,
            )
        elif node.type == NodeType.DECISION:
            return self._evaluate_decision_node(
                node,
                evidence,
                verified_quotes,
                violations,
                requires_review,
                verified_quote_texts,
                failed_quotes,
            )
        else:  # PROCESS
            return self._evaluate_process_node(
                node,
                evidence,
                verified_quotes,
                violations,
                requires_review,
                verified_quote_texts,
                failed_quotes,
            )

    def _evaluate_start_node(
        self,
        node: Node,
        evidence: ExtractedEvidence,
        verified_quotes: Dict[str, VerifiedQuote],
        transcript: Transcript,
        violations: List[Violation],
        requires_review: bool,
        verified_quote_texts: List[str],
        failed_quotes: List[str],
    ) -> NodeVerdict:
        """
        START node rules:
        - Primary quote must have passed verification
        - Verified timestamp must equal beginning of first AGENT turn
        - If agent said anything before introduction: order violation
        """
        satisfied = False
        verified_timestamp = None

        # Check if primary evidence exists and is verified
        if evidence.primary_evidence_quote:
            vq = verified_quotes.get(evidence.primary_evidence_quote)
            if vq and vq.verified:
                verified_timestamp = vq.corrected_timestamp

                # Check if this is the first AGENT turn
                first_agent_turn = None
                for turn in transcript.turns:
                    if turn.role == "assistant":
                        first_agent_turn = turn
                        break

                if (
                    first_agent_turn
                    and abs(verified_timestamp - first_agent_turn.beginning) < 1.0
                ):
                    satisfied = True
                else:
                    violations.append(
                        Violation(
                            code=ViolationCode.V03_ORDER_VIOLATION,
                            severity="critical",
                            description=f"START node not at beginning of conversation (expected t={first_agent_turn.beginning if first_agent_turn else 0}s, got t={verified_timestamp}s)",
                            node_id=node.id,
                            edge=None,
                            timestamp=verified_timestamp,
                        )
                    )
            else:
                # Primary quote failed verification or doesn't exist
                violations.append(
                    Violation(
                        code=ViolationCode.V01_REQUIRED_NODE_NOT_FOUND,
                        severity="critical",
                        description="START node primary evidence not verified",
                        node_id=node.id,
                        edge=None,
                        timestamp=None,
                    )
                )

        return NodeVerdict(
            node_id=node.id,
            satisfied=satisfied and not requires_review,
            violations=violations,
            requires_human_review=requires_review,
            verified_timestamp=verified_timestamp,
            verified_quotes=verified_quote_texts,
            failed_quotes=failed_quotes,
        )

    def _evaluate_end_node(
        self,
        node: Node,
        evidence: ExtractedEvidence,
        verified_quotes: Dict[str, VerifiedQuote],
        transcript: Transcript,
        violations: List[Violation],
        requires_review: bool,
        verified_quote_texts: List[str],
        failed_quotes: List[str],
    ) -> NodeVerdict:
        """
        END node rules per logic.md:
        - Primary quote must have passed verification
        - Verified timestamp must be later than all other satisfied nodes
        - (Order check happens in Stage 7 edge validation)
        """
        satisfied = False
        verified_timestamp = None

        # Check if primary evidence exists and is verified
        if evidence.primary_evidence_quote:
            vq = verified_quotes.get(evidence.primary_evidence_quote)
            if vq and vq.verified:
                verified_timestamp = vq.corrected_timestamp
                satisfied = True
            else:
                violations.append(
                    Violation(
                        code=ViolationCode.V01_REQUIRED_NODE_NOT_FOUND,
                        severity="critical",
                        description="END node primary evidence not verified",
                        node_id=node.id,
                        edge=None,
                        timestamp=None,
                    )
                )

        return NodeVerdict(
            node_id=node.id,
            satisfied=satisfied and not requires_review,
            violations=violations,
            requires_human_review=requires_review,
            verified_timestamp=verified_timestamp,
            verified_quotes=verified_quote_texts,
            failed_quotes=failed_quotes,
        )

    def _evaluate_process_node(
        self,
        node: Node,
        evidence: ExtractedEvidence,
        verified_quotes: Dict[str, VerifiedQuote],
        violations: List[Violation],
        requires_review: bool,
        verified_quote_texts: List[str],
        failed_quotes: List[str],
    ) -> NodeVerdict:
        """
        PROCESS node rules:
        - Each sub-requirement that failed verification: V-04 violation
        - If primary quote was hallucinated: V-01 violation
        - All sub-requirements must have verified quotes to satisfy node
        """
        # Check if all satisfied sub-requirements have verified quotes
        satisfied_with_verified = []
        satisfied_without_verified = []

        for sub_req in evidence.sub_requirements:
            if sub_req.satisfied:
                if sub_req.quote:
                    vq = verified_quotes.get(sub_req.quote)
                    if vq and vq.verified:
                        satisfied_with_verified.append(sub_req)
                    else:
                        satisfied_without_verified.append(sub_req)
                        # V-04 violation already added in main evaluate_node
                else:
                    # Sub-requirement marked satisfied but no quote provided
                    satisfied_without_verified.append(sub_req)

        # Node is satisfied only if all sub-requirements have verified evidence
        satisfied = (
            len(satisfied_with_verified) > 0
            and len(satisfied_without_verified) == 0
            and len(evidence.sub_requirements) > 0
        )

        # Get verified timestamp from earliest verified quote
        verified_timestamp = None
        if verified_quote_texts:
            timestamps = []
            for quote_text in verified_quote_texts:
                vq = verified_quotes.get(quote_text)
                if vq and vq.corrected_timestamp:
                    timestamps.append(vq.corrected_timestamp)
            if timestamps:
                verified_timestamp = min(timestamps)

        return NodeVerdict(
            node_id=node.id,
            satisfied=satisfied and not requires_review,
            violations=violations,
            requires_human_review=requires_review,
            verified_timestamp=verified_timestamp,
            verified_quotes=verified_quote_texts,
            failed_quotes=failed_quotes,
        )

    def _evaluate_decision_node(
        self,
        node: Node,
        evidence: ExtractedEvidence,
        verified_quotes: Dict[str, VerifiedQuote],
        violations: List[Violation],
        requires_review: bool,
        verified_quote_texts: List[str],
        failed_quotes: List[str],
    ) -> NodeVerdict:
        """
        DECISION node rules:
        - Same as PROCESS node rules
        - Plus: Branch taken must match evidence collected
        - (Branch validation would require edge context - TBD)
        """
        # For now, use same logic as PROCESS
        # In full implementation, would check if branch matches evidence
        # e.g., if patient said "returning" but agent collected new patient info
        return self._evaluate_process_node(
            node,
            evidence,
            verified_quotes,
            violations,
            requires_review,
            verified_quote_texts,
            failed_quotes,
        )

    def detect_unauthorized_steps(
        self,
        transcript: Transcript,
        node_verdicts: List[NodeVerdict],
        threshold_seconds: float = 60.0,
    ) -> List[Violation]:
        """
        Detect unauthorized steps.

        Unauthorized step: cluster of AGENT turns with no verified quotes
        spanning more than threshold_seconds.

        Args:
            transcript: The conversation transcript
            node_verdicts: All node verdicts with verified quotes
            threshold_seconds: Min duration to flag (default 60s)

        Returns:
            List of V-06 violations for unauthorized steps
        """
        # Collect all verified quote timestamps
        verified_timestamps = set()
        for verdict in node_verdicts:
            if verdict.verified_timestamp:
                verified_timestamps.add(verdict.verified_timestamp)

        violations = []
        current_unverified_start = None
        current_unverified_end = None

        for turn in transcript.turns:
            if turn.role == "assistant":
                # Check if this turn contains any verified quote
                has_verified_quote = False
                for verdict in node_verdicts:
                    for quote_text in verdict.verified_quotes:
                        if quote_text.lower() in turn.content.lower():
                            has_verified_quote = True
                            break
                    if has_verified_quote:
                        break

                if not has_verified_quote:
                    # Unverified AGENT turn
                    if current_unverified_start is None:
                        current_unverified_start = turn.beginning
                    current_unverified_end = turn.end
                else:
                    # Verified turn - check if previous cluster exceeded threshold
                    if current_unverified_start is not None:
                        duration = current_unverified_end - current_unverified_start
                        if duration > threshold_seconds:
                            violations.append(
                                Violation(
                                    code=ViolationCode.V06_UNAUTHORIZED_STEP,
                                    severity="minor",
                                    description=f"Unauthorized step detected: {duration:.1f}s of unverified agent dialogue",
                                    node_id=None,
                                    edge=None,
                                    timestamp=current_unverified_start,
                                )
                            )
                    current_unverified_start = None
                    current_unverified_end = None

        # Check final cluster
        if current_unverified_start is not None:
            duration = current_unverified_end - current_unverified_start
            if duration > threshold_seconds:
                violations.append(
                    Violation(
                        code=ViolationCode.V06_UNAUTHORIZED_STEP,
                        severity="minor",
                        description=f"Unauthorized step detected: {duration:.1f}s of unverified agent dialogue",
                        node_id=None,
                        edge=None,
                        timestamp=current_unverified_start,
                    )
                )

        return violations
