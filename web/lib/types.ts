export type Athlete = {
  id: string;
  email: string;
  display_name: string;
  role: string;
  kind: "hosted" | "local" | string;
  today: string;
  prefs: {
    timezone?: string;
    pace_units?: string;
    easy_pace?: string;
    easy_pace_unit?: string;
    no_watch?: boolean;
    intro_seen?: boolean | null;
    date_format?: string;
    show_ids?: boolean;
    preferred?: string;
    [key: string]: unknown;
  };
};

export type Prescription = {
  line: string;
  tolerance: string;
  block: string;
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
};

export type HomeResponse = {
  today: string;
  athlete: Athlete;
  hello: string;
  strava_offer: boolean;
  copy: string;
  season: HomeSeason | null;
};

export type CurrentSeason = {
  today: string;
  inputs: {
    current_time: string;
    start_date: string;
    goal_time: string;
    goal_date: string;
  };
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
};

export type ActivityRow = {
  date?: string;
  shown_date?: string;
  name?: string;
  label?: string;
  meters?: number | null;
  work?: string;
  hr?: string;
  heart_rate?: number | null;
  extra?: boolean;
  id?: string;
};

export type ActivitiesResponse = {
  rows: ActivityRow[];
  all: ActivityRow[];
  notice?: string | null;
};

export type SeasonWrite = {
  inputs: CurrentSeason["inputs"];
  committed?: boolean;
  strava_offer?: boolean;
  plan?: unknown;
};

export type AuthResult = {
  email: string;
  display_name: string;
  kind: string;
  confirm?: boolean;
  message?: string;
};
