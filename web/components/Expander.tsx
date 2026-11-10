import type { ReactNode, SyntheticEvent } from "react";

type Props = {
  title: ReactNode;
  children: ReactNode;
  className?: string;
  /** Controlled open state. Leave unset to let the browser toggle it. */
  open?: boolean;
  /** Starts open. The person can still close it. */
  defaultOpen?: boolean;
  onToggle?: (event: SyntheticEvent<HTMLDetailsElement>) => void;
};

/** The Streamlit expander: a thin gray chevron and a regular-weight title. */
export function Expander({ title, children, className, open, defaultOpen, onToggle }: Props) {
  const classes = className ? `rio-expander ${className}` : "rio-expander";
  return (
    <details className={classes} open={open ?? (defaultOpen ? true : undefined)} onToggle={onToggle}>
      <summary>
        <span className="rio-chevron" aria-hidden="true" />
        {title}
      </summary>
      {children}
    </details>
  );
}
