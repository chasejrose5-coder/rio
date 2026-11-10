import type { ActivitiesResponse, Athlete, AuthResult, CurrentSeason, HomeResponse, PlanResponse, SeasonWrite } from "./types";

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

  plan: (month?: string) => {
    const query = month ? `?month=${encodeURIComponent(month)}` : "";
    return request<PlanResponse>(`/plan${query}`);
  },

  activities: () => request<ActivitiesResponse>("/activities"),

  markWeek: (week: number, choice: string, digest: string) =>
    request<SeasonWrite>("/seasons/current/marks", {
      method: "POST",
      body: JSON.stringify({ week, choice }),
      headers: digest ? { "If-Match": digest } : {},
    }),
};
