"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Footer } from "./Footer";
import { Nav } from "./Nav";
import { RequireUser } from "./RequireUser";
import { ApiError, api } from "@/lib/api";
import { hideBanner } from "@/lib/activity";
import { useAuth } from "@/lib/auth";
import { formatDate } from "@/lib/plan";
import type { LapTable } from "@/lib/types";

type Mode = "loading" | "empty" | "ready" | "error";

export function LastSessionView() {
  return (
    <RequireUser>
      <LastBody />
    </RequireUser>
  );
}

function LastBody() {
  const { athlete, status } = useAuth();
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("loading");
  const [fixtures, setFixtures] = useState<string[]>([]);
  const [files, setFiles] = useState<string[]>([]);
  const [session, setSession] = useState("");
  const [file, setFile] = useState("—");
  const [shown, setShown] = useState<LapTable | null>(null);
  const [problem, setProblem] = useState("");

  useEffect(() => {
    if (status !== "in") return;
    if (athlete?.role !== "admin") {
      router.replace("/home");
      return;
    }
    void (async () => {
      try {
        const [named, intervals] = await Promise.all([api.fixtureNames(), api.intervalFiles()]);
        const fixtureNames = named.fixtures || [];
        const intervalNames = intervals.files || [];
        setFixtures(fixtureNames);
        setFiles(intervalNames);
        if (!fixtureNames.length && !intervalNames.length) {
          setMode("empty");
          return;
        }
        const first = fixtureNames[0] || "";
        setSession(first);
        setFile(fixtureNames.length ? "—" : intervalNames[0] || "—");
        setMode("ready");
      } catch (caught) {
        setProblem(caught instanceof ApiError ? caught.message : "That file could not be read.");
        setMode("error");
      }
    })();
  }, [athlete?.role, router, status]);

  useEffect(() => {
    if (mode !== "ready") return;
    const chosenFile = file !== "—" ? file : "";
    const chosenSession = !chosenFile ? session : "";
    if (!chosenFile && !chosenSession) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setShown(null);
      setProblem("No session files.");
      return;
    }
    void (async () => {
      try {
        const body = chosenFile ? await api.intervalFill(chosenFile) : await api.fixtureSession(chosenSession);
        setShown(body);
        setProblem("");
      } catch (caught) {
        setShown(null);
        setProblem(caught instanceof ApiError ? caught.message : `Could not read ${chosenFile || chosenSession}.`);
      }
    })();
  }, [file, mode, session]);

  const format = athlete?.prefs.date_format || "iso";
  const banner = shown && !hideBanner(shown.banner) ? shown.banner : "";
  const rows = shown?.rows || [];
  const heading = shown?.distance_heading || "Distance (m)";

  return (
    <div className="page-last">
      <Nav />
      <main>
        <header className="rio-hero">
          {banner ? <p className="rio-synthetic">{banner}</p> : null}
          <h1>Last Session</h1>
        </header>
        {mode === "loading" ? <p className="rio-wait">Loading</p> : null}
        {mode === "empty" ? <p className="rio-empty">No session files.</p> : null}
        {mode === "error" ? <p className="rio-error">{problem}</p> : null}
        {mode === "ready" ? (
          <>
            <div className="rio-file-row">
              {fixtures.length ? (
                <label className="rio-file">
                  Session
                  <select value={session} onChange={(event) => setSession(event.target.value)}>
                    {fixtures.map((name) => (
                      <option key={name} value={name}>
                        {name}
                      </option>
                    ))}
                  </select>
                </label>
              ) : null}
              {files.length ? (
                <label className="rio-file">
                  Intervals file
                  <select value={file} onChange={(event) => setFile(event.target.value)}>
                    {fixtures.length ? <option value="—">—</option> : null}
                    {files.map((name) => (
                      <option key={name} value={name}>
                        {name}
                      </option>
                    ))}
                  </select>
                </label>
              ) : null}
            </div>
            {problem ? <p className="rio-empty">{problem}</p> : null}
            {shown ? (
              <>
                <section className="rio-card">
                  <p className="rio-mark-label">Laps</p>
                  <div className="rio-table-wrap">
                    <table className="rio-table">
                      <thead>
                        <tr>
                          <th>Lap</th>
                          <th>{heading}</th>
                          <th>Seconds</th>
                          <th>Rest (s)</th>
                        </tr>
                      </thead>
                      <tbody>
                        {rows.map((row, index) => (
                          <tr key={index}>
                            <td>{cell(row.Lap)}</td>
                            <td>{cell(row[heading])}</td>
                            <td>{cell(row.Seconds)}</td>
                            <td>{cell(row["Rest (s)"])}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
                <section className="rio-card">
                  <Field label="Date" value={shown.date ? formatDate(shown.date, format) : "—"} />
                  <Field label="Family" value={shown.family || "—"} />
                  <Field label="Confidence" value={shown.confidence || "—"} />
                  <Field label="Reason codes" value={shown.reason_codes?.length ? shown.reason_codes.join(", ") : "—"} />
                  {shown.prose ? <p className="rio-prose">{shown.prose}</p> : null}
                </section>
              </>
            ) : null}
          </>
        ) : null}
        <Footer />
      </main>
    </div>
  );
}

function cell(value: string | number | undefined): string {
  if (value === null || value === undefined) return "";
  return String(value);
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="rio-fields">
      <div className="rio-k">{label}</div>
      <div className="rio-v">{value}</div>
    </div>
  );
}
