import { useCallback, useState } from 'react';
import type { FormEvent, KeyboardEvent } from 'react';

interface ChatInputProps {
  readonly onSend: (message: string) => void;
  readonly disabled?: boolean;
}

export function ChatInput({
  onSend,
  disabled = false,
}: ChatInputProps): JSX.Element {
  const [value, setValue] = useState('');

  const handleSubmit = useCallback(
    (e: FormEvent): void => {
      e.preventDefault();
      const trimmed = value.trim();
      if (trimmed.length === 0 || disabled) return;
      onSend(trimmed);
      setValue('');
    },
    [value, disabled, onSend],
  );

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>): void => {
      // Submit on Enter, allow Shift+Enter for newlines
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        const trimmed = value.trim();
        if (trimmed.length === 0 || disabled) return;
        onSend(trimmed);
        setValue('');
      }
    },
    [value, disabled, onSend],
  );

  return (
    <form className="chat-input" onSubmit={handleSubmit}>
      <textarea
        className="chat-input__textarea"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask about Cal Poly Pomona..."
        disabled={disabled}
        rows={1}
        aria-label="Message input"
      />
      <button
        className="chat-input__send"
        type="submit"
        disabled={disabled || value.trim().length === 0}
        aria-label="Send message"
      >
        Send
      </button>
    </form>
  );
}
