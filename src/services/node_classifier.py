"""
Node classification service for Stage 2 - classifies nodes by behavior.
"""

from enum import Enum
from typing import Dict
from ..models.workflow import WorkflowGraph, Node, NodeType


class NodeBehavior(str, Enum):
    """Node behavior classification for batching strategy"""

    ANCHORED = "anchored"  # START, END - fixed points in conversation
    SEQUENTIAL = "sequential"  # Most PROCESS/DECISION - follows predecessor
    CONDITIONAL = "conditional"  # Error handling - can appear anywhere


class NodeClassifier:
    """Classifies nodes by behavior for batching (logic.md Stage 2)"""

    # Keywords that indicate conditional/error-handling nodes
    CONDITIONAL_KEYWORDS = [
        "error",
        "unclear",
        "difficulty",
        "technical",
        "retry",
        "repeat",
        "problem",
        "issue",
        "complaint",
    ]

    def classify_nodes(self, workflow: WorkflowGraph) -> Dict[str, NodeBehavior]:
        """
        Classify all nodes in workflow by behavior.

        Args:
            workflow: The workflow graph to classify

        Returns:
            Dictionary mapping {node_id: behavior}
        """
        classifications = {}

        for node in workflow.nodes:
            if node.type == NodeType.START:
                classifications[node.id] = NodeBehavior.ANCHORED
            elif node.type == NodeType.END:
                classifications[node.id] = NodeBehavior.ANCHORED
            elif self._is_conditional(node):
                classifications[node.id] = NodeBehavior.CONDITIONAL
            else:
                # Default: PROCESS and DECISION nodes are sequential
                classifications[node.id] = NodeBehavior.SEQUENTIAL

        return classifications

    def _is_conditional(self, node: Node) -> bool:
        """
        Check if node description contains conditional keywords.

        Args:
            node: The node to check

        Returns:
            True if node should be treated as conditional
        """
        desc_lower = node.data.description.lower()
        return any(kw in desc_lower for kw in self.CONDITIONAL_KEYWORDS)
