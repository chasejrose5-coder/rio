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
};

export type AuthResult = {
  email: string;
  display_name: string;
  kind: string;
  confirm?: boolean;
  message?: string;
};
