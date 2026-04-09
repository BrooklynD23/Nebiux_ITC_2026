interface ErrorBannerProps {
  readonly message: string;
  readonly onDismiss?: () => void;
}

export function ErrorBanner({
  message,
  onDismiss,
}: ErrorBannerProps): JSX.Element {
  return (
    <div className="error-banner" role="alert">
      <p className="error-banner__text">{message}</p>
      {onDismiss && (
        <button
          className="error-banner__dismiss"
          onClick={onDismiss}
          type="button"
          aria-label="Dismiss error"
        >
          Dismiss
        </button>
      )}
    </div>
  );
}
