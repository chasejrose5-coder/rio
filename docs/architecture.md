# RIO architecture

This is the code as it stands. RIO is a local running-intelligence layer for one 800 m season. Rules choose workouts and labels. A model is allowed only to rephrase a paragraph that the rules already wrote. The app does not compute a goal probability or a readiness score. A season plan that contains either field is rejected.

Intervals.icu is a read-only adapter. The product is the season, the menu, and the labels.

## Pathways

These are the paths that exist. They do not all meet.

1. **Season plan.** Start takes four inputs: current 800 time, start date, goal 800 time, goal date. `sequence()` builds an ordered list of sessions from the frozen menu and the locked 800 m weights. The four inputs go in the URL. Marks, entered results, and pulled activities stay in this browser. Season and Weekly can mark a week `on_track`, `not_hitting`, or `smashing`. `adapt()` then rewrites only the weeks after that week. Session can enter rep times, or fill them from a local Intervals JSON file, and the same adapt runs. Opening Dashboard, Weekly, Session, Progress, or Activity data can do that automatically for a matched Tuesday or Thursday that does not already have a mark. The stored times fill that day's boxes and stay editable.

2. **Classify a session.** A fixture YAML file, a local Intervals JSON file, or a live Intervals activity becomes laps in `normalize()`. `classify()` applies if-then rules and returns one family, reason codes, a confidence word (`high` or `unsure`), and `ontology_version` `v0.1`. Last Session shows that. The CLI prints it. The ledger can store it in memory. This path does not change the season plan.

3. **Prescribe the next one to three days.** `prescribe()` reads the in-memory ledger, `constraints.yml`, and every template file. It returns one to three menu ids. Next shows that for one fixture. Accept can write the first row to a planned YAML file. Decisions reads that file. This path does not call `sequence()` or `adapt()`, and it does not call Intervals.

4. **Explain.** Last Session, Next, and Decisions ask `explain.py` for one paragraph. If the explain API is configured and recorded spend is under $25, the paragraph may be rephrased. A rephrase that changes the family, the template id, or the reasons is dropped. The rules text remains. No other page calls the model.

5. **Pull activities.** Opening Dashboard, Weekly, Session, Progress, or Activity data asks Intervals for the last 14 days, matches each activity to a planned date, and then runs auto-adapt. The first open of any other page asks for that same 14-day window and does not judge a mark. Refresh on Activity data asks for every activity from 1970-01-01 through today, matches them, and then runs auto-adapt. The reduced rows are saved in this browser with the marks. The full activity JSON is not stored. Nothing is written back to Intervals.

6. **Load fixtures into SQLite.** `db/load.py` can create `data/rio.sqlite` from `db/schema.sql` and the four YAML fixtures. The Streamlit app does not open that database.

## Fixtures and Intervals

| Piece | Talks to Intervals | Stays on fixtures or local files |
| --- | --- | --- |
| `adapters/intervals_icu.py` | GET one activity, or GET a date range, when the API key is set | `to_normalize_input()` also runs on a JSON object already in memory |
| `adapters/intervals_cli.py` | `--activity-id` and `--list` | `--file` reads a JSON file and does not use the network. `--save-json` writes the fetched body to disk |
| `ui/activities.py` | `list_activities` and `fetch_activity` on Dashboard, Weekly, Session, Progress, Activity data, and app load | Tests pass fake list and fetch functions |
| `ui/auto_adapt.py` | No | Judges rows already stored from a pull or a test |
| `ui/last_session.py` | No | Reads `tests/fixtures/intervals/*.json` |
| `ui/activity_data.py` | No | Displays stored rows and, for a planned day with no match, a local JSON file named by the result |
| Session page result fill | No | Select box reads the same local JSON directory |
| Last Session, Next, Ledger | No | `tests/fixtures/*.yml` |
| Decisions, `engines/accept.py` | No | `tests/fixtures/planned/*.yml`, source `fixture` |
| `engines/season.py`, `engines/prescribe.py`, `engines/classify.py` | No | Menu files, paper files, and fixture YAML |
| `db/load.py` | No | Writes fixture workouts into SQLite |

The two JSON files in `tests/fixtures/intervals/` are synthetic. The README there says real saves from `--save-json` would be named `real_<date>_<name>.json`. None of those are in the tree. A file whose name or text says synthetic is labeled `SYNTHETIC / FIXTURE` on Last Session.

## Paper files

`rio/v0.1/` is ontology version `v0.1`. The folder name is the version string the ledger stores.

`rio/v0.1/capacities.yml` is read by the ledger. Eight capacities: max velocity, speed, speed endurance, anaerobic capacity, aerobic power, threshold, aerobic, race readiness. Each row has a dose, an expression window, a decay window, and a recovery cost. Aerobic dose is 0. The other doses are 1.0. Description text is not copied onto a ledger entry.

`rio/v0.1/constraints.yml` is read by prescribe. Four absolute rules, then two preferences, in that order: `no_quality_after_high_recovery`, `no_second_hard_day`, `no_back_to_back_speed_endurance`, `closed_menu_only`, `prefer_gap`, `prefer_variety`.

`rio/v0.1/event_weights.yml` is read by the season. The `800` block is checked against the weights locked in `engines/season.py`. They sum to 1. Speed endurance 0.28, anaerobic capacity 0.18, speed 0.16, aerobic power 0.16, max velocity 0.10, threshold 0.07, aerobic 0.03, race readiness 0.02.

`rio/v0.1/goal.yml` is read by the ledger, prescribe, the Goal page, and prescription prose. The four fields are `current_mark` `2:02.90`, `target_time` `1:55.00`, `target_date` `unknown`, `limiting_capacities` `unknown`. Unknown stays the word unknown.

`rio/v0.1/events.yml` lists 800 as the scored event and 400, 1500, 3000, and 5000 as unscored. No Python file reads it.

`rio/v0.1/adaptations.yml` lists useful, fade, recovery, and evidence notes per capacity. No Python file reads it. Season adaptation is the code in `adapt()`, not this file.

`docs/goal.md` is a second goal, for athlete Chase Rose: current 2:02.9 on 4.19.26, target 1:55.0 on 3.19.27, meet Stanford Invitational qualifying standard, secondary event 400 m unscored, limiting capacity written as Speed Endurance. `classify()` reads the `Target 800` line and uses it as the pace the rules compare against. The season builder does not read this file. `show_season()` prints those same numbers only because they are the function's default arguments. The Start form uses the same numbers as hardcoded defaults. Editing `docs/goal.md` changes classification pace. It does not change a generated season unless someone types the new values into Start.

`docs/intervals_field_map.md` is the field list Activity data's detail groups follow. It is not parsed.

`docs/phase0_log.md` is a note from 2026-09-30. No code reads it.

`tests/labeled_sessions.yml` says the exam file is empty. The season and accept tests read it only to assert those paths did not change it. The engines do not read it. The season file says it does not write the exam file.

## Templates

`rio/templates/800m/` holds 82 YAML recipes. `load_menu()` reads every `*.yml` in that folder. The id inside the file must match the file name. Each recipe has `id`, `name`, `family`, `primary_stimulus`, `secondary_stimulus`, `default_structure`, and `constraints`.

The season places a subset. Phases 1–7 are a six-day week: Sunday, Monday, and Wednesday are `aer_5000_r0_x1`, Tuesday and Thursday are quality, Saturday is one long run, Friday is off. The first training week uses `aer_9500_r0_x1`. Each later training week steps up 500 m along the frozen aerobic menu, holds at `aer_15000_r0_x1`, or steps back down that same ladder when the 10% rule requires it. It does not go below 9.5 km, and `aer_8000_r0_x1` is not the Saturday long run. Phase 8 is a shorter taper and can place `rr_800_r0_x1` on the last Saturday. The phase lists name the quality ids the week is allowed to use, plus a few aerobic ids.

Ladder and step ids (`*_up_*`, `*_py_*`, `*_dn_*`) and several other recipes stay on the menu for prescribe and the Library. They are not in those phase lists, so a generated season does not place them.

The four practice fixtures in `tests/fixtures/` are separate from the menu. Each is one repeated lap: `easy.yml` (aerobic), `se_400.yml` (speed endurance), `vo2_800.yml` (aerobic power), `race_800.yml` (race readiness). The note on each says Chase did not run it. `expected_family` is on the file for tests. `normalize()` drops that field before classification.

`tests/fixtures/planned/aer_4000_r0_x1.yml` is the one accepted planned row. Source is `fixture`. Placeholder date is 2026-10-17.

## Engines

### `engines/season.py`

Builds and adapts the 800 m season. Rules only.

Reads the current 800 time, start date, goal 800 time, and goal date passed in by the caller. Reads `event_weights.yml` and checks it against the locked weights. Reads the template menu through `load_menu()`. Reads `ONTOLOGY_VERSION` from the ledger module.

Writes a dict: `ontology_version`, `season_length_weeks`, `start_date`, and `sessions`. Each session has `week_number`, `day_of_week`, `date`, `template_id`, `reason_codes`, and `target_outcome`. `adapt()` returns a new dict. The caller's plan is copied, not edited. `show_season()` prints one line per week to stdout. Running the file as a script does that for the default dates.

Week 1 is the Sunday–Saturday week that contains the start date. Days before the start date are left out. Later weeks are full weeks. Whole weeks from start to goal set the length. Phase 8 is the last two weeks, or one week when the season is one week or eight weeks. From eight weeks up, phases 1–7 each get a week, then leftover weeks fill caps and rotate through phases 1–4. A shorter season fills the taper, then phases 7, 6, and 5, and compresses phases 1–4.

Quality days take the higher primary-capacity weight when more than one template is eligible. A tie is not recorded as `capacity_weight`. Same-weight templates rotate by week index. Volume and hard-session count may not rise more than 10 percent from the previous week (`new * 10 <= previous * 11`). The current time and the goal time do not pick the template. The goal time is written into target outcomes that mention goal pace.

`adapt()` takes `on_track`, `not_hitting`, or `smashing`. A list uses the same order: not hitting wins, then smashing, otherwise on track. On track leaves the plan. Not hitting moves later weeks back one phase, or marks the next week `extra_easy_week` when the phase cannot move back. Smashing moves later weeks forward one phase, stopping at phase 7, or marks later weeks `harder_template` when they cannot advance. Phase 8 stays the taper. The judged week stays as written. The 10 percent rule still applies.

Does not call prescribe, classify, explain, or Intervals. Does not write a file, the exam file, the ledger, or SQLite. Does not read `docs/goal.md`, `goal.yml`, `events.yml`, or `adaptations.yml`. Does not place a score on the plan.

### `engines/prescribe.py`

Picks the next one to three days from the ledger. Rules only.

Reads `constraints.yml`, every template in `rio/templates/800m/`, and a `Ledger` (its goal, its capacities, and its entries). The start day is the `on` argument, or today when that is omitted.

Writes a dict with `ontology_version`, the union of reason codes, and `rows`. Each row has `template_id`, the recipe `parameters`, `ontology_version`, `prescribed_on`, and `reason_codes`. A scratch copy of the ledger records the chosen family so the next day can see it. The caller's ledger is left as it was. `show_fixture_prescriptions()` prints ids for the four fixture files. Running the file does that.

Absolute rules run first. Preferences only rank templates those rules already allowed. `closed_menu_only` rejects an id that is not on the menu. The day after a high recovery cost may only be easy. The day after a moderate or high recovery cost may not be another hard day (dose 1.0). Supporting dose 0.4 is named in the constraint text. No capacity in `capacities.yml` has dose 0.4, so that branch does not match a current capacity row. Speed endurance cannot follow speed endurance until the gap in the rule has passed. `prefer_gap` prefers a limiting capacity the ledger shows as low or decaying. With `goal.yml` as written, limiting capacities are unknown, so that preference does not fire on the stock goal. `prefer_variety` prefers a capacity not deposited in the last three days. A remaining tie uses the day-after-hard recipe when yesterday was moderate or high, then the ledger's capacity order, then a recipe that calls itself the default or the reference, then the lowest template id.

Does not build a season, call `adapt()`, classify a workout, call a model, call Intervals, or write a planned file. Does not invent a template id.

### `engines/classify.py`

Labels one normalized session. If-then rules. No model.

Reads the laps `normalize()` returns, and the `Target 800` line in `docs/goal.md`. Near goal pace is within 5 percent. Strong but slower is slower than that band and at most 1.40 times goal pace. Talkable is at least 1.90 times goal pace.

Writes `family`, `reason_codes`, `confidence`, and `ontology_version`. Confidence is `high` when one rule matches and `unsure` when the family is `unsure`.

The rules, in the order they are tested:

- Most work steps 60–150 m and rest longer than 2 minutes: max velocity.
- All work steps 200–300 m, rest longer than 2 minutes, pace near goal 800: speed.
- All work steps 300–500 m, rest 60–120 seconds, pace near goal 800: speed endurance.
- All work steps 600–1000 m, pace strong but slower than goal 800: aerobic power.
- One lap, rest 0, pace talkable: aerobic.
- One 800 m at or faster than the near-goal band: race readiness.

Empty laps are `unsure` / `no_pattern`. Missing rest is `unsure` / `rest_missing`. Two rules at once is `unsure` / `conflicting_rules`. Anything else is `unsure` / `no_pattern`.

Does not label threshold or anaerobic capacity. Those families exist on the menu and in `capacities.yml`, and this file has no rule for them. Does not read the ledger, the season, or Intervals. Does not write a file. Does not turn `confidence` into a readiness score.

### `engines/normalize.py`

Turns an adapter payload into work laps.

Reads a dict or a list. Lap lists may be named `laps`, `intervals`, `steps`, or `workout_steps`. Distance may be meters, kilometers, or miles. Time may be seconds or `h:mm:ss`. Pace may fill seconds when distance is known. Warm-up and cool-down roles are skipped. Rest and recovery roles, and a following zero-distance step, attach rest to the previous work lap. A repeated `laps` count expands one lap that many times. One blank lap can inherit activity-level distance, time, rest, and pace.

Writes `{"laps": [...]}`. Each lap has only `distance_m`, `seconds`, and `rest_s`. A missing rest stays `None`. Zero is a real rest.

Does not copy label fields (`family`, `expected_family`, `classification`, stimuli, `ontology_version`, and the other names in `LABEL_KEYS`). Does not classify. Does not call the network. Does not write a file.

### `engines/ledger.py`

Holds classifications in a Python list on the `Ledger` object.

Reads `capacities.yml` and `goal.yml` through `load_paper()`. `record_fixture()` reads one YAML fixture with `parse_fixture()`, classifies it, and stores one entry. The session date is the `on` argument, because fixture files have no date. Source is the `source` on the fixture. `record_fixtures()` does that for every `*.yml` directly in `tests/fixtures/` (not the planned or intervals subfolders).

Writes entries in memory. Each entry copies dose, expression window, decay, and recovery cost from the capacity row for that family, plus ontology version, source, date, and reason codes. `deposits_on()` returns which entries are still inside the expression window and which are inside the decay window. Day 0 is the entry date. The spans are inclusive. `load_paper()` is also what the season uses to read the weights file.

Does not write SQLite, even though `db/schema.sql` has `classifications` and `ledger_entries` tables. Does not accept a family that has no capacity row, so `unsure` cannot be recorded. Does not call Intervals. Does not change `goal.yml`. The Goal page and prescribe see `unknown` for target date and limiting capacities because that is what the file says.

### `engines/explain.py`

Writes one paragraph. This is the only file that may call a model.

Reads a classification (`explain`), or a template id plus prescription reason codes plus the four `goal.yml` fields (`explain_prescription`), or a template id plus reason codes (`explain_decision`). Reads environment variables `RIO_EXPLAIN_API_KEY`, `RIO_EXPLAIN_MODEL`, and `RIO_EXPLAIN_BASE_URL`. Optional price variables are `RIO_EXPLAIN_INPUT_USD_PER_MILLION` and `RIO_EXPLAIN_OUTPUT_USD_PER_MILLION`. Optional `RIO_EXPLAIN_SPEND_PATH` pins the spend file. Otherwise, when the service role is configured and migration 011 is present, spend is the `explain_spend` row. Before that SQL, or when the path is set, spend is `data/explain_spend.json`.

Writes one paragraph under 60 words. When the API settings are missing, the call fails, the paragraph fails its checks, or the spend cap would break, the original restatement is returned. A successful call reserves a worst-case cost, then replaces it with the call's cost. The cap is $25, stored as microdollars. Default prices are $150 and $600 per million tokens so the record reaches $25 before a typical invoice does.

The classification paragraph must keep the family and every reason. The prescription and decision paragraphs must keep the template id and must not add reps, distances, rest, or interval math. A different template id is dropped.

Does not choose a template, classify a session, or adapt a plan. Does not run on Dashboard, Calendar, Library, Activity data, Progress, Weekly, Season, Session, Settings, Ledger, or Goal. Session says it does not call a model.

### `engines/accept.py`

Records a yes for a template prescribe already chose.

Reads a template id, recipe parameters, reason codes, and a placeholder date. Checks the id and the parameters against the menu. `accept_fixture_prescription()` builds a ledger from `race_800.yml` recorded on 2026-10-16, prescribes on 2026-10-17, and accepts the first row.

Writes `tests/fixtures/planned/<template_id>.yml`. The row fields are `template_id`, `parameters`, `placeholder_date`, `ontology_version`, `source` (`fixture` only), and `reason_codes`. The placeholder date cannot be today. Running the file prints that YAML.

Does not choose the workout. Does not write the ledger. Does not call Intervals. Does not read or write the season plan. The Streamlit Decisions page only reads the file. It does not call `accept()`.

## Adapters

### `adapters/__init__.py`

Says Intervals.icu is an adapter, not the product. It exports nothing else.

### `adapters/intervals_icu.py`

Read-only HTTP client and a JSON converter.

Reads `RIO_INTERVALS_API_KEY` and `RIO_INTERVALS_ATHLETE_ID` from the environment. A blank athlete id becomes `"0"` (the key's own athlete). A missing key raises `IntervalsIcuError` and the message does not include the key.

`fetch_activity()` GETs `https://intervals.icu/api/v1/activity/<id>?intervals=true`. One request, no retry. `list_activities(oldest, newest)` GETs `/athlete/<id>/activities` and returns only `id`, `name`, `start_date_local`, and `type` for each row. Auth is HTTP basic with username `API_KEY` and the key as the password. 401, 404, and 429 get fixed messages. 429 includes the `Retry-After` header or the word missing.

`to_normalize_input()` builds `{"intervals": [...]}` from `icu_intervals`, in order. Distance stays meters on `distance_m`. `elapsed_time` becomes `seconds`. `moving_time` is not a fallback. `RECOVERY` becomes role `rest`. `WORK` becomes `work`. Other types are lowercased so warm-up and cool-down still match the skip roles in normalize. Missing and null fields stay off the step. Label fields are not copied. Laps are not dropped, merged, or filled in.

Does not POST, PUT, or DELETE. Does not write the ledger, the season, or SQLite. Does not classify.

### `adapters/intervals_cli.py`

Command line: `python -m adapters.intervals_cli`.

Reads one of `--file`, `--activity-id`, or `--list` with `--oldest` and `--newest`. A live command loads `.env` from the working directory and the project root. Existing environment values win. Values are never printed. `--save-json` is only valid with `--activity-id`.

Writes stdout: for one activity, id, name, date, normalized laps, and the classify result. For a list, one line per activity with id, name, date, and type. `--save-json` writes the fetched activity JSON to the given path. Exit code 1 prints the adapter error on stderr.

Does not store a live fetch unless `--save-json` is passed. Does not call prescribe, the season, explain, or the UI.

## Database

### `db/schema.sql`

SQLite tables and no seed rows: `ontology_versions`, `athletes`, `goals`, `workouts`, `workout_steps`, `classifications`, `ledger_entries`, `prescriptions`. `workouts.source` may be `fixture` or `intervals`. Foreign keys are on.

### `db/load.py`

Apply the schema and load fixture workouts.

Reads `db/schema.sql` and every `*.yml` or `*.yaml` directly in `tests/fixtures/`. Parses flat key-value lines. Counts files in `data/seed` that are not hidden and not `.gitkeep`. That folder is not in the tree, so the count is zero.

Writes `data/rio.sqlite`. The file is deleted and recreated on each run, including journal sidecars. Inserts one athlete named Chase, then one `workouts` row per fixture (`source` `fixture`, title from the file stem, note from `note` and `detail`) and one `workout_steps` row per lap. Elapsed time includes rest between reps and not a rest after the last rep. Prints the seed count, the athlete name, the workout count, the step count, and the database path.

Does not classify, does not call a model, and does not insert goals, ontology versions, classifications, ledger entries, or prescriptions. Does not read Intervals. The UI imports only `parse_fixture` and `fixture_paths` from this file. It never opens the database. `*.db`, `db.sqlite3`, and `data/rio.sqlite` are gitignored.

## UI shell

`ui/streamlit_app.py` is the app. `st.navigation` runs the pages below. The nav is hidden and the app draws its own links. Every page is wrapped so that a visit with the four URL inputs rebuilds the plan through `sequence()`, restores this browser's record, pulls activities when that page should, and writes the record back.

URL fields for a plan are `current_time`, `start_date`, `goal_time`, and `goal_date`. Session links add `date`. An extra activity link adds `activity`.

Browser key is `rio.plan.v1` plus those four strings. The payload is JSON: `marks` by week number, `actuals` by date, and `activities` when any were stored. Another browser opening the same URL rebuilds the plan and finds no record of its own.

Pull rules inside the wrapper:

- Dashboard, Weekly, Session, Progress, and Activity data call `sync_recent` for the last 14 days, at most 40 activities, newest first, and then `auto_adapt`.
- The first open of any other page calls `sync_recent` once and does not judge a mark.
- Refresh on Activity data calls `sync_all` from 1970-01-01 through today, with no cap, and then `auto_adapt`.
- Opening one of those five pages again pulls the 14-day window again.
- A failed list keeps the previous stored activities and shows the error. The key stays in the environment and is not printed.
- Auto-adapt runs after a successful pull on those five pages, and after Refresh. It does not run on the first-load pull of another page.

Marks the user taps on Season or Weekly call `adapt()` for that week. A result on Session calls `judge()` and then the same adapt. Settings can require a confirm step before either of those. Auto-adapt does not use that confirm step.

Display preferences live in the Streamlit session: units (`km` or `miles`), show template ids, compact CSS, date format (`iso` or short), confirm before adapt, and a notifications toggle. Notifications are stored and the page says nothing is sent. Preferences are not written onto the plan and are not passed into `adapt()`.

The page banner `SYNTHETIC / DEMO` is on the season pages. Last Session and Activity data use `SYNTHETIC / FIXTURE` when the file or the stored name says synthetic.

Does not classify inside the season pages. Does not call explain except on Last Session, Next, and Decisions. Does not write SQLite or a plan file.

### Pages

**Start** (`page_start`, default). Four inputs. Generate season calls `sequence()` and opens Season with those inputs in the URL. A bad input stays on the page with the error. Does not adapt. Does not read `docs/goal.md`.

**Dashboard** (`/dashboard`). From the stored plan: the next session on or after today, days until the goal, the current phase, the last week mark, and one focus line from this week's primary templates. Extra activities in the last 14 days are listed. Opening the page reads those 14 days and can store a mark for an unmarked quality day before the page draws. Does not call explain.

**Calendar** (`/calendar`). One month of the stored plan, Sunday–Saturday. Opens on the month that contains today. A session day gets a short label and links to Session. Race is only `rr_800_r0_x1`. Does not call explain or `adapt()`.

**Library** (`/library`). Every template `load_menu()` returns. Search matches name, id, or capacity. Capacity and phase narrow the same list. Phase membership comes from the season's phase lists, plus the easy day in every phase and the long runs in phases 1–7. Does not add templates. Does not call explain.

**Last Session** (`/last-session`). A fixture YAML file, or a JSON file from `tests/fixtures/intervals`. The JSON path runs `to_normalize_input`, then `normalize`, `classify`, and `explain`. The YAML path parses the fixture and runs the same three. Does not call Intervals. Explain spend stays capped at $25.

**Activity data** (`/activity`). After the 14-day pull, or a full pull from Refresh: one row per matched session with a date, a template or label, WORK meters, and average heart rate. A line is weekly completed WORK meters. A dot is each matched row that has an average heart rate. A second table lists every stored activity that has an activity distance or an average heart rate. An unmatched row is labeled extra. Warm-up and cool-down stay out of WORK meters. Template meters are not used. A local JSON file can fill a planned day that has a result ref and no matched work meters. Detail groups for distance, elapsed time, the interval table, max heart rate, zones, decoupling, and stream samples say `not pulled.` because those samples are not in the stored row. Does not call explain. Does call `adapt()` through auto-adapt when a matched quality day can be judged.

**Next** (`/next`). One fixture, recorded yesterday on a fresh ledger, then `prescribe()` as of today. Shows the template id, the day, the recipe parameters, the reason codes, and `explain_prescription`. Does not write a planned file and does not touch the season.

**Decisions** (`/decisions`). Reads one planned YAML file. Shows the stored acceptance fields and `explain_decision`. Does not call `accept()` and does not call prescribe on that visit.

**Ledger** (`/ledger`). Records all four fixtures as of today and shows deposits, emerging, and decaying. Banner `FIXTURE` when any source is fixture. The list disappears when the process stops. Does not call explain.

**Goal** (`/goal`). The four fields of `rio/v0.1/goal.yml`. Does not show `docs/goal.md`.

**Progress** (`/progress`). One row per plan week: phase, status, days remaining, and completed WORK distance. The week that contains today is current even if it has a mark. Another marked week is done. An unmarked week after today is upcoming. A past week with no mark has a blank status. Volume is loaded file distance overridden by a matched activity's WORK meters. A day with neither is 0. A line plots that weekly distance. Dots are matched activities that have an average heart rate, clipped to the season. Opening the page reads the last 14 days and can store a mark for an unmarked quality day before the page draws. Does not call explain.

**Weekly** (`/weekly`). One week of the plan, defaulting to the week that contains today. Recap shows sessions with a stored result, the marks, this week's WORK volume beside the week before, and one sentence if the next week already carries an adapt reason code. Day cards link to Session. A matched day shows that activity's rep times, WORK distance, and heart rate. Extra activities in the week are listed. Opening the page reads the last 14 days and can store a mark for an unmarked quality day before the page draws. The mark buttons call `adapt()`. The recap itself does not call `adapt()` or explain.

**Season** (`/season`). The plan grouped by week, Sunday through Saturday, with the calendar date. A row opens Session. Reason codes are in an expander. The mark buttons call `adapt()`. Does not record workouts by itself.

**Session** (`/session`). One planned day, or an extra activity opened by id. Shows the plain workout text, the recipe structure, the target outcome, then fixed pre-warm-up, warm-up, cool-down, and core notes. Those notes are the same on every session and are not stored on the session, so `adapt()` never reads them. Tuesday and Thursday quality, other than an `aer_` id, take one time per rep. A continuous session takes one time. A local JSON file fills WORK elapsed times into those boxes. The numbers stay editable. Filled times go through `judge()`. The activity id or the filename is stored on the actual. Opening the page reads the last 14 days. A matched quality day's stored WORK times fill the boxes and stay editable. A matched activity shows those rep times, the completed WORK distance, and the average heart rate beside the template. Does not write to Intervals and does not call explain.

**Settings** (`/settings`). The display preferences above. Confirm sits in front of a hand-entered result and a hand-entered week mark. Nothing here is written onto the plan.

## Supporting UI modules

### `ui/plan_store.py`

Share a plan by its four inputs. Marks, actuals, and activity matches stay in the browser.

Reads query params or a dict with `current_time`, `start_date`, `goal_time`, `goal_date`. Dates must be real `YYYY-MM-DD`. Each field is at most 40 characters. Reads a JSON string from localStorage.

Writes the storage key, the URL dict, and a stable JSON object. Marks must be `on_track`, `not_hitting`, or `smashing`. An actual must have a template id, one of those marks, a non-empty numbers list, and text. Optional `slots` and an Intervals id or filename (`intervals`, at most 120 characters). An activity row must have a date, an id, a matched flag, and a name. Optional start, template id (only when matched), heart rate, activity distance, WORK meters, and rep times. Unknown fields, scores, and junk are left out. An empty activity list is omitted so an older record still loads.

Does not write a file, an account, or the network. Does not call a model. The JavaScript bridge that talks to `localStorage` lives in `streamlit_app.py`, not in this file.

### `ui/activities.py`

Pull Intervals activities and match them by date.

Reads the plan's sessions, today's date, and optional stored rows. Loads `.env` the same way as the CLI, then copies `INTERVALS_API_KEY` and `INTERVALS_ATHLETE_ID` onto the `RIO_` names when those are empty. Calls `list_activities` and `fetch_activity` unless the caller passes substitutes. Uses `work_elapsed`, `work_distance`, `activity_distance`, and `activity_heart_rate` from `last_session.py`.

Writes a list of reduced activity dicts. `sync_recent` replaces stored rows inside the 14-day window and keeps rows outside it. `sync_all` replaces rows from 1970-01-01 through today and keeps rows after today. The same id keeps one row.

Matching: group by the calendar date on `start_date_local` (then `start_date`, then `date`). The earliest activity whose type is `run` fills a planned date. A date with no run uses the earliest activity. Every other activity that day is extra (`matched` false). A date with no planned session is extra. A matched row copies the planned template id, WORK elapsed times (at most 32), WORK distance, activity distance, and average heart rate. Warm-up and cool-down stay out of WORK distance. A failed detail read keeps the listed summary. A failed list becomes `PullError` and the caller keeps the old record. The 14-day pull stops after 40 listed rows, newest first. The history pull reads every listed row.

Does not call engines, explain, or `adapt()`. Does not write a file. Does not send anything to Intervals except the two GETs.

### `ui/auto_adapt.py`

Judge a matched quality day and adapt later weeks.

Reads the plan, stored activities, stored actuals, the goal time in seconds, and optional base plans. A quality day is Tuesday or Thursday and the template id does not start with `aer_`. The first matched activity on that date is the one that counts. If its template id is set and differs from the session, it is skipped. A day that already has a mark is left as stored. Empty and missing rep times are ignored. Rep times go through `fit_slots` and `judge()` with the same 3 percent band as a hand-entered result.

Writes a new plan, a new actuals dict, and the week marks just applied. The caller's plan and actuals are not changed. `bases` keeps the plan from before that week's results, so a later mark does not adapt an already adapted plan. Weeks are applied from earliest to latest. `not_hitting` wins, then `smashing`, otherwise `on_track`, which leaves later weeks as written. The actual stores the text, the numbers, the mark, the template id, the slots, and the activity id when it fits.

Does not call Intervals. Does not call a model. Does not mark recovery days, long runs, or extra activities. Does not change a day that already has a mark.

### `ui/result.py`

Turns one entered result into `on_track`, `not_hitting`, or `smashing`.

Reads a template id, a text result, and a goal 800 time. The id's trailing `_meters_rrest_xreps` supplies the rep length and the box count. Text may be times, one distance, or a distance with times. `goal_seconds()` accepts `m:ss` or `m:ss.s`.

Writes `{numbers, mark}` or `None`. `None` means empty or unreadable, and the caller ignores it. Times are compared with goal 800 pace over the rep, or over the distance written in the text. The average of the times is the actual. A distance alone is compared with the rep length. Within 3 percent is on track. The 3 percent line itself stays on track. Slower or shorter is not hitting. Faster or longer is smashing.

Does not call `adapt()`. The Session page does that after a successful judge. Does not read a file or the network. Does not produce a score.

### `ui/last_session.py`

Open one local Intervals JSON file. Display input only.

Reads `tests/fixtures/intervals/*.json`, or a path the caller passes. `open_intervals()` returns the normalize payload plus a date when the activity has one, and a synthetic banner when the file says so. `quality_fill()` returns WORK elapsed times and the activity id, or the filename when there is no id. `loaded_distances()` and `activity_by_ref()` resolve a stored id or filename back to a file in that directory. The ref has to belong to that day's template.

Writes nothing. The read stays on disk. WORK distance sums WORK interval distances. Activity distance is the activity `distance` field and is not used as the volume. Average heart rate is `average_heartrate` on the activity. Lap heart rates stay on the laps. `moving_time` is not a stand-in for elapsed time. A WORK interval with no elapsed time is an empty slot.

Does not call the network. Does not classify. The page that calls it does.

### `ui/activity_data.py`

Matched Intervals workouts, for display.

Reads stored activity rows, plan sessions, optional file distances and file heart rates, and a date format. `activity_view()` builds four groups from one stored row using the field-map labels.

Writes session rows, an all-activities list, heart-rate points, and weekly WORK meter totals. Newest start first. A matched activity with no work meters and no heart rate is left off the session list. An activity with no distance and no heart rate is left off the all-activities list. Weekly totals are empty when no row has work meters, so the page draws no line. A date outside the season is left out of the weekly totals.

Does not call Intervals, a model, or `adapt()`. Does not treat template meters as completed work.

### `ui/dashboard.py`

Display fields for Dashboard.

Reads the stored plan, the marks, and today. Writes the next workout on or after today, days until the goal (zero once the goal date has passed), the phase of the week that contains today, the latest week mark, and one focus line. An easy week says so. Otherwise the line names primary templates in date order. A taper with no primary work says it stays fresh.

Does not pull activities, adapt, or call a model. Extra activities are rendered by the page, not by this module.

### `ui/calendar.py`

One month of the stored plan.

Reads sessions and a month. Writes month titles, the opening month, short labels, and Sunday–Saturday grids. Days outside the month stay in the grid and carry no session. Labels: Race for `rr_800_r0_x1`, Race readiness for other `rr_` ids, Long for the long-run ids or the long-run reason code, Easy for other `aer_` ids, Speed for `spd_` and `mv_`, and Threshold, Aerobic power, Speed endurance, or Anaerobic for the other prefixes.

Does not adapt, classify, or call the network.

### `ui/library.py`

The frozen menu as a searchable list.

Reads the menu dicts and the season's phase lists, long-run ids, and recovery id. Writes rows with id, name, capacity label, family, and phases, and a filtered copy of those rows.

Does not load the YAML itself. The page calls `load_menu()`. Does not change the menu.

### `ui/progress.py`

Week rows and two charts.

Reads the plan window, marks, today, and a date-to-meters map. Writes week rows (`done`, `current`, `upcoming`, or a blank status), a volume SVG, and a heart-rate SVG. Current wins when the week contains today. Volume is the meters it was given. Template meters are not read here. Heart-rate dots are the points it was given, limited to the season weeks.

Does not pull activities or call `adapt()`.

### `ui/recap.py`

One selected week: what was recorded, and what the next week already says.

Reads that week's sessions, actuals, marks, and distances. A session counts as completed when that day has a stored result for the same template. A week mark with no results still counts as marked. Volume is this week beside the week before, from the distances it was given. The next-week sentence is fixed words for the first matching adapt code already on the following week: easy week, harder session, moved back, or advanced. Otherwise the next week stays as written. The last week says so.

Does not call `adapt()`. Does not call a model.

### `ui/settings.py`

Display preferences.

Reads a loose dict. Writes a complete preference dict, defaulting unknown values. Also formats dates and rewrites km or meter text for display in miles. The stored plan stays in meters. A statute mile is used only for that rounding.

Does not write the plan, call `adapt()`, or send notifications.

## Tests

Tests are plain Python assertions. They do not start Streamlit and they do not call Intervals unless a test patches the HTTP client. Several tests also assert that explain's spend cap constant is still $25.

`tests/test_season.py` checks phase lengths, dates, the 10 percent rule, calendar dates, quality weights, a 17-week season, a short season, and adaptation.

`tests/test_prescribe.py` runs prescribe on the four fixture ledgers.

`tests/test_fixtures.py` classifies the four YAML fixtures and checks the expected family.

`tests/test_accept.py` accepts the race fixture prescription and checks the planned row.

`tests/test_explain.py` checks classification prose, prescription prose, and decision prose, including a wrong template id, invented structure, missing goal fields, and the spend cap. The cap tests use a temporary spend file.

`tests/test_intervals_adapter.py` checks the two synthetic JSON files, the lap converter, config and HTTP errors, and the CLI. Network calls are patched. The recovery fixture classifies as speed endurance. The autosplit fixture is `rest_missing`. `--file` does not use the network. `--save-json` writes the fetched body. `--save-json` without a fetch is rejected.

`tests/test_activities.py` checks the 14-day window, the history range, date matching, WORK times, volume, heart rate, the 40-activity cap, a failed detail, a failed list, `.env` aliasing, and that a pull does not spend.

`tests/test_activity_data.py` checks matched rows, the not-pulled detail groups, the all-activities table, weekly WORK meters, file fallback, heart-rate labels, and that the page path does not spend.

`tests/test_auto_adapt.py` checks that a matched quality day adapts later weeks, that not hitting wins, that a hand mark stays, that on track leaves later weeks, and that recovery, the long run, extras, and empty reps do not adapt.

`tests/test_last_session.py` checks the JSON directory, the synthetic banner, a bad file, WORK times, distance, heart rate, and that the page stays offline.

`tests/test_plan_store.py` checks the four URL inputs, the storage key, the marks and actuals round trip, the Intervals ref, pulled activities, and that the store does not leave the browser.

`tests/test_result.py` checks the 3 percent band, distance, ignored input, rep boxes, and that two results adapt once.

`tests/test_dashboard.py`, `tests/test_calendar.py`, `tests/test_library.py`, `tests/test_progress.py`, `tests/test_recap.py`, and `tests/test_settings.py` check those display modules against a plan from `sequence()` or against fixed rows.

There is no test module for `db/load.py`. There is no separate test module for `normalize.py`. Its behavior is covered through classify, the adapter tests, and Last Session.

## What is wired, and what is only on disk

Wired into the running app: the season builder and `adapt()`, the menu, the weights file, the browser store, the activity pull, matching, auto-adapt on Dashboard, Weekly, Session, Progress, and Activity data, hand-entered results, local Intervals JSON for Last Session and for Session boxes, classify and normalize on Last Session, prescribe on Next, the planned YAML file on Decisions, the in-memory ledger on Ledger, `goal.yml` on Goal, and explain on the three prose pages.

Present and used by a script, not by a page: `adapters/intervals_cli.py`, `db/load.py`, `engines/accept.py` as a writer (the page only reads what it wrote), and the stdout helpers on season and prescribe.

Present and unused by the engines and the app: `rio/v0.1/events.yml`, `rio/v0.1/adaptations.yml`, and `docs/phase0_log.md`. `tests/labeled_sessions.yml` is read by two tests that check it stayed empty. The SQLite tables for goals, classifications, ledger entries, and prescriptions are never inserted. The schema allows an Intervals workout source. No loader inserts one.
