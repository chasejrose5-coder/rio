/**
 * App entry for the stretching library and today's prescription.
 * The words and the rules live in stretch-content.ts. This file only re-exports them.
 */

export type {
  Completion,
  DayKind,
  Exercise,
  Prescription,
  PrescribedRoutine,
  Region,
  Routine,
  Severity,
  SoreSpot,
  StretchSession,
  StretchType,
} from "./stretch-content";

export {
  EXERCISE_AREAS,
  EXERCISES,
  REGIONS,
  ROUTINES,
  SHARP_MESSAGE,
  STRETCH_DISCLAIMER,
  classifyDay,
  easyRoutineId,
  exerciseById,
  exercisesOf,
  extraExercises,
  filterExercises,
  prescribe,
  regionById,
  routineById,
  routineIdsFor,
  spotState,
  weekLabel,
  weekProgress,
  weekStart,
} from "./stretch-content";
