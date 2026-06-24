"""
API routes for workflow compliance verification.
"""

import uuid
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import asyncio

from ..models import WorkflowGraph, Transcript, ComplianceResult
from ..services import ComplianceVerifier
from ..db import save_verification, get_verification, get_recent_verifications


router = APIRouter(prefix="/api")


class VerifyRequest(BaseModel):
    """Request model for compliance verification endpoint"""

    workflow: WorkflowGraph
    transcript: Transcript
    workflow_name: Optional[str] = None


class VerifyResponse(BaseModel):
    """Response model for compliance verification endpoint"""

    verification_id: str
    result: ComplianceResult
    workflow: WorkflowGraph
    transcript: Transcript


@router.post("/verify", response_model=VerifyResponse)
async def verify_workflow(request: VerifyRequest):
    """
    Verify if an agent followed a workflow correctly using 9-stage compliance verification.

    This endpoint performs complete compliance verification per logic.md:
    - Stage 1: Graph validation & path finding
    - Stage 2-3: Smart batching with windowing
    - Stage 4: LLM evidence extraction
    - Stage 5: Quote verification firewall
    - Stage 6: Rule engine (deterministic node evaluation)
    - Stage 7: Edge validation & path matching
    - Stage 8: Metrics calculation
    - Stage 9: Binary PASS/FAIL verdict

    Args:
        request: Verification request with workflow and transcript

    Returns:
        ComplianceResult with binary PASS/FAIL verdict, violations, and metrics
    """
    try:
        # Initialize compliance verifier (orchestrates all 9 stages)
        verifier = ComplianceVerifier()

        # Run complete compliance verification
        result = await verifier.verify(
            workflow=request.workflow,
            transcript=request.transcript,
            workflow_name=request.workflow_name,
        )

        # Save to database
        await save_verification(result, request.workflow, request.transcript)

        return VerifyResponse(
            verification_id=result.id,
            result=result,
            workflow=request.workflow,
            transcript=request.transcript,
        )

    except ValueError as e:
        # Validation errors (e.g., invalid workflow graph)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Other errors
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify/stream")
async def verify_workflow_stream(request: VerifyRequest):
    """
    Verify workflow with SSE streaming updates.

    This endpoint streams progress updates during the 9-stage compliance verification:
    - Batching progress
    - LLM extraction progress (per batch)
    - Quote verification progress
    - Final result

    Args:
        request: Verification request with workflow and transcript

    Returns:
        Streaming response with progress updates
    """

    async def event_generator():
        try:
            # Send initial event
            yield f"data: {json.dumps({'type': 'start', 'stage': 'initialization'})}\n\n"
            await asyncio.sleep(0.1)

            # Initialize verifier
            verifier = ComplianceVerifier()

            # Stage 1: Validate graph
            yield f"data: {json.dumps({'type': 'progress', 'stage': 1, 'description': 'Validating workflow graph'})}\n\n"
            await asyncio.sleep(0.1)

            validation_errors = request.workflow.validate_graph()
            if validation_errors:
                raise ValueError(f"Invalid workflow: {', '.join(validation_errors)}")

            valid_paths = request.workflow.find_all_valid_paths()
            yield f"data: {json.dumps({'type': 'progress', 'stage': 1, 'description': f'Found {len(valid_paths)} valid paths'})}\n\n"
            await asyncio.sleep(0.1)

            # Stage 2-3: Build batches
            yield f"data: {json.dumps({'type': 'progress', 'stage': 2, 'description': 'Building smart batches'})}\n\n"
            await asyncio.sleep(0.1)

            batches = verifier.batch_builder.build_batches(
                request.workflow, request.transcript
            )
            yield f"data: {json.dumps({'type': 'progress', 'stage': 3, 'description': f'Created {len(batches)} batches'})}\n\n"
            await asyncio.sleep(0.1)

            # Stage 4: Extract evidence (this is the LLM-heavy stage)
            yield f"data: {json.dumps({'type': 'progress', 'stage': 4, 'description': 'Extracting evidence via LLM'})}\n\n"
            await asyncio.sleep(0.1)

            extracted_evidence = await verifier._extract_evidence_from_batches(
                request.workflow, batches
            )
            yield f"data: {json.dumps({'type': 'progress', 'stage': 4, 'description': f'Extracted evidence from {len(batches)} batches'})}\n\n"
            await asyncio.sleep(0.1)

            # Stage 5: Quote verification
            yield f"data: {json.dumps({'type': 'progress', 'stage': 5, 'description': 'Verifying quotes (hallucination firewall)'})}\n\n"
            await asyncio.sleep(0.1)

            verified_quotes = verifier._verify_all_quotes(
                extracted_evidence, request.transcript
            )
            yield f"data: {json.dumps({'type': 'progress', 'stage': 5, 'description': f'Verified {len(verified_quotes)} quotes'})}\n\n"
            await asyncio.sleep(0.1)

            # Stage 6: Rule engine
            yield f"data: {json.dumps({'type': 'progress', 'stage': 6, 'description': 'Applying deterministic rule engine'})}\n\n"
            await asyncio.sleep(0.1)

            node_verdicts = []
            for node in request.workflow.nodes:
                evidence = extracted_evidence.get(node.id)
                if evidence:
                    verdict = verifier.rule_engine.evaluate_node(
                        node,
                        evidence,
                        verified_quotes,
                        request.transcript,
                        request.workflow,
                    )
                    node_verdicts.append(verdict)

            unauthorized_violations = verifier.rule_engine.detect_unauthorized_steps(
                request.transcript, node_verdicts
            )

            # Stage 7: Edge validation
            yield f"data: {json.dumps({'type': 'progress', 'stage': 7, 'description': 'Validating edge traversal and path matching'})}\n\n"
            await asyncio.sleep(0.1)

            (
                edge_violations,
                valid_path_matched,
                first_deviation,
                actual_sequence,
                required_sequence,
            ) = verifier.edge_validator.validate_execution_sequence(
                request.workflow, node_verdicts
            )

            # Combine violations
            all_violations = []
            for verdict in node_verdicts:
                all_violations.extend(verdict.violations)
            all_violations.extend(edge_violations)
            all_violations.extend(unauthorized_violations)

            # Stage 8: Metrics calculation
            yield f"data: {json.dumps({'type': 'progress', 'stage': 8, 'description': 'Calculating compliance metrics'})}\n\n"
            await asyncio.sleep(0.1)

            metrics = verifier._calculate_metrics(
                request.workflow,
                node_verdicts,
                all_violations,
                valid_path_matched,
                first_deviation,
            )

            # Stage 9: Binary verdict
            yield f"data: {json.dumps({'type': 'progress', 'stage': 9, 'description': 'Computing binary PASS/FAIL verdict'})}\n\n"
            await asyncio.sleep(0.1)

            verdict = "PASS" if verifier._is_pass(metrics, all_violations) else "FAIL"
            requires_human_review = any(
                nv.requires_human_review for nv in node_verdicts
            )
            summary = verifier._generate_summary(
                verdict, metrics, all_violations, actual_sequence, required_sequence
            )

            # Create final result
            result = ComplianceResult(
                id=str(uuid.uuid4()),
                workflow_name=request.workflow_name or "Unnamed Workflow",
                verdict=verdict,
                violations=all_violations,
                metrics=metrics,
                actual_sequence=actual_sequence,
                required_sequence=required_sequence,
                requires_human_review=requires_human_review,
                node_verdicts=node_verdicts,
                summary=summary,
            )

            # Save to database
            await save_verification(result, request.workflow, request.transcript)

            # Send complete event
            complete_data = {
                "type": "complete",
                "verification_id": result.id,
                "result": result.model_dump(),
            }
            yield f"data: {json.dumps(complete_data)}\n\n"

        except ValueError as e:
            error_data = {"type": "error", "message": f"Validation error: {str(e)}"}
            yield f"data: {json.dumps(error_data)}\n\n"
        except Exception as e:
            error_data = {"type": "error", "message": f"Internal error: {str(e)}"}
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/verify/recent")
async def get_recent():
    """
    Get recent compliance verification results.

    Returns:
        List of recent ComplianceResult objects
    """
    return await get_recent_verifications(limit=10)


@router.get("/verify/{verification_id}")
async def get_verification_result(verification_id: str):
    """
    Retrieve a compliance verification result by ID.

    Args:
        verification_id: The verification ID

    Returns:
        The ComplianceResult
    """
    result = await get_verification(verification_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Verification not found")
    return result
