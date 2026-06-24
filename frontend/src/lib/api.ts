import type {
  VerificationRequest,
  VerificationResponse,
  DatabaseVerification,
  HistoryItem
} from "@/types";

// Use relative URLs to go through Next.js API routes (proxy)
// This avoids CORS issues and keeps the backend URL server-side only
const BASE_URL = "";

class APIError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "APIError";
  }
}

export async function verify(
  request: VerificationRequest
): Promise<VerificationResponse> {
  const response = await fetch(`${BASE_URL}/api/verify`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
    signal: AbortSignal.timeout(300_000), // 5 minute timeout for LLM processing
  });

  if (!response.ok) {
    const error = await response.text();
    throw new APIError(
      response.status,
      error || "Verification failed"
    );
  }

  return response.json();
}

export async function getVerification(
  verificationId: string
): Promise<DatabaseVerification> {
  const response = await fetch(`${BASE_URL}/api/verify/${verificationId}`);

  if (!response.ok) {
    throw new APIError(
      response.status,
      "Failed to load verification"
    );
  }

  return response.json();
}

export async function getRecentVerifications(): Promise<HistoryItem[]> {
  const response = await fetch(`${BASE_URL}/api/verify/recent`);

  if (!response.ok) {
    throw new APIError(
      response.status,
      "Failed to load verification history"
    );
  }

  return response.json();
}

export async function verifyStream(
  request: VerificationRequest,
  onProgress: (event: {
    type: string;
    stage?: number;
    description?: string;
    verification_id?: string;
    result?: VerificationResponse;
  }) => void
): Promise<void> {
  const response = await fetch(`${BASE_URL}/api/verify/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new APIError(
      response.status,
      error || "Streaming verification failed"
    );
  }

  // Parse SSE stream
  const reader = response.body?.getReader();
  const decoder = new TextDecoder();

  if (!reader) {
    throw new Error("No response body");
  }

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split("\n");

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = line.slice(6);
          try {
            const event = JSON.parse(data);
            onProgress(event);
          } catch (e) {
            console.error("Failed to parse SSE event:", e);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
