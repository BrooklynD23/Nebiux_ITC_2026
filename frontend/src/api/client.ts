import type { ChatRequest, ChatResponse } from '../types';
import { sendMockMessage } from './mock';

/**
 * When true, the client returns mock data instead of calling the backend.
 * Controlled via the VITE_USE_MOCK environment variable.
 * Defaults to true for Sprint 1 development.
 */
const USE_MOCK: boolean =
  import.meta.env.VITE_USE_MOCK !== 'false';

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

  const response = await fetch('/chat', {
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
