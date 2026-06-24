"use client";

import { useMemo, useCallback } from "react";
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
} from "reactflow";
import "reactflow/dist/style.css";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Workflow, NodeResult } from "@/types";

interface GraphVisualizerProps {
  workflow: Workflow;
  nodeResults: NodeResult[];
}

export default function GraphVisualizer({ workflow, nodeResults }: GraphVisualizerProps) {
  const getNodeColor = useCallback((nodeId: string) => {
    const result = nodeResults.find((r) => r.node_id === nodeId);
    if (!result) return "#94a3b8"; // gray - no result

    if (result.satisfied) {
      return "#22c55e"; // green - satisfied
    } else if (result.requires_human_review) {
      return "#eab308"; // yellow - needs review
    } else if (result.violations.some(v => v.severity === "critical")) {
      return "#ef4444"; // red - critical violation
    } else {
      return "#f97316"; // orange - minor violation
    }
  }, [nodeResults]);

  const getNodeLabel = useCallback((nodeId: string) => {
    const workflowNode = workflow.nodes.find((n) => n.id === nodeId);

    if (!workflowNode) return nodeId;

    return workflowNode.data.label;
  }, [workflow.nodes]);

  // Memoize nodes to prevent recreation on every render
  const nodes: Node[] = useMemo(() => {
    return workflow.nodes.map((node) => ({
      id: node.id,
      type: "default",
      position: node.position,
      data: {
        label: getNodeLabel(node.id),
      },
      style: {
        background: getNodeColor(node.id),
        color: "white",
        border: "2px solid rgba(255,255,255,0.3)",
        borderRadius: "8px",
        padding: "10px",
        fontWeight: 500,
        fontSize: "14px",
        minWidth: "150px",
        textAlign: "center",
      },
    }));
  }, [workflow.nodes, getNodeColor, getNodeLabel]);

  // Memoize edges to prevent recreation on every render
  const edges: Edge[] = useMemo(() => {
    return workflow.edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: "smoothstep",
      animated: true,
      style: { stroke: "#94a3b8", strokeWidth: 2 },
    }));
  }, [workflow.edges]);

  const legend = [
    { status: "satisfied", color: "#22c55e", label: "Satisfied" },
    { status: "review", color: "#eab308", label: "Needs Review" },
    { status: "critical", color: "#ef4444", label: "Critical Violation" },
    { status: "minor", color: "#f97316", label: "Minor Violation" },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Workflow Graph Visualization</CardTitle>
        <CardDescription>
          Interactive workflow graph showing node status and transitions
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[600px] border rounded-lg overflow-hidden">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            fitView
            attributionPosition="bottom-right"
          >
            <Background />
            <Controls />
            <MiniMap
              nodeColor={(node) => node.style?.background as string}
              maskColor="rgba(0, 0, 0, 0.1)"
            />
          </ReactFlow>
        </div>

        {/* Legend */}
        <div className="mt-4 flex flex-wrap gap-4">
          {legend.map((item) => (
            <div key={item.status} className="flex items-center gap-2">
              <div
                className="w-4 h-4 rounded"
                style={{ backgroundColor: item.color }}
              />
              <span className="text-sm text-muted-foreground">{item.label}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
