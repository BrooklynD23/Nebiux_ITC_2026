const STARTER_QUESTIONS: readonly string[] = [
  'What are the library hours?',
  'How do I apply for graduation?',
  'What dining options are on campus?',
  'Where can I find parking information?',
];

interface StarterPromptsProps {
  readonly onSelect: (question: string) => void;
}

export function StarterPrompts({
  onSelect,
}: StarterPromptsProps): JSX.Element {
  return (
    <div className="starter-prompts">
      <p className="starter-prompts__heading">
        Ask me anything about Cal Poly Pomona:
      </p>
      <div className="starter-prompts__buttons">
        {STARTER_QUESTIONS.map((question) => (
          <button
            key={question}
            className="starter-prompts__button"
            onClick={() => onSelect(question)}
            type="button"
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  );
}
