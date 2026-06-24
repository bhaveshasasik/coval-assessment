"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Upload, Play, Loader2, CheckCircle2 } from "lucide-react";
import { verify } from "@/lib/api";
import type { VerificationResponse } from "@/types";

interface FileUploadProps {
  onVerificationComplete: (result: VerificationResponse) => void;
}

export default function FileUpload({ onVerificationComplete }: FileUploadProps) {
  const [workflowFile, setWorkflowFile] = useState<File | null>(null);
  const [transcriptFile, setTranscriptFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleWorkflowUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && file.type === "application/json") {
      setWorkflowFile(file);
      setError(null);
    } else {
      setError("Please upload a valid JSON file");
    }
  };

  const handleTranscriptUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && file.type === "application/json") {
      setTranscriptFile(file);
      setError(null);
    } else {
      setError("Please upload a valid JSON file");
    }
  };

  const handleRun = async () => {
    if (!workflowFile || !transcriptFile) {
      setError("Please upload both workflow and transcript files");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const workflowText = await workflowFile.text();
      const transcriptText = await transcriptFile.text();

      const workflow = JSON.parse(workflowText);
      const transcript = JSON.parse(transcriptText);

      const result = await verify({
        workflow,
        transcript,
        workflow_name: workflowFile.name.replace(".json", ""),
        confidence_threshold: 0.7,
      });

      onVerificationComplete(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to verify workflow");
      console.error("Verification error:", err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card className="animate-fade-in">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Upload className="w-5 h-5" />
          Upload Files
        </CardTitle>
        <CardDescription>
          Upload workflow graph and conversation transcript to begin verification
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Workflow Upload */}
        <div className="space-y-2">
          <label htmlFor="workflow-upload" className="block text-sm font-medium">
            Workflow Graph (JSON)
          </label>
          <div className="relative">
            <input
              type="file"
              accept=".json"
              onChange={handleWorkflowUpload}
              className="block w-full text-sm text-foreground border border-border rounded-lg cursor-pointer bg-background hover:bg-muted focus:outline-none file:mr-4 file:py-2 file:px-4 file:border-0 file:text-sm file:font-semibold file:bg-primary file:text-primary-foreground hover:file:bg-primary/90"
              id="workflow-upload"
            />
          </div>
          {workflowFile && (
            <p className="text-xs text-green-600 dark:text-green-400 flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3" />
              {workflowFile.name}
            </p>
          )}
        </div>

        {/* Transcript Upload */}
        <div className="space-y-2">
          <label htmlFor="transcript-upload" className="block text-sm font-medium">
            Conversation Transcript (JSON)
          </label>
          <div className="relative">
            <input
              type="file"
              accept=".json"
              onChange={handleTranscriptUpload}
              className="block w-full text-sm text-foreground border border-border rounded-lg cursor-pointer bg-background hover:bg-muted focus:outline-none file:mr-4 file:py-2 file:px-4 file:border-0 file:text-sm file:font-semibold file:bg-primary file:text-primary-foreground hover:file:bg-primary/90"
              id="transcript-upload"
            />
          </div>
          {transcriptFile && (
            <p className="text-xs text-green-600 dark:text-green-400 flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3" />
              {transcriptFile.name}
            </p>
          )}
        </div>

        {/* Error Message */}
        {error && (
          <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
            <p className="text-sm text-destructive">{error}</p>
          </div>
        )}

        {/* Run Button */}
        <Button
          onClick={handleRun}
          disabled={!workflowFile || !transcriptFile || isLoading}
          className="w-full"
          size="lg"
        >
          {isLoading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Running Verification...
            </>
          ) : (
            <>
              <Play className="w-4 h-4" />
              Run Verification
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  );
}
