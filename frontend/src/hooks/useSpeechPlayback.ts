import { useCallback, useEffect, useMemo, useState } from 'react';

function stripMarkdownForSpeech(markdown: string): string {
  return markdown
    .replace(/!\[[^\]]*]\([^)]*\)/g, ' ')
    .replace(/\[([^\]]+)]\([^)]*\)/g, '$1')
    .replace(/`{1,3}([^`]+)`{1,3}/g, '$1')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/[*_~>-]/g, ' ')
    .replace(/\n+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

interface UseSpeechPlaybackReturn {
  readonly isSupported: boolean;
  readonly speakingMessageId: string | null;
  readonly togglePlayback: (messageId: string, markdown: string) => void;
}

export function useSpeechPlayback(): UseSpeechPlaybackReturn {
  const [speakingMessageId, setSpeakingMessageId] = useState<string | null>(
    null,
  );

  const isSupported = useMemo(
    () =>
      typeof window !== 'undefined' &&
      'speechSynthesis' in window &&
      'SpeechSynthesisUtterance' in window,
    [],
  );

  const stopPlayback = useCallback((): void => {
    if (!isSupported) {
      return;
    }

    window.speechSynthesis.cancel();
    setSpeakingMessageId(null);
  }, [isSupported]);

  const togglePlayback = useCallback(
    (messageId: string, markdown: string): void => {
      if (!isSupported) {
        return;
      }

      if (speakingMessageId === messageId) {
        stopPlayback();
        return;
      }

      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(
        stripMarkdownForSpeech(markdown),
      );

      utterance.rate = 1;
      utterance.onend = () => setSpeakingMessageId((current) => {
        if (current === messageId) {
          return null;
        }
        return current;
      });
      utterance.onerror = () => setSpeakingMessageId((current) => {
        if (current === messageId) {
          return null;
        }
        return current;
      });

      setSpeakingMessageId(messageId);
      window.speechSynthesis.speak(utterance);
    },
    [isSupported, speakingMessageId, stopPlayback],
  );

  useEffect(() => stopPlayback, [stopPlayback]);

  return {
    isSupported,
    speakingMessageId,
    togglePlayback,
  };
}
