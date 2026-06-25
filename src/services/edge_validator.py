"""
Edge validator for Stage 7 - path matching and sequence validation.
"""

from typing import List, Dict, Tuple, Optional, Set
from ..models import WorkflowGraph
from ..models.evidence import NodeVerdict, Violation, ViolationCode
from .node_classifier import NodeClassifier, NodeBehavior


class EdgeValidator:
    """
    Validate edge traversal and path matching.
    """

    def __init__(self):
        self.classifier = NodeClassifier()

    def validate_execution_sequence(
        self,
        workflow: WorkflowGraph,
        node_verdicts: List[NodeVerdict],
        valid_paths: Optional[List[List[str]]] = None,
    ) -> Tuple[List[Violation], bool, Optional[float], List[str], List[str]]:
        """
        Validate execution sequence against workflow edges and valid paths.

        Args:
            workflow: The workflow graph
            node_verdicts: All node verdicts from rule engine
            valid_paths: Pre-computed valid paths (if None, will be computed)

        Returns:
            Tuple of:
            - violations: List of V-02, V-03 violations
            - valid_path_matched: Whether sequence matches a valid path
            - first_deviation: Timestamp of first critical violation
            - actual_sequence: Actual node execution order
            - required_sequence: Closest matching valid path
        """
        # Filter to satisfied nodes not requiring human review
        satisfied = [
            nv
            for nv in node_verdicts
            if nv.satisfied
            and not nv.requires_human_review
            and nv.verified_timestamp is not None
        ]

        # Sort by verified timestamp to get actual execution sequence
        satisfied.sort(key=lambda nv: nv.verified_timestamp)
        actual_sequence = [nv.node_id for nv in satisfied]

        violations = []
        adj = workflow.get_adjacency_list()
        if valid_paths is None:
            valid_paths = workflow.find_all_valid_paths()

        if not actual_sequence:
            # No satisfied nodes - can't validate sequence
            return ([], False, None, [], [])

        # Check 1: Are consecutive transitions valid edges?
        for i in range(len(actual_sequence) - 1):
            current = actual_sequence[i]
            next_node = actual_sequence[i + 1]

            if next_node not in adj.get(current, []):
                violations.append(
                    Violation(
                        code=ViolationCode.V02_INVALID_EDGE_TRAVERSAL,
                        severity="critical",
                        description=f"Invalid transition: {current} -> {next_node}",
                        node_id=None,
                        edge=f"{current}->{next_node}",
                        timestamp=satisfied[i + 1].verified_timestamp,
                    )
                )

        # Check 2: Does sequence match a valid path?
        # Remove conditional nodes for path matching
        classifications = self.classifier.classify_nodes(workflow)
        sequential_sequence = [
            node_id
            for node_id in actual_sequence
            if classifications.get(node_id) != NodeBehavior.CONDITIONAL
        ]

        valid_path_matched = sequential_sequence in valid_paths

        # Check 3: Missing required nodes
        if valid_path_matched:
            closest_path = sequential_sequence
        else:
            closest_path = self._find_closest_path(sequential_sequence, valid_paths)

        for node_id in closest_path:
            if node_id not in actual_sequence:
                # Check if it's conditional - conditionals are optional
                if classifications.get(node_id) != NodeBehavior.CONDITIONAL:
                    violations.append(
                        Violation(
                            code=ViolationCode.V01_REQUIRED_NODE_NOT_FOUND,
                            severity="critical",
                            description=f"Required node not found: {node_id}",
                            node_id=node_id,
                            edge=None,
                            timestamp=None,
                        )
                    )

        # Check 4: Order violations
        # Build precedence map from graph
        precedence = self._build_precedence_map(workflow)

        for nv in satisfied:
            for required_predecessor in precedence.get(nv.node_id, []):
                pred_verdict = next(
                    (v for v in satisfied if v.node_id == required_predecessor), None
                )
                if (
                    pred_verdict
                    and pred_verdict.verified_timestamp > nv.verified_timestamp
                ):
                    violations.append(
                        Violation(
                            code=ViolationCode.V03_ORDER_VIOLATION,
                            severity="critical",
                            description=f"Node {nv.node_id} occurred before required predecessor {required_predecessor}",
                            node_id=nv.node_id,
                            edge=None,
                            timestamp=nv.verified_timestamp,
                        )
                    )

        # Find first deviation point
        first_deviation = None
        critical_violations = [v for v in violations if v.severity == "critical"]
        if critical_violations:
            timestamps = [v.timestamp for v in critical_violations if v.timestamp]
            first_deviation = min(timestamps) if timestamps else None

        return (
            violations,
            valid_path_matched,
            first_deviation,
            actual_sequence,
            closest_path,
        )

    def _find_closest_path(
        self, actual: List[str], valid_paths: List[List[str]]
    ) -> List[str]:
        """
        Find valid path with most overlap to actual sequence.

        Args:
            actual: Actual execution sequence
            valid_paths: List of valid paths from graph

        Returns:
            Valid path with highest overlap
        """
        if not valid_paths:
            return []

        best_match = valid_paths[0]
        best_overlap = 0

        for path in valid_paths:
            overlap = len(set(actual) & set(path))
            if overlap > best_overlap:
                best_overlap = overlap
                best_match = path

        return best_match

    def _build_precedence_map(self, workflow: WorkflowGraph) -> Dict[str, List[str]]:
        """
        Build map of {node_id: [required_predecessors]}.

        A node's predecessors are all nodes that must come before it
        according to the graph structure.

        Args:
            workflow: The workflow graph

        Returns:
            Dictionary mapping each node to its required predecessors
        """
        precedence: Dict[str, Set[str]] = {node.id: set() for node in workflow.nodes}
        adj = workflow.get_adjacency_list()

        # For each node, find all nodes reachable from start that lead to it
        start_node = workflow.get_start_node()
        if not start_node:
            return {k: list(v) for k, v in precedence.items()}

        # BFS to find all paths from start
        def find_predecessors(node_id: str, visited: Set[str]) -> Set[str]:
            """Find all predecessors of a node"""
            preds = set()
            for source, targets in adj.items():
                if node_id in targets and source not in visited:
                    preds.add(source)
                    visited.add(source)
                    preds.update(find_predecessors(source, visited))
            return preds

        for node in workflow.nodes:
            if node.id != start_node.id:
                precedence[node.id] = find_predecessors(node.id, set())

        return {k: list(v) for k, v in precedence.items()}

    def calculate_edge_accuracy(
        self, workflow: WorkflowGraph, node_verdicts: List[NodeVerdict]
    ) -> Tuple[float, int, int]:
        """
        Calculate edge accuracy metric per logic.md Stage 8.

        Args:
            workflow: The workflow graph
            node_verdicts: All node verdicts

        Returns:
            Tuple of (accuracy, correct_edges, total_transitions)
        """
        satisfied = [
            nv
            for nv in node_verdicts
            if nv.satisfied and nv.verified_timestamp is not None
        ]

        if len(satisfied) < 2:
            return (1.0, 0, 0)

        satisfied.sort(key=lambda x: x.verified_timestamp)

        adj = workflow.get_adjacency_list()
        correct_edges = 0
        total_transitions = len(satisfied) - 1

        for i in range(len(satisfied) - 1):
            if satisfied[i + 1].node_id in adj.get(satisfied[i].node_id, []):
                correct_edges += 1

        edge_accuracy = (
            correct_edges / total_transitions if total_transitions > 0 else 1.0
        )

        return (edge_accuracy, correct_edges, total_transitions)
