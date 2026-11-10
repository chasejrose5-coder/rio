/** Creators lines. The sentences live in creators-copy.ts, generated from Streamlit. */

import { CREATORS } from "./creators-copy";

export { CREATORS };

export function visibleCreatorLines(): string[] {
  return [CREATORS.banner, CREATORS.heading, CREATORS.alt, CREATORS.name, ...CREATORS.paragraphs, CREATORS.close];
}
