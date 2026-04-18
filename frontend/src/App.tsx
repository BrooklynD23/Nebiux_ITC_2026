import { useEffect, useState } from 'react';
import campusBackground from './assets/CPP_BG.jpg';
import cppLogo from './assets/cpp-logo.png';
import { listConversations } from './api/admin';
import type { ConversationSummary } from './api/admin';
import { ConversationTable } from './components/ConversationTable';
import { FloatingChatPanel } from './components/FloatingChatPanel';
import { StatCard } from './components/StatCard';
import { useChat } from './hooks/useChat';

type View = 'landing' | 'home' | 'admin';

type ResourcePreview = {
  title: string;
  description: string;
  url: string;
};

const LIBRARY_PREVIEW: ResourcePreview = {
  title: 'Library Hours',
  description:
    'Preview the library hours page with current building access and service schedules.',
  url: 'https://www.cpp.edu/library/hours/index.shtml',
};

const GRADUATION_PREVIEW: ResourcePreview = {
  title: 'Applying for Graduation',
  description:
    'Preview the registrar page with graduation requirements, deadlines, and next steps.',
  url: 'https://www.cpp.edu/registrar/graduation/applying-for-graduation.shtml',
};

const DINING_PREVIEW: ResourcePreview = {
  title: 'Dining Options',
  description:
    'Preview CPP dining resources with campus food locations and meal options.',
  url: 'https://www.cpp.edu/aboutcpp/visitor-information/dining.shtml',
};

const PARKING_PREVIEW: ResourcePreview = {
  title: 'Parking Information',
  description:
    'Preview parking and transportation details, including permits, maps, and visitor guidance.',
  url: 'https://www.cpp.edu/parking/',
};

const RESOURCE_PREVIEWS: readonly ResourcePreview[] = [
  LIBRARY_PREVIEW,
  GRADUATION_PREVIEW,
  DINING_PREVIEW,
  PARKING_PREVIEW,
];

function getPreviewForPrompt(prompt: string): ResourcePreview | null {
  const normalizedPrompt = prompt.trim().toLowerCase();

  if (normalizedPrompt.includes('graduation')) {
    return GRADUATION_PREVIEW;
  }

  if (normalizedPrompt.includes('parking')) {
    return PARKING_PREVIEW;
  }

  if (normalizedPrompt.includes('dining')) {
    return DINING_PREVIEW;
  }

  if (normalizedPrompt.includes('library')) {
    return LIBRARY_PREVIEW;
  }

  return null;
}

function getPreviewFromUrl(url: string): ResourcePreview {
  return (
    RESOURCE_PREVIEWS.find((preview) => preview.url === url) ?? {
      title: 'Official CPP page',
      description:
        'Preview the official campus resource referenced in the latest assistant answer.',
      url,
    }
  );
}


export default function App(): JSX.Element {
  const [activeView, setActiveView] = useState<View>('landing');
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [activePreview, setActivePreview] = useState<ResourcePreview | null>(null);
  const { messages, isLoading, error, send, resetConversation } = useChat();

  // Admin state
  const [adminToken, setAdminToken] = useState<string | null>(null);
  const [showTokenModal, setShowTokenModal] = useState(false);
  const [tokenInput, setTokenInput] = useState('');
  const [tokenError, setTokenError] = useState<string | null>(null);
  const [tokenLoading, setTokenLoading] = useState(false);
  const [adminSummaries, setAdminSummaries] = useState<ConversationSummary[]>([]);
  const [adminLoading, setAdminLoading] = useState(false);
  const [adminError, setAdminError] = useState<string | null>(null);

  const userMessages = messages.filter((message) => message.role === 'user');
  const answeredMessages = messages.filter(
    (message) => message.role === 'assistant' && message.status === 'answered',
  );
  const currentSessionQuestions = userMessages.length;
  const currentSessionAnswered = answeredMessages.length;

  // Admin stats derived from real data
  const adminTotalQuestions = adminSummaries.reduce((sum, s) => sum + s.turn_count, 0);
  const adminAnsweredCount = adminSummaries.filter((s) => s.last_status === 'answered').length;
  const adminRefusedCount = adminSummaries.filter(
    (s) => s.last_status !== null && s.last_status !== 'answered',
  ).length;

  const adminStats = [
    {
      label: 'Total conversations',
      value: `${adminSummaries.length}`,
      description: 'All stored conversations in the backend.',
    },
    {
      label: 'Questions asked',
      value: `${adminTotalQuestions}`,
      description: 'Sum of turns across all conversations.',
    },
    {
      label: 'Answered',
      value: `${adminAnsweredCount}`,
      description: 'Conversations where last status is "answered".',
    },
    {
      label: 'Refused / not found',
      value: `${adminRefusedCount}`,
      description: 'Conversations with a non-answered last status.',
    },
  ];

  const heroStats = [
    { label: 'Campus topics indexed', value: '1.2k+' },
    { label: 'Average response time', value: '< 2s' },
    { label: 'Support available', value: '24/7' },
  ];

  const supportPillars = [
    {
      title: 'Explore campus life',
      copy:
        'Learn more about academics, student services, dining, parking, and the day-to-day experience at Cal Poly Pomona.',
    },
    {
      title: 'Find answers with confidence',
      copy:
        'Get helpful guidance quickly so you can keep moving toward your next step.',
    },
    {
      title: 'Connect with real people',
      copy:
        'When you want to speak with someone directly, we can help you reach the right campus office.',
    },
  ];

  const landingMoments = [
    'Ask about admissions, financial aid, student life, or campus services.',
    'Browse answers and next steps in a way that feels welcoming and easy to follow.',
    'Reach out to university staff whenever your question needs a personal response.',
  ];

  useEffect(() => {
    const latestAssistantMessage = [...messages]
      .reverse()
      .find(
        (message) =>
          message.role === 'assistant' &&
          message.status === 'answered' &&
          message.citations &&
          message.citations.length > 0,
      );

    const latestCitationUrl = latestAssistantMessage?.citations?.[0]?.url;

    if (!latestCitationUrl) {
      return;
    }

    setActivePreview((currentPreview) => {
      if (currentPreview?.url === latestCitationUrl) {
        return currentPreview;
      }

      return getPreviewFromUrl(latestCitationUrl);
    });
  }, [messages]);

  function handlePromptSelection(prompt: string): void {
    const preview = getPreviewForPrompt(prompt);

    if (preview) {
      setActivePreview(preview);
    }

    setIsChatOpen(true);
    void send(prompt);
  }

  function handleAdminNavClick(): void {
    if (adminToken) {
      setActiveView('admin');
      return;
    }
    setShowTokenModal(true);
  }

  async function handleTokenSubmit(e: React.FormEvent): Promise<void> {
    e.preventDefault();
    setTokenLoading(true);
    setTokenError(null);
    try {
      const summaries = await listConversations(tokenInput);
      setAdminToken(tokenInput);
      setAdminSummaries(summaries);
      setShowTokenModal(false);
      setTokenInput('');
      setActiveView('admin');
    } catch (err) {
      const msg = err instanceof Error ? err.message : '';
      setTokenError(
        msg === '401' ? 'Invalid token.' : 'Could not connect to the server.',
      );
    } finally {
      setTokenLoading(false);
    }
  }

  async function refreshAdminData(): Promise<void> {
    if (!adminToken) return;
    setAdminLoading(true);
    setAdminError(null);
    try {
      const summaries = await listConversations(adminToken);
      setAdminSummaries(summaries);
    } catch {
      setAdminError('Failed to reload conversations.');
    } finally {
      setAdminLoading(false);
    }
  }

  return (
    <div className="site-shell">
      <div className="site-backdrop" />

      <header className="topbar">
        <button
          className="brand-lockup brand-lockup--button"
          onClick={() => setActiveView('landing')}
          type="button"
        >
          <img
            alt="Cal Poly Pomona logo"
            className="brand-lockup__logo"
            src={cppLogo}
          />
          <div>
            <p className="brand-lockup__eyebrow">Bronco Knowledge Assistant</p>
            <h1 className="brand-lockup__title">Cal Poly Pomona support hub</h1>
          </div>
        </button>

        <nav className="topbar__nav" aria-label="Primary navigation">
          <button
            className={`topbar__link ${activeView === 'landing' ? 'is-active' : ''}`}
            onClick={() => setActiveView('landing')}
            type="button"
          >
            Landing
          </button>
          <button
            className={`topbar__link ${activeView === 'home' ? 'is-active' : ''}`}
            onClick={() => setActiveView('home')}
            type="button"
          >
            Home
          </button>
          <button
            className={`topbar__link ${activeView === 'admin' ? 'is-active' : ''}`}
            onClick={handleAdminNavClick}
            type="button"
          >
            Admin
          </button>
        </nav>
      </header>

      <main className="page-frame">
        {activeView === 'landing' && (
          <div className="landing-page">
            <section
              className="hero-panel hero-panel--landing"
              style={{
                backgroundImage: `linear-gradient(180deg, rgba(7, 66, 42, 0.96) 0%, rgba(6, 60, 39, 0.92) 58%, rgba(6, 60, 39, 0.78) 78%, rgba(244, 248, 243, 0.88) 100%), linear-gradient(90deg, rgba(6, 60, 39, 0.88) 0%, rgba(6, 60, 39, 0.54) 26%, rgba(6, 60, 39, 0.18) 20%), url(${campusBackground})`,
              }}
            >
              <div className="hero-panel__content">
                <p className="section-kicker">Learn by doing</p>
                <h2 className="hero-panel__title">
                  Have Questions? We Have Answers.
                </h2>
                <p className="hero-panel__copy">
                  We are here to help families of future and current Broncos.<br></br>
                  Explore student life, discover resources, and feel more at home with
                  every question.
                </p>

                <div className="hero-panel__actions">
                  <button
                    className="button button--primary"
                    onClick={() => setActiveView('home')}
                    type="button"
                  >
                    Start asking
                  </button>
                  <a
                    className="button button--secondary button--link"
                    href="https://engage.cpp.edu/register/ask_us_a_question"
                    rel="noreferrer"
                    target="_blank"
                  >
                    Speak with campus staff
                  </a>
                </div>

                <div className="hero-metrics">
                  {heroStats.map((stat) => (
                    <article className="hero-metric" key={stat.label}>
                      <strong>{stat.value}</strong>
                      <span>{stat.label}</span>
                    </article>
                  ))}
                  <br></br>
                  <br></br>
                  <br></br>
                </div>
              </div>

              <div className="hero-panel__visual" aria-hidden="true">
                <div className="hero-panel__visual-mark">
                  <img alt="" src={cppLogo} />
                </div>
                <div className="hero-panel__visual-copy">
                  <span>Bronco-first support</span>
                  <strong>Friendly guidance for future students and families.</strong>
                </div>
              </div>
            </section>

            <section className="landing-support">
              <div className="landing-section-heading">
                <h3>If you want to...</h3>
              </div>

              <div className="landing-support__grid">
                {supportPillars.map((pillar) => (
                  <article className="landing-support__item" key={pillar.title}>
                    <h4>{pillar.title}</h4>
                    <p>{pillar.copy}</p>
                  </article>
                ))}
              </div>
            </section>

            <section className="landing-detail">
              <div className="landing-detail__intro">
                <h3>Start with a question and let us help guide the way.</h3>
              </div>

              <div className="landing-detail__steps">
                {landingMoments.map((step) => (
                  <div className="landing-detail__step" key={step}>
                    <span />
                    <p>{step}</p>
                  </div>
                ))}
              </div>
            </section>

            <section className="landing-cta landing-cta--split">
              <div>
                <h3>Have a unique question? Speak to staff.</h3>
                <p className="landing-cta__copy">
                  If you would rather connect with someone on campus directly,
                  we would be glad to help you reach the right team.
                </p>
              </div>
              <div className="landing-cta__actions">
                <a
                  className="button button--primary button--link"
                  href="https://engage.cpp.edu/register/ask_us_a_question"
                  rel="noreferrer"
                  target="_blank"
                >
                  Contact campus staff
                </a>
                <button
                  className="button button--secondary"
                  onClick={() => setActiveView('home')}
                  type="button"
                >
                  Ask Bronco Assistant first
                </button>
              </div>
            </section>
          </div>
        )}

        {activeView === 'home' && (
          <section className="workspace-grid">
            <div className="workspace-card workspace-card--feature">
              <p className="section-kicker">Welcome!</p>
              <h2>Bronco Assistant</h2>
              <p>
                Let the assistant help with admissions, advising, dining,
                parking, and everyday questions about campus life.
              </p>

              <div className="signal-strip">
                <div>
                  <span># Questions Asked</span>
                  <strong>{currentSessionQuestions}</strong>
                </div>
                <div>
                  <span># Responses Returned</span>
                  <strong>{currentSessionAnswered}</strong>
                </div>
                <div>
                  <span>Chat state</span>
                  <strong>{isChatOpen ? 'Open' : 'Closed'}</strong>
                </div>
              </div>

              <section
                aria-labelledby="resource-preview-title"
                className="resource-preview"
              >
                {activePreview ? (
                  <>
                    <div className="resource-preview__header">
                      <div>
                        <p className="section-kicker">Website preview</p>
                        <h3 id="resource-preview-title">{activePreview.title}</h3>
                      </div>
                      <a
                        className="button button--secondary button--link resource-preview__link"
                        href={activePreview.url}
                        rel="noreferrer"
                        target="_blank"
                      >
                        Open full page
                      </a>
                    </div>
                    <p className="resource-preview__copy">
                      {activePreview.description}
                    </p>
                    <div className="resource-preview__frame">
                      <iframe
                        loading="lazy"
                        referrerPolicy="strict-origin-when-cross-origin"
                        src={activePreview.url}
                        title={activePreview.title}
                      />
                    </div>
                  </>
                ) : (
                  <div className="resource-preview__empty" aria-hidden="true" />
                )}
              </section>
            </div>

            <div className="workspace-card">
              <p className="section-kicker">Quick links</p>
              <div className="quick-links">
                <button
                  className="quick-links__item"
                  onClick={() => handlePromptSelection('How do I apply for graduation?')}
                  type="button"
                >
                  Graduation help
                </button>
                <button
                  className="quick-links__item"
                  onClick={() => handlePromptSelection('Where can I find parking information?')}
                  type="button"
                >
                  Parking info
                </button>
                <button
                  className="quick-links__item"
                  onClick={() => handlePromptSelection('What dining options are on campus?')}
                  type="button"
                >
                  Dining options
                </button>
              </div>
            </div>

            <button
              className="chat-launcher"
              onClick={() => setIsChatOpen(true)}
              type="button"
            >
              <span className="chat-launcher__label">Ask Bronco Assistant</span>
              <span className="chat-launcher__meta">
                Chat popup for campus questions
              </span>
            </button>

            <FloatingChatPanel
              error={error}
              isLoading={isLoading}
              isOpen={isChatOpen}
              messages={messages}
              onClose={() => setIsChatOpen(false)}
              onReset={() => {
                setActivePreview(null);
                resetConversation();
              }}
              onSend={handlePromptSelection}
            />
          </section>
        )}

        {activeView === 'admin' && (
          <section className="dashboard">
            <div className="dashboard__header">
              <div>
                <p className="section-kicker">Admin dashboard</p>
                <h2>Conversation review</h2>
              </div>
              <div className="dashboard__header-actions">
                <button
                  className="button button--secondary"
                  disabled={adminLoading}
                  onClick={() => void refreshAdminData()}
                  type="button"
                >
                  {adminLoading ? 'Refreshing…' : 'Refresh'}
                </button>
                <button
                  className="button button--secondary"
                  onClick={() => setActiveView('home')}
                  type="button"
                >
                  Return to home
                </button>
              </div>
            </div>

            {adminError && (
              <div className="error-banner" role="alert">
                <span>{adminError}</span>
              </div>
            )}

            <div className="stats-grid">
              {adminStats.map((stat) => (
                <StatCard
                  key={stat.label}
                  label={stat.label}
                  value={stat.value}
                  description={stat.description}
                />
              ))}
            </div>

            <div className="dashboard__content dashboard__content--full">
              <section className="dashboard-panel">
                <div className="dashboard-panel__header">
                  <h3>Conversations</h3>
                  <p>{adminSummaries.length} total — click a row to expand</p>
                </div>
                {adminSummaries.length === 0 ? (
                  <p className="conv-empty">No conversations found.</p>
                ) : (
                  <ConversationTable summaries={adminSummaries} token={adminToken!} />
                )}
              </section>
            </div>
          </section>
        )}
      </main>

      {showTokenModal && (
        <div
          className="token-modal"
          onClick={() => {
            setShowTokenModal(false);
            setTokenError(null);
            setTokenInput('');
          }}
        >
          <div
            className="token-modal__card"
            onClick={(e) => e.stopPropagation()}
          >
            <h3>Admin access</h3>
            <p>Enter your API token to view the admin dashboard.</p>
            <form onSubmit={(e) => void handleTokenSubmit(e)}>
              <input
                autoFocus
                className="token-modal__input"
                onChange={(e) => setTokenInput(e.target.value)}
                placeholder="Bearer token"
                type="password"
                value={tokenInput}
              />
              {tokenError && (
                <p className="token-modal__error">{tokenError}</p>
              )}
              <div className="token-modal__actions">
                <button
                  className="button button--primary"
                  disabled={tokenLoading || !tokenInput}
                  type="submit"
                >
                  {tokenLoading ? 'Verifying…' : 'Confirm'}
                </button>
                <button
                  className="button button--secondary"
                  onClick={() => {
                    setShowTokenModal(false);
                    setTokenError(null);
                    setTokenInput('');
                  }}
                  type="button"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
