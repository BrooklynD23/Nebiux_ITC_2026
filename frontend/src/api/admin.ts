const BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000';

function headers(token: string): HeadersInit {
  return { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` };
}

export interface ConversationSummary {
  readonly conversation_id: string;
  readonly created_at: string;
  readonly updated_at: string;
  readonly turn_count: number;
  readonly last_status: string | null;
  readonly last_user_message_preview: string | null;
}

export interface Citation {
  readonly title: string;
  readonly url: string;
  readonly snippet: string;
}

export interface TranscriptMessage {
  readonly id: number;
  readonly role: string;
  readonly content: string;
  readonly citations: Citation[] | null;
  readonly status: string | null;
  readonly created_at: string;
}

export interface RetrievedChunk {
  readonly chunk_id: string;
  readonly title: string;
  readonly section: string | null;
  readonly url: string;
  readonly snippet: string;
  readonly score: number;
}

export interface TurnReview {
  readonly raw_query: string;
  readonly normalized_query: string;
  readonly status: string;
  readonly refusal_trigger: string | null;
  readonly debug_requested: boolean;
  readonly debug_authorized: boolean;
  readonly llm_prompt_tokens: number | null;
  readonly retrieved_chunks: RetrievedChunk[];
  readonly created_at: string;
}

export interface ConversationTurn {
  readonly user_message: TranscriptMessage;
  readonly assistant_message: TranscriptMessage;
  readonly review: TurnReview;
}

export interface ConversationDetail {
  readonly conversation_id: string;
  readonly created_at: string;
  readonly updated_at: string;
  readonly turns: ConversationTurn[];
}

export async function listConversations(
  token: string,
  limit = 50,
  offset = 0,
): Promise<ConversationSummary[]> {
  const res = await fetch(
    `${BASE}/admin/conversations?limit=${limit}&offset=${offset}`,
    { headers: headers(token) },
  );
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json() as Promise<ConversationSummary[]>;
}

export async function getConversation(
  token: string,
  conversationId: string,
): Promise<ConversationDetail> {
  const res = await fetch(`${BASE}/admin/conversations/${conversationId}`, {
    headers: headers(token),
  });
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json() as Promise<ConversationDetail>;
}
