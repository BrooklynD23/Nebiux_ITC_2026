export function LoadingIndicator(): JSX.Element {
  return (
    <div className="loading-indicator" aria-label="Loading response">
      <span className="loading-indicator__dot" />
      <span className="loading-indicator__dot" />
      <span className="loading-indicator__dot" />
    </div>
  );
}
