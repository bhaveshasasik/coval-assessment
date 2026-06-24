"use client";

import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Download, Copy, Check, Loader2 } from "lucide-react";
import type { MetricsExport } from "@/types";

interface JSONViewerDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  data: MetricsExport | null;
  isLoading?: boolean;
}

export default function JSONViewerDialog({
  open,
  onOpenChange,
  data,
  isLoading = false,
}: JSONViewerDialogProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    if (!data) return;

    try {
      await navigator.clipboard.writeText(JSON.stringify(data, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  const handleDownload = () => {
    if (!data) return;

    const jsonString = JSON.stringify(data, null, 2);
    const blob = new Blob([jsonString], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `verification-${data.conversation_id}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Verification Metrics JSON</DialogTitle>
          <DialogDescription>
            Structured verification results in JSON format
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-auto border rounded-lg bg-muted p-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
            </div>
          ) : data ? (
            <pre className="text-xs font-mono">
              {JSON.stringify(data, null, 2)}
            </pre>
          ) : (
            <div className="text-center py-12 text-muted-foreground">
              <p>No data available</p>
            </div>
          )}
        </div>

        <DialogFooter className="flex-row justify-between sm:justify-between">
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleCopy}
              disabled={!data || isLoading}
            >
              {copied ? (
                <>
                  <Check className="w-4 h-4 mr-2" />
                  Copied!
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4 mr-2" />
                  Copy
                </>
              )}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleDownload}
              disabled={!data || isLoading}
            >
              <Download className="w-4 h-4 mr-2" />
              Download
            </Button>
          </div>
          <Button variant="default" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
