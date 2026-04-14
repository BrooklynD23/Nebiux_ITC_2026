import { useCallback, useRef, useState } from 'react';
import type { FormEvent, KeyboardEvent } from 'react';
import { useVoiceInput } from '../hooks/useVoiceInput';

interface ChatInputProps {
  readonly onSend: (message: string) => void;
  readonly disabled?: boolean;
}

export function ChatInput({
  onSend,
  disabled = false,
}: ChatInputProps): JSX.Element {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { helperText, isSupported, status, toggleCapture } = useVoiceInput({
    disabled,
    onTranscript: (transcript) => {
      setValue((current) => {
        const trimmedCurrent = current.trim();
        if (trimmedCurrent.length === 0) {
          return transcript;
        }
        return `${current.trimEnd()} ${transcript}`;
      });
      textareaRef.current?.focus();
    },
  });

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
      <div className="chat-input__controls">
        <div className="chat-input__field-group">
          <textarea
            ref={textareaRef}
            className="chat-input__textarea"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about Cal Poly Pomona..."
            disabled={disabled}
            rows={1}
            aria-label="Message input"
            aria-describedby={helperText ? 'voice-helper-text' : undefined}
          />
          <button
            className={`chat-input__voice-button chat-input__voice-button--${status}`}
            type="button"
            onClick={() => {
              void toggleCapture();
            }}
            disabled={
              disabled ||
              status === 'processing' ||
              (!isSupported && status !== 'error')
            }
            aria-label={
              status === 'listening'
                ? 'Stop voice input'
                : 'Start voice input'
            }
          >
            {status === 'listening'
              ? 'Stop'
              : status === 'processing'
                ? 'Working...'
                : 'Voice'}
          </button>
        </div>

        <button
          className="chat-input__send"
          type="submit"
          disabled={disabled || value.trim().length === 0}
          aria-label="Send message"
        >
          Send
        </button>
      </div>

      {helperText && (
        <p
          id="voice-helper-text"
          className={`chat-input__helper chat-input__helper--${status}`}
          role="status"
          aria-live="polite"
        >
          {helperText}
        </p>
      )}
    </form>
  );
}
