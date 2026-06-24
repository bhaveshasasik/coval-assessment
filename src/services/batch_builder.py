"""
Batch builder for Stage 3 - smart batching with transcript windowing.
"""

from typing import List, Dict, Tuple
from pydantic import BaseModel
from ..models import WorkflowGraph, Transcript, ConversationTurn, Node, NodeType
from .node_classifier import NodeBehavior, NodeClassifier


class TranscriptWindow(BaseModel):
    """Represents a time window in the transcript"""

    start: float
    end: float
    node_ids: List[str]


class Batch(BaseModel):
    """A batch of nodes to analyze together"""

    node_ids: List[str]
    turns: List[ConversationTurn]
    is_conditional: bool
    window_start: float
    window_end: float


class BatchBuilder:
    """Builds batches"""

    BUFFER_SECONDS = 30  # Buffer around windows
    MAX_NODES_PER_BATCH = 3  # Max nodes per batch
    MIN_OVERLAP_RATIO = 0.5  # 50% overlap required

    def __init__(self):
        self.classifier = NodeClassifier()

    def build_batches(
        self, workflow: WorkflowGraph, transcript: Transcript
    ) -> List[Batch]:
        """
        Group nodes into batches with overlapping windows.

        Returns:
            List of batches, each with node IDs and transcript slice.
            Expected for NexaCare: 3 batches
        """
        classifications = self.classifier.classify_nodes(workflow)
        total_duration = transcript.total_duration

        if len(workflow.nodes) == 0:
            return []

        max_y = max(n.position.y for n in workflow.nodes)

        # Separate by behavior
        anchored = []
        sequential = []
        conditional = []

        for node in workflow.nodes:
            behavior = classifications[node.id]
            if behavior == NodeBehavior.ANCHORED:
                anchored.append(node)
            elif behavior == NodeBehavior.SEQUENTIAL:
                sequential.append(node)
            else:
                conditional.append(node)

        batches = []

        # Build conditional batch (full transcript)
        if conditional:
            batches.append(
                Batch(
                    node_ids=[n.id for n in conditional],
                    turns=transcript.turns,  # Full transcript
                    is_conditional=True,
                    window_start=0.0,
                    window_end=total_duration,
                )
            )

        # Calculate windows for anchored/sequential
        node_windows: Dict[str, Tuple[float, float]] = {}
        for node in anchored + sequential:
            window = self._calculate_window(
                node, classifications[node.id], total_duration, max_y
            )
            node_windows[node.id] = window

        # Sort by window start time
        ordered_nodes = sorted(
            anchored + sequential, key=lambda n: node_windows[n.id][0]
        )

        # Greedily batch by 50% overlap, max 3 nodes per batch
        current_batch: list[Node] = []
        for node in ordered_nodes:
            if not current_batch:
                current_batch.append(node)
            else:
                # Check overlap with batch window
                batch_start = min(node_windows[n.id][0] for n in current_batch)
                batch_end = max(node_windows[n.id][1] for n in current_batch)
                node_start, node_end = node_windows[node.id]

                overlap = self._calculate_overlap(
                    (batch_start, batch_end), (node_start, node_end)
                )
                smaller_window = min(batch_end - batch_start, node_end - node_start)

                if (
                    overlap >= self.MIN_OVERLAP_RATIO * smaller_window
                    and len(current_batch) < self.MAX_NODES_PER_BATCH
                ):
                    current_batch.append(node)
                else:
                    # Close current batch, start new one
                    batches.append(
                        self._finalize_batch(current_batch, node_windows, transcript)
                    )
                    current_batch = [node]

        # Close final batch
        if current_batch:
            batches.append(
                self._finalize_batch(current_batch, node_windows, transcript)
            )

        return batches

    def _calculate_window(
        self, node: Node, behavior: NodeBehavior, total_duration: float, max_y: float
    ) -> Tuple[float, float]:
        """
        Calculate time window for a node.

        For ANCHORED nodes:
        - START: first 10% of conversation
        - END: last 10% of conversation

        For SEQUENTIAL nodes:
        - Use position.y ratio with 15% buffer
        """
        if behavior == NodeBehavior.ANCHORED:
            if node.type == NodeType.START:
                # First 10%
                return (0.0, total_duration * 0.1)
            else:  # END
                # Last 10%
                return (total_duration * 0.9, total_duration)
        else:  # SEQUENTIAL
            # position.y ratio with 15% buffer
            ratio = node.position.y / max_y if max_y > 0 else 0.5
            center = ratio * total_duration
            buffer = total_duration * 0.15
            return (max(0.0, center - buffer), min(total_duration, center + buffer))

    def _calculate_overlap(
        self, window1: Tuple[float, float], window2: Tuple[float, float]
    ) -> float:
        """Calculate overlap between two windows"""
        start = max(window1[0], window2[0])
        end = min(window1[1], window2[1])
        return max(0.0, end - start)

    def _finalize_batch(
        self,
        nodes: List[Node],
        node_windows: Dict[str, Tuple[float, float]],
        transcript: Transcript,
    ) -> Batch:
        """
        Create batch with transcript slice.

        Applies 30-second buffer on each side
        """
        # Union of all windows
        starts = [node_windows[n.id][0] for n in nodes]
        ends = [node_windows[n.id][1] for n in nodes]
        batch_start = max(0.0, min(starts) - self.BUFFER_SECONDS)
        batch_end = min(transcript.total_duration, max(ends) + self.BUFFER_SECONDS)

        # Slice transcript to turns in window
        turns = [
            turn
            for turn in transcript.turns
            if turn.beginning >= batch_start and turn.beginning <= batch_end
        ]

        return Batch(
            node_ids=[n.id for n in nodes],
            turns=turns,
            is_conditional=False,
            window_start=batch_start,
            window_end=batch_end,
        )
