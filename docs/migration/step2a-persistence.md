# Step 2a persistence

The API stores the two session fields step 1 left in the browser tab.

`season_quality_base` is written to `public.season_state.quality_base`. The key is the athlete and the four season inputs, the same key as `plans`. The plan, marks, and actuals stay on `plans`. A Streamlit save does not send this table, so it does not clear it.

`rio_workout_notes` is `workout_notes` on that row: `{date: {note, viewed}}`. The plan is saved first. The note is saved after that, and the model is not called from these routes.

Jay runs `supabase/migrations/009_season_state.sql` in the SQL editor. Row level security limits each athlete to their own rows. `delete_past_season` removes the row when a past season is deleted.

When the row is missing, the API rebuilds the bases before it adapts:

1. `sequence()` for the four inputs. The saved plan is not the starting point.
2. Marked weeks, smallest week number first.
3. The base for a week is the plan from before that week. Adapting an earlier week drops later bases.

That order is the one `auto_adapt` uses. The rebuilt bases are stored on the next successful write so the following request does not adapt the week again.

Local accounts keep the same JSON under the sealed key `rio.api.state.v1`. It is not a plan key. The plan key is written last so the Streamlit file still opens the season. A record that does not fit leaves the bases empty and the next request uses the order above.
