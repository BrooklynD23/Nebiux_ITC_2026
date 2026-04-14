interface AssistantAudioButtonProps {
  readonly isSpeaking: boolean;
  readonly onToggle: () => void;
}

export function AssistantAudioButton({
  isSpeaking,
  onToggle,
}: AssistantAudioButtonProps): JSX.Element {
  return (
    <button
      className="assistant-audio-button"
      type="button"
      onClick={onToggle}
      aria-label={isSpeaking ? 'Stop reading this answer aloud' : 'Read this answer aloud'}
    >
      {isSpeaking ? 'Stop' : 'Read aloud'}
    </button>
  );
}
