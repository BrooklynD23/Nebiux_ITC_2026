import ReactMarkdown from 'react-markdown';
import type { Message } from '../types';
import { AssistantAudioButton } from './AssistantAudioButton';
import { CitationList } from './CitationList';
import { RefusalMessage } from './RefusalMessage';

interface MessageBubbleProps {
  readonly message: Message;
  readonly onTogglePlayback?: () => void;
  readonly playbackSupported?: boolean;
  readonly isSpeaking?: boolean;
}

export function MessageBubble({
  message,
  onTogglePlayback,
  playbackSupported = false,
  isSpeaking = false,
}: MessageBubbleProps): JSX.Element {
  const isUser = message.role === 'user';
  const isNotFound = message.status === 'not_found';
  const isError = message.status === 'error';

  return (
    <div
      className={`message-bubble message-bubble--${message.role}`}
      data-status={message.status}
    >
      <div className="message-bubble__content">
        {isNotFound ? (
          <RefusalMessage />
        ) : isError ? (
          <p className="message-bubble__error">{message.content}</p>
        ) : isUser ? (
          <p>{message.content}</p>
        ) : (
          <ReactMarkdown>{message.content}</ReactMarkdown>
        )}
      </div>

      {!isUser && !isNotFound && !isError && playbackSupported && onTogglePlayback && (
        <AssistantAudioButton
          isSpeaking={isSpeaking}
          onToggle={onTogglePlayback}
        />
      )}

      {!isUser && message.citations && message.citations.length > 0 && (
        <CitationList citations={message.citations} />
      )}
    </div>
  );
}
