/** Plain meanings for the training words. Added beside the existing copy. */

export const GLOSSARY: { term: string; meaning: string }[] = [
  { term: "Max velocity", meaning: "Short all-out sprints." },
  { term: "Speed endurance", meaning: "Holding fast pace as you tire." },
  { term: "Anaerobic capacity", meaning: "Hard efforts of 30 to 90 s." },
  { term: "Aerobic power", meaning: "Fast running you can sustain for several minutes." },
  { term: "Threshold", meaning: "Comfortably hard, about 1-hour race pace." },
  { term: "Taper", meaning: "Fewer, shorter sessions before the race." },
  { term: "Zone 2", meaning: "Easy, conversational effort." },
  { term: "Karvonen", meaning: "Zones from the gap between resting and max heart rate." },
];

export const PHASE_PLAIN: Record<number, string> = {
  1: "Aerobic, with max velocity and speed beside it.",
  2: "Aerobic, with max velocity and speed beside it. The short fast reps step up from phase 1.",
  3: "Threshold and aerobic power, with aerobic and speed beside them.",
  4: "Speed endurance and aerobic power, with aerobic and speed beside them.",
  5: "Speed endurance and aerobic power, with speed beside them. The reps are longer than in phase 4.",
  6: "Anaerobic capacity, with speed endurance and speed beside it.",
  7: "Race readiness, with speed endurance and speed beside it.",
  8: "Race readiness and max velocity. The taper stays fresh.",
};

export const MEDICAL_NOTE =
  "Not medical advice. If pain is sharp or getting worse, or your heart rate stays unusually high, stop and see a doctor or physio.";
