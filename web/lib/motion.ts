/** The underline grows once, when the page actually changes. */
export function navShouldArm(previous: string | null, path: string): boolean {
  return previous !== path;
}
