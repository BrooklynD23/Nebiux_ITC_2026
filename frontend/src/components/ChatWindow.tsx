import type { Message } from '../types';
import { ChatInput } from './ChatInput';
import { LoadingIndicator } from './LoadingIndicator';
import { MessageList } from './MessageList';
import { StarterPrompts } from './StarterPrompts';
import './ChatWindow.css';

interface ChatWindowProps {
  readonly messages: readonly Message[];
  readonly isLoading: boolean;
  readonly onSend: (message: string) => void;
}

export function ChatWindow({
  messages,
  isLoading,
  onSend,
}: ChatWindowProps): JSX.Element {
  const hasMessages = messages.length > 0;

  return (
    <div className="chat-window">
      <div className="chat-window__messages">
        {hasMessages ? (
          <MessageList messages={messages} />
        ) : (
          <StarterPrompts onSelect={onSend} />
        )}
        {isLoading && <LoadingIndicator />}
      </div>
      <ChatInput onSend={onSend} disabled={isLoading} />
    </div>
  );
}
