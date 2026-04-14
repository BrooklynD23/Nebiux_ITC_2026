import { useEffect, useRef } from 'react';
import { useSpeechPlayback } from '../hooks/useSpeechPlayback';
import type { Message } from '../types';
import { MessageBubble } from './MessageBubble';

interface MessageListProps {
  readonly messages: readonly Message[];
}

export function MessageList({ messages }: MessageListProps): JSX.Element {
  const bottomRef = useRef<HTMLDivElement>(null);
  const { isSupported, speakingMessageId, togglePlayback } =
    useSpeechPlayback();

  // Auto-scroll to the latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="message-list">
      {messages.map((message) => (
        <MessageBubble
          key={message.id}
          message={message}
          playbackSupported={isSupported}
          isSpeaking={speakingMessageId === message.id}
          onTogglePlayback={() => togglePlayback(message.id, message.content)}
        />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
