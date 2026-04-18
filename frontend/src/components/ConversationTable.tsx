import { useState } from 'react';
import { getConversation } from '../api/admin';
import type { ConversationDetail, ConversationSummary } from '../api/admin';

interface Props {
  readonly summaries: readonly ConversationSummary[];
  readonly token: string;
}

type DetailEntry = ConversationDetail | 'loading' | 'error';

function formatDate(iso: string): string {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(iso));
}

export function ConversationTable({ summaries, token }: Props): JSX.Element {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [detailCache, setDetailCache] = useState<Record<string, DetailEntry>>({});

  async function handleRowClick(id: string): Promise<void> {
    if (expandedId === id) {
      setExpandedId(null);
      return;
    }
    setExpandedId(id);
    if (detailCache[id]) return;
    setDetailCache((prev) => ({ ...prev, [id]: 'loading' }));
    try {
      const detail = await getConversation(token, id);
      setDetailCache((prev) => ({ ...prev, [id]: detail }));
    } catch {
      setDetailCache((prev) => ({ ...prev, [id]: 'error' }));
    }
  }

  return (
    <div className="user-table-wrapper">
      <table className="user-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Started</th>
            <th>Turns</th>
            <th>Last status</th>
            <th>Last question</th>
            <th aria-label="Expand" />
          </tr>
        </thead>
        <tbody>
          {summaries.map((s) => {
            const isExpanded = expandedId === s.conversation_id;
            const detail = detailCache[s.conversation_id];
            return (
              <>
                <tr
                  key={s.conversation_id}
                  className={`conv-row${isExpanded ? ' conv-row--expanded' : ''}`}
                  onClick={() => void handleRowClick(s.conversation_id)}
                >
                  <td>
                    <code className="conv-id" title={s.conversation_id}>
                      {s.conversation_id.slice(0, 8)}
                    </code>
                  </td>
                  <td>{formatDate(s.created_at)}</td>
                  <td>{s.turn_count}</td>
                  <td>
                    <span className={`status-badge status-badge--${s.last_status ?? 'unknown'}`}>
                      {s.last_status ?? '—'}
                    </span>
                  </td>
                  <td className="conv-preview">{s.last_user_message_preview ?? '—'}</td>
                  <td className="conv-expand-toggle">{isExpanded ? '▲' : '▼'}</td>
                </tr>

                {isExpanded && (
                  <tr key={`${s.conversation_id}-detail`} className="conv-detail-row">
                    <td colSpan={6}>
                      {detail === 'loading' && (
                        <p className="conv-detail-state">Loading…</p>
                      )}
                      {detail === 'error' && (
                        <p className="conv-detail-state conv-detail-state--error">
                          Failed to load conversation.
                        </p>
                      )}
                      {detail && detail !== 'loading' && detail !== 'error' && (
                        <div className="conv-turns">
                          {detail.turns.map((turn, i) => (
                            <div key={i} className="conv-turn">
                              <div className="conv-turn__badge">Turn {i + 1}</div>

                              <div className="conv-turn__block">
                                <span className="conv-turn__label">Question</span>
                                <p>{turn.review.raw_query}</p>
                              </div>

                              <div className="conv-turn__block">
                                <span className="conv-turn__label">Answer</span>
                                <p>{turn.assistant_message.content}</p>
                              </div>

                              {turn.assistant_message.citations &&
                                turn.assistant_message.citations.length > 0 && (
                                  <div className="conv-turn__block">
                                    <span className="conv-turn__label">Sources</span>
                                    <ul className="conv-turn__sources">
                                      {turn.assistant_message.citations.map((c, ci) => (
                                        <li key={ci}>
                                          <a href={c.url} target="_blank" rel="noreferrer">
                                            {c.title}
                                          </a>
                                          {c.snippet && (
                                            <span className="conv-turn__snippet"> — {c.snippet}</span>
                                          )}
                                        </li>
                                      ))}
                                    </ul>
                                  </div>
                                )}

                              <div className="conv-turn__meta">
                                <span>
                                  <strong>Status:</strong> {turn.review.status}
                                </span>
                                {turn.review.llm_prompt_tokens != null && (
                                  <span>
                                    <strong>Tokens:</strong>{' '}
                                    {turn.review.llm_prompt_tokens.toLocaleString()}
                                  </span>
                                )}
                                {turn.review.refusal_trigger && (
                                  <span>
                                    <strong>Refusal:</strong> {turn.review.refusal_trigger}
                                  </span>
                                )}
                                {turn.review.normalized_query !== turn.review.raw_query && (
                                  <span>
                                    <strong>Normalized:</strong> {turn.review.normalized_query}
                                  </span>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </td>
                  </tr>
                )}
              </>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
