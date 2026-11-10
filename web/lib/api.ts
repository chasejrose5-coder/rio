import type {
  ActivitiesResponse,
  Athlete,
  LibraryResponse,
  ProfileResponse,
  AuthResult,
  CurrentSeason,
  HomeResponse,
  LapTable,
  PastSeasonsResponse,
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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiBase()}${path}`, {
      ...init,
      credentials: "include",
      headers: {
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...(init?.headers ?? {}),
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

  home: (justGenerated = false) =>
    request<HomeResponse>(`/home?just_generated=${justGenerated ? "true" : "false"}`),

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

  activities: () => request<ActivitiesResponse>("/activities"),

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

  session: (date: string) => request<SessionResponse>(`/sessions/${encodeURIComponent(date)}`),

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
