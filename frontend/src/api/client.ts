import type {
  ChatRequest,
  ChatResponse,
  TranscriptionResponse,
} from '../types';
import { sendMockMessage } from './mock';

/**
 * When true, the client returns mock data instead of calling the backend.
 * Controlled via the VITE_USE_MOCK environment variable.
 * Defaults to false so local Docker/manual runs hit the real backend.
 */
const USE_MOCK: boolean =
  import.meta.env.VITE_USE_MOCK === 'true';

/**
 * Base URL for the backend API.
 * Leave empty (default) for local dev — Vite proxy forwards /chat and /transcribe.
 * Set to the full origin (e.g. https://api.example.com) for production / vite preview.
 */
const API_BASE: string = (
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? ''
).replace(/\/$/, '');

/**
 * Send a chat message and return the API response.
 *
 * In Sprint 1 (USE_MOCK=true), returns simulated responses.
 * In Sprint 2+, calls the real POST /chat endpoint.
 */
export async function sendMessage(
  conversationId: string | undefined,
  message: string,
): Promise<ChatResponse> {
  if (USE_MOCK) {
    return sendMockMessage(conversationId, message);
  }

  const body: ChatRequest = {
    ...(conversationId ? { conversation_id: conversationId } : {}),
    message,
  };

  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }

  const data: ChatResponse = (await response.json()) as ChatResponse;
  return data;
}

export async function transcribeAudio(
  audioBlob: Blob,
  filename: string,
): Promise<string> {
  if (USE_MOCK) {
    return 'Where is the registrar office?';
  }

  const body = new FormData();
  body.append('audio', audioBlob, filename);

  const response = await fetch(`${API_BASE}/transcribe`, {
    method: 'POST',
    body,
  });

  if (!response.ok) {
    const fallback = `Voice input failed: ${response.status} ${response.statusText}`;
    let detail = fallback;

    try {
      const payload = (await response.json()) as { detail?: string };
      detail = payload.detail ?? fallback;
    } catch {
      detail = fallback;
    }

    throw new Error(detail);
  }

  const data = (await response.json()) as TranscriptionResponse;
  return data.transcript;
}
