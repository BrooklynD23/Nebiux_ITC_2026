import type { Citation } from '../types';

interface CitationListProps {
  readonly citations: readonly Citation[];
}

export function CitationList({ citations }: CitationListProps): JSX.Element | null {
  if (citations.length === 0) {
    return null;
  }

  return (
    <div className="citation-list">
      <p className="citation-list__heading">Sources:</p>
      <ul className="citation-list__items">
        {citations.map((citation, index) => (
          <li key={`${citation.url}-${index}`} className="citation-list__item">
            <a
              href={citation.url}
              target="_blank"
              rel="noopener noreferrer"
              className="citation-list__link"
              title={citation.snippet}
            >
              {citation.title}
            </a>
            <p className="citation-list__snippet">{citation.snippet}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
