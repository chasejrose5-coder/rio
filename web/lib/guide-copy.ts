/**
 * Plain-language guidance for the screens that already exist.
 * Sentences here are the guide page and the "What this means" notes.
 * Change the wording in this file only.
 */

export const GUIDE_TITLE = "How to use RIO";

export const GUIDE_LEDE =
  "RIO builds an 800 m season for the runner who is signed in. This page says what each screen is for, and how to read the plan.";

export const GUIDE_LINK = "Read this in the guide";

export type GuideSection = {
  id: string;
  title: string;
  paragraphs: readonly string[];
};

export type PageMeaning = {
  /** Anchor on /guide. The footer link goes here. */
  section: string;
  sentences: readonly string[];
};

const gettingStarted: GuideSection = {
  id: "getting-started",
  title: "Getting started",
  paragraphs: [
    "Create an account with your name, email, and a password of at least 8 characters. On a machine that keeps accounts in a local file, a first name is enough and the account stays on that machine. A hosted account sends a confirmation link. Open it, then log in.",
    "When no easy pace is saved yet, the next screen asks for one. Enter minutes and seconds, like 7:25, and choose per mile or per kilometer. Easy and long runs use this pace. Quality workouts stay on your 800.",
    "The intro, when it shows, has three steps: set your goal on Start, connect Strava in Settings, and open Plan to mark how the week went. Done and Skip both save that you have seen it.",
    "Start asks for your 800 m time today, the day this season starts, the 800 m time you are aiming for, and the race date. Times use minutes:seconds.tenths, like 2:05.0. A rough guess is fine. Generate season plan opens Home.",
    "Home can then offer to connect Strava, so your runs show up. You can connect later in Settings. Strava is the only place runs are imported from, and that data is only visible to you.",
  ],
};

/** Page notes. Each one is also a section of the guide. Two to four sentences. */
export const PAGE_MEANINGS = {
  guide: {
    section: "getting-started",
    sentences: [
      "This page explains each screen and how to read the plan.",
      "Start with Getting started, then open the section for the page you are on.",
    ],
  },
  home: {
    section: "home",
    sentences: [
      "Home shows how many days are left until your goal 800, plus the current phase, the last timed effort, this week's focus, and progress status.",
      "Below that is today's workout or the next one, the next three days, and a season note when one is waiting.",
      "A note has a headline and a paragraph. Got it marks it seen.",
    ],
  },
  plan: {
    section: "plan",
    sentences: [
      "Plan is every week from the start date to the goal date, with the phase of each week and a pace-status line.",
      "Calendar, This week, and Full season are three views of that plan.",
      "On a hard Tuesday or Thursday you can mark the week On track, Not hitting, or Smashing.",
    ],
  },
  session: {
    section: "session",
    sentences: [
      "Start session opens the next planned day, or the last day of the season when that day has passed.",
      "The page shows the workout, the pace line, the structure, the target, and the reasons for that day, plus the warm-up and cool-down.",
      "A quality day asks for the time of each rep. With \"I don't use a watch\" on in Settings, you finish with Done instead.",
    ],
  },
  activity: {
    section: "activity",
    sentences: [
      "Activity is the runs Strava has brought in for this season.",
      "Refresh pulls the latest runs. The page then shows completed distance, the latest heart rate, and this week's distance, run count, and marks.",
      "Connect Strava in Settings when the page is still waiting for runs.",
    ],
  },
  "past-seasons": {
    section: "past-seasons",
    sentences: [
      "Past seasons lists every season saved on this account, the current one included, with the start date, the goal date, and the goal time.",
      "Open plan loads that season on Plan.",
      "Delete season asks you to confirm, and the panel lists facts already stored, such as workouts logged, distance, phases, notes, and a timed 800.",
    ],
  },
  library: {
    section: "library",
    sentences: [
      "Library is the menu of workouts a season can use, and search, What it trains, and Phase narrow that list.",
      "What it trains names that quality, such as speed or a long easy run.",
      "A phase is a training block, and the season moves through eight of them.",
    ],
  },
  settings: {
    section: "settings",
    sentences: [
      "Settings holds your name, time zone, password, and email.",
      "Logging turns on Done when you don't use a watch, and Preferences set pace units, the start date, compact mode, dates, and whether a timed run asks before the plan changes.",
      "Strava connects here, and a season can be exported as JSON.",
      "The danger zone clears marks, resets the plan, deletes the account, or clears data stored in this browser.",
    ],
  },
  about: {
    section: "about",
    sentences: [
      "About is the short account of the phases, the 10% rise from one week to the next, how a session is labeled, and what a hard-day mark does to later weeks.",
      "The same rules are written out on this guide, under Phases, The week, and Progress.",
      "The sentences on About stay the short version.",
    ],
  },
  more: {
    section: "more",
    sentences: [
      "More collects the rest of the app in this tab: Past seasons, Profile, Settings, About, and Creators.",
      "Each row is the link to that page.",
    ],
  },
  profile: {
    section: "profile",
    sentences: [
      "Profile keeps the easy pace and the season you set on Start.",
      "You can change the easy pace here, and easy and long runs use it while the harder sessions stay on your 800 time.",
      "The current 800, the start date, and the goal date stay with the season. Saving a new goal 800 time keeps it on the account and does not rebuild the season.",
    ],
  },
  creators: {
    section: "creators",
    sentences: [
      "Creators is a short note from the person who built RIO, written for any runner using the plan.",
      "It sits with the other pages under More.",
    ],
  },
  start: {
    section: "start",
    sentences: [
      "Start is the form that builds a season: your 800 m time today, the start date, the 800 m time you want, and the race date.",
      "Times are minutes:seconds.tenths, like 2:05.0, and a rough guess is fine.",
      "Generate season plan opens Home with that season.",
    ],
  },
  "easy-pace": {
    section: "easy-pace",
    sentences: [
      "This screen shows when the account has no easy pace yet.",
      "Enter minutes and seconds, like 7:25, and choose per mile or per kilometer.",
      "Easy and long runs use that pace, the harder sessions stay on your 800 time, and Profile is where you change it later.",
    ],
  },
  intro: {
    section: "intro",
    sentences: [
      "The intro is three steps: set the goal on Start, connect Strava in Settings, and check Plan.",
      "Done and Skip both save that you have seen it, then open the app.",
    ],
  },
  admin: {
    section: "admin",
    sentences: [
      "Admin appears in the nav only for an admin login.",
      "It lists accounts, and it can load a separate test season without changing this login.",
      "Startup photos can be shown, reordered, or given a new credit, then saved.",
    ],
  },
  "last-session": {
    section: "last-session",
    sentences: [
      "Last Session is for an admin login. It reads a fixture session or an intervals file and shows the laps, the family, and the reason codes.",
      "Any other login is sent back to Home.",
    ],
  },
  next: {
    section: "next",
    sentences: [
      "Next is an admin page for a fixture session.",
      "It shows the prescription the rules write for that file.",
    ],
  },
  decisions: {
    section: "decisions",
    sentences: [
      "Decisions is an admin page for a planned fixture row.",
      "It shows the parameters, and Deposits, Emerging, and Decaying when that row has them.",
    ],
  },
  ledger: {
    section: "ledger",
    sentences: [
      "Ledger is an admin page of deposits, emerging, and decaying rows.",
      "The line under the title is the as-of date when the file has one.",
    ],
  },
  goal: {
    section: "goal",
    sentences: [
      "Goal is an admin page for the fixture goal.",
      "The card lists the current mark, the target time, the target date, and the limiting capacities.",
    ],
  },
} as const satisfies Record<string, PageMeaning>;

export type PageMeaningId = keyof typeof PAGE_MEANINGS;

const reading: GuideSection[] = [
  {
    id: "phases",
    title: "Phases",
    paragraphs: [
      "A training block is one phase. The season moves through eight of them. Home calls the current one the training block.",
      "Phases 1–7 are a six-day week. Sunday, Monday, and Wednesday are easy. Tuesday and Thursday are hard. Saturday is the long run. Friday is off.",
      "Phase 1 is aerobic, with max velocity and speed beside it. Phase 2 is the same, and the short fast reps step up from phase 1. Phase 3 is threshold and aerobic power, with aerobic and speed beside them. Phase 4 is speed endurance and aerobic power, with aerobic and speed beside them.",
      "Phase 5 is speed endurance and aerobic power, with speed beside them, and the reps are longer than in phase 4. Phase 6 is anaerobic capacity, with speed endurance and speed beside it. Phase 7 is race readiness, with speed endurance and speed beside it.",
      "Phase 8 is a shorter taper: race readiness and max velocity. The taper stays fresh. It has no hard speed endurance or anaerobic work. The 800 m race can sit on the last Saturday.",
      "From eight weeks up, phases 1–7 each get a week. Phase 8 is the last two weeks, or one week when the season is one week or eight weeks. Weeks still left fill phases 1–4 up to a cap, then phases 5–7. Anything past those caps rotates through phases 1–4. A shorter season fills the taper, then phases 7, 6, and 5, and compresses phases 1–4.",
    ],
  },
  {
    id: "week",
    title: "The week",
    paragraphs: [
      "Tuesday and Thursday are the quality days, unless that day is an easy run. Saturday is the long run. Sunday, Monday, and Wednesday are easy. Friday is off.",
      "The Saturday long run starts at 9.5 km. Each later training week steps it up by 500 m, holds, or steps back one rung, and it stops at 15 km. The first training week uses 9.5 km. The ladder begins there, so 8 km is outside it.",
      "The usual easy day is one continuous 5 km run. When a week would rise too fast, the plan can use a 4 km or a 10 km easy run instead.",
      "From one week to the next, distance and the number of hard sessions can rise by at most 10%. Hard sessions are the ones that are not easy runs. If a week would climb faster, the plan holds or picks an easier session. The taper may drop.",
    ],
  },
  {
    id: "workout-lines",
    title: "Workout lines",
    paragraphs: [
      "A quality line states the reps, the time for each rep, and the rest. When every rep is the same, it reads like 6 × 400 m @ 71.2 s, 90 s rest: six reps, 400 metres each, 71.2 seconds each, then 90 seconds of rest. When the reps differ, each distance and time is listed on its own.",
      "The time after the @ is the time for that rep. When the reps share one time, that time is their average. The prescription keeps that average with the line. Tolerance is the window around the time. Block adds the rep times and the rests between them. A speed workout leaves Block off.",
      "On the session page, a quality day has a box for each rep. The label is Rep 1, Rep 2, and so on, and the hint is to enter the time for each rep. Times save as you type. If Settings asks first, Confirm saves the result and Cancel leaves it.",
      "An easy or long run is one effort. Its line is a pace, such as Run at 7:25 per mile, rather than a row of rep times.",
    ],
  },
  {
    id: "paces",
    title: "Paces",
    paragraphs: [
      "Easy and long runs use the easy pace you entered, per mile or per kilometer. The line is that pace. It is the pace from the easy-pace screen, or from Profile if you change it later.",
      "Quality workouts ignore that pace and stay on your 800. Their times come from the goal and the current 800, and from runs you have already logged.",
      "If the easy pace is missing, a continuous easy or long run asks you to set it. The page does that instead of inventing a pace.",
    ],
  },
  {
    id: "progress",
    title: "Progress",
    paragraphs: [
      "Home's Progress status and Plan's pace-status line read the same clock. With no logged runs it says No runs yet. After runs are logged it says on track, ahead, or behind.",
      "On track means the logs have not moved the 800 the calendar is aiming at. Ahead means the logs have tightened that 800. Behind means they have eased it.",
      "Plan also marks each week done, current, or upcoming. The week that contains today is current. A marked week that is not the current week is done. A future week is upcoming. A past week with no mark shows a dash.",
      "A hard day is a Tuesday or Thursday that is not an easy run. A result within 3% of the target is On track. Slower or shorter is Not hitting. Faster or longer is Smashing. On track leaves later weeks as they are. Not hitting moves later weeks back one phase. Smashing moves them forward one phase and stops at phase 7. Phase 8 stays the taper. When more than one mark applies, Not hitting wins. Later weeks are what change.",
      "Without a watch, a hard day asks for Behind, On target, or Ahead before Done. Easy and long runs do not ask for that choice.",
    ],
  },
  {
    id: "notes",
    title: "Notes",
    paragraphs: [
      "Home and Start session can show a note for a day: a headline, a paragraph, and sometimes a Carry forward line you can open. Got it marks that note seen.",
      "The words come from the season already stored. A thin week can ask you to connect Strava or log the hard day, so a later note has something to say.",
      "Past seasons can count those notes. The count appears in the delete panel when it was stored, under Notes or Insights.",
    ],
  },
  {
    id: "past-stats",
    title: "Past-season stats",
    paragraphs: [
      "The row itself shows the start date, the goal date, and the goal time. The extra facts appear when you choose Delete season, before anything is removed.",
      "The panel lists only facts already stored. It can include the season dates, the goal time, an event name, workouts logged, workouts completed, distance logged, a timed 800, the best 800, the last 800, phases completed, notes, insights, and adaptations.",
      "A missing fact is left off the panel. Nothing there is estimated from the calendar. Deleting the season you are training now sends you back to Start to set up another one.",
    ],
  },
];

const pageSections: GuideSection[] = (
  [
    ["home", "Home"],
    ["plan", "Plan"],
    ["session", "Start session"],
    ["activity", "Activity"],
    ["past-seasons", "Past seasons"],
    ["library", "Library"],
    ["settings", "Settings"],
    ["about", "About"],
    ["more", "More"],
    ["profile", "Profile"],
    ["creators", "Creators"],
    ["start", "Start"],
    ["easy-pace", "Easy pace"],
    ["intro", "Intro"],
    ["admin", "Admin"],
    ["last-session", "Last Session"],
    ["next", "Next"],
    ["decisions", "Decisions"],
    ["ledger", "Ledger"],
    ["goal", "Goal"],
  ] as const
).map(([id, title]) => ({
  id,
  title,
  paragraphs: PAGE_MEANINGS[id].sentences,
}));

export const GUIDE_SECTIONS: readonly GuideSection[] = [gettingStarted, ...pageSections, ...reading];

export function meaningHref(section: string): string {
  return `/guide#${section}`;
}
