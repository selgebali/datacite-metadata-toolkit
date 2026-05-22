const fs = require("fs");
const path = require("path");

function parseVersion(v) {
  return String(v)
    .split(".")
    .map((part) => Number.parseInt(part, 10))
    .map((n) => (Number.isFinite(n) ? n : 0));
}

function compareVersions(a, b) {
  const av = parseVersion(a);
  const bv = parseVersion(b);
  const len = Math.max(av.length, bv.length);

  for (let i = 0; i < len; i += 1) {
    const ai = av[i] || 0;
    const bi = bv[i] || 0;
    if (ai !== bi) return ai - bi;
  }
  return 0;
}

function listManifestVersions(repoRoot) {
  const manifestDir = path.join(repoRoot, "manifest");
  if (!fs.existsSync(manifestDir)) return [];

  const versions = fs
    .readdirSync(manifestDir, { withFileTypes: true })
    .filter((d) => d.isFile())
    .map((d) => d.name)
    .map((name) => {
      const m = /^datacite-(.+)\.json$/i.exec(name);
      if (!m) return null;
      if (m[1] === "current") return null;
      return m[1];
    })
    .filter(Boolean);

  return Array.from(new Set(versions)).sort(compareVersions);
}

function findLatestManifestVersion(repoRoot) {
  const versions = listManifestVersions(repoRoot);
  return versions.length ? versions[versions.length - 1] : null;
}

function getArgValue(argv, flag) {
  const idx = argv.indexOf(flag);
  if (idx === -1) return null;
  const value = argv[idx + 1];
  if (!value || value.startsWith("--")) return null;
  return value;
}

function resolveManifestPath(repoRoot, argv) {
  const manifestArg = getArgValue(argv, "--manifest");
  if (manifestArg) {
    return path.isAbsolute(manifestArg)
      ? manifestArg
      : path.join(repoRoot, manifestArg);
  }

  const versionArg = getArgValue(argv, "--version");
  if (versionArg) {
    return path.join(repoRoot, "manifest", `datacite-${versionArg}.json`);
  }

  const latest = findLatestManifestVersion(repoRoot);
  if (latest) {
    return path.join(repoRoot, "manifest", `datacite-${latest}.json`);
  }

  throw new Error(
    "No DataCite manifest found. Specify --version or ensure the manifest/ directory contains a datacite-X.Y.json file."
  );
}

function resolveCurrentVersion(repoRoot) {
  const currentManifest = path.join(repoRoot, "manifest", "datacite-current.json");
  if (fs.existsSync(currentManifest)) {
    try {
      const json = JSON.parse(fs.readFileSync(currentManifest, "utf8"));
      if (json.currentVersion) return String(json.currentVersion);
    } catch {
      // fall through to latest detected version
    }
  }

  return findLatestManifestVersion(repoRoot) || "4.6";
}

/**
 * Returns the root directory that contains the vocabulary files
 * (class/, property/, vocab/, manifest/, context/, dist/).
 *
 * In datacite-metadata-toolkit the vocabulary lives under rdf-vocabulary-staging/.
 * In schema.datacite.org-linked-data (the flat publication mirror) the vocabulary lives at the repo root.
 */
function resolveVocabRoot(projectRoot) {
  const stagingPath = path.join(projectRoot, "rdf-vocabulary-staging");
  if (fs.existsSync(stagingPath)) return stagingPath;
  return projectRoot;
}

module.exports = {
  compareVersions,
  findLatestManifestVersion,
  getArgValue,
  listManifestVersions,
  resolveCurrentVersion,
  resolveManifestPath,
  resolveVocabRoot,
};
