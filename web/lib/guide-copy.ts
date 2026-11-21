/**
 * Plain-language guidance for the screens that already exist.
 * Sentences here are the guide page and the "What this means" notes.
 * Change the wording in this file only.
 */

export const GUIDE_TITLE = "How to use RIO";

export const GUIDE_LEDE = "How to start, how to read today's workout, and how the week is built.";

export const GUIDE_LINK = "Read this in the guide";

export type GuideDetail = {
  summary: string;
  paragraphs: readonly string[];
};

export type GuideSection = {
  id: string;
  title: string;
  paragraphs: readonly string[];
  bullets?: readonly string[];
  details?: readonly GuideDetail[];
};

export type PageMeaning = {
  /** Anchor on /guide. The footer link goes here. */
  section: string;
  sentences: readonly string[];
};

/** Page notes. One or two sentences. Off-guide pages link to Getting started. */
export const PAGE_MEANINGS = {
  guide: {
    section: "getting-started",
    sentences: ["This page is the short map. Open the section for the screen you are on."],
  },
  home: {
    section: "today",
    sentences: ["Home is the days left, the current phase, and today's workout or the next one."],
  },
  plan: {
    section: "pages",
    sentences: ["Plan is every week from the start date to the goal date, as a calendar or a full list."],
  },
  session: {
    section: "today",
    sentences: ["Start session is the next planned day, with the workout line and a time for each rep."],
  },
  activity: {
    section: "pages",
    sentences: ["Activity is the runs Strava brought in for this season. Refresh asks for newer ones."],
  },
  "past-seasons": {
    section: "pages",
    sentences: ["Past seasons lists every saved season. Open plan loads one, and Delete shows the stored facts."],
  },
  library: {
    section: "pages",
    sentences: ["Library sits under Training, next to Stretching and Core. Search, What it trains, and Phase narrow the list."],
  },
  core: {
    section: "pages",
    sentences: [
      "Core, under Training, is a daily circuit: about 8 minutes on a hard day, 12 to 15 minutes on an easy day, and none on race day or the day before.",
      "Not medical advice, and a painful area is a reason to see a professional.",
    ],
  },
  stretching: {
    section: "stretching",
    sentences: [
      "Stretching sits under Training, next to Library, and follows today's plan in your Settings time zone, and the date picks a different routine for the next day of that kind.",
      "A hard day warms up and cools down, a long run recovers longer, an easy or rest day stays short, a race day gets a primer, and sharp pain adds no stretches.",
    ],
  },
  settings: {
    section: "pages",
    sentences: ["Settings holds your name, pace units, heart rate, and Strava. The danger zone clears the plan or the account."],
  },
  about: {
    section: "phases",
    sentences: ["About is the short account of the phases and the weekly rise."],
  },
  more: {
    section: "pages",
    sentences: ["More links to Past seasons, Profile, Settings, Guide, and About."],
  },
  profile: {
    section: "paces",
    sentences: ["Profile keeps the easy pace and the season you set on Start. A new goal time does not rebuild it."],
  },
  creators: {
    section: "getting-started",
    sentences: ["A short note on how a season is built, for any runner using the plan."],
  },
  start: {
    section: "getting-started",
    sentences: ["Start asks for today's 800, the two dates, and the goal time, then builds the season."],
  },
  "easy-pace": {
    section: "paces",
    sentences: ["Enter an easy pace like 7:25, per mile or per kilometer. Easy and long runs use it."],
  },
  "heart-rate": {
    section: "paces",
    sentences: [
      "Resting and max heart rate set five Karvonen zones.",
      "Without a heart rate monitor, the easy pace question stays.",
    ],
  },
  intro: {
    section: "getting-started",
    sentences: ["The intro points you to Start, Strava, and Plan. Done and Skip both save that you have seen it."],
  },
  admin: {
    section: "getting-started",
    sentences: ["Only an admin login sees this screen. It lists accounts and can load a test season."],
  },
  "last-session": {
    section: "getting-started",
    sentences: ["This screen reads a fixture and shows the laps. Any other login is sent Home."],
  },
  next: {
    section: "getting-started",
    sentences: ["This screen shows the prescription the rules write for a fixture file."],
  },
  decisions: {
    section: "getting-started",
    sentences: ["This screen shows one planned fixture row and the groups stored with it."],
  },
  ledger: {
    section: "getting-started",
    sentences: ["This screen lists the groups stored on the fixture, with the date the file was read."],
  },
  goal: {
    section: "getting-started",
    sentences: ["This screen shows the fixture goal: the current mark, the target time, and the target date."],
  },
} as const satisfies Record<string, PageMeaning>;

export type PageMeaningId = keyof typeof PAGE_MEANINGS;

export const GUIDE_SECTIONS: readonly GuideSection[] = [
  {
    id: "getting-started",
    title: "Getting started",
    paragraphs: ["Create an account, save an easy pace, then generate the season."],
    bullets: [
      "Name, email, and a password of at least 8 characters. A local account needs only a first name. A hosted account sends a confirmation link.",
      "Easy pace is minutes and seconds, like 7:25, per mile or per kilometer.",
      "On Start, enter today's 800, the start date, the goal 800, and the race date. Times look like 2:05.0. Generate season plan opens Home.",
      "Connect Strava on Home or in Settings. Strava is the only place runs are imported from, and those runs are only visible to you.",
    ],
  },
  {
    id: "today",
    title: "Today's workout",
    paragraphs: [
      "Home shows the days left until your goal 800, the current phase, and today's workout or the next one. Start session opens that day.",
    ],
    bullets: [
      "A quality line reads like 6 × 400 m @ 71.2 s, 90 s rest: the reps, the time for each rep, and the rest.",
      "When the reps share that time, it is their average. Tolerance is the window around it. Block adds the reps and the rests between them.",
      "Type a time for each rep, or finish with Done when you don't use a watch. Got it clears a season note.",
    ],
  },
  {
    id: "paces",
    title: "Paces",
    paragraphs: [
      "Easy and long runs use the pace you saved, such as Run at 7:25 per mile. Profile is where you change it.",
      "Quality workouts stay on your 800. If the easy pace is missing, the page asks you to set it.",
    ],
  },
  {
    id: "week",
    title: "The week",
    paragraphs: [
      "Tuesday and Thursday are quality days, unless that day is an easy run. Saturday is the long run. Sunday, Monday, and Wednesday are easy, and Friday is off.",
      "The Saturday long run starts at 9.5 km and steps up 500 m a week until 15 km. From one week to the next, distance and hard sessions can rise by at most 10%.",
    ],
    details: [
      {
        summary: "Long-run ladder",
        paragraphs: [
          "The first training week uses 9.5 km. Later weeks step up 500 m, hold, or step back one rung, and the run stops at 15 km. 8 km is outside the ladder.",
          "The usual easy day is one continuous 5 km run. When a week would rise too fast, the plan can use a 4 km or a 10 km easy run instead.",
          "Hard sessions are the ones that are not easy runs. If a week would climb faster than 10%, the plan holds or picks an easier session. The taper may drop.",
        ],
      },
    ],
  },
  {
    id: "phases",
    title: "Phases",
    paragraphs: ["The season moves through eight phases. Home calls the current one the training block."],
    details: [
      {
        summary: "The eight phases",
        paragraphs: [
          "Phases 1–7 are a six-day week. Phase 8 is a shorter taper, and the 800 m race can sit on the last Saturday.",
          "Phase 1 is aerobic, with max velocity and speed beside it. Phase 2 steps the short fast reps up. Phase 3 adds threshold and aerobic power. Phase 4 brings speed endurance.",
          "Phase 5 keeps that work with longer reps. Phase 6 is anaerobic capacity. Phase 7 is race readiness. Phase 8 stays fresh: race readiness and max velocity, with no hard speed endurance or anaerobic work.",
          "From eight weeks up, phases 1–7 each get a week and phase 8 is the last two, or one week when the season is one or eight weeks. Extra weeks fill phases 1–4 up to a cap, then 5–7, then rotate through 1–4. A shorter season fills the taper, then phases 7, 6, and 5.",
        ],
      },
    ],
  },
  {
    id: "progress",
    title: "Progress",
    paragraphs: [
      "With no logged runs, progress says No runs yet. After runs are logged it says on track, ahead, or behind.",
      "Ahead means the logs have tightened the 800. Behind means they have eased it. On track means they have not moved it.",
    ],
    details: [
      {
        summary: "What a mark changes",
        paragraphs: [
          "On a hard Tuesday or Thursday, mark the week On track, Not hitting, or Smashing. Within 3% of the target is On track and leaves later weeks as they are. Slower or shorter is Not hitting and moves later weeks back one phase. Faster or longer is Smashing and moves them forward, stopping at phase 7.",
          "Phase 8 stays the taper. Not hitting wins when more than one mark applies. Without a watch, a hard day asks for Behind, On target, or Ahead. Easy and long runs do not.",
        ],
      },
    ],
  },
  {
    id: "pages",
    title: "The other pages",
    paragraphs: ["Each of these is one job."],
    bullets: [
      "Plan shows the weeks from the start date to the goal date, as Calendar, This week, or Full season.",
      "Activity shows Strava runs, distance, and heart rate. Refresh asks for newer runs.",
      "Library, under Training, is the workout menu. Search, What it trains, and Phase narrow the same list.",
      "Core, under Training, rotates anti-extension, anti-rotation, lateral, flexion, and running-specific work.",
      "Past seasons lists each saved season by start date, goal date, and goal time. Open plan loads it. Delete shows facts already stored, such as workouts logged and a timed 800.",
      "Settings holds your name, time zone, pace units, and Strava. The danger zone clears marks, the plan, or the account.",
      "Profile keeps the easy pace and the season from Start. Saving a new goal 800 time does not rebuild the season.",
      "About is the short version of the phases and the 10% rise. More links to Past seasons, Profile, Settings, Guide, and About.",
    ],
  },
  {
    id: "stretching",
    title: "Stretching",
    paragraphs: [
      "Stretching sits under Training, next to Library, and follows today's plan in your Settings time zone. The date picks a different routine for the next day of that kind.",
      "A hard day warms up and cools down, a long run recovers longer, an easy or rest day stays short, a race day gets a primer, and sharp pain adds no stretches.",
    ],
  },
];

export function guidePlainText(sections: readonly GuideSection[] = GUIDE_SECTIONS): string {
  return [
    GUIDE_TITLE,
    GUIDE_LEDE,
    ...sections.flatMap((section) => [
      section.title,
      ...section.paragraphs,
      ...(section.bullets ?? []),
      ...(section.details ?? []).flatMap((detail) => [detail.summary, ...detail.paragraphs]),
    ]),
  ].join("\n");
}

export function meaningHref(section: string): string {
  return `/guide#${section}`;
}
