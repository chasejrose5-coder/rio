import type {
  ActivitiesResponse,
  Athlete,
  LibraryResponse,
  ProfileResponse,
  AuthResult,
  CurrentSeason,
  HomeResponse,
  LapTable,
  LedgerBody,
  PastSeasonsResponse,
  FixturePrescription,
  PlannedRow,
  PlanResponse,
  ResultWrite,
  SeasonWrite,
  SessionResponse,
  StravaStatus,
} from "./types";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function apiBase(): string {
  const raw = process.env.NEXT_PUBLIC_RIO_API_URL || "http://localhost:8000";
  return raw.replace(/\/$/, "");
}

const PREVIEW_KEY = "rio_test_preview";

export function previewing(): boolean {
  if (typeof window === "undefined") return false;
  return window.sessionStorage.getItem(PREVIEW_KEY) === "1";
}

export function startPreview(): void {
  window.sessionStorage.setItem(PREVIEW_KEY, "1");
}

export function stopPreview(): void {
  window.sessionStorage.removeItem(PREVIEW_KEY);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiBase()}${path}`, {
      ...init,
      credentials: "include",
      headers: {
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...(init?.headers ?? {}),
        ...(init?.method && init.method !== "GET" && previewing() && !path.startsWith("/auth/sign-out")
          ? { "X-RIO-Preview": "test" }
          : {}),
      },
    });
  } catch {
    throw new ApiError(0, "The server could not be reached.");
  }
  const text = await response.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text) as unknown;
    } catch {
      data = null;
    }
  }
  if (!response.ok) {
    const detail =
      data && typeof data === "object" && "detail" in data && typeof data.detail === "string"
        ? data.detail
        : "Something went wrong. Try again.";
    throw new ApiError(response.status, detail);
  }
  return data as T;
}

export const api = {
  me: () => request<Athlete>("/auth/me"),

  signIn: (email: string, password: string) =>
    request<AuthResult>("/auth/sign-in", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  signUp: (name: string, email: string, password: string) =>
    request<AuthResult>("/auth/sign-up", {
      method: "POST",
      body: JSON.stringify({ name, email, password }),
    }),

  forgot: (email: string) =>
    request<{ ok: boolean; message: string }>("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),

  reset: (token: string, password: string) =>
    request<{ ok: boolean; message: string }>("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, password }),
    }),

  accountMode: () => request<{ mode: "hosted" | "local" | "unconfigured" }>("/auth/availability"),

  /** 503 means accounts are local, which is when Streamlit hides Forgot password. */
  /** Hosted accounts are the ones that can email a reset link. Local is a 503. */
  accountsHosted: async (): Promise<boolean> => {
    try {
      await request<{ url: string }>("/auth/google");
      return true;
    } catch {
      return false;
    }
  },

  signOut: () => request<{ ok: boolean }>("/auth/sign-out", { method: "POST" }),

  changePassword: (currentPassword: string, newPassword: string) =>
    request<{ ok: boolean; message: string }>("/auth/password", {
      method: "POST",
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    }),

  changeEmail: (email: string, password: string) =>
    request<{ ok: boolean; email: string; message: string }>("/auth/email", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  deleteAccount: (body: { confirm: boolean; email?: string; password?: string }) =>
    request<{ deleted: boolean }>("/auth/delete", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  clearMarks: () =>
    request<CurrentSeason>("/seasons/current/clear", {
      method: "POST",
      body: JSON.stringify({ confirm: true }),
    }),

  resetPlan: () =>
    request<{ reset: boolean }>("/seasons/reset", {
      method: "POST",
      body: JSON.stringify({ confirm: true }),
    }),

  createSeason: (inputs: { current_time: string; start_date: string; goal_time: string; goal_date: string }) =>
    request<SeasonWrite>("/seasons", {
      method: "POST",
      body: JSON.stringify(inputs),
    }),

  currentSeason: async (): Promise<CurrentSeason | null> => {
    try {
      return await request<CurrentSeason>("/seasons/current");
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) return null;
      throw error;
    }
  },

  home: (justGenerated = false) => {
    const params = new URLSearchParams();
    params.set("just_generated", justGenerated ? "true" : "false");
    if (previewing()) params.set("preview", "test");
    return request<HomeResponse>(`/home?${params.toString()}`);
  },

  dismissStrava: () =>
    request<Athlete>("/settings", {
      method: "PATCH",
      body: JSON.stringify({ strava_prompt_seen: true }),
    }),

  stravaConnect: () => request<{ url: string }>("/strava/connect"),

  viewNote: (date: string, note: object) =>
    request("/seasons/current/notes", {
      method: "POST",
      body: JSON.stringify({ date, note, viewed: true }),
    }),

  patchSettings: (body: Record<string, unknown>) =>
    request<Athlete>("/settings", { method: "PATCH", body: JSON.stringify(body) }),

  watchless: (body: { date: string; outcome?: string; time?: string; missed?: boolean }) =>
    request("/seasons/current/watchless", { method: "POST", body: JSON.stringify(body) }),

  plan: (
    month?: string,
    inputs?: { current_time: string; start_date: string; goal_time: string; goal_date: string },
  ) => {
    const params = new URLSearchParams();
    if (month) params.set("month", month);
    if (inputs) {
      params.set("current_time", inputs.current_time);
      params.set("start_date", inputs.start_date);
      params.set("goal_time", inputs.goal_time);
      params.set("goal_date", inputs.goal_date);
    }
    if (previewing()) params.set("preview", "test");
    const suffix = params.toString();
    return request<PlanResponse>(`/plan${suffix ? `?${suffix}` : ""}`);
  },

  pastSeasons: () => request<PastSeasonsResponse>("/seasons/past"),

  deletePastSeason: (body: {
    current_time: string;
    start_date: string;
    goal_time: string;
    goal_date: string;
    confirm: boolean;
  }) =>
    request<{ deleted: boolean; inputs: PastSeasonsResponse["seasons"][number]["inputs"]; stats: PastSeasonsResponse["seasons"][number]["stats"] }>(
      "/seasons/past",
      { method: "DELETE", body: JSON.stringify(body) },
    ),

  activities: () => request<ActivitiesResponse>(previewing() ? "/activities?preview=test" : "/activities"),

  profile: () => request<ProfileResponse>("/profile"),

  saveGoal: (goalTime: string) =>
    request<ProfileResponse>("/profile/goal", {
      method: "PUT",
      body: JSON.stringify({ goal_time: goalTime }),
    }),

  library: (query?: { q?: string; family?: string; phase?: number }) => {
    const params = new URLSearchParams();
    if (query?.q) params.set("q", query.q);
    if (query?.family) params.set("family", query.family);
    if (typeof query?.phase === "number") params.set("phase", String(query.phase));
    const suffix = params.toString();
    return request<LibraryResponse>(`/library${suffix ? `?${suffix}` : ""}`);
  },

  markWeek: (week: number, choice: string, digest: string) =>
    request<SeasonWrite>("/seasons/current/marks", {
      method: "POST",
      body: JSON.stringify({ week, choice }),
      headers: digest ? { "If-Match": digest } : {},
    }),

  session: (date: string) =>
    request<SessionResponse>(
      `/sessions/${encodeURIComponent(date)}${previewing() ? "?preview=test" : ""}`,
    ),

  postResult: (
    body: { date: string; text: string; slots?: (number | null)[] | null; intervals?: string | null },
    digest: string,
  ) =>
    request<ResultWrite>("/seasons/current/results", {
      method: "POST",
      body: JSON.stringify(body),
      headers: digest ? { "If-Match": digest } : {},
    }),

  intervalFiles: () => request<{ files: string[] }>("/fixtures/intervals"),

  intervalFill: (name: string) =>
    request<LapTable & { name: string; times: (number | null)[]; source: string }>(
      `/fixtures/intervals/${encodeURIComponent(name)}`,
    ),

  fixtureNames: () => request<{ fixtures: string[] }>("/fixtures"),

  fixtureSession: (name: string) => request<LapTable>(`/fixtures/session?name=${encodeURIComponent(name)}`),

  adminAccounts: () =>
    request<{ available: boolean; accounts: { email: string; display_name: string; role: string }[] }>("/admin/accounts"),

  testSeason: () =>
    request<{ loaded: boolean; name?: string; inputs?: string[]; runs?: number; plan?: Record<string, unknown> }>(
      "/admin/test-season",
    ),

  loadTestSeason: () =>
    request<{ loaded: boolean; created: boolean; runs: number; name: string }>("/admin/test-season", { method: "POST" }),

  deleteTestSeason: (confirm: boolean) =>
    request<{ deleted: boolean; message: string }>("/admin/test-season", {
      method: "DELETE",
      body: JSON.stringify({ confirm }),
    }),

  hero: () =>
    request<{ photos: { id: string; file: string; credit: string; source: string; enabled: boolean }[] }>("/admin/hero"),

  saveHero: (photos: { id: string; enabled: boolean; credit: string }[]) =>
    request<{ saved: boolean; photos: { id: string; file: string; credit: string; source: string; enabled: boolean }[] }>(
      "/admin/hero",
      { method: "PUT", body: JSON.stringify({ photos }) },
    ),

  prescribe: (name: string) =>
    request<FixturePrescription>("/fixtures/prescribe", { method: "POST", body: JSON.stringify({ name }) }),

  plannedRows: () => request<{ rows: PlannedRow[] }>("/fixtures/planned"),

  ledger: () => request<LedgerBody>("/fixtures/ledger"),

  goalFixture: () => request<Record<string, unknown>>("/fixtures/goal"),

  stravaStatus: () => request<StravaStatus>("/strava/status"),

  stravaSync: (scope: "recent" | "all") =>
    request<{ synced?: boolean; notice?: string | null; count?: number; strava?: StravaStatus }>("/strava/sync", {
      method: "POST",
      body: JSON.stringify({ scope }),
    }),

  stravaDisconnect: () => request<{ connected: boolean }>("/strava/disconnect", { method: "POST" }),

  stravaCallback: (code: string, state: string) =>
    request<{ connected?: boolean; athlete_name?: string }>(
      `/strava/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`,
      { headers: { "X-RIO-Response": "json" } },
    ),
};
