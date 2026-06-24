"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { VerificationResult } from "@/types";
import { CheckCircle2, XCircle, AlertTriangle, TrendingUp, Target, Shield } from "lucide-react";

interface AuditDashboardProps {
  result: VerificationResult;
}

export default function AuditDashboard({ result }: AuditDashboardProps) {
  const getVerdictColor = (verdict: string) => {
    return verdict === "PASS"
      ? "text-green-600 dark:text-green-500"
      : "text-red-600 dark:text-red-500";
  };

  const getVerdictBg = (verdict: string) => {
    return verdict === "PASS"
      ? "bg-green-50 border-green-200 dark:bg-green-950/20 dark:border-green-900/30"
      : "bg-red-50 border-red-200 dark:bg-red-950/20 dark:border-red-900/30";
  };

  const formatPercentage = (value: number) => (value * 100).toFixed(1) + "%";

  const metrics = [
    {
      label: "Node Completion",
      value: result.metrics.node_completion_rate,
      icon: Target,
      description: "Satisfied nodes / total nodes",
    },
    {
      label: "Edge Accuracy",
      value: result.metrics.edge_accuracy,
      icon: TrendingUp,
      description: "Valid transitions / total transitions",
    },
    {
      label: "Critical Nodes",
      value: result.metrics.critical_node_pass ? 1.0 : 0.0,
      icon: Shield,
      description: "START and all END nodes satisfied",
    },
  ];

  const criticalViolations = result.violations.filter(v => v.severity === "critical");
  const minorViolations = result.violations.filter(v => v.severity === "minor");

  return (
    <div className="space-y-6">
      {/* Overall Verdict */}
      <Card className={`${getVerdictBg(result.verdict)} animate-fade-in`}>
        <CardHeader>
          <CardTitle className="text-2xl">Compliance Verdict</CardTitle>
        </CardHeader>
        <CardContent>
          <div className={`text-6xl font-bold font-mono ${getVerdictColor(result.verdict)}`}>
            {result.verdict}
          </div>
        </CardContent>
      </Card>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {metrics.map((metric) => (
          <Card key={metric.label}>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <metric.icon className="w-5 h-5 text-muted-foreground" />
                <span className="text-2xl font-bold font-mono tabular-nums">
                  {metric.label === "Critical Nodes"
                    ? (result.metrics.critical_node_pass ? "✓" : "✗")
                    : formatPercentage(metric.value)
                  }
                </span>
              </div>
            </CardHeader>
            <CardContent>
              <CardTitle className="text-sm mb-1">{metric.label}</CardTitle>
              <CardDescription className="text-xs">{metric.description}</CardDescription>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Additional Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Valid Path Matched */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <CheckCircle2 className="w-4 h-4" />
              Valid Path
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-3xl font-bold ${result.metrics.valid_path_matched ? "text-green-600 dark:text-green-500" : "text-red-600 dark:text-red-500"}`}>
              {result.metrics.valid_path_matched ? "✓ Yes" : "✗ No"}
            </div>
            <p className="text-sm text-muted-foreground mt-1">
              Execution follows a valid workflow path
            </p>
          </CardContent>
        </Card>

        {/* Order Violation */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <AlertTriangle className="w-4 h-4" />
              Order Violations
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-3xl font-bold ${result.metrics.order_violation ? "text-red-600 dark:text-red-500" : "text-green-600 dark:text-green-500"}`}>
              {result.metrics.order_violation ? "✗ Yes" : "✓ No"}
            </div>
            <p className="text-sm text-muted-foreground mt-1">
              Steps executed out of order
            </p>
          </CardContent>
        </Card>

        {/* Human Review */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <XCircle className="w-4 h-4" />
              Human Review
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold font-mono tabular-nums">
              {result.metrics.low_confidence_count}
            </div>
            <p className="text-sm text-muted-foreground mt-1">
              Nodes requiring manual review
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Violations */}
      {result.violations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Violations Detected</CardTitle>
            <CardDescription>
              {criticalViolations.length} critical, {minorViolations.length} minor
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {criticalViolations.length > 0 && (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
                <p className="text-sm font-semibold text-destructive mb-2">Critical Violations:</p>
                <ul className="text-sm text-destructive/80 space-y-1">
                  {criticalViolations.map((v, idx) => (
                    <li key={idx} className="font-mono text-xs">
                      [{v.code}] {v.description}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {minorViolations.length > 0 && (
              <div className="p-3 bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900/30 rounded-lg">
                <p className="text-sm font-semibold text-amber-700 dark:text-amber-500 mb-2">Minor Violations:</p>
                <ul className="text-sm text-amber-600 dark:text-amber-400 space-y-1">
                  {minorViolations.slice(0, 5).map((v, idx) => (
                    <li key={idx} className="font-mono text-xs">
                      [{v.code}] {v.description}
                    </li>
                  ))}
                </ul>
                {minorViolations.length > 5 && (
                  <p className="text-xs text-muted-foreground mt-2">
                    + {minorViolations.length - 5} more minor violations
                  </p>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Execution Sequence */}
      {result.actual_sequence.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Execution Sequence</CardTitle>
            <CardDescription>Node traversal order</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <p className="text-sm font-medium mb-1">Actual:</p>
              <p className="text-sm font-mono text-muted-foreground">
                {result.actual_sequence.join(" → ")}
              </p>
            </div>
            {result.required_sequence.length > 0 && (
              <div>
                <p className="text-sm font-medium mb-1">Expected:</p>
                <p className="text-sm font-mono text-muted-foreground">
                  {result.required_sequence.join(" → ")}
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
