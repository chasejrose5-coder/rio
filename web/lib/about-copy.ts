// Generated from the Streamlit page. Do not edit the sentences.
export const ABOUT = {
  "index": "About",
  "heading": "About",
  "credit": "Photo by Botond Dobozi on Pexels",
  "sections": [
    {
      "title": "Eight phases",
      "visible": [
        "Phases 1–7 are a six-day week. Sunday, Monday, and Wednesday are easy. Tuesday and Thursday are hard. Saturday is the long run. Friday is off.",
        "Phase 8 is a shorter taper. The 800 m race can sit on the last Saturday."
      ],
      "rows": [
        {
          "label": "Phase 1",
          "line": "Aerobic, with max velocity and speed beside it."
        },
        {
          "label": "Phase 2",
          "line": "Aerobic, with max velocity and speed beside it. The short fast reps step up from phase 1."
        },
        {
          "label": "Phase 3",
          "line": "Threshold and aerobic power, with aerobic and speed beside them."
        },
        {
          "label": "Phase 4",
          "line": "Speed endurance and aerobic power, with aerobic and speed beside them."
        },
        {
          "label": "Phase 5",
          "line": "Speed endurance and aerobic power, with speed beside them. The reps are longer than in phase 4."
        },
        {
          "label": "Phase 6",
          "line": "Anaerobic capacity, with speed endurance and speed beside it."
        },
        {
          "label": "Phase 7",
          "line": "Race readiness, with speed endurance and speed beside it."
        },
        {
          "label": "Phase 8",
          "line": "Race readiness and max velocity. The taper stays fresh. No hard speed endurance or anaerobic work."
        }
      ],
      "closing": [
        "From eight weeks up, phases 1–7 each get a week. Phase 8 is the last two weeks, or one week when the season is one week or eight weeks. Weeks still left fill phases 1–4 up to a cap, then phases 5–7. Anything past those caps rotates through phases 1–4. A shorter season fills the taper, then phases 7, 6, and 5, and compresses phases 1–4."
      ],
      "hidden": []
    },
    {
      "title": "10% rule",
      "visible": [
        "From one week to the next, distance and the number of hard sessions can rise by at most 10%. Hard sessions are the ones that are not easy runs. If a week would climb faster, the plan holds or picks an easier session. The taper may drop."
      ],
      "rows": [],
      "closing": [],
      "hidden": [
        "From one week to the next, planned distance and the number of hard sessions may rise by at most 10%. Hard sessions are the ones that are not easy runs. A rise fits when the new week times 10 is still no more than the previous week times 11.",
        "If the week as written would climb faster, the plan holds or uses an easier session. The taper may drop. The same cap still applies after a mark changes later weeks."
      ]
    },
    {
      "title": "Classification",
      "visible": [
        "RIO labels each session with rules. It reads how far the rep is, how long you rest, and how that pace compares with your goal 800. You see one kind of work and a short reason."
      ],
      "rows": [],
      "closing": [],
      "hidden": [
        "Classification is rules, not AI. The rules read each rep's distance, the rest, and the pace against the goal 800. The result is one family, the reason codes, and the ontology version.",
        "A model does not pick the family. On Last Session, Next, and Decisions, a model may only rephrase a paragraph the rules already wrote. A rephrase that changes the family, the template, or the reasons is dropped. Those calls stop once recorded spend reaches $25."
      ]
    },
    {
      "title": "Hard days",
      "visible": [
        "Tuesday and Thursday are hard days, unless that day is an easy run. A result within 3% of the target is on track. Slower or shorter means the week fell short. Faster or longer means it went better. On track leaves later weeks as they are. Falling short moves later weeks back one phase. Doing better moves them forward one phase and stops at phase 7. Phase 8 stays the taper. When more than one mark applies, falling short wins. Later weeks are what change."
      ],
      "rows": [],
      "closing": [],
      "hidden": [
        "A hard day is a Tuesday or Thursday that is not an easy run. A result within 3% of the target is on_track. Slower or shorter is not_hitting. Faster or longer is smashing. Season and Weekly can mark a week with those same three words.",
        "The marked week stays as written. On track leaves the later weeks. Not hitting moves them back one phase, or makes the next week easy when the phase cannot move back. Smashing moves them forward one phase and stops at phase 7, or uses a harder session from the menu when the phase cannot advance. Phase 8 stays the taper.",
        "Not hitting wins when more than one mark applies, then smashing. A matched activity on a hard day is judged when that day has no mark yet. Later weeks are what change."
      ]
    }
  ]
} as const;
