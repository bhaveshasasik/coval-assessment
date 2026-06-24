"""
Compliance verifier orchestrator - ties all 9 stages together.
"""

import uuid
from typing import Dict, List
from ..models import WorkflowGraph, Transcript
from ..models.evidence import (
    ExtractedEvidence,
    VerifiedQuote,
    NodeVerdict,
    ComplianceMetrics,
    ComplianceResult,
)
from .batch_builder import BatchBuilder
from .quote_verifier import QuoteVerifier
from .rule_engine import RuleEngine
from .edge_validator import EdgeValidator
from .llm_service import LLMService


class ComplianceVerifier:
    """
    Main orchestrator for logic.md 9-stage compliance verification.

    Stages:
    1. Graph validation & path finding (done in workflow model)
    2. Node classification (done in batch builder)
    3. Smart batching with windowing
    4. LLM evidence extraction (integrated with LLMService)
    5. Quote verification firewall
    6. Rule engine (deterministic node evaluation)
    7. Edge validation & path matching
    8. Metrics calculation
    9. Binary PASS/FAIL verdict
    """

    def __init__(self):
        self.batch_builder = BatchBuilder()
        self.quote_verifier = QuoteVerifier()
        self.rule_engine = RuleEngine()
        self.edge_validator = EdgeValidator()
        self.llm_service = LLMService()

    async def verify(
        self,
        workflow: WorkflowGraph,
        transcript: Transcript,
        workflow_name: str | None = None,
    ) -> ComplianceResult:
        """
        Run complete compliance verification per logic.md.

        Args:
            workflow: The workflow graph to verify against
            transcript: The conversation transcript to analyze
            workflow_name: Optional name for the workflow

        Returns:
            ComplianceResult with binary PASS/FAIL verdict
        """
        # Stage 1: Validate graph structure
        validation_errors = workflow.validate_graph()
        if validation_errors:
            raise ValueError(f"Invalid workflow: {', '.join(validation_errors)}")

        valid_paths = workflow.find_all_valid_paths()

        # Stage 2-3: Build batches (classification happens inside)
        batches = self.batch_builder.build_batches(workflow, transcript)

        # Stage 4: Extract evidence from batches using LLM service
        extracted_evidence = await self._extract_evidence_from_batches(
            workflow, batches
        )

        # Stage 5: Verify all quotes through hallucination firewall
        verified_quotes = self._verify_all_quotes(extracted_evidence, transcript)

        # Stage 6: Apply rule engine to each node
        node_verdicts = []
        for node in workflow.nodes:
            evidence = extracted_evidence.get(node.id)
            if evidence:
                verdict = self.rule_engine.evaluate_node(
                    node, evidence, verified_quotes, transcript, workflow
                )
                node_verdicts.append(verdict)

        # Detect unauthorized steps
        unauthorized_violations = self.rule_engine.detect_unauthorized_steps(
            transcript, node_verdicts
        )

        # Stage 7: Validate edge traversal and path matching
        (
            edge_violations,
            valid_path_matched,
            first_deviation,
            actual_sequence,
            required_sequence,
        ) = self.edge_validator.validate_execution_sequence(
            workflow, node_verdicts, valid_paths
        )

        # Combine all violations
        all_violations = []
        for verdict in node_verdicts:
            all_violations.extend(verdict.violations)
        all_violations.extend(edge_violations)
        all_violations.extend(unauthorized_violations)

        # Stage 8: Calculate metrics
        metrics = self._calculate_metrics(
            workflow, node_verdicts, all_violations, valid_path_matched, first_deviation
        )

        # Stage 9: Binary verdict
        verdict = "PASS" if self._is_pass(metrics, all_violations) else "FAIL"

        # Check if any nodes require human review
        requires_human_review = any(nv.requires_human_review for nv in node_verdicts)

        # Generate summary
        summary = self._generate_summary(
            verdict, metrics, all_violations, actual_sequence, required_sequence
        )

        return ComplianceResult(
            id=str(uuid.uuid4()),
            workflow_name=workflow_name or "Unnamed Workflow",
            verdict=verdict,
            violations=all_violations,
            metrics=metrics,
            actual_sequence=actual_sequence,
            required_sequence=required_sequence,
            requires_human_review=requires_human_review,
            node_verdicts=node_verdicts,
            summary=summary,
        )

    async def _extract_evidence_from_batches(
        self, workflow: WorkflowGraph, batches: List
    ) -> Dict[str, ExtractedEvidence]:
        """
        Stage 4: Extract evidence using LLM service.

        Args:
            workflow: The workflow graph
            batches: List of batches with transcript slices

        Returns:
            Dictionary mapping {node_id: ExtractedEvidence}
        """
        extracted_evidence = {}

        for batch in batches:
            # Find the workflow nodes that belong to this batch
            batch_nodes = []
            for node in workflow.nodes:
                if node.id in batch.node_ids:
                    batch_nodes.append(node)

            # Build metadata the LLM needs for each node
            nodes_info = []
            for node in batch_nodes:
                nodes_info.append(
                    {
                        "id": node.id,
                        "label": node.data.label,
                        "description": node.data.description,
                    }
                )

            # Send batch transcript slice + node info to LLM for evidence extraction
            batch_evidence = await self.llm_service.extract_evidence_batch(
                batch, nodes_info
            )
            extracted_evidence.update(batch_evidence)

        return extracted_evidence

    def _verify_all_quotes(
        self, extracted_evidence: Dict[str, ExtractedEvidence], transcript: Transcript
    ) -> Dict[str, VerifiedQuote]:
        """
        Run quote verification firewall on all extracted quotes.

        Args:
            extracted_evidence: Evidence extracted from LLM per node
            transcript: The conversation transcript

        Returns:
            Dictionary mapping {quote_text: VerifiedQuote}
        """
        verified_quotes = {}

        for evidence in extracted_evidence.values():
            # Verify primary evidence quote
            if evidence.primary_evidence_quote:
                vq = self.quote_verifier.verify_quote(
                    evidence.primary_evidence_quote,
                    evidence.primary_evidence_timestamp or 0.0,
                    "AGENT",  # Primary evidence typically from agent
                    transcript,
                )
                verified_quotes[evidence.primary_evidence_quote] = vq

            # Verify sub-requirement quotes
            for sub_req in evidence.sub_requirements:
                if sub_req.quote:
                    vq = self.quote_verifier.verify_quote(
                        sub_req.quote,
                        sub_req.timestamp or 0.0,
                        sub_req.speaker or "AGENT",
                        transcript,
                    )
                    verified_quotes[sub_req.quote] = vq

        return verified_quotes

    def _calculate_metrics(
        self,
        workflow: WorkflowGraph,
        node_verdicts: List[NodeVerdict],
        violations: List,
        valid_path_matched: bool,
        first_deviation: float,
    ) -> ComplianceMetrics:
        """
        Calculate compliance metrics per logic.md Stage 8.
        """
        total_nodes = len(workflow.nodes)
        satisfied_count = sum(1 for nv in node_verdicts if nv.satisfied)

        # Node completion rate
        node_completion_rate = satisfied_count / total_nodes if total_nodes > 0 else 0.0

        # Critical node pass (START + all ENDs must be satisfied)
        start_node = workflow.get_start_node()
        end_nodes = workflow.get_end_nodes()

        start_satisfied = (
            any(nv.node_id == start_node.id and nv.satisfied for nv in node_verdicts)
            if start_node
            else False
        )

        ends_satisfied = (
            all(
                any(nv.node_id == end.id and nv.satisfied for nv in node_verdicts)
                for end in end_nodes
            )
            if end_nodes
            else False
        )

        critical_node_pass = start_satisfied and ends_satisfied

        # Edge accuracy
        edge_accuracy, correct_edges, total_transitions = (
            self.edge_validator.calculate_edge_accuracy(workflow, node_verdicts)
        )

        # Order violation
        order_violation = any(v.code == "V-03" for v in violations)

        # Low confidence count
        low_confidence_count = sum(
            1 for nv in node_verdicts if nv.requires_human_review
        )

        # Unauthorized steps
        unauthorized_steps = sum(1 for v in violations if v.code == "V-06")

        return ComplianceMetrics(
            node_completion_rate=node_completion_rate,
            critical_node_pass=critical_node_pass,
            edge_accuracy=edge_accuracy,
            valid_path_matched=valid_path_matched,
            order_violation=order_violation,
            first_deviation_point=first_deviation,
            low_confidence_count=low_confidence_count,
            unauthorized_steps=unauthorized_steps,
            sub_requirement_coverage=None,  # TODO: Calculate from sub-requirements
        )

    def _is_pass(self, metrics: ComplianceMetrics, violations: List) -> bool:
        """
        Binary verdict per logic.md Stage 9.

        PASS requires ALL THREE:
        1. Zero critical violations
        2. valid_path_matched == True
        3. critical_node_pass == True
        """
        critical_violations = [v for v in violations if v.severity == "critical"]

        return (
            len(critical_violations) == 0
            and metrics.valid_path_matched
            and metrics.critical_node_pass
        )

    def _generate_summary(
        self,
        verdict: str,
        metrics: ComplianceMetrics,
        violations: List,
        actual_sequence: List[str],
        required_sequence: List[str],
    ) -> str:
        """
        Generate human-readable summary of verification.
        """
        summary_parts = [
            f"Verdict: {verdict}",
            f"Node completion: {metrics.node_completion_rate * 100:.1f}%",
            f"Edge accuracy: {metrics.edge_accuracy * 100:.1f}%",
            f"Valid path matched: {metrics.valid_path_matched}",
        ]

        if violations:
            critical = [v for v in violations if v.severity == "critical"]
            summary_parts.append(f"Critical violations: {len(critical)}")

        if metrics.low_confidence_count > 0:
            summary_parts.append(
                f"Human review required: {metrics.low_confidence_count} nodes"
            )

        if actual_sequence:
            summary_parts.append(f"Actual sequence: {' -> '.join(actual_sequence)}")
            summary_parts.append(f"Required sequence: {' -> '.join(required_sequence)}")

        return " | ".join(summary_parts)
