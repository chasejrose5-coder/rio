"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Footer } from "./Footer";
import { Nav } from "./Nav";
import { RequireUser } from "./RequireUser";
import { useAdminOnly } from "./useAdminOnly";
import { ApiError, api, startPreview } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type Account = { email: string; display_name: string; role: string };
type Photo = { id: string; file: string; credit: string; source: string; enabled: boolean };

export function AdminView() {
  return (
    <RequireUser>
      <AdminBody />
    </RequireUser>
  );
}

function AdminBody() {
  const allowed = useAdminOnly();
  const { athlete } = useAuth();
  const router = useRouter();
  const local = athlete?.kind === "local";
  const [accounts, setAccounts] = useState<Account[] | null>(null);
  const [available, setAvailable] = useState(true);
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [heroNote, setHeroNote] = useState("");
  const [heroError, setHeroError] = useState("");
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!allowed) return;
    void (async () => {
      try {
        const [listed, hero] = await Promise.all([api.adminAccounts(), api.hero()]);
        setAvailable(listed.available);
        setAccounts(listed.accounts);
        setPhotos(hero.photos);
      } catch (caught) {
        setError(caught instanceof ApiError ? caught.message : "That page is for the admin account.");
      }
    })();
  }, [allowed]);

  async function loadSeason() {
    setBusy(true);
    setError("");
    setNote("");
    try {
      await api.loadTestSeason();
      setNote("TEST Athlete is loaded.");
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "The test season could not be saved.");
    } finally {
      setBusy(false);
    }
  }

  async function removeSeason() {
    setError("");
    setNote("");
    if (!confirm) {
      setError("Confirm the delete first.");
      return;
    }
    setBusy(true);
    try {
      const body = await api.deleteTestSeason(true);
      setNote(body.message);
      setConfirm(false);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "The test season could not be removed.");
    } finally {
      setBusy(false);
    }
  }

  async function openView(path: string) {
    setError("");
    setNote("");
    try {
      const body = await api.testSeason();
      if (!body.loaded) {
        setError("Load the test season first.");
        return;
      }
      startPreview();
      router.push(path);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Load the test season first.");
    }
  }

  function move(index: number, direction: -1 | 1) {
    const next = index + direction;
    if (next < 0 || next >= photos.length) return;
    const copy = photos.slice();
    const [row] = copy.splice(index, 1);
    copy.splice(next, 0, row);
    setPhotos(copy);
  }

  async function savePhotos() {
    setHeroError("");
    setHeroNote("");
    setBusy(true);
    try {
      const saved = await api.saveHero(
        photos.map((photo) => ({ id: photo.id, enabled: photo.enabled, credit: photo.credit })),
      );
      setPhotos(saved.photos);
      setHeroNote("Startup photos saved.");
    } catch (caught) {
      setHeroError(caught instanceof ApiError ? caught.message : "credit is empty");
    } finally {
      setBusy(false);
    }
  }

  if (!allowed) {
    return (
      <div className="page-admin">
        <Nav />
        <main>
          <p className="rio-wait">Loading</p>
        </main>
      </div>
    );
  }

  return (
    <div className="page-admin">
      <Nav />
      <main>
        <header className="rio-hero">
          <h1>Admin</h1>
          <p className="rio-range">Accounts and the startup photos.</p>
        </header>
        <section className="rio-card">
          <p className="rio-mark-label">Accounts</p>
          {!available ? <p className="rio-note">The account list isn&apos;t available on this server yet.</p> : null}
          {available && accounts && accounts.length === 0 ? <p className="rio-empty">No accounts yet.</p> : null}
          {available && accounts && accounts.length > 0 ? (
            <div className="rio-table-wrap">
              <table className="rio-table">
                <thead>
                  <tr>
                    <th>Email</th>
                    <th>Name</th>
                    {local ? null : <th>Role</th>}
                  </tr>
                </thead>
                <tbody>
                  {accounts.map((row) => (
                    <tr key={row.email}>
                      <td>{row.email || "—"}</td>
                      <td>{row.display_name || "—"}</td>
                      {local ? null : <td>{row.role || "athlete"}</td>}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
          <p className="rio-note">Read only.</p>
        </section>
        <section className="rio-card">
          <p className="rio-mark-label">Test season</p>
          <p className="rio-note">A separate TEST athlete with an 800 m season and eight weeks of runs. This login is not changed.</p>
          {error ? <p className="rio-error">{error}</p> : null}
          {note ? <p className="rio-note">{note}</p> : null}
          <button type="button" className="rio-primary" disabled={busy} onClick={() => void loadSeason()}>
            Load test season
          </button>
          <label className="rio-check">
            <input type="checkbox" checked={confirm} onChange={(event) => setConfirm(event.target.checked)} />
            Remove the TEST athlete and all of its data
          </label>
          <button type="button" className="rio-secondary" disabled={busy} onClick={() => void removeSeason()}>
            Delete test season
          </button>
          <div className="rio-admin-views">
            <button type="button" className="rio-secondary" onClick={() => void openView("/home")}>
              View test Home
            </button>
            <button type="button" className="rio-secondary" onClick={() => void openView("/plan")}>
              View test Plan
            </button>
            <button type="button" className="rio-secondary" onClick={() => void openView("/activity")}>
              View test Activity
            </button>
          </div>
        </section>
        <section className="rio-hero-editor">
          <p className="rio-mark-label">Startup photos</p>
          <p className="rio-settings-note">Show, reorder, or edit the credit line.</p>
          {heroNote ? <p className="rio-settings-note">{heroNote}</p> : null}
          {heroError ? <p className="rio-error">{heroError}</p> : null}
          {photos.map((photo, index) => (
            <div className="rio-hero-frame" key={photo.id}>
              <label className="rio-check">
                <input
                  type="checkbox"
                  checked={photo.enabled}
                  onChange={(event) => {
                    const enabled = event.target.checked;
                    setPhotos((current) => current.map((item) => (item.id === photo.id ? { ...item, enabled } : item)));
                  }}
                />
                Show on the startup page
              </label>
              <p className="rio-photo-credit">{photo.credit}</p>
              <label>
                Credit line
                <input
                  type="text"
                  value={photo.credit}
                  onChange={(event) => {
                    const credit = event.target.value;
                    setPhotos((current) => current.map((item) => (item.id === photo.id ? { ...item, credit } : item)));
                  }}
                />
              </label>
              <div className="rio-done-row">
                <button type="button" className="rio-secondary" disabled={index === 0} onClick={() => move(index, -1)}>
                  Move up
                </button>
                <button type="button" className="rio-secondary" disabled={index + 1 >= photos.length} onClick={() => move(index, 1)}>
                  Move down
                </button>
              </div>
            </div>
          ))}
          <button type="button" className="rio-primary" disabled={busy || photos.length === 0} onClick={() => void savePhotos()}>
            Save photos
          </button>
        </section>
        <Footer />
      </main>
    </div>
  );
}
