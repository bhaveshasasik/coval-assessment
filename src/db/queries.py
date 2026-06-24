"""
Database query functions for CRUD operations on verifications.
"""

import json
import aiosqlite
from typing import List, Optional
from .database import get_db_connection
from ..models import ComplianceResult, WorkflowGraph, Transcript
from ..services import MetricsExportService


async def save_verification(
    verification: ComplianceResult, workflow: WorkflowGraph, transcript: Transcript
) -> str:
    """
    Save a compliance verification result to the database.

    Args:
        verification: The ComplianceResult
        workflow: The original workflow graph
        transcript: The original transcript

    Returns:
        The verification ID
    """
    critical_violations = [
        v for v in verification.violations if v.severity == "critical"
    ]

    # Generate formatted metrics JSON
    metrics_export_service = MetricsExportService()
    metrics_json = metrics_export_service.export_metrics(
        verification, workflow, transcript
    )

    async with await get_db_connection() as db:
        await db.execute(
            """
            INSERT INTO verifications (
                id, workflow_name, verdict,
                node_completion_rate, critical_node_pass,
                edge_accuracy, valid_path_matched,
                order_violation, first_deviation_point,
                low_confidence_count, unauthorized_steps,
                requires_human_review,
                critical_violation_count, total_violation_count,
                actual_sequence, required_sequence,
                summary,
                workflow_json, transcript_json, results_json, metrics_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                verification.id,
                verification.workflow_name,
                verification.verdict,
                verification.metrics.node_completion_rate,
                verification.metrics.critical_node_pass,
                verification.metrics.edge_accuracy,
                verification.metrics.valid_path_matched,
                verification.metrics.order_violation,
                verification.metrics.first_deviation_point,
                verification.metrics.low_confidence_count,
                verification.metrics.unauthorized_steps,
                verification.requires_human_review,
                len(critical_violations),
                len(verification.violations),
                json.dumps(verification.actual_sequence),
                json.dumps(verification.required_sequence),
                verification.summary,
                workflow.model_dump_json(),
                transcript.model_dump_json(),
                verification.model_dump_json(),
                json.dumps(metrics_json),
            ),
        )
        await db.commit()

    return verification.id


async def get_verification(verification_id: str) -> Optional[dict]:
    """
    Retrieve a verification by ID.

    Args:
        verification_id: The verification ID

    Returns:
        Dictionary with verification data, or None if not found
    """
    async with await get_db_connection() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT * FROM verifications WHERE id = ?
        """,
            (verification_id,),
        )
        row = await cursor.fetchone()

        if row is None:
            return None

        return {
            "id": row["id"],
            "workflow_name": row["workflow_name"],
            "timestamp": row["timestamp"],
            "verdict": row["verdict"],
            "node_completion_rate": row["node_completion_rate"],
            "critical_node_pass": bool(row["critical_node_pass"]),
            "edge_accuracy": row["edge_accuracy"],
            "valid_path_matched": bool(row["valid_path_matched"]),
            "order_violation": bool(row["order_violation"]),
            "first_deviation_point": row["first_deviation_point"],
            "low_confidence_count": row["low_confidence_count"],
            "unauthorized_steps": row["unauthorized_steps"],
            "requires_human_review": bool(row["requires_human_review"]),
            "critical_violation_count": row["critical_violation_count"],
            "total_violation_count": row["total_violation_count"],
            "actual_sequence": json.loads(row["actual_sequence"])
            if row["actual_sequence"]
            else [],
            "required_sequence": json.loads(row["required_sequence"])
            if row["required_sequence"]
            else [],
            "summary": row["summary"],
            "workflow": json.loads(row["workflow_json"]),
            "transcript": json.loads(row["transcript_json"]),
            "results": json.loads(row["results_json"]),
            "metrics_json": json.loads(row["metrics_json"])
            if row["metrics_json"]
            else None,
        }


async def get_recent_verifications(limit: int = 10) -> List[dict]:
    """
    Get the most recent verifications.

    Args:
        limit: Maximum number of results to return

    Returns:
        List of verification summaries
    """
    async with await get_db_connection() as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT id, workflow_name, timestamp, verdict,
                   node_completion_rate, edge_accuracy,
                   critical_violation_count, requires_human_review
            FROM verifications
            ORDER BY timestamp DESC
            LIMIT ?
        """,
            (limit,),
        )
        rows = await cursor.fetchall()

        return [
            {
                "id": row["id"],
                "workflow_name": row["workflow_name"],
                "timestamp": row["timestamp"],
                "verdict": row["verdict"],
                "node_completion_rate": row["node_completion_rate"],
                "edge_accuracy": row["edge_accuracy"],
                "critical_violation_count": row["critical_violation_count"],
                "requires_human_review": bool(row["requires_human_review"]),
            }
            for row in rows
        ]


async def delete_verification(verification_id: str) -> bool:
    """
    Delete a verification by ID.

    Args:
        verification_id: The verification ID

    Returns:
        True if deleted, False if not found
    """
    async with await get_db_connection() as db:
        cursor = await db.execute(
            """
            DELETE FROM verifications WHERE id = ?
        """,
            (verification_id,),
        )
        await db.commit()
        return cursor.rowcount > 0
