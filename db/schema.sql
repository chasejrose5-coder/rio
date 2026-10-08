-- SQLite tables only. No rows.
PRAGMA foreign_keys = ON;

CREATE TABLE ontology_versions (
  version TEXT PRIMARY KEY
);

CREATE TABLE athletes (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL
);

CREATE TABLE goals (
  id INTEGER PRIMARY KEY,
  athlete_id INTEGER NOT NULL REFERENCES athletes (id),
  event TEXT NOT NULL,
  current_mark TEXT,
  current_mark_date TEXT,
  target_mark TEXT,
  target_date TEXT,
  meet TEXT,
  secondary_event TEXT,
  next_priority_race TEXT,
  next_race_date TEXT,
  limiting_capacity TEXT
);

CREATE TABLE workouts (
  id INTEGER PRIMARY KEY,
  athlete_id INTEGER REFERENCES athletes (id),
  source TEXT NOT NULL CHECK (source IN ('fixture', 'intervals')),
  title TEXT,
  started_at TEXT,
  note TEXT,
  distance_m REAL,
  elapsed_s INTEGER,
  avg_hr INTEGER
);

CREATE TABLE workout_steps (
  id INTEGER PRIMARY KEY,
  workout_id INTEGER NOT NULL REFERENCES workouts (id),
  step_index INTEGER NOT NULL,
  distance_m REAL,
  seconds INTEGER,
  rest_s INTEGER,
  pace TEXT,
  UNIQUE (workout_id, step_index)
);

CREATE TABLE classifications (
  id INTEGER PRIMARY KEY,
  workout_id INTEGER NOT NULL REFERENCES workouts (id),
  ontology_version TEXT NOT NULL REFERENCES ontology_versions (version),
  family TEXT NOT NULL
);

CREATE TABLE ledger_entries (
  id INTEGER PRIMARY KEY,
  athlete_id INTEGER NOT NULL REFERENCES athletes (id),
  classification_id INTEGER NOT NULL REFERENCES classifications (id),
  ontology_version TEXT NOT NULL REFERENCES ontology_versions (version),
  recorded_at TEXT
);

CREATE TABLE prescriptions (
  id INTEGER PRIMARY KEY,
  athlete_id INTEGER NOT NULL REFERENCES athletes (id),
  ontology_version TEXT NOT NULL REFERENCES ontology_versions (version),
  template_id TEXT,
  prescribed_on TEXT
);
