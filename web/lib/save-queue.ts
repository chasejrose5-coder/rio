/** One save at a time.

Buttons use `once`: a second tap while a save is in flight is ignored.
Autosave uses `queue`: keystrokes collapse to the latest value, and that
value is sent only after the in-flight save returns.
*/

export function createSaveQueue<T>() {
  let flight: Promise<void> | null = null;
  let queued: { value: T } | null = null;
  let run: ((value: T) => Promise<void>) | null = null;

  return {
    get busy(): boolean {
      return flight !== null;
    },

    push(value: T, mode: "once" | "queue", job: (value: T) => Promise<void>): Promise<void> | null {
      if (mode === "once" && flight) return null;
      queued = { value };
      run = job;
      if (flight) return flight;
      const pump = async () => {
        try {
          while (queued && run) {
            const next = queued.value;
            const jobNow = run;
            queued = null;
            await jobNow(next);
          }
        } finally {
          flight = null;
          run = null;
        }
      };
      flight = pump();
      return flight;
    },
  };
}
