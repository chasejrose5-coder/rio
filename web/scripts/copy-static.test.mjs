import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import {
  REQUIRED_FONT_FILES,
  copyStaticAssets,
  defaultRepoRoot,
  defaultWebRoot,
} from "./copy-static.mjs";

function writeFile(file, contents) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, contents);
}

function fixtureRepo() {
  const repoRoot = fs.mkdtempSync(path.join(os.tmpdir(), "rio-static-"));
  const webRoot = path.join(repoRoot, "web");
  for (const name of REQUIRED_FONT_FILES) {
    const body = name.endsWith(".txt") ? `SIL Open Font License\n${name}\n` : `woff2:${name}`;
    writeFile(path.join(repoRoot, "ui", "static", "fonts", name), body);
  }
  writeFile(path.join(repoRoot, "ui", "static", "photos", "home-aerial.jpg"), "photo-bytes");
  writeFile(path.join(repoRoot, "ui", "static", "photos", "nested", "credit.txt"), "Photo credit");
  writeFile(path.join(webRoot, "public", "favicon.svg"), "<svg></svg>");
  return { repoRoot, webRoot };
}

test("replaces public symlinks with the ui/static bytes and leaves the source in place", () => {
  const { repoRoot, webRoot } = fixtureRepo();
  const outside = fs.mkdtempSync(path.join(os.tmpdir(), "rio-outside-"));
  writeFile(path.join(outside, "keep.txt"), "keep");
  fs.symlinkSync(outside, path.join(webRoot, "public", "fonts"));
  fs.symlinkSync("../../ui/static/photos", path.join(webRoot, "public", "photos"));

  const linkedPhoto = path.join(repoRoot, "linked-photo.jpg");
  writeFile(linkedPhoto, "linked-photo");
  fs.symlinkSync(linkedPhoto, path.join(repoRoot, "ui", "static", "photos", "alias.jpg"));

  const summary = copyStaticAssets({ repoRoot, webRoot });
  assert.equal(summary.fonts, REQUIRED_FONT_FILES.length);
  assert.equal(summary.photos, 3);

  assert.equal(fs.readFileSync(path.join(outside, "keep.txt"), "utf8"), "keep");
  assert.equal(fs.existsSync(path.join(outside, "OFL-Inter.txt")), false);
  assert.equal(
    fs.readFileSync(path.join(repoRoot, "ui", "static", "fonts", "OFL-Inter.txt"), "utf8"),
    "SIL Open Font License\nOFL-Inter.txt\n",
  );

  const fontsDest = path.join(webRoot, "public", "fonts");
  const photosDest = path.join(webRoot, "public", "photos");
  assert.equal(fs.lstatSync(fontsDest).isSymbolicLink(), false);
  assert.equal(fs.lstatSync(photosDest).isSymbolicLink(), false);
  assert.equal(fs.lstatSync(path.join(photosDest, "alias.jpg")).isSymbolicLink(), false);
  assert.equal(fs.readFileSync(path.join(photosDest, "alias.jpg"), "utf8"), "linked-photo");
  assert.equal(fs.readFileSync(path.join(photosDest, "nested", "credit.txt"), "utf8"), "Photo credit");
  assert.equal(fs.readFileSync(path.join(fontsDest, "inter-latin-400-normal.woff2"), "utf8"), "woff2:inter-latin-400-normal.woff2");
  assert.equal(fs.readFileSync(path.join(webRoot, "public", "favicon.svg"), "utf8"), "<svg></svg>");

  copyStaticAssets({ repoRoot, webRoot });
  assert.equal(fs.readFileSync(path.join(fontsDest, "OFL-Manrope.txt"), "utf8"), "SIL Open Font License\nOFL-Manrope.txt\n");
});

test("names ui/static and the Vercel root-directory setting when the source is missing", () => {
  const repoRoot = fs.mkdtempSync(path.join(os.tmpdir(), "rio-missing-"));
  const webRoot = path.join(repoRoot, "web");
  fs.mkdirSync(webRoot, { recursive: true });
  assert.throws(
    () => copyStaticAssets({ repoRoot, webRoot }),
    (error) => {
      assert.match(error.message, /Missing ui\/static\./);
      assert.match(error.message, /Include source files outside of the Root Directory in the Build Step/);
      assert.match(error.message, /Cannot copy '\.\.\/\.\.\/ui\/static\/fonts'/);
      assert.match(error.message, /npm run build/);
      return true;
    },
  );
});

test("names the missing photos directory when fonts are present", () => {
  const { repoRoot, webRoot } = fixtureRepo();
  fs.rmSync(path.join(repoRoot, "ui", "static", "photos"), { recursive: true });
  assert.throws(
    () => copyStaticAssets({ repoRoot, webRoot }),
    /Missing ui\/static\/photos\./,
  );
});

test("refuses an empty photos directory and a fonts directory missing a license", () => {
  const { repoRoot, webRoot } = fixtureRepo();
  for (const name of fs.readdirSync(path.join(repoRoot, "ui", "static", "photos"))) {
    fs.rmSync(path.join(repoRoot, "ui", "static", "photos", name), { recursive: true });
  }
  assert.throws(
    () => copyStaticAssets({ repoRoot, webRoot }),
    /ui\/static\/photos has no files to copy/,
  );

  const again = fixtureRepo();
  fs.rmSync(path.join(again.repoRoot, "ui", "static", "fonts", "OFL-Inter.txt"));
  assert.throws(
    () => copyStaticAssets(again),
    /ui\/static\/fonts is missing OFL-Inter\.txt/,
  );
});

test("the repo copy matches ui/static byte for byte and leaves no public symlinks", () => {
  const summary = copyStaticAssets({ repoRoot: defaultRepoRoot, webRoot: defaultWebRoot });
  for (const folder of ["fonts", "photos"]) {
    const source = path.join(defaultRepoRoot, "ui", "static", folder);
    const dest = path.join(defaultWebRoot, "public", folder);
    const names = fs.readdirSync(source);
    assert.equal(summary[folder], names.length);
    assert.equal(fs.lstatSync(dest).isDirectory(), true);
    assert.equal(fs.lstatSync(dest).isSymbolicLink(), false);
    for (const name of names) {
      const src = path.join(source, name);
      const copied = path.join(dest, name);
      assert.equal(fs.lstatSync(copied).isSymbolicLink(), false, name);
      assert.equal(fs.lstatSync(copied).isFile(), true, name);
      assert.ok(fs.readFileSync(src).equals(fs.readFileSync(copied)), name);
    }
  }
  assert.match(fs.readFileSync(path.join(defaultWebRoot, "public", "fonts", "OFL-Inter.txt"), "utf8"), /SIL Open Font License/);
  assert.match(fs.readFileSync(path.join(defaultWebRoot, "public", "fonts", "OFL-Manrope.txt"), "utf8"), /SIL Open Font License/);
  assert.ok(fs.statSync(path.join(defaultWebRoot, "public", "fonts", "inter-latin-400-normal.woff2")).size > 0);
  assert.ok(fs.statSync(path.join(defaultWebRoot, "public", "photos", "home-aerial.jpg")).size > 0);
});
