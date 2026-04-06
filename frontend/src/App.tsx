import { useCallback } from 'react';
import { ChatWindow } from './components/ChatWindow';
import { ErrorBanner } from './components/ErrorBanner';
import { useChat } from './hooks/useChat';

export default function App(): JSX.Element {
  const { messages, isLoading, error, send, resetConversation } = useChat();

  const handleSend = useCallback(
    (text: string): void => {
      void send(text);
    },
    [send],
  );

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="app-header__title">CPP Campus Knowledge Agent</h1>
        <button
          className="app-header__reset"
          onClick={resetConversation}
          type="button"
        >
          Reset Conversation
        </button>
      </header>

      {error && <ErrorBanner message={error} />}

      <ChatWindow
        messages={messages}
        isLoading={isLoading}
        onSend={handleSend}
      />
    </div>
  );
}
