import { useCallback, useState } from 'react';
import { sendMessage } from '../api/client';
import type { Message } from '../types';

interface UseChatReturn {
  readonly messages: readonly Message[];
  readonly conversationId: string | undefined;
  readonly isLoading: boolean;
  readonly error: string | null;
  readonly send: (text: string) => Promise<void>;
  readonly resetConversation: () => void;
}

function createId(): string {
  return crypto.randomUUID();
}

/**
 * Custom hook that manages the full conversation lifecycle.
 *
 * Handles sending messages, tracking loading/error state,
 * and building the message history for display.
 */
export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<readonly Message[]>([]);
  const [conversationId, setConversationId] = useState<string | undefined>(
    undefined,
  );
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const send = useCallback(
    async (text: string): Promise<void> => {
      const trimmed = text.trim();
      if (trimmed.length === 0) return;

      // Clear any previous error
      setError(null);

      // Add user message
      const userMessage: Message = {
        id: createId(),
        role: 'user',
        content: trimmed,
        timestamp: Date.now(),
      };

      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);

      try {
        const response = await sendMessage(conversationId, trimmed);

        // Track conversation ID from first response
        if (!conversationId) {
          setConversationId(response.conversation_id);
        }

        const assistantMessage: Message = {
          id: createId(),
          role: 'assistant',
          content: response.answer_markdown,
          status: response.status,
          citations: response.citations,
          timestamp: Date.now(),
        };

        setMessages((prev) => [...prev, assistantMessage]);
      } catch (err) {
        const errorMsg =
          err instanceof Error ? err.message : 'An unexpected error occurred';
        setError(errorMsg);

        // Add an error message to the chat
        const errorMessage: Message = {
          id: createId(),
          role: 'assistant',
          content: 'Sorry, something went wrong. Please try again.',
          status: 'error',
          citations: [],
          timestamp: Date.now(),
        };

        setMessages((prev) => [...prev, errorMessage]);
      } finally {
        setIsLoading(false);
      }
    },
    [conversationId],
  );

  const resetConversation = useCallback((): void => {
    setMessages([]);
    setConversationId(undefined);
    setIsLoading(false);
    setError(null);
  }, []);

  return {
    messages,
    conversationId,
    isLoading,
    error,
    send,
    resetConversation,
  };
}
