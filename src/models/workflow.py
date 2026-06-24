"""
Workflow models for representing workflow graphs with nodes and edges.
"""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from enum import Enum


class NodeType(str, Enum):
    """Types of nodes in a workflow"""

    START = "start"
    DECISION = "decision"
    PROCESS = "process"
    END = "end"


class NodeData(BaseModel):
    """Data contained within a workflow node"""

    label: str = Field(..., description="Display name of the node")
    description: str = Field(
        ..., description="Detailed description of what happens at this node"
    )


class Position(BaseModel):
    """Visual position of a node in the graph"""

    x: float
    y: float


class Node(BaseModel):
    """A single node in the workflow graph"""

    id: str = Field(..., description="Unique identifier for the node")
    type: NodeType = Field(
        ..., description="Type of node (start, decision, process, end)"
    )
    data: NodeData = Field(..., description="Node data including label and description")
    position: Position = Field(..., description="Visual position in the graph")


class Edge(BaseModel):
    """A directed edge connecting two nodes"""

    id: str = Field(..., description="Unique identifier for the edge")
    source: str = Field(..., description="ID of the source node")
    target: str = Field(..., description="ID of the target node")


class WorkflowGraph(BaseModel):
    """Complete workflow graph with nodes and edges"""

    nodes: List[Node] = Field(..., description="List of all nodes in the workflow")
    edges: List[Edge] = Field(..., description="List of all edges connecting nodes")

    def get_adjacency_list(self) -> Dict[str, List[str]]:
        """Build adjacency list representation of the graph"""
        adj_list: Dict[str, List[str]] = {node.id: [] for node in self.nodes}
        for edge in self.edges:
            adj_list[edge.source].append(edge.target)
        return adj_list

    def get_start_node(self) -> Optional[Node]:
        """Get the start node of the workflow"""
        for node in self.nodes:
            if node.type == NodeType.START:
                return node
        return None

    def get_end_nodes(self) -> List[Node]:
        """Get all end nodes of the workflow"""
        return [node for node in self.nodes if node.type == NodeType.END]

    def validate_graph(self) -> List[str]:
        """
        Validate graph structure.

        Returns:
            List of validation errors (empty list if valid)
        """
        errors = []

        # Check exactly one START node
        start_nodes = [n for n in self.nodes if n.type == NodeType.START]
        if len(start_nodes) != 1:
            errors.append(f"Expected 1 START node, found {len(start_nodes)}")

        # Check at least one END node
        end_nodes = [n for n in self.nodes if n.type == NodeType.END]
        if len(end_nodes) == 0:
            errors.append("Expected at least 1 END node, found 0")

        # Validate all edges reference existing nodes
        node_ids = {n.id for n in self.nodes}
        for edge in self.edges:
            if edge.source not in node_ids:
                errors.append(
                    f"Edge {edge.id} references non-existent source: {edge.source}"
                )
            if edge.target not in node_ids:
                errors.append(
                    f"Edge {edge.id} references non-existent target: {edge.target}"
                )

        return errors

    def find_all_valid_paths(self) -> List[List[str]]:
        """
        DFS from START to all END nodes to find complete valid paths.

        Returns:
            List of paths, where each path is a list of node IDs in order.
            Example for NexaCare: [["1", "2", "3", "5"], ["1", "2", "3", "4", "5"]]
        """
        start_node = self.get_start_node()
        if not start_node:
            return []

        end_nodes = self.get_end_nodes()
        end_node_ids = {n.id for n in end_nodes}

        adj = self.get_adjacency_list()
        paths = []

        def dfs(node_id: str, path: List[str]):
            """Recursive DFS to find all paths from current node to END nodes"""
            if node_id in end_node_ids:
                paths.append(path[:])  # Found complete path
                return

            for next_id in adj.get(node_id, []):
                if next_id not in path:  # Avoid cycles
                    path.append(next_id)
                    dfs(next_id, path)
                    path.pop()

        dfs(start_node.id, [start_node.id])
        return paths
