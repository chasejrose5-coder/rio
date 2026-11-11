/**
 * Copy Streamlit's static fonts and photos into the Next public folder.
 *
 * ui/static is the source of truth. web/public/fonts and web/public/photos are
 * generated, gitignored, and must be real files. Symlinks to ../../ui/static
 * make Vercel fail the deploy with: Cannot copy '../../ui/static/fonts'.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
export const defaultWebRoot = path.resolve(here, "..");
export const defaultRepoRoot = path.resolve(defaultWebRoot, "..");

export const REQUIRED_FONT_FILES = Object.freeze([
  "inter-latin-400-normal.woff2",
  "inter-latin-500-normal.woff2",
  "inter-latin-600-normal.woff2",
  "manrope-latin-700-normal.woff2",
  "manrope-latin-800-normal.woff2",
  "OFL-Inter.txt",
  "OFL-Manrope.txt",
]);

const PAIRS = [
  {
    label: "fonts",
    sourceRel: path.join("ui", "static", "fonts"),
    publicName: "fonts",
    required: REQUIRED_FONT_FILES,
  },
  {
    label: "photos",
    sourceRel: path.join("ui", "static", "photos"),
    publicName: "photos",
    required: [],
  },
];

const VERCEL_HINT = [
  "ui/static is the source of truth. Streamlit serves fonts and photos from ui/static.",
  "This script copies ui/static/fonts and ui/static/photos into web/public as real files",
  "so /fonts/* and /photos/* stay the same and Vercel can package the Next.js output.",
  "web/public/fonts and web/public/photos must not be symlinks. A symlink is what fails",
  "the deploy with: Cannot copy '../../ui/static/fonts'.",
  "",
  "On Vercel, Root Directory is web, so ui/static is outside that directory.",
  'Vercel uploads it only when "Include source files outside of the Root Directory in the Build Step"',
  "is enabled (Project Settings → Build and Deployment). That setting is on by default.",
  "Turn it on, keep the Build Command as npm run build, and redeploy.",
].join("\n");

function missingMessage(repoRoot, missingPath) {
  const rel = path.relative(repoRoot, missingPath) || missingPath;
  return [`[copy-static] Missing ${rel}.`, "", VERCEL_HINT].join("\n");
}

function isDirectory(target) {
  try {
    return fs.statSync(target).isDirectory();
  } catch {
    return false;
  }
}

function isInside(parent, candidate) {
  const rel = path.relative(path.resolve(parent), path.resolve(candidate));
  if (rel === "") return true;
  if (path.isAbsolute(rel)) return false;
  return !rel.split(path.sep).includes("..");
}

function fromRel(root, rel) {
  return path.join(root, ...rel.split("/"));
}

function listDereferenced(dir) {
  const files = [];
  const seenDirs = new Set();

  function walk(current, prefix) {
    let real;
    try {
      real = fs.realpathSync(current);
    } catch (error) {
      const reason = error && error.code ? error.code : error;
      throw new Error(`[copy-static] Cannot read ${current} (${reason}).`);
    }
    if (seenDirs.has(real)) {
      throw new Error(`[copy-static] Symlink cycle at ${current}.`);
    }
    seenDirs.add(real);

    for (const name of fs.readdirSync(current)) {
      const full = path.join(current, name);
      const rel = prefix ? `${prefix}/${name}` : name;
      const listed = fs.lstatSync(full);
      if (listed.isSymbolicLink()) {
        let followed;
        try {
          followed = fs.statSync(full);
        } catch {
          throw new Error(`[copy-static] Broken symlink at ${full}.`);
        }
        if (followed.isDirectory()) {
          walk(full, rel);
          continue;
        }
        if (followed.isFile()) {
          files.push(rel);
          continue;
        }
        throw new Error(`[copy-static] Unsupported symlink at ${full}.`);
      }
      if (listed.isDirectory()) {
        walk(full, rel);
        continue;
      }
      if (listed.isFile()) {
        files.push(rel);
        continue;
      }
      throw new Error(`[copy-static] Unsupported file at ${full}.`);
    }
  }

  walk(dir, "");
  files.sort();
  return files;
}

function removeDest(webRoot, dest) {
  const publicRoot = path.resolve(webRoot, "public");
  if (!isInside(publicRoot, dest)) {
    throw new Error(`[copy-static] Refusing to delete ${dest}, which is outside web/public.`);
  }
  let listed;
  try {
    listed = fs.lstatSync(dest);
  } catch (error) {
    if (error && error.code === "ENOENT") return;
    throw error;
  }
  // Unlink a symlink. rm on the link would follow it into ui/static.
  if (listed.isSymbolicLink()) {
    fs.unlinkSync(dest);
    return;
  }
  fs.rmSync(dest, { recursive: true, force: true });
}

function assertRealTree(dir) {
  for (const name of fs.readdirSync(dir)) {
    const full = path.join(dir, name);
    const listed = fs.lstatSync(full);
    if (listed.isSymbolicLink()) {
      throw new Error(`[copy-static] Refusing to leave a symlink in the Next public folder: ${full}`);
    }
    if (listed.isDirectory()) assertRealTree(full);
  }
}

function copyPair({ repoRoot, webRoot, source, dest, label, required }) {
  if (!isDirectory(source)) {
    throw new Error(missingMessage(repoRoot, source));
  }
  const files = listDereferenced(source);
  if (files.length === 0) {
    throw new Error(`[copy-static] ${path.relative(repoRoot, source)} has no files to copy.`);
  }
  for (const name of required) {
    if (!files.includes(name)) {
      throw new Error(`[copy-static] ${path.relative(repoRoot, source)} is missing ${name}.`);
    }
  }

  fs.mkdirSync(path.join(webRoot, "public"), { recursive: true });
  removeDest(webRoot, dest);
  fs.mkdirSync(dest, { recursive: true });

  for (const rel of files) {
    const target = fromRel(dest, rel);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.copyFileSync(fromRel(source, rel), target);
  }

  assertRealTree(dest);
  if (fs.lstatSync(dest).isSymbolicLink()) {
    throw new Error(`[copy-static] ${path.relative(webRoot, dest)} is still a symlink.`);
  }

  for (const rel of files) {
    const src = fs.readFileSync(fromRel(source, rel));
    const copied = fs.readFileSync(fromRel(dest, rel));
    if (!src.equals(copied)) {
      throw new Error(`[copy-static] Copied ${label}/${rel} does not match ui/static.`);
    }
  }

  const copiedNames = listDereferenced(dest);
  if (copiedNames.join("\n") !== files.join("\n")) {
    throw new Error(`[copy-static] ${label} copy does not match ui/static file for file.`);
  }
  return files.length;
}

export function copyStaticAssets({ repoRoot, webRoot }) {
  const staticRoot = path.join(repoRoot, "ui", "static");
  if (!isDirectory(staticRoot)) {
    throw new Error(missingMessage(repoRoot, staticRoot));
  }

  const summary = {};
  for (const pair of PAIRS) {
    const count = copyPair({
      repoRoot,
      webRoot,
      source: path.join(repoRoot, pair.sourceRel),
      dest: path.join(webRoot, "public", pair.publicName),
      label: pair.label,
      required: pair.required,
    });
    summary[pair.label] = count;
  }
  return summary;
}

function isDirectRun() {
  const entry = process.argv[1];
  if (!entry) return false;
  const modulePath = fileURLToPath(import.meta.url);
  try {
    return fs.realpathSync(entry) === fs.realpathSync(modulePath);
  } catch {
    return path.resolve(entry) === modulePath;
  }
}

if (isDirectRun()) {
  try {
    const summary = copyStaticAssets({
      repoRoot: defaultRepoRoot,
      webRoot: defaultWebRoot,
    });
    console.log(`[copy-static] fonts: ${summary.fonts} files -> public/fonts`);
    console.log(`[copy-static] photos: ${summary.photos} files -> public/photos`);
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  }
}
