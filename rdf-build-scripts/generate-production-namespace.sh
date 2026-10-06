#!/usr/bin/env bash
# Generates a production-namespace/ copy of rdf-vocabulary-staging/ for the
# public TIB/w3id namespace.
#
# Usage (from repo root):
#   bash rdf-build-scripts/generate-production-namespace.sh
#
# Defaults:
#   Source namespace:    https://schema.stage.datacite.org/linked-data/
#   Canonical namespace: https://w3id.org/tib/datacite/
#   GitHub Pages path:   /datacite
#   Publication backend: https://tibhannover.github.io/datacite/
#   Output directory:    production-namespace/
#
# Override any value with environment variables:
#   SOURCE_NAMESPACE="https://example.test/staging/" \
#   CANONICAL_NAMESPACE="https://w3id.org/tib/datacite/" \
#   PAGES_BASE_PATH="/datacite" \
#   PUBLICATION_BASE_URL="https://tibhannover.github.io/datacite/" \
#   DST="production-namespace" \
#   bash rdf-build-scripts/generate-production-namespace.sh

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SRC="${SRC:-rdf-vocabulary-staging}"
DST="${DST:-production-namespace}"
SOURCE_NAMESPACE="${SOURCE_NAMESPACE:-https://schema.stage.datacite.org/linked-data/}"
CANONICAL_NAMESPACE="${CANONICAL_NAMESPACE:-https://w3id.org/tib/datacite/}"
PAGES_BASE_PATH="${PAGES_BASE_PATH:-/datacite}"
PUBLICATION_BASE_URL="${PUBLICATION_BASE_URL:-https://tibhannover.github.io${PAGES_BASE_PATH}/}"

if [ ! -d "$SRC" ]; then
  echo "Error: $SRC not found. Run from the repo root." >&2
  exit 1
fi

rm -rf "$DST"
cp -r "$SRC" "$DST"

export SOURCE_NAMESPACE
export CANONICAL_NAMESPACE
export PAGES_BASE_PATH
export PUBLICATION_BASE_URL

find "$DST" -type f | while read -r file; do
  perl -0pi -e 's/\Q$ENV{SOURCE_NAMESPACE}\E/$ENV{CANONICAL_NAMESPACE}/g' "$file"
done

find "$DST" -type f -name "*.html" | while read -r file; do
  perl -0pi -e 's|/linked-data|$ENV{PAGES_BASE_PATH}|g' "$file"
done

README_TEMPLATE="$SCRIPT_DIR/templates/production-namespace-README.md"
if [ -f "$README_TEMPLATE" ]; then
  cp "$README_TEMPLATE" "$DST/README.md"
  perl -0pi \
    -e 's|\Q{{CANONICAL_NAMESPACE}}\E|$ENV{CANONICAL_NAMESPACE}|g;' \
    -e 's|\Q{{PAGES_BASE_PATH}}\E|$ENV{PAGES_BASE_PATH}|g;' \
    -e 's|\Q{{PUBLICATION_BASE_URL}}\E|$ENV{PUBLICATION_BASE_URL}|g;' \
    "$DST/README.md"
fi

# Rebuild section index pages inside the publication bundle so navigation and
# labels match the target GitHub Pages project path.
(
  cd "$DST"
  PAGES_BASE_PATH="$PAGES_BASE_PATH" node "$SCRIPT_DIR/generate-index-pages.js"
)

# Publish the curated mapping sets so their w3id mapping_set_id IRIs resolve
# (https://w3id.org/tib/datacite/mappings/<file>). Internal tooling inputs such
# as target-vocabularies.json stay in the toolkit repository.
MAPPINGS_SRC="${MAPPINGS_SRC:-mappings}"
mkdir -p "$DST/mappings"
cp "$MAPPINGS_SRC"/datacite-*.sssom.tsv \
   "$MAPPINGS_SRC/SKOS_crosswalks.jsonld" \
   "$MAPPINGS_SRC/jskos-mappings.json" \
   "$MAPPINGS_SRC/target-sources.json" \
   "$DST/mappings/"
cp -r "$MAPPINGS_SRC/conversion" "$MAPPINGS_SRC/coverage" "$DST/mappings/"

CHECKSUMS_FILE="CHECKSUMS.sha256"
INTEGRITY_FILE="manifest/bundle-integrity.json"
rm -f "$DST/$CHECKSUMS_FILE" "$DST/$INTEGRITY_FILE"

(
  cd "$DST"
  find . -type f \
    ! -path "./$CHECKSUMS_FILE" \
    ! -path "./$INTEGRITY_FILE" \
    -print \
    | LC_ALL=C sort \
    | sed 's#^\./##' \
    | while IFS= read -r file; do
        shasum -a 256 "$file"
      done
) > "$DST/$CHECKSUMS_FILE"

ARTIFACT_FILE_COUNT="$(wc -l < "$DST/$CHECKSUMS_FILE" | tr -d ' ')"
BUNDLE_CHECKSUM="$(shasum -a 256 "$DST/$CHECKSUMS_FILE" | awk '{print $1}')"

mkdir -p "$(dirname "$DST/$INTEGRITY_FILE")"
cat > "$DST/$INTEGRITY_FILE" <<EOF
{
  "artifactFileCount": $ARTIFACT_FILE_COUNT,
  "bundleChecksumAlgorithm": "sha256-of-CHECKSUMS.sha256",
  "bundleChecksum": "$BUNDLE_CHECKSUM",
  "checksumsFile": "$CHECKSUMS_FILE",
  "excludedFromChecksum": [
    "$CHECKSUMS_FILE",
    "$INTEGRITY_FILE"
  ],
  "canonicalNamespace": "$CANONICAL_NAMESPACE",
  "publicationBaseUrl": "$PUBLICATION_BASE_URL",
  "pagesBasePath": "$PAGES_BASE_PATH"
}
EOF

echo "Done. Production namespace written to $DST/"
echo "Files: $(find "$DST" -type f | wc -l | tr -d ' ')"
echo "Artifact files checksummed: $ARTIFACT_FILE_COUNT"
echo "Bundle checksum: $BUNDLE_CHECKSUM"
echo "Canonical namespace: $CANONICAL_NAMESPACE"
echo "GitHub Pages base path: $PAGES_BASE_PATH"
echo "Publication backend: $PUBLICATION_BASE_URL"
