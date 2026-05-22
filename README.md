# DataCite Metadata Toolkit

> **Note** — this repo is being renamed from `datacite4.6-jsonld` to **`datacite-metadata-toolkit`** to better reflect its scope (now covers DataCite 4.6 + 4.7, JSON Schema profiles, XML conversion, and crosswalk mappings — not just JSON-LD).

This repository provides machine-readable linked-data resources and tooling for the **DataCite Metadata Schema** (currently versions 4.6 and 4.7): RDF class and property definitions, controlled vocabulary terms as resolvable IRIs, JSON Schema validation profiles, an XML-to-JSON conversion script, and SKOS / JSKOS / SSSOM crosswalk mappings to external vocabularies (Schema.org, DCTERMS, DCAT-AP, Wikidata).

It is the **source of truth** for the DataCite linked-data namespace. The namespace itself is published from a separate flat-layout mirror, [`datacite/schema.datacite.org-linked-data`](https://github.com/datacite/schema.datacite.org-linked-data), which is kept in sync by an automated PR workflow ([`.github/workflows/sync-to-publication.yml`](.github/workflows/sync-to-publication.yml)). **Do not edit the publication repo directly** — all changes start here.

---

## Repository Layout

```
.
├── rdf-vocabulary-staging/          # Vocabulary source files (edit these)
│   ├── class/                       # 21 RDF class definitions (Resource, Creator, Title, …)
│   ├── property/                    # 80 RDF property definitions at 4.7 (79 at 4.6)
│   ├── vocab/                       # 11 controlled vocabulary schemes (counts shown for 4.7; 4.6 totals 147)
│   │   ├── contributorType/         # 22 terms
│   │   ├── dateType/                # 12 terms
│   │   ├── descriptionType/         # 6 terms
│   │   ├── funderIdentifierType/    # 5 terms
│   │   ├── identifierType/          # 1 term
│   │   ├── nameType/                # 2 terms
│   │   ├── numberType/              # 4 terms
│   │   ├── relatedIdentifierType/   # 23 terms  (21 at 4.6 — adds RAiD, SWHID in 4.7)
│   │   ├── relationType/            # 39 terms  (38 at 4.6 — adds Other in 4.7)
│   │   ├── resourceTypeGeneral/     # 34 terms  (32 at 4.6 — adds Poster, Presentation in 4.7)
│   │   └── titleType/               # 4 terms
│   ├── context/
│   │   └── fullcontext.jsonld       # JSON-LD context mapping DataCite keys to IRIs
│   └── manifest/
│       ├── datacite-4.6.json        # Versioned index for DataCite 4.6
│       └── datacite-4.7.json        # Versioned index for DataCite 4.7
│
├── validation-and-conversion/
│   ├── schemas/
│   │   ├── schema-profiles/         # JSON Schema profiles for API validation
│   │   │   ├── datacite4.6-schema.json    # Core attribute schema
│   │   │   ├── datacite4.6-profile.json   # Modular submission profile (POST/PUT)
│   │   │   ├── integrated.json            # Self-contained bundled profile
│   │   │   ├── datacite_api.jsonld        # JSON-LD context for REST API payloads
│   │   │   ├── rules.json                 # Supplementary validation rules
│   │   │   └── titleTypes.jsonld          # Title-type SKOS fragment
│   │   └── xsd/                     # Official DataCite XSD schema files
│   ├── scripts/
│   │   ├── convert.py               # Convert DataCite XML → REST API JSON
│   │   ├── validate.js              # Validate JSKOS mappings (requires jskos-validate)
│   │   └── validate_xml.rb          # Validate DataCite XML against XSD
│   └── examples/                    # Example records and an XML ↔ JSON roundtrip experiment
│
├── mappings/
│   ├── SKOS_crosswalks.jsonld          # SKOS mappings to Schema.org, DCAT, DCTERMS, Wikidata
│   ├── datacite-schemaorg.sssom.tsv    # SSSOM mappings: DataCite → Schema.org
│   ├── datacite-dcterms.sssom.tsv      # SSSOM mappings: DataCite → DCTERMS / DCAT-AP
│   └── jskos-mappings.json             # Same mappings in JSKOS format for Cocoda
│
├── rdf-build-scripts/               # Vocabulary build + release pipeline
│   ├── detect-datacite-release.js   # Detect changes in a new DataCite release
│   ├── apply-datacite-release-plan.js  # Apply an approved change plan to vocab files
│   ├── release-snapshot.js          # Manifest + dist + index regeneration
│   ├── build-distribution.js        # Bundle vocab into .jsonld/.ttl/.rdf
│   ├── manifest-sync.js             # Sync the manifest with files on disk
│   ├── update-current-pointers.js   # Update datacite-current pointer files
│   ├── update-root-index.js         # Patch root index.html with current version info
│   ├── generate-index-pages.js      # Build HTML index pages for GitHub Pages
│   ├── generate-production-namespace.sh  # Rewrite staging URLs to production URLs
│   ├── synCheck.py                  # Sync check: verify profile $defs match vocab term files
│   └── lib/                         # Shared libraries (versioning, release-import modules)
│
├── .github/workflows/
│   ├── deploy-pages.yml             # Publish vocabulary + schema profiles to GitHub Pages
│   ├── detect-datacite-release.yml  # CI runner for detect-datacite-release.js
│   ├── apply-datacite-release-plan.yml  # CI runner for apply-datacite-release-plan.js
│   └── release-snapshot.yml         # CI runner for release-snapshot.js
│
└── website/
    ├── index.html                   # Landing page (deployed to GitHub Pages)
    └── docs-index.html              # Documentation index page
```

**Generated directories** (regenerated by build scripts; the snapshots committed under `rdf-vocabulary-staging/dist/` and `reports/` are the most recent published artefacts and should not be edited by hand):

- `rdf-vocabulary-staging/dist/` — bundled distribution files (`build-distribution.js`)
- `reports/` — release detect/apply reports (`detect-datacite-release.js`, `apply-datacite-release-plan.js`)
- `production-namespace/` — production-tier copy, not committed (`generate-production-namespace.sh`)

---

## Namespace and resolvable IRIs

The staging namespace is rooted at `https://schema.stage.datacite.org/linked-data/`. Every file in `rdf-vocabulary-staging/` and `validation-and-conversion/schemas/schema-profiles/` declares an `$id` (JSON Schema) or `@id` (JSON-LD) whose URL path mirrors its location on disk, so a file's canonical IRI is predictable from its folder:

| Resource | Canonical IRI |
|---|---|
| Class | `…/linked-data/class/<ClassName>` |
| Property | `…/linked-data/property/<propertyName>` |
| SKOS ConceptScheme | `…/linked-data/vocab/<scheme>` |
| SKOS Concept | `…/linked-data/vocab/<scheme>/<Term>` |
| JSON-LD context | `…/linked-data/context/fullcontext.jsonld` |
| Manifest | `…/linked-data/manifest/datacite-4.6.json` |
| Schema profile | `…/linked-data/schema-profiles/<filename>` |

The GitHub Pages deploy publishes this layout so the IRIs resolve to both human-readable HTML pages and machine-readable JSON-LD. `generate-production-namespace.sh` rewrites the staging host to `https://schema.datacite.org/linked-data/` for production release.

### Shared controlled lists

Two `relatedItem` sub-properties reuse the controlled vocabularies of other DataCite properties — per spec, **not** as parallel vocabularies. The JSON-LD context (`rdf-vocabulary-staging/context/fullcontext.jsonld`) reflects this by pointing both `@vocab` bases at the canonical scheme directories:

| Sub-property | Reuses list from | Spec reference |
|---|---|---|
| `relatedItemType` | `resourceTypeGeneral` (vocab/resourceTypeGeneral/) | [4.7 §20.a](https://datacite-metadata-schema.readthedocs.io/en/4.7/properties/relateditem/): *"Use the controlled list values as stated in 10.a resourceTypeGeneral"* |
| `relatedItemIdentifierType` | `relatedIdentifierType` (vocab/relatedIdentifierType/) | [4.7 §20.1.a](https://datacite-metadata-schema.readthedocs.io/en/4.7/properties/relateditem/): matches property 12.a exactly |

This means a value like `Dataset` appearing under `relatedItemType` resolves to the same SKOS Concept IRI as it would under `resourceTypeGeneral` (`…/vocab/resourceTypeGeneral/Dataset`). Consumers distinguish the two usages by the **predicate** (`property:relatedItemType` vs `property:resourceTypeGeneral`), not the object. This eliminates the maintenance hazard of keeping two parallel vocabularies in sync as new values are added (e.g. 4.7's `Poster`/`Presentation` automatically apply to both fields).

Three related fields are **open lists** per spec — values are free text, not constrained to a controlled vocabulary. The context types them as `xsd:string`:

| Sub-property | Spec reference | Typical values |
|---|---|---|
| `alternateIdentifierType` | [4.7 §11.a](https://datacite-metadata-schema.readthedocs.io/en/4.7/properties/alternateidentifier/) | Free text (e.g. Local accession number, Inventory number) |
| `subjectScheme` | [4.7 §6.a](https://datacite-metadata-schema.readthedocs.io/en/4.7/properties/subject/) | Free text (e.g. LCSH, ANZSRC Fields of Research, MeSH) |
| `nameIdentifierScheme`, `affiliationIdentifierScheme`, `rightsIdentifierScheme`, `publisherIdentifierScheme` | various — recommended values, not strictly closed | ORCID, ROR, ISNI, SPDX, … |

---

## How to Use

### 1. Explore the vocabulary

`rdf-vocabulary-staging/manifest/datacite-4.6.json` is a versioned index of every defined class, property, and vocabulary term. Start there to discover what is available.

Individual term files follow a predictable structure:

- **Class files** (`class/Resource.jsonld`) — define the IRI, `rdf:type`, `rdfs:label`, and `rdfs:comment` for a DataCite entity.
- **Property files** (`property/identifier.jsonld`) — define the IRI and (where applicable) domain/range for a DataCite metadata field.
- **Vocab term files** (`vocab/resourceTypeGeneral/Dataset.jsonld`) — define a controlled term with `skos:prefLabel`, `skos:definition`, `skos:inScheme`, and optional `skos:closeMatch` mappings.

### 2. Use the JSON-LD context

`rdf-vocabulary-staging/context/fullcontext.jsonld` maps DataCite-style compact JSON keys to their full IRIs. Reference it in your JSON-LD documents:

```json
{
  "@context": "https://schema.stage.datacite.org/linked-data/context/fullcontext.jsonld",
  "@type": "Resource",
  "identifier": "10.1234/example",
  "creator": [{ "creatorName": "Smith, Jane" }]
}
```

### 3. Validate a DataCite XML record

`validation-and-conversion/scripts/validate_xml.rb` validates an XML file against the DataCite XSD schema. Requires Ruby.

### 4. Convert DataCite XML to REST API JSON

`validation-and-conversion/scripts/convert.py` parses a DataCite XML file and produces a JSON payload matching the DataCite REST API structure (a `data.attributes` envelope). Python 3 only — no external packages required.

```bash
python3 validation-and-conversion/scripts/convert.py \
    validation-and-conversion/examples/datacite-example-full-v4.xml \
    --output record.json
```

### 5. Validate JSKOS mappings

`validation-and-conversion/scripts/validate.js` validates an NDJSON file containing JSKOS mappings or concept records using the `jskos-validate` package.

```bash
npm install jskos-validate
node validation-and-conversion/scripts/validate.js mappings/jskos-mappings.json
```

### 6. Generate the production namespace

Rewrite staging IRIs to the production host:

```bash
bash rdf-build-scripts/generate-production-namespace.sh
# Output is written to production-namespace/
```

### 7. Validate against a JSON Schema profile

Once deployed, each profile is fetchable at its `$id` URL — e.g. `https://schema.stage.datacite.org/linked-data/schema-profiles/integrated.json` — so validators can resolve `$ref`s remotely. You can also validate against a local copy:

```bash
npx ajv-cli validate \
    -s validation-and-conversion/schemas/schema-profiles/integrated.json \
    -d your-metadata-record.json
```

See the [Schema Profiles](#schema-profiles) section below for which profile to choose.

### 8. Explore crosswalk mappings

The `mappings/` folder provides four complementary views of how DataCite terms align with external vocabularies. **All four files use the same canonical IRI scheme**: subject IRIs resolve to the linked-data namespace (`https://schema.stage.datacite.org/linked-data/{property,class,vocab/<scheme>}/<name>`) and Schema.org targets use the HTTPS form (`https://schema.org/<name>`). Tools can merge any subset of these files into a single RDF graph without IRI conflicts.

- **`SKOS_crosswalks.jsonld`** — SKOS-predicate mappings (`skos:exactMatch`, `skos:closeMatch`, etc.) to Schema.org, DCAT, DCTERMS, and Wikidata, embedded directly in the vocabulary JSON-LD. Uses CURIE prefixes `datacite-prop:`, `datacite-class:`, `datacite-vocab:`.
- **`datacite-schemaorg.sssom.tsv`** — machine-readable [SSSOM](https://mapping-commons.github.io/sssom/) mapping set from DataCite 4.6 properties and controlled vocabulary terms to Schema.org only. Suitable for automated alignment pipelines and SSSOM-aware tools.
- **`datacite-dcterms.sssom.tsv`** — companion SSSOM mapping set strictly limited to DataCite terms with **no** adequate Schema.org equivalent (currently four `dateType` values — `Accepted`, `Submitted`, `Valid`, `Withdrawn` — and the `relationType` pair `IsReplacedBy` / `Replaces`), mapped to DCTERMS (Dublin Core Terms). Overlap with the Schema.org SSSOM file is excluded by design — see that file for DataCite terms that have both Schema.org and DCTERMS targets.
- **`jskos-mappings.json`** — the same mappings in [JSKOS](https://gbv.github.io/jskos/) format for use with [Cocoda](https://coli-conc.gbv.de/cocoda/) and compatible mapping registries.

---

## Schema Profiles

### Which profile to use

| File | What it is | Use it when |
|---|---|---|
| `datacite4.6-schema.json` | Core attribute schema | You want a minimal schema for the `data.attributes` object only |
| `datacite4.6-profile.json` | Modular submission profile | You're validating client submissions to the REST API and prefer external `$defs`/context references |
| `integrated.json` | Self-contained bundled profile | You need a single file with all enumerations, context, response/submit validators, and export rules embedded — no external `$ref` resolution |
| `datacite_api.jsonld` | JSON-LD context for REST payloads | You want to interpret REST API JSON as linked data |
| `rules.json` | Supplementary validation rules | Layered on top of the main profile for additional checks |
| `titleTypes.jsonld` | Title-type SKOS fragment | Standalone SKOS-style definition of title types |

### What's in `integrated.json`

The integrated profile bundles five concerns into one self-contained file:

- **Root attributes schema** — structure and validation of `data.attributes` (creators, titles, publisher, relatedIdentifiers, …), mirroring the REST API. `additionalProperties: false` for strict client-side validation.
- **`$defs` enumerations** — every controlled vocabulary (`resourceTypeGeneral`, `relationType`, `descriptionType`, `contributorType`, etc.) inlined. Each term has an `iriMap` entry pointing to its canonical staging IRI (`…/linked-data/vocab/<scheme>/<term>`), so the same JSON can be validated *and* exported as RDF without re-mapping.
- **`profile.@context`** — a complete JSON-LD context mapping DataCite keys to RDF predicates (`creator → schema:creator`, `identifier → dcterms:identifier`, etc.). Embedded so consumers can generate RDF graphs without an external context fetch.
- **`responseProfile` and `submitProfile`** — JSON:API envelope validators for GET responses and POST/PUT submissions, embedded so a single file handles both directions.
- **`exportProfile`** — rules for converting validated JSON into RDF/JSON-LD, including language-tag handling and DOI normalization to `https://doi.org/<doi>`.

### Sync check

`rdf-build-scripts/synCheck.py` verifies that the controlled-list `$defs` inside `datacite4.6-profile.json` stay in sync with the published vocab term files under `rdf-vocabulary-staging/vocab/`. Run it whenever you add or remove vocabulary terms.

---

## Upgrading to a New DataCite Version

The release pipeline is a three-step process: **detect → review → apply**. All three steps have both a GitHub Actions workflow (for CI) and a local Node.js command (for development).

### Prerequisites

- Node.js 20+
- [Apache Jena](https://jena.apache.org/download/) (`riot` on PATH) — only needed for `build-distribution` / `release-snapshot`, which generate `.ttl` and `.rdf` files.

### Step 1 — Detect

**What it does:** Fetches the official DataCite schema release page, compares it to the local manifest versions, and writes a machine-readable JSON plan plus a Markdown report under `reports/`.

**Via GitHub Actions:**

1. Go to **Actions → Detect DataCite Release → Run workflow**
2. Optionally fill in `version` (e.g. `4.7`) and `release_date` (e.g. `2026-03-03`). Leave both blank to auto-detect the next release.
3. Enable **Commit plan files** (default: on) to push the plan to the branch automatically.

**Locally:**

```bash
# Auto-detect next release
node rdf-build-scripts/detect-datacite-release.js

# Target a specific version
node rdf-build-scripts/detect-datacite-release.js --version 4.7 --release-date 2026-03-03
```

**Output files:**

| File | Description |
|---|---|
| `reports/release-import-plan-4.7.json` | Machine-readable change plan — edit this to approve/skip changes |
| `reports/release-import-plan-4.7.md` | Human-readable summary of detected changes |

### Step 2 — Review and approve the plan

Open `reports/release-import-plan-4.7.json`. Each detected change has a `"status"` field:

| Status | Meaning |
|---|---|
| `"proposed"` | Automatically detected; ready to approve |
| `"apply"` | **Change this from `"proposed"` to approve it for the next step** |
| `"skip"` | Intentionally excluded from this run |
| `"manual"` | Requires manual attention before it can be applied (e.g. renames, removals) |

Change every `"proposed"` entry you want to apply to `"apply"`. Entries left as `"proposed"` or `"manual"` are skipped.

**Typical 4.6 → 4.7 plan looks like:**

```jsonc
{
  "targetVersion": "4.7",
  "releaseDate": "2026-03-03",
  "changes": [
    {
      "id": "controlled-list-values-added:resourceTypeGeneral:4.7",
      "module": "controlled-list",
      "kind": "controlled-list-values-added",
      "status": "apply",       // ← set to "apply" to include
      "summary": "Add resourceTypeGeneral terms: Poster, Presentation"
    },
    {
      "id": "controlled-list-values-added:relatedIdentifierType:4.7",
      "module": "controlled-list",
      "status": "apply",
      "summary": "Add relatedIdentifierType terms: RAiD, SWHID"
    },
    {
      "id": "simple-property-added:relationTypeInformation:4.7",
      "module": "simple-property",
      "status": "apply",
      "summary": "Add simple property relationTypeInformation"
    }
  ]
}
```

### Step 3 — Apply

**What it does:** Reads the approved plan, writes new vocab term files into `rdf-vocabulary-staging/`, updates scheme files and `context/fullcontext.jsonld`, then builds a full versioned snapshot (manifest + dist bundles + index pages).

**Via GitHub Actions:**

1. Go to **Actions → Apply DataCite Release Plan → Run workflow**
2. Set `plan_path` to `reports/release-import-plan-4.7.json`
3. Leave module toggles at their defaults unless you want to selectively run only some modules
4. Enable **Commit generated files** (default: on) to push all outputs back to the branch

**Locally:**

```bash
node rdf-build-scripts/apply-datacite-release-plan.js \
  --plan reports/release-import-plan-4.7.json \
  --set-current
```

**What gets written:**

| Path | Description |
|---|---|
| `rdf-vocabulary-staging/vocab/<scheme>/<Term>.jsonld` | New term files |
| `rdf-vocabulary-staging/vocab/<scheme>/<scheme>.jsonld` | Updated scheme with new `hasTopConcept` entries |
| `rdf-vocabulary-staging/property/<name>.jsonld` | New property files (for simple-property changes) |
| `rdf-vocabulary-staging/context/fullcontext.jsonld` | Updated context mappings |
| `rdf-vocabulary-staging/manifest/datacite-4.7.json` | New versioned manifest |
| `rdf-vocabulary-staging/manifest/release-matrix-4.6-4.7.json` | Change delta between versions |
| `rdf-vocabulary-staging/manifest/datacite-current.json` | Updated current-version pointer |
| `rdf-vocabulary-staging/dist/datacite-4.7.{jsonld,ttl,rdf}` | Bundled distribution in 3 RDF formats |
| `rdf-vocabulary-staging/dist/datacite-current.jsonld` | Pointer to the current distribution |
| `rdf-vocabulary-staging/dist/datacite.{jsonld,ttl,rdf}` | Moving "latest" aliases |
| `rdf-vocabulary-staging/*/index.html` | Updated vocabulary browser index pages |
| `reports/release-apply-4.7.md` | Summary of what was applied |

### Manual snapshot (without a plan)

To rebuild the manifest and distribution for an existing version — for example after manually editing vocab files — use the snapshot workflow directly:

**Via GitHub Actions:** Run **Build Versioned Snapshot** with `version` (e.g. `4.6`) and an optional `release_date`.

**Locally:**

```bash
node rdf-build-scripts/release-snapshot.js --version 4.6
```

This runs: `manifest-sync --write --validate` → `build-distribution` → `update-current-pointers` → `generate-index-pages` → `update-root-index`.

### Individual script reference

All scripts run from the repository root and auto-detect `rdf-vocabulary-staging/` as the vocabulary root.

| Script | Usage | Description |
|---|---|---|
| `manifest-sync.js` | `--check \| --write \| --validate [--version x.y] [--manifest <path>] [--allow-narrow]` | Rebuilds or validates a manifest from files on disk |
| `build-distribution.js` | `[--version x.y]` | Bundles vocab files into `dist/datacite-<v>.jsonld` and converts to `.ttl`/`.rdf` |
| `update-current-pointers.js` | `[--version x.y]` | Writes `datacite-current.json` and `dist/datacite.jsonld` aliases |
| `generate-index-pages.js` | _(no args)_ | Regenerates HTML browser index pages for `class/`, `property/`, `vocab/`, `context/`, `dist/`, `manifest/` |
| `update-root-index.js` | _(no args)_ | Patches AUTO marker blocks in `rdf-vocabulary-staging/index.html` if that file exists (no-op otherwise) |
| `detect-datacite-release.js` | `[--version x.y] [--release-date YYYY-MM-DD]` | Detects changes, writes plan to `reports/` |
| `apply-datacite-release-plan.js` | `--plan <path> [--modules <csv>] [--set-current]` | Applies an approved plan to vocab source files |
| `release-snapshot.js` | `--version x.y [--release-date YYYY-MM-DD] [--no-set-current]` | Full snapshot: manifest-sync + dist + pointers + index pages |
| `synCheck.py` | `[--profile <filename>]` | Verifies `$defs` enums in a schema profile match vocab term files on disk |

**Module IDs** (for `--modules` CSV in apply):

| ID | What it handles |
|---|---|
| `controlled-list` | Adds new terms to vocab schemes and creates term `.jsonld` files |
| `simple-property` | Creates a new property `.jsonld` and adds its context entry |
| `property-group` | Creates a group of related properties with shared context entries |
| `complex-structure` | Creates new class + property files for a complex nested structure |
| `rename` | Renames a controlled-list term |
| `removal` | Removes deprecated terms or context entries |

---

## Version History

`rdf-vocabulary-staging/manifest/datacite-current.json` points at the current published version (currently **4.7**). Each release leaves a versioned manifest, an apply report under `reports/`, and a release-matrix delta under `rdf-vocabulary-staging/manifest/release-matrix-<prev>-<next>.json`.

### DataCite 4.7 (current)

Applied on top of 4.6 via the Detect → Review → Apply pipeline. Changes:

- **`resourceTypeGeneral`**: adds **`Poster`**, **`Presentation`**
- **`relatedIdentifierType`**: adds **`RAiD`**, **`SWHID`**
- **`relationType`**: adds **`Other`**
- New property **`relationTypeInformation`** (additional information about the selected relationType, applies to both `relatedIdentifier` and `relatedItem`)
- **`descriptionType=SeriesInformation`** is soft-deprecated — the spec directs new content to encode series metadata via the structured `relatedItem` property with `relationType=IsPublishedIn` instead. The `SeriesInformation` term remains valid for backwards compatibility; see [vocab/descriptionType/SeriesInformation.jsonld](rdf-vocabulary-staging/vocab/descriptionType/SeriesInformation.jsonld) for the supersession note.

See `reports/release-apply-4.7.md` and `rdf-vocabulary-staging/manifest/release-matrix-4.6-4.7.json` for the full apply record.

### DataCite 4.6

Adds or updates these controlled values, all represented in the vocabulary files:

| Field | New values |
|---|---|
| `resourceTypeGeneral` | `Project`, `Award` |
| `relatedIdentifierType` | `RRID`, `CSTR` |
| `contributorType` | `Translator` |
| `relationType` | `IsTranslationOf`, `HasTranslation` |
| `dateType` | `Coverage` |

4.6 also introduced the `subject` sub-property **`classificationCode`** to support subject schemes such as ANZSRC that lack per-term `valueURI`s.

---

## Key Concepts

**JSON-LD** — A JSON-based format for linked data. An `@context` maps compact JSON keys to globally unique IRIs so different systems interpret the same key identically.

**SKOS** — The W3C Simple Knowledge Organization System. Used here to define controlled vocabulary terms and to map DataCite terms to equivalent terms in Schema.org, DCAT, and other vocabularies.

**JSKOS** — A JSON-based serialization of SKOS, used for interoperable mapping registries such as Cocoda.

**SSSOM** — The Simple Standard for Sharing Ontology Mappings. A TSV-based format that records each alignment between two terms with a predicate, justification, and provenance. The `.sssom.tsv` files in `mappings/` can be loaded directly by tools such as [sssom-py](https://mapping-commons.github.io/sssom-py/) or imported into ontology alignment pipelines.

**JSON Schema profile vs JSON-LD context** — The schema profiles (`validation-and-conversion/schemas/schema-profiles/`) check the *structure* of a JSON record (required fields, allowed values, data types). The JSON-LD context (`rdf-vocabulary-staging/context/fullcontext.jsonld`) gives those fields *semantic meaning* as linked data. Both can be applied to the same JSON document.

**Staging vs production namespace** — Vocabulary files use the staging host `https://schema.stage.datacite.org/linked-data/`. The production namespace (`https://schema.datacite.org/linked-data/`) is generated separately via `generate-production-namespace.sh` for release.

---

## References

- DataCite Metadata Schema 4.6 — https://schema.datacite.org/meta/kernel-4.6/
- DataCite REST API — https://support.datacite.org/docs/api
- DataCite 4.6 Release Notes — https://support.datacite.org/docs/datacite-metadata-schema-46-release-notes
- JSON-LD specification — https://json-ld.org/
- JSON Schema specification — https://json-schema.org/
- SKOS Primer — https://www.w3.org/TR/skos-primer/
- JSKOS format — https://gbv.github.io/jskos/
- SSSOM specification — https://mapping-commons.github.io/sssom/
