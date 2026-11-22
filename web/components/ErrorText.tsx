import type { ReactNode } from "react";

/** A visible, announced error. The "Error:" prefix is read with the message. */
export function ErrorText({ children, testId }: { children: ReactNode; testId?: string }) {
  if (children == null || children === false || children === "") return null;
  return (
    <p className="rio-error" role="alert" data-testid={testId}>
      <span className="rio-error-prefix">Error:</span> {children}
    </p>
  );
}

/** A load that failed, with a way to run it again. */
export function LoadError({ message, onRetry, testId }: { message: string; onRetry: () => void; testId?: string }) {
  if (!message) return null;
  return (
    <div className="rio-load-error">
      <ErrorText testId={testId}>{message}</ErrorText>
      <button type="button" className="rio-secondary" onClick={onRetry}>
        Try again
      </button>
    </div>
  );
}
