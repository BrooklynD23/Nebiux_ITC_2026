import { ChatWindow } from './ChatWindow';
import { ErrorBanner } from './ErrorBanner';
import type { Message } from '../types';

interface FloatingChatPanelProps {
  readonly error: string | null;
  readonly isLoading: boolean;
  readonly isOpen: boolean;
  readonly messages: readonly Message[];
  readonly onClose: () => void;
  readonly onReset: () => void;
  readonly onSend: (message: string) => void;
}

export function FloatingChatPanel({
  error,
  isLoading,
  isOpen,
  messages,
  onClose,
  onReset,
  onSend,
}: FloatingChatPanelProps): JSX.Element | null {
  if (!isOpen) {
    return null;
  }

  return (
    <div className="chat-modal" role="dialog" aria-modal="true">
      <div className="chat-modal__header">
        <div>
          <p className="chat-modal__eyebrow">Student support popup</p>
          <h3 className="chat-modal__title">Bronco Assistant</h3>
        </div>

        <div className="chat-modal__actions">
          <button className="button button--ghost" onClick={onReset} type="button">
            Reset
          </button>
          <button className="button button--ghost" onClick={onClose} type="button">
            Close
          </button>
        </div>
      </div>

      {error && <ErrorBanner message={error} />}

      <ChatWindow isLoading={isLoading} messages={messages} onSend={onSend} />
    </div>
  );
}
