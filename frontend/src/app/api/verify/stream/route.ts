import { NextRequest } from 'next/server';

const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000';

export const maxDuration = 300; // Allow up to 5 minutes for LLM processing

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Forward the request to FastAPI's streaming endpoint
    const response = await fetch(`${FASTAPI_URL}/api/verify/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(300_000), // 5 minute timeout
    });

    if (!response.ok) {
      const error = await response.text();
      return new Response(
        JSON.stringify({ error: error || 'Verification failed' }),
        {
          status: response.status,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Return the SSE stream directly
    return new Response(response.body, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    });
  } catch (error) {
    console.error('Streaming verification error:', error);
    return new Response(
      JSON.stringify({ error: 'Failed to connect to backend' }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}
