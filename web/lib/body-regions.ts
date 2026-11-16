/** Library slugs grouped into the sore-spot areas. Unlisted slugs stay as the white outline. */
export const REGION_OF: Record<string, string | null> = {
  chest: "shoulders",
  deltoids: "shoulders",
  trapezius: "upper-back",
  "upper-back": "upper-back",
  neck: "neck",
  abs: "abs",
  obliques: "abs",
  quadriceps: "quads",
  adductors: "adductors",
  tibialis: "shins",
  calves: "calves",
  feet: "feet",
  ankles: "feet",
  hamstring: "hamstrings",
  gluteal: "glutes",
  "lower-back": "lower-back",
  biceps: null,
  triceps: null,
  forearm: null,
  hands: null,
  knees: null,
  head: null,
  hair: null,
};

type Extra = { region: string; paths: string[] };

/** One side only. Rendering mirrors these across the figure. */
export const FRONT_EXTRAS: Extra[] = [
  {
    region: "hip-flexors",
    paths: ["M318 790 C300 830 308 900 340 920 C362 890 358 830 348 790 Z"],
  },
  {
    region: "it-band",
    paths: ["M256 820 C246 870 248 950 260 1000 L286 988 C294 930 290 860 276 820 Z"],
  },
];

export const BACK_EXTRAS: Extra[] = [
  {
    region: "it-band",
    paths: ["M978 820 C968 870 970 950 982 1000 L1008 988 C1016 930 1012 860 998 820 Z"],
  },
];
