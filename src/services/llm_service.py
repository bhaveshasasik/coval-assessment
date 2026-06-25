"""
LLM service for compliance evidence extraction using Anthropic Claude.

Stage 4 Evidence Extraction - Extracts evidence from transcript batches
to verify workflow compliance.
"""

import os
import json
import asyncio
import logging
from typing import Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..models.evidence import ExtractedEvidence

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


class LLMService:
    """Service for interacting with Anthropic Claude for compliance evidence extraction."""

    # ========================================================================
    # System Prompt
    # ========================================================================
    SYSTEM_PROMPT_COMPLIANCE = """You are a strict clinical compliance auditor.

Default assumption: a requirement was NOT met unless explicit verbatim evidence exists in the transcript.

Rules:
- Partial completion does not count
- Patient volunteering information unprompted does NOT satisfy the agent's obligation to collect it
- For every quote you cite, extract the EXACT STRING from the transcript (verbatim)
- Include the exact timestamp when the quote was spoken
- Identify whether the AGENT or PATIENT said it
- Mark confidence as "high" only when evidence is unambiguous, "low" if uncertain

Return only valid JSON, no preamble or explanation."""

    def __init__(
        self, api_key: str | None = None, model: str = "claude-sonnet-4-5-20250929"
    ):
        """
        Initialize the LLM service.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Claude model to use
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY must be set or passed as argument")

        self.model = model
        self.llm = ChatAnthropic(
            anthropic_api_key=self.api_key, model=self.model, temperature=0.0
        )

    # ========================================================================
    # Evidence Extraction (Stage 4)
    # ========================================================================

    async def extract_evidence_batch(
        self, batch, nodes_info: List[Dict]
    ) -> Dict[str, "ExtractedEvidence"]:
        """
        Extract evidence for a batch of nodes from transcript slice (Stage 4).

        Args:
            batch: Batch containing node IDs and transcript turns
            nodes_info: List of node metadata (id, label, description)

        Returns:
            Dictionary mapping {node_id: ExtractedEvidence}
        """
        transcript_text = self._format_transcript_for_llm(batch.turns)

        nodes_with_negatives = [
            {
                **node_info,
                "negative_examples": self._generate_negative_examples(node_info),
            }
            for node_info in nodes_info
        ]

        user_message = self._build_compliance_prompt(
            transcript_text, nodes_with_negatives
        )

        response = await self._call_llm_with_retry(user_message)

        return self._parse_evidence_response(response, batch.node_ids)

    def _format_transcript_for_llm(self, turns: List) -> str:
        """
        Format transcript turns with indices, speakers, and timestamps.

        Example output:
        [Turn 0, AGENT, t=2.0] "Thank you for calling NexaCare..."
        [Turn 1, PATIENT, t=9.7] "Yeah. Hi. Listen..."
        """
        formatted = []
        for i, turn in enumerate(turns):
            speaker = "AGENT" if turn.role == "assistant" else "PATIENT"
            formatted.append(
                f'[Turn {i}, {speaker}, t={turn.beginning:.1f}] "{turn.content}"'
            )
        return "\n".join(formatted)

    def _generate_negative_examples(self, node_info: Dict) -> List[str]:
        """
        Generate 2 negative examples.
        Extract key actions from description and negate them.
        """
        desc = node_info.get("description", "").lower()
        negatives = []

        if "collect" in desc or "ask" in desc:
            negatives.append(
                "Agent mentioning fields without explicitly collecting them from patient"
            )
        if "confirm" in desc or "verify" in desc:
            negatives.append("Agent stating information without patient confirmation")
        if "identify" in desc or "determine" in desc:
            negatives.append(
                "Patient volunteering information without being asked by agent"
            )

        return (
            negatives[:2]
            if negatives
            else [
                "Partial or implicit coverage does not satisfy this requirement",
                "Information must be explicitly collected by the agent",
            ]
        )

    def _build_compliance_prompt(
        self, transcript_text: str, nodes_with_negatives: List[Dict]
    ) -> str:
        """Build user message for compliance extraction."""

        prompt = f"""Transcript (with turn indices, speakers, timestamps):
{transcript_text}

Nodes to evaluate:
{json.dumps(nodes_with_negatives, indent=2)}

For each node, extract evidence for every sub-requirement. Return JSON with this schema:
{{
  "nodes": [
    {{
      "node_id": "string",
      "sub_requirements": [
        {{
          "requirement": "string",
          "satisfied": boolean,
          "quote": "exact verbatim string or null",
          "timestamp": float or null,
          "speaker": "AGENT" or "PATIENT" or null,
          "confidence": "high" or "low",
          "reasoning": "string"
        }}
      ],
      "node_satisfied": boolean,
      "node_confidence": "high" or "low",
      "primary_evidence_quote": "string or null",
      "primary_evidence_timestamp": float or null
    }}
  ]
}}"""

        return prompt

    async def _call_llm_with_retry(
        self, user_message: str, max_retries: int = 3
    ) -> str:
        """Call LLM with exponential backoff retry."""

        for attempt in range(max_retries):
            try:
                messages = [
                    SystemMessage(content=self.SYSTEM_PROMPT_COMPLIANCE),
                    HumanMessage(content=user_message),
                ]
                response = await self.llm.ainvoke(messages)
                return response.content
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(
                        f"LLM extraction failed after {max_retries} attempts: {e}"
                    )
                    raise

                wait_time = 2**attempt
                logger.warning(
                    f"LLM extraction attempt {attempt + 1} failed, retrying in {wait_time}s: {e}"
                )
                await asyncio.sleep(wait_time)

        raise RuntimeError("LLM call failed after all retries")

    def _parse_evidence_response(
        self, response_text: str, node_ids: List[str]
    ) -> Dict[str, "ExtractedEvidence"]:
        """
        Parse LLM response into ExtractedEvidence objects.

        Handles JSON extraction from markdown code blocks.
        """
        from ..models.evidence import ExtractedEvidence, SubRequirementEvidence

        json_text = response_text
        if "```json" in response_text:
            json_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            json_text = response_text.split("```")[1].split("```")[0]

        try:
            data = json.loads(json_text.strip())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.debug(f"Raw response: {response_text[:500]}...")
            return self._empty_evidence_for_nodes(node_ids)

        evidence_map = {}
        for node_data in data.get("nodes", []):
            node_id = node_data.get("node_id")
            if node_id:
                try:
                    sub_reqs = [
                        SubRequirementEvidence(**sr)
                        for sr in node_data.get("sub_requirements", [])
                    ]

                    evidence_map[node_id] = ExtractedEvidence(
                        node_id=node_id,
                        sub_requirements=sub_reqs,
                        node_satisfied=node_data.get("node_satisfied", False),
                        node_confidence=node_data.get("node_confidence", "low"),
                        primary_evidence_quote=node_data.get("primary_evidence_quote"),
                        primary_evidence_timestamp=node_data.get(
                            "primary_evidence_timestamp"
                        ),
                    )
                except Exception as e:
                    logger.error(f"Error parsing evidence for node {node_id}: {e}")
                    evidence_map[node_id] = self._empty_evidence_for_node(node_id)

        for node_id in node_ids:
            if node_id not in evidence_map:
                evidence_map[node_id] = self._empty_evidence_for_node(node_id)

        return evidence_map

    def _empty_evidence_for_nodes(
        self, node_ids: List[str]
    ) -> Dict[str, "ExtractedEvidence"]:
        """Return empty evidence for all nodes (used on parse failure)."""
        return {node_id: self._empty_evidence_for_node(node_id) for node_id in node_ids}

    def _empty_evidence_for_node(self, node_id: str) -> "ExtractedEvidence":
        """Return empty evidence for a single node."""
        from ..models.evidence import ExtractedEvidence

        return ExtractedEvidence(
            node_id=node_id,
            sub_requirements=[],
            node_satisfied=False,
            node_confidence="low",
            primary_evidence_quote=None,
            primary_evidence_timestamp=None,
        )
