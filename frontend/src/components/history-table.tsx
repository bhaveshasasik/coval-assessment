"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { HistoryItem } from "@/types";
import { History, RefreshCw, Eye, Loader2 } from "lucide-react";
import { getRecentVerifications } from "@/lib/api";

interface HistoryTableProps {
  onLoadVerification: (id: string) => void;
}

export default function HistoryTable({ onLoadVerification }: HistoryTableProps) {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchHistory = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getRecentVerifications();
      setHistory(data || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load history");
      console.error("History fetch error:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    // Initial load on mount
    let mounted = true;

    const loadHistory = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await getRecentVerifications();
        if (mounted) {
          setHistory(data || []);
        }
      } catch (err) {
        if (mounted) {
          setError(err instanceof Error ? err.message : "Failed to load history");
          console.error("History fetch error:", err);
        }
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    };

    loadHistory();

    return () => {
      mounted = false;
    };
  }, []);

  const getVerdictStyle = (verdict: string) => {
    return verdict === "PASS"
      ? "text-green-600 bg-green-50 dark:text-green-400 dark:bg-green-950/30"
      : "text-red-600 bg-red-50 dark:text-red-400 dark:bg-red-950/30";
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <History className="w-5 h-5" />
              Verification History
            </CardTitle>
            <CardDescription>
              Recent verification runs - click to view details
            </CardDescription>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchHistory}
            disabled={isLoading}
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4" />
            )}
            Refresh
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {error && (
          <div className="p-3 mb-4 bg-destructive/10 border border-destructive/20 rounded-lg">
            <p className="text-sm text-destructive">{error}</p>
          </div>
        )}

        {isLoading && history.length === 0 ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
          </div>
        ) : history.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <History className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p className="text-sm">No verification history yet</p>
            <p className="text-xs mt-1">Upload and run your first verification above</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-3 px-4 font-medium text-sm">Workflow</th>
                  <th className="text-center py-3 px-4 font-medium text-sm">Verdict</th>
                  <th className="text-center py-3 px-4 font-medium text-sm">Completion</th>
                  <th className="text-center py-3 px-4 font-medium text-sm">Violations</th>
                  <th className="text-center py-3 px-4 font-medium text-sm">Actions</th>
                </tr>
              </thead>
              <tbody>
                {history.map((item) => (
                  <tr key={item.id} className="border-b hover:bg-muted/50">
                    <td className="py-3 px-4">
                      <div className="text-sm font-medium">
                        {item.workflow_name || "Unnamed Workflow"}
                      </div>
                      <div className="text-xs text-muted-foreground font-mono">
                        ID: {item.id.slice(0, 8)}...
                      </div>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span
                        className={`inline-block px-3 py-1 rounded-full text-sm font-semibold font-mono ${getVerdictStyle(
                          item.verdict
                        )}`}
                      >
                        {item.verdict}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className="text-sm font-mono tabular-nums">
                        {(item.node_completion_rate * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className={`text-sm font-mono tabular-nums ${
                        item.critical_violation_count > 0
                          ? "text-red-600 dark:text-red-400"
                          : "text-muted-foreground"
                      }`}>
                        {item.critical_violation_count}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onLoadVerification(item.id)}
                      >
                        <Eye className="w-4 h-4" />
                        View
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
