/** Status values returned by the /chat endpoint. */
export type MessageStatus = 'answered' | 'not_found' | 'error';

/** A single citation returned alongside an answer. */
export interface Citation {
  readonly title: string;
  readonly url: string;
  readonly snippet: string;
}

/** Request body for POST /chat. */
export interface ChatRequest {
  readonly conversation_id?: string;
  readonly message: string;
}

/** Response body from POST /chat. */
export interface ChatResponse {
  readonly conversation_id: string;
  readonly status: MessageStatus;
  readonly answer_markdown: string;
  readonly citations: readonly Citation[];
}

/** Role of a message in the conversation. */
export type MessageRole = 'user' | 'assistant';

/** A single message displayed in the chat window. */
export interface Message {
  readonly id: string;
  readonly role: MessageRole;
  readonly content: string;
  readonly status?: MessageStatus;
  readonly citations?: readonly Citation[];
  readonly timestamp: number;
}
