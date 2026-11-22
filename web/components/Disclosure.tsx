"use client";

import { useId, useState, type ReactNode } from "react";

type Props = {
  title: ReactNode;
  children: ReactNode;
  className?: string;
  defaultOpen?: boolean;
};

/** A button that shows the longer copy. Keyboard and aria-expanded stay on the button. */
export function Disclosure({ title, children, className, defaultOpen = false }: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const panelId = useId();
  const classes = className ? `rio-disclosure ${className}` : "rio-disclosure";
  return (
    <div className={classes}>
      <button type="button" aria-expanded={open} aria-controls={panelId} onClick={() => setOpen((value) => !value)}>
        <span className={open ? "rio-chevron is-open" : "rio-chevron"} aria-hidden="true" />
        {title}
      </button>
      <div id={panelId} hidden={!open}>
        {open ? children : null}
      </div>
    </div>
  );
}
