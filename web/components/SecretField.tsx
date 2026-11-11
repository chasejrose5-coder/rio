"use client";

import { useState } from "react";

export function SecretField({
  id,
  autoComplete,
  value,
  onChange,
}: {
  id: string;
  autoComplete: string;
  value: string;
  onChange: (value: string) => void;
}) {
  const [shown, setShown] = useState(false);
  return (
    <div className="rio-password">
      <input
        id={id}
        type={shown ? "text" : "password"}
        autoComplete={autoComplete}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
      <button
        type="button"
        className="rio-eye"
        aria-label={shown ? "Hide password" : "Show password"}
        onMouseDown={(event) => event.preventDefault()}
        onClick={() => setShown((current) => !current)}
      >
        <Eye open={shown} />
      </button>
    </div>
  );
}

function Eye({ open }: { open: boolean }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.7"
      />
      <circle cx="12" cy="12" r="2.6" fill="none" stroke="currentColor" strokeWidth="1.7" />
      {open ? <path d="M4 5l16 14" stroke="currentColor" strokeWidth="1.7" /> : null}
    </svg>
  );
}
