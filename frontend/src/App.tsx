import { useState } from 'react';
import { FloatingChatPanel } from './components/FloatingChatPanel';
import { StatCard } from './components/StatCard';
import { UserTable } from './components/UserTable';
import { MOCK_ACTIVITY, MOCK_USERS } from './data/admin';
import { useChat } from './hooks/useChat';

type View = 'landing' | 'home' | 'admin';

function formatTimestamp(timestamp: number): string {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(timestamp);
}

export default function App(): JSX.Element {
  const [activeView, setActiveView] = useState<View>('landing');
  const [isChatOpen, setIsChatOpen] = useState(false);
  const { messages, isLoading, error, send, resetConversation } = useChat();

  const userMessages = messages.filter((message) => message.role === 'user');
  const answeredMessages = messages.filter(
    (message) => message.role === 'assistant' && message.status === 'answered',
  );
  const totalConversations = MOCK_USERS.reduce(
    (total, user) => total + user.conversations,
    0,
  );
  const currentSessionQuestions = userMessages.length;
  const currentSessionAnswered = answeredMessages.length;
  const dashboardUsers = [...MOCK_USERS];

  if (currentSessionQuestions > 0) {
    dashboardUsers.unshift({
      id: 'session-now',
      name: 'Current visitor',
      role: 'Prospective student',
      status: isLoading ? 'Active now' : 'Exploring',
      conversations: 1,
      lastQuestion:
        userMessages[userMessages.length - 1]?.content ?? 'Started a session',
      channel: 'Website popup',
      satisfaction: currentSessionAnswered > 0 ? 'Positive' : 'Pending',
    });
  }

  const activityFeed =
    currentSessionQuestions > 0
      ? [
          {
            id: 'session-feed',
            label: 'Live website session',
            detail: `${
              userMessages[userMessages.length - 1]?.content ?? 'Chat opened'
            }`,
            time: formatTimestamp(Date.now()),
          },
          ...MOCK_ACTIVITY,
        ]
      : MOCK_ACTIVITY;

  const heroStats = [
    { label: 'Campus topics indexed', value: '1.2k+' },
    { label: 'Average response time', value: '< 2s' },
    { label: 'Student support coverage', value: '24/7' },
  ];

  const overviewStats = [
    {
      label: 'Tracked users',
      value: `${dashboardUsers.length}`,
      description: 'Visitors represented in the dashboard overview.',
    },
    {
      label: 'Conversations',
      value: `${totalConversations + (currentSessionQuestions > 0 ? 1 : 0)}`,
      description: 'Sessions started across web, kiosk, and advisor channels.',
    },
    {
      label: 'Questions answered',
      value: `${53 + currentSessionAnswered}`,
      description: 'Resolved prompts with citations and grounded answers.',
    },
    {
      label: 'Live intent signals',
      value: `${currentSessionQuestions}`,
      description: 'Prompts collected from the current browser session.',
    },
  ];

  return (
    <div className="site-shell">
      <div className="site-backdrop" />

      <header className="topbar">
        <div className="brand-lockup">
          <span className="brand-lockup__badge">CPP</span>
          <div>
            <p className="brand-lockup__eyebrow">Bronco Knowledge Assistant</p>
            <h1 className="brand-lockup__title">Cal Poly Pomona support hub</h1>
          </div>
        </div>

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
            onClick={() => setActiveView('admin')}
            type="button"
          >
            Admin
          </button>
        </nav>
      </header>

      <main className="page-frame">
        {activeView === 'landing' && (
          <section className="hero-panel">
            <div className="hero-panel__content">
              <p className="section-kicker">Landing page</p>
              <h2 className="hero-panel__title">
                A front door for Cal Poly Pomona questions, guidance, and
                campus support.
              </h2>
              <p className="hero-panel__copy">
                This skeletal frontend framework gives the project a branded
                landing page, a student-facing home experience with a chatbot
                popup, and an admin dashboard ready to plug into real analytics.
              </p>

              <div className="hero-panel__actions">
                <button
                  className="button button--primary"
                  onClick={() => setActiveView('home')}
                  type="button"
                >
                  Open student home
                </button>
                <button
                  className="button button--secondary"
                  onClick={() => setActiveView('admin')}
                  type="button"
                >
                  View admin dashboard
                </button>
              </div>

              <div className="hero-metrics">
                {heroStats.map((stat) => (
                  <article className="hero-metric" key={stat.label}>
                    <strong>{stat.value}</strong>
                    <span>{stat.label}</span>
                  </article>
                ))}
              </div>
            </div>

            <aside className="preview-card">
              <p className="section-kicker">Framework coverage</p>
              <h3>Designed around the frontend you asked for</h3>
              <ul className="preview-card__list">
                <li>Landing page for onboarding and value proposition</li>
                <li>Home page with floating chatbot popup and quick actions</li>
                <li>Admin dashboard with user overview and recent activity</li>
                <li>Frontend-only analytics placeholders for future APIs</li>
              </ul>
            </aside>
          </section>
        )}

        {activeView === 'home' && (
          <section className="workspace-grid">
            <div className="workspace-card workspace-card--feature">
              <p className="section-kicker">Home page</p>
              <h2>Guide students to the right answer faster.</h2>
              <p>
                Keep the main experience lightweight, then let the chatbot step
                in as a contextual popup for admissions, advising, dining,
                parking, and campus life questions.
              </p>

              <div className="signal-strip">
                <div>
                  <span>Current prompts sent</span>
                  <strong>{currentSessionQuestions}</strong>
                </div>
                <div>
                  <span>Responses returned</span>
                  <strong>{currentSessionAnswered}</strong>
                </div>
                <div>
                  <span>Chat state</span>
                  <strong>{isChatOpen ? 'Open' : 'Closed'}</strong>
                </div>
              </div>
            </div>

            <div className="workspace-card">
              <p className="section-kicker">Quick links</p>
              <div className="quick-links">
                <button
                  className="quick-links__item"
                  onClick={() => {
                    setIsChatOpen(true);
                    void send('How do I apply for graduation?');
                  }}
                  type="button"
                >
                  Graduation help
                </button>
                <button
                  className="quick-links__item"
                  onClick={() => {
                    setIsChatOpen(true);
                    void send('Where can I find parking information?');
                  }}
                  type="button"
                >
                  Parking info
                </button>
                <button
                  className="quick-links__item"
                  onClick={() => {
                    setIsChatOpen(true);
                    void send('What dining options are on campus?');
                  }}
                  type="button"
                >
                  Dining options
                </button>
              </div>
            </div>

            <div className="workspace-card workspace-card--status">
              <p className="section-kicker">Implementation note</p>
              <h3>Ready for real usage telemetry</h3>
              <p>
                The dashboard is wired to reflect this session immediately and
                includes mock records so the layout is useful before the backend
                analytics endpoints exist.
              </p>
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
              onReset={resetConversation}
              onSend={(text) => {
                void send(text);
              }}
            />
          </section>
        )}

        {activeView === 'admin' && (
          <section className="dashboard">
            <div className="dashboard__header">
              <div>
                <p className="section-kicker">Admin dashboard</p>
                <h2>Overview of the people using the campus assistant.</h2>
              </div>
              <button
                className="button button--secondary"
                onClick={() => setActiveView('home')}
                type="button"
              >
                Return to home
              </button>
            </div>

            <div className="stats-grid">
              {overviewStats.map((stat) => (
                <StatCard
                  key={stat.label}
                  label={stat.label}
                  value={stat.value}
                  description={stat.description}
                />
              ))}
            </div>

            <div className="dashboard__content">
              <section className="dashboard-panel">
                <div className="dashboard-panel__header">
                  <h3>User overview</h3>
                  <p>Placeholder table for the records your backend will feed.</p>
                </div>
                <UserTable users={dashboardUsers} />
              </section>

              <section className="dashboard-panel">
                <div className="dashboard-panel__header">
                  <h3>Recent activity</h3>
                  <p>Combines seed data with the current browser session.</p>
                </div>

                <div className="activity-feed">
                  {activityFeed.map((item) => (
                    <article className="activity-feed__item" key={item.id}>
                      <div>
                        <strong>{item.label}</strong>
                        <p>{item.detail}</p>
                      </div>
                      <span>{item.time}</span>
                    </article>
                  ))}
                </div>
              </section>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
