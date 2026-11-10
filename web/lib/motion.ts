/** The underline grows once, when the page actually changes. */
export function navShouldArm(previous: string | null, path: string): boolean {
  return previous !== path;
}

/** The page rise plays the first time a page is shown in this tab. */
export function pageShouldRise(previous: string | null, page: string): boolean {
  return previous !== page;
}
