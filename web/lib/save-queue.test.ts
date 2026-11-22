import assert from "node:assert/strict";
import test from "node:test";
import { createSaveQueue } from "./save-queue.ts";

function deferred() {
  let resolve: () => void = () => undefined;
  const promise = new Promise<void>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

test("a second tap while saving is ignored and does not post again", async () => {
  const queue = createSaveQueue<string>();
  const seen: string[] = [];
  const gate = deferred();
  const first = queue.push("done", "once", async (value) => {
    seen.push(value);
    await gate.promise;
  });
  const second = queue.push("done-again", "once", async (value) => {
    seen.push(value);
  });
  assert.equal(second, null);
  assert.equal(queue.busy, true);
  gate.resolve();
  await first;
  assert.deepEqual(seen, ["done"]);
  assert.equal(queue.busy, false);
});

test("autosave keeps the latest value and sends it with the digest from the save that just finished", async () => {
  const queue = createSaveQueue<string>();
  const seen: { value: string; digest: string }[] = [];
  let digest = "d1";
  const gate = deferred();
  const first = queue.push("2:05", "queue", async (value) => {
    seen.push({ value, digest });
    await gate.promise;
    digest = "d2";
  });
  assert.ok(first);
  const second = queue.push("2:04.5", "queue", async (value) => {
    seen.push({ value, digest });
  });
  assert.equal(second, first);
  gate.resolve();
  await first;
  assert.deepEqual(seen, [
    { value: "2:05", digest: "d1" },
    { value: "2:04.5", digest: "d2" },
  ]);
});
