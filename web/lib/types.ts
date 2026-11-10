export type Athlete = {
  id: string;
  email: string;
  display_name: string;
  role: string;
  kind: "hosted" | "local" | string;
  today: string;
  next_session?: string | null;
  prefs: {
    timezone?: string;
    pace_units?: string;
    easy_pace?: string;
    easy_pace_unit?: string;
    no_watch?: boolean;
    intro_seen?: boolean | null;
    date_format?: string;
    show_ids?: boolean;
    compact?: boolean;
    preferred?: string;
    [key: string]: unknown;
  };
};

export type Prescription = {
  line: string;
  tolerance: string;
  block: string;
  average?: string;
};

export type WorkoutFacts = {
  distance: string;
  pace: string;
  rest: string;
  reps: string;
};

export type WorkoutCard = {
  date?: string;
  shown_date?: string;
  day_of_week?: string;
  template_id?: string;
  label?: string;
  facts?: WorkoutFacts | null;
  prescription?: Prescription | null;
  actual?: {
    template_id?: string;
    completed?: boolean;
    missed?: boolean;
    mark?: string;
    text?: string;
  } | null;
};

export type PhaseDay = {
  day?: string;
  short?: string;
  role?: string;
};

export type PhaseStep = {
  label?: string;
  text?: string;
};

export type HomeSeason = {
  inputs: {
    current_time: string;
    start_date: string;
    goal_time: string;
    goal_date: string;
  };
  digest: string;
  view: {
    days_remaining?: number | null;
    phase?: string;
    mark?: { week?: number; mark?: string } | null;
    focus?: string;
  };
  phase: {
    collapsed?: string;
    panel?: {
      headline?: string;
      focus?: string;
      days?: PhaseDay[];
      steps?: PhaseStep[];
      marks?: string;
      note?: string;
    };
  } | null;
  pace_status?: string;
  next: WorkoutCard | null;
  upcoming: WorkoutCard[];
  next_days: WorkoutCard[];
  activities?: { date?: string; name?: string; id?: string; matched?: boolean }[];
  notes: {
    date: string;
    note: { headline?: string; body?: string; carry_forward?: string };
    viewed: boolean;
  }[];
  logging?: string;
  next_session?: string | null;
};

export type TestPreview = {
  active: boolean;
  banner: string;
  runs: number;
  status: string;
};

export type HomeResponse = {
  today: string;
  athlete: Athlete;
  hello: string;
  strava_offer: boolean;
  copy: string;
  season: HomeSeason | null;
  next_session?: string | null;
  broken?: boolean;
  preview?: TestPreview;
};

export type CurrentSeason = {
  today: string;
  inputs: {
    current_time: string;
    start_date: string;
    goal_time: string;
    goal_date: string;
  };
  plan?: { season_length_weeks?: number; start_date?: string };
  digest?: string;
  marks?: Record<string, string>;
  actuals?: Record<
    string,
    {
      template_id?: string;
      completed?: boolean;
      missed?: boolean;
      numbers?: unknown[];
      slots?: unknown[];
      mark?: string;
    }
  >;
};

export type PlanSession = {
  date: string;
  shown_date?: string;
  day_of_week?: string;
  week_number?: number;
  template_id?: string;
  label?: string;
  target?: string;
  reason_codes?: string[];
  prescription?: Prescription | null;
};

export type PlanWeek = {
  week: number;
  phase: string;
  status: string | null;
  days_remaining: number | null;
  meters: number;
  volume: string;
};

export type PlanDay = {
  date: string;
  in_month: boolean;
  day: number;
  label: string;
  template_id: string;
  today: boolean;
};

export type PlanResponse = {
  inputs: CurrentSeason["inputs"];
  digest: string;
  marks: Record<string, string>;
  prefs: Athlete["prefs"] & {
    units?: string;
    confirm_adapt?: boolean;
    today?: string;
    easy_pace_phrase?: string;
    date_format?: string;
  };
  months: string[];
  month: string;
  month_title: string;
  calendar: PlanDay[][];
  weeks: PlanWeek[];
  sessions: PlanSession[];
  actuals?: CurrentSeason["actuals"];
  pace_status?: string;
  preview?: TestPreview;
};

export type SeasonStat = { label: string; value: string };

export type StoredSeason = {
  inputs: CurrentSeason["inputs"];
  stats: SeasonStat[];
};

export type PastSeasonsResponse = {
  today: string;
  seasons: StoredSeason[];
  open?: StoredSeason[];
};

export type ActivityRow = {
  date?: string;
  shown_date?: string;
  name?: string;
  label?: string;
  template_id?: string;
  meters?: number | null;
  work?: string;
  distance?: string;
  hr?: string;
  heart_rate?: number | null;
  extra?: boolean;
  id?: string;
};

export type LoggedActivity = {
  id: string;
  date: string;
  name: string;
  matched: boolean;
  reps: string;
  volume: string;
  heart_rate: string;
};

export type RunLap = {
  rep?: string;
  target?: string;
  actual?: string;
  rest?: string;
};

export type RunCard = {
  id: string;
  date: string;
  shown_date: string;
  name: string;
  template_id?: string;
  status: string;
  detail: string;
  laps?: RunLap[];
  meters?: number;
  heart_rate?: number | null;
};

export type WeekGroup = {
  title: string;
  open: boolean;
  cards: RunCard[];
};

export type StravaStatus = {
  configured: boolean;
  connected: boolean;
  athlete_name: string;
  last_sync_at: number | string | null;
  redirect_uri?: string;
  count?: number;
};

export type ActivitiesResponse = {
  rows: ActivityRow[];
  all: ActivityRow[];
  cards?: RunCard[];
  groups?: WeekGroup[];
  summary?: {
    title?: string;
    distance?: string;
    runs?: number;
    counts?: Record<string, number>;
  };
  weekly_meters?: number[];
  heart?: { date: string; bpm: number }[];
  figures?: { distance: string; heart: string };
  length?: number;
  start_date?: string;
  goal_date?: string;
  notice?: string | null;
  strava?: StravaStatus;
  logged?: LoggedActivity[];
  preview?: TestPreview;
};

export type ParameterRow = { Parameter: string; Value: string };

export type PrescriptionRow = {
  template_id?: string;
  prescribed_on?: string;
  parameters?: Record<string, unknown>;
  parameter_rows?: ParameterRow[];
  reason_codes?: string[];
  prose?: string;
};

export type FixturePrescription = {
  name: string;
  on: string;
  limiting_capacities?: unknown;
  rows: PrescriptionRow[];
  banner?: string | null;
  ontology_version?: string;
};

export type PlannedRow = {
  name: string;
  template_id: string;
  parameters?: Record<string, unknown>;
  parameter_rows?: ParameterRow[];
  reason_codes: string[];
  placeholder_date: string;
  ontology_version: string;
  source: string;
  prose: string;
  banner?: string | null;
};

export type LedgerBody = {
  as_of: string;
  entries: Record<string, unknown>[];
  emerging: Record<string, unknown>[];
  decaying: Record<string, unknown>[];
  banner?: string | null;
  deposits_rows: Record<string, unknown>[];
  emerging_rows: Record<string, unknown>[];
  decaying_rows: Record<string, unknown>[];
};

export type LapTable = {
  name?: string;
  date?: string;
  banner?: string | null;
  times?: (number | null)[];
  source?: string;
  laps?: { distance_m?: number; seconds?: number | null; rest_s?: number | null }[];
  distance_heading?: string;
  rows?: Record<string, string | number>[];
  family?: string;
  confidence?: string;
  reason_codes?: string[];
  prose?: string;
};

export type SessionResponse = {
  date: string;
  session: {
    date?: string;
    day_of_week?: string;
    template_id?: string;
    week_number?: number;
    reason_codes?: string[];
    target_outcome?: string;
  };
  actual: {
    template_id?: string;
    completed?: boolean;
    missed?: boolean;
    mark?: string;
    text?: string;
    numbers?: unknown[];
    slots?: unknown[];
  } | null;
  quality: boolean;
  note: { headline?: string; body?: string; carry_forward?: string } | null;
  viewed: boolean | null;
  digest: string;
  label: string;
  structure: string;
  target: string;
  reasons: string[];
  shown_date: string;
  facts?: WorkoutFacts | null;
  prescription?: Prescription | null;
  logging: string;
  confirm_adapt: boolean;
  show_id: boolean;
  boxes: number;
  seed: (number | null)[];
  summary: string;
  match: { reps: string; work: string; heart_rate: string } | null;
  heart_rate: string;
};

export type ResultWrite = SeasonWrite & {
  committed?: boolean;
  insight?: { status?: string; date?: string; id?: string };
  actuals?: Record<string, { mark?: string; numbers?: unknown[]; text?: string }>;
};

export type SeasonWrite = {
  inputs: CurrentSeason["inputs"];
  committed?: boolean;
  strava_offer?: boolean;
  plan?: unknown;
};

export type LibraryWorkout = {
  id: string;
  description: string;
  capacity: string;
  family: string;
  phases: number[];
};

export type LibraryResponse = {
  count: number;
  workouts: LibraryWorkout[];
  families: { id: string; label: string }[];
};

export type ProfileField = {
  label: string;
  value: string;
};

export type ProfileResponse = {
  ready: boolean;
  fields: ProfileField[];
  profile_key?: string;
  goal_time?: string;
  goal_override?: string | null;
  shown_goal?: string;
  inputs?: {
    current_time?: string;
    start_date?: string;
    goal_time?: string;
    goal_date?: string;
  };
  easy_pace?: string;
  easy_pace_unit?: string;
  easy_pace_phrase?: string;
  prefs?: {
    date_format?: string;
    compact?: boolean;
    [key: string]: unknown;
  };
};

export type AuthResult = {
  email: string;
  display_name: string;
  kind: string;
  confirm?: boolean;
  message?: string;
};
