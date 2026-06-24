"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Transcript } from "@/types";
import { MessageCircle, User, Bot } from "lucide-react";

interface TranscriptViewerProps {
  transcript: Transcript;
}

export default function TranscriptViewer({ transcript }: TranscriptViewerProps) {
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(1);
    return `${mins}:${secs.padStart(4, "0")}`;
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MessageCircle className="w-5 h-5" />
          Conversation Transcript
        </CardTitle>
        <CardDescription>
          View conversation turns between user and agent
        </CardDescription>
      </CardHeader>
      <CardContent>
        {transcript.turns.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <MessageCircle className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p className="text-sm">No transcript data available</p>
            <p className="text-xs mt-1">Transcript will appear here after verification</p>
          </div>
        ) : (
          <div className="space-y-3 max-h-[600px] overflow-y-auto pr-2">
            {transcript.turns.map((turn, index) => (
              <div
                key={index}
                className={`p-4 rounded-lg border ${
                  turn.role === "user"
                    ? "bg-muted/50 border-border"
                    : "bg-primary/5 border-primary/20"
                }`}
              >
                <div className="flex items-start gap-3">
                  <div className={`mt-1 ${turn.role === "user" ? "text-muted-foreground" : "text-primary"}`}>
                    {turn.role === "user" ? (
                      <User className="w-5 h-5" />
                    ) : (
                      <Bot className="w-5 h-5" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="font-semibold text-sm capitalize">
                        {turn.role === "user" ? "User" : "Agent"}
                      </span>
                      <span className="text-xs text-muted-foreground font-mono">
                        {formatTime(turn.beginning)} - {formatTime(turn.end)}
                      </span>
                    </div>
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">
                      {turn.content}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
