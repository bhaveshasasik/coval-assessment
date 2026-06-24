"use client";

import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import FileUpload from "@/components/file-upload";
import AuditDashboard from "@/components/audit-dashboard";
import GraphVisualizer from "@/components/graph-visualizer";
import TranscriptViewer from "@/components/transcript-viewer";
import HistoryTable from "@/components/history-table";
import { VerificationResponse, Workflow, Transcript } from "@/types";
import { CheckCircle2, FileText } from "lucide-react";
import { getVerification } from "@/lib/api";
import { ThemeToggle } from "@/components/theme-toggle";

export default function Home() {
  const [verificationData, setVerificationData] = useState<{
    response: VerificationResponse;
    workflow: Workflow;
    transcript: Transcript;
  } | null>(null);

  const handleVerificationComplete = (result: VerificationResponse) => {
    // Backend now returns: { verification_id, result, workflow, transcript }
    setVerificationData({
      response: result,
      workflow: result.workflow || { nodes: [], edges: [] },
      transcript: result.transcript || { turns: [] },
    });
  };

  const handleLoadVerification = async (verificationId: string) => {
    try {
      // Backend GET /api/verify/{id} returns full data from database
      const data = await getVerification(verificationId);

      setVerificationData({
        response: {
          verification_id: data.id,
          result: data.results, // ComplianceResult is in "results" field
          workflow: data.workflow,
          transcript: data.transcript,
        },
        workflow: data.workflow || { nodes: [], edges: [] },
        transcript: data.transcript || { turns: [] },
      });
    } catch (error) {
      console.error("Failed to load verification:", error);
    }
  };

  return (
    <main className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        {/* Header */}
        <header className="mb-8">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary rounded-lg">
                <CheckCircle2 className="w-6 h-6 text-primary-foreground" />
              </div>
              <h1 className="text-3xl font-bold">Workflow Verification System</h1>
            </div>
            <ThemeToggle />
          </div>
          <p className="text-muted-foreground">
            Analyze and verify conversational AI agent workflow compliance
          </p>
        </header>

        {/* Upload Section */}
        <div className="mb-6">
          <FileUpload onVerificationComplete={handleVerificationComplete} />
        </div>

        {/* Results Section */}
        {verificationData ? (
          <Tabs defaultValue="dashboard" className="space-y-6 animate-slide-up">
            <TabsList className="grid w-full grid-cols-4 lg:w-auto">
              <TabsTrigger value="dashboard">Dashboard</TabsTrigger>
              <TabsTrigger value="graph">Graph</TabsTrigger>
              <TabsTrigger value="transcript">Transcript</TabsTrigger>
              <TabsTrigger value="history">History</TabsTrigger>
            </TabsList>

            <TabsContent value="dashboard" className="space-y-6">
              <AuditDashboard result={verificationData.response.result} />
            </TabsContent>

            <TabsContent value="graph">
              <GraphVisualizer
                workflow={verificationData.workflow}
                nodeResults={verificationData.response.result.node_verdicts}
              />
            </TabsContent>

            <TabsContent value="transcript">
              <TranscriptViewer
                transcript={verificationData.transcript}
              />
            </TabsContent>

            <TabsContent value="history">
              <HistoryTable onLoadVerification={handleLoadVerification} />
            </TabsContent>
          </Tabs>
        ) : (
          <div className="text-center py-20">
            <FileText className="w-16 h-16 mx-auto mb-4 text-muted-foreground opacity-30" />
            <h3 className="text-lg font-medium mb-2">No Verification Data</h3>
            <p className="text-sm text-muted-foreground">
              Upload workflow and transcript files above to begin verification
            </p>
          </div>
        )}
      </div>
    </main>
  );
}
