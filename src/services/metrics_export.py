"""
Service for exporting compliance verification results to structured JSON format.
"""

from datetime import datetime, timezone
from typing import Dict, Any
from ..models import ComplianceResult, WorkflowGraph, Transcript


class MetricsExportService:
    """Transform compliance results into structured metrics JSON format"""

    def export_metrics(
        self,
        verification: ComplianceResult,
        workflow: WorkflowGraph,
        transcript: Transcript,
    ) -> Dict[str, Any]:
        """
        Export verification result to structured JSON format.

        Args:
            verification: The ComplianceResult object
            workflow: The workflow graph
            transcript: The conversation transcript

        Returns:
            Dictionary with structured metrics matching the desired format
        """
        # Build node lookup for labels
        node_lookup = {node.id: node for node in workflow.nodes}

        # Transform node verdicts to node_results format
        node_results = []
        for verdict in verification.node_verdicts:
            node = node_lookup.get(verdict.node_id)
            label = node.data.label if node else "Unknown Node"

            # Determine status based on violations and satisfaction
            status = self._determine_node_status(verdict, verification)

            # Get primary evidence quote (use first verified quote if available)
            evidence_quote = (
                verdict.verified_quotes[0] if verdict.verified_quotes else None
            )
            verified_at = verdict.verified_timestamp

            node_results.append(
                {
                    "node_id": verdict.node_id,
                    "label": label,
                    "status": status,
                    "evidence_quote": evidence_quote,
                    "verified_at": verified_at,
                }
            )

        # Format timestamp
        verified_at = datetime.now(timezone.utc).isoformat()

        # Build the structured output
        return {
            "conversation_id": verification.id,
            "workflow_id": verification.workflow_name or "unnamed-workflow",
            "verified_at": verified_at,
            "result": verification.verdict,
            "violations": [
                {
                    "code": v.code.value if hasattr(v.code, "value") else str(v.code),
                    "severity": v.severity,
                    "description": v.description,
                    **({"node_id": v.node_id} if v.node_id else {}),
                    **({"edge": v.edge} if v.edge else {}),
                    **({"timestamp": v.timestamp} if v.timestamp else {}),
                }
                for v in verification.violations
            ],
            "metrics": {
                "node_completion_rate": verification.metrics.node_completion_rate,
                "critical_node_pass": verification.metrics.critical_node_pass,
                "edge_accuracy": verification.metrics.edge_accuracy,
                "valid_path_matched": verification.metrics.valid_path_matched,
                "order_violation": verification.metrics.order_violation,
                **(
                    {
                        "first_deviation_point": verification.metrics.first_deviation_point
                    }
                    if verification.metrics.first_deviation_point
                    else {}
                ),
                **(
                    {
                        "sub_requirement_coverage": verification.metrics.sub_requirement_coverage
                    }
                    if verification.metrics.sub_requirement_coverage is not None
                    else {}
                ),
                "low_confidence_count": verification.metrics.low_confidence_count,
                "unauthorized_steps": verification.metrics.unauthorized_steps,
            },
            "steps_taken": verification.actual_sequence,
            "steps_required": verification.required_sequence,
            "human_review_required": verification.requires_human_review,
            "node_results": node_results,
        }

    def _determine_node_status(self, verdict, verification: ComplianceResult) -> str:
        """
        Determine the status of a node based on verdict and violations.

        Returns: "visited", "out_of_order", or "not_visited"
        """
        # Check if node has order violation
        order_violations = [
            v
            for v in verification.violations
            if v.node_id == verdict.node_id and "order" in v.description.lower()
        ]

        if order_violations:
            return "out_of_order"

        # Check if node was visited (has verified timestamp or quotes)
        if verdict.verified_timestamp or verdict.verified_quotes:
            return "visited"

        return "not_visited"
