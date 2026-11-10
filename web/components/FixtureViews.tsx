"use client";

import { useEffect, useState, type ReactNode } from "react";
import { Footer } from "./Footer";
import { Nav } from "./Nav";
import { RequireUser } from "./RequireUser";
import { useAdminOnly } from "./useAdminOnly";
import { ApiError, api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatDate } from "@/lib/plan";
import type { FixturePrescription, LedgerBody, PlannedRow } from "@/lib/types";

function Shell({ title, subtitle, banner, children }: { title: string; subtitle?: string; banner?: string | null; children: ReactNode }) {
  const allowed = useAdminOnly();
  return (
    <RequireUser>
      <div className="page-fixture">
        <Nav />
        <main>
          <header className="rio-hero">
            {banner ? <p className="rio-synthetic">{banner}</p> : null}
            <h1>{title}</h1>
            {subtitle ? <p className="rio-range">{subtitle}</p> : null}
          </header>
          {allowed ? children : <p className="rio-wait">Loading</p>}
          <Footer />
        </main>
      </div>
    </RequireUser>
  );
}

function plain(value: unknown): string {
  if (Array.isArray(value)) {
    const text = value.map((item) => String(item).trim()).filter(Boolean).join(", ");
    return text || "—";
  }
  if (value === null || value === undefined) return "—";
  const text = String(value).trim();
  return text || "—";
}

function codes(list: string[] | undefined): string {
  return list && list.length ? list.join(", ") : "—";
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="rio-fields">
      <div className="rio-k">{label}</div>
      <div className="rio-v">{value}</div>
    </div>
  );
}

function DataTable({ rows }: { rows: Record<string, unknown>[] }) {
  if (!rows.length) return <p className="rio-empty">—</p>;
  const headers = Object.keys(rows[0]);
  return (
    <div className="rio-table-wrap">
      <table className="rio-table">
        <thead>
          <tr>
            {headers.map((header) => (
              <th key={header}>{header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>
              {headers.map((header) => (
                <td key={header}>{row[header] === null || row[header] === undefined ? "" : String(row[header])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function NextView() {
  const allowed = useAdminOnly();
  const [names, setNames] = useState<string[]>([]);
  const [name, setName] = useState("");
  const [body, setBody] = useState<FixturePrescription | null>(null);
  const [empty, setEmpty] = useState(false);
  const [problem, setProblem] = useState("");

  useEffect(() => {
    if (!allowed) return;
    void api
      .fixtureNames()
      .then((listed) => {
        const found = listed.fixtures || [];
        setNames(found);
        setEmpty(found.length === 0);
        setName(found[0] || "");
      })
      .catch((caught) => setProblem(caught instanceof ApiError ? caught.message : "No session files."));
  }, [allowed]);

  useEffect(() => {
    if (!allowed || !name) return;
    void api
      .prescribe(name)
      .then((next) => {
        setBody(next);
        setProblem("");
      })
      .catch((caught) => {
        setBody(null);
        setProblem(caught instanceof ApiError ? caught.message : "No session files.");
      });
  }, [allowed, name]);

  const banner = body?.banner === "FIXTURE" ? "FIXTURE" : "";
  return (
    <Shell title="Next" banner={banner}>
      {empty ? <p className="rio-empty">No session files.</p> : null}
      {names.length ? (
        <label className="rio-file">
          Session
          <select value={name} onChange={(event) => setName(event.target.value)}>
            {names.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
      ) : null}
      {problem ? <p className="rio-empty">{problem}</p> : null}
      {body ? (
        <>
          <section className="rio-card">
            <Field label="limiting_capacities" value={plain(body.limiting_capacities)} />
          </section>
          {body.rows.map((row, index) => {
            const template = (row.template_id || "").trim();
            return (
              <section className="rio-card" key={`${template}-${index}`}>
                <p className="rio-subject">
                  <span className="rio-k">template_id</span> {template || "—"}
                </p>
                <Field label="prescribed_on" value={plain(row.prescribed_on)} />
                <p className="rio-mark-label">parameters</p>
                {(row.parameter_rows || []).map((item) => (
                  <Field key={item.Parameter} label={item.Parameter} value={item.Value || "—"} />
                ))}
                <Field label="Reason codes" value={codes(row.reason_codes)} />
                {template && row.prose ? <p className="rio-prose">{row.prose}</p> : null}
              </section>
            );
          })}
        </>
      ) : null}
    </Shell>
  );
}

export function DecisionsView() {
  const allowed = useAdminOnly();
  const [rows, setRows] = useState<PlannedRow[]>([]);
  const [name, setName] = useState("");
  const [empty, setEmpty] = useState(false);
  const [problem, setProblem] = useState("");

  useEffect(() => {
    if (!allowed) return;
    void api
      .plannedRows()
      .then((body) => {
        const found = body.rows || [];
        setRows(found);
        setEmpty(found.length === 0);
        setName(found[0]?.name || "");
      })
      .catch((caught) => setProblem(caught instanceof ApiError ? caught.message : "No planned rows."));
  }, [allowed]);

  const row = rows.find((item) => item.name === name) || null;
  const banner = row?.banner === "FIXTURE" ? "FIXTURE" : "";
  return (
    <Shell title="Decisions" banner={banner}>
      {empty ? <p className="rio-empty">No planned rows.</p> : null}
      {problem ? <p className="rio-error">{problem}</p> : null}
      {rows.length > 1 ? (
        <label className="rio-file">
          Planned
          <select value={name} onChange={(event) => setName(event.target.value)}>
            {rows.map((item) => (
              <option key={item.name} value={item.name}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
      ) : null}
      {row ? (
        <section className="rio-card">
          <p className="rio-subject">
            <span className="rio-k">template_id</span> {row.template_id || "—"}
          </p>
          <p className="rio-mark-label">parameters</p>
          {(row.parameter_rows || []).map((item) => (
            <Field key={item.Parameter} label={item.Parameter} value={item.Value || "—"} />
          ))}
          <Field label="reason_codes" value={codes(row.reason_codes)} />
          {row.template_id && row.prose ? <p className="rio-prose">{row.prose}</p> : null}
          <Field label="placeholder_date" value={plain(row.placeholder_date)} />
          <Field label="ontology_version" value={plain(row.ontology_version)} />
          <Field label="source" value={plain(row.source)} />
        </section>
      ) : null}
    </Shell>
  );
}

export function LedgerView() {
  const allowed = useAdminOnly();
  const { athlete } = useAuth();
  const [body, setBody] = useState<LedgerBody | null>(null);
  const [problem, setProblem] = useState("");
  const format = athlete?.prefs.date_format || "iso";

  useEffect(() => {
    if (!allowed) return;
    void api
      .ledger()
      .then(setBody)
      .catch((caught) => setProblem(caught instanceof ApiError ? caught.message : "The ledger could not be read."));
  }, [allowed]);

  const subtitle = body?.as_of ? `As of ${formatDate(body.as_of, format)}` : "";
  return (
    <Shell title="Ledger" subtitle={subtitle} banner={body?.banner}>
      {problem ? <p className="rio-error">{problem}</p> : null}
      {body ? (
        <>
          <section className="rio-card">
            <p className="rio-mark-label">Deposits</p>
            <DataTable rows={body.deposits_rows} />
          </section>
          <section className="rio-card">
            <p className="rio-mark-label">Emerging</p>
            <DataTable rows={body.emerging_rows} />
          </section>
          <section className="rio-card">
            <p className="rio-mark-label">Decaying</p>
            <DataTable rows={body.decaying_rows} />
          </section>
        </>
      ) : null}
    </Shell>
  );
}

const GOAL_FIELDS = ["current_mark", "target_time", "target_date", "limiting_capacities"] as const;

export function GoalView() {
  const allowed = useAdminOnly();
  const [goal, setGoal] = useState<Record<string, unknown> | null>(null);
  const [problem, setProblem] = useState("");

  useEffect(() => {
    if (!allowed) return;
    void api
      .goalFixture()
      .then(setGoal)
      .catch((caught) => setProblem(caught instanceof ApiError ? caught.message : "The goal could not be read."));
  }, [allowed]);

  return (
    <Shell title="Goal">
      {problem ? <p className="rio-error">{problem}</p> : null}
      {goal ? (
        <section className="rio-card">
          {GOAL_FIELDS.map((key) => (
            <Field key={key} label={key} value={plain(goal[key])} />
          ))}
        </section>
      ) : null}
    </Shell>
  );
}
