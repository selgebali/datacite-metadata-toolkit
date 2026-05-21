# rdf-vocabulary-staging

This directory contains the **source files for the DataCite linked-data vocabulary (versions 4.6 and 4.7)**. These are the files you edit when adding or updating vocabulary terms, classes, properties, or context mappings. Build scripts in `../rdf-build-scripts/` consume this directory to produce distribution bundles and GitHub Pages content.

---

## Directory layout

```
rdf-vocabulary-staging/
├── class/          # 21 RDF class definitions (DataCite 4.6 + 4.7)
├── property/       # 79 RDF property definitions (DataCite 4.6 + 4.7)
├── vocab/          # 11 controlled vocabulary schemes — 152 terms total (DataCite 4.6 + 4.7)
│   ├── contributorType/       (22 terms)
│   ├── dateType/              (12 terms)
│   ├── descriptionType/       (6 terms)
│   ├── funderIdentifierType/  (5 terms  — added in DataCite 4.7)
│   ├── identifierType/        (1 term   — added in DataCite 4.7)
│   ├── nameType/              (2 terms)
│   ├── numberType/            (4 terms)
│   ├── relatedIdentifierType/ (23 terms)
│   ├── relationType/          (39 terms)
│   ├── resourceTypeGeneral/   (34 terms)
│   └── titleType/             (4 terms)
├── context/
│   └── fullcontext.jsonld     # JSON-LD context mapping DataCite keys to IRIs
└── manifest/
    ├── datacite-4.6.json      # Versioned index for DataCite 4.6
    └── datacite-4.7.json      # Versioned index for DataCite 4.7
```

**Generated at build time** (not committed):

- `dist/` — bundled distribution files (`.jsonld`, `.ttl`, `.rdf`) produced by `build-distribution.js`
- `*/index.html` — section-level HTML browser pages produced by `generate-index-pages.js`

---

## File types

### `class/`

Each file defines one DataCite entity as an RDF class:

- `@id` — stable IRI for the class
- `@type` — `rdf:Class`
- `rdfs:label` — human-readable name
- `rdfs:comment` — short description

Example: `class/Resource.jsonld` defines the top-level citable resource class.

### `property/`

Each file defines one DataCite metadata field as an RDF property, with `@id`, `@type`, and where applicable `rdfs:domain` / `rdfs:range`.

Example: `property/identifier.jsonld` describes the mandatory DOI field.

### `vocab/`

Each subdirectory represents one SKOS ConceptScheme. It contains:

- **`<scheme>.jsonld`** — the ConceptScheme definition, listing all `skos:hasTopConcept` members
- **`<Term>.jsonld`** — one file per controlled term, with `skos:prefLabel`, `skos:definition`, `skos:inScheme`, and optional `skos:closeMatch` or `skos:exactMatch` cross-references to external vocabularies
- **`context.jsonld`** — a local JSON-LD context used by the term files in that directory

### `context/fullcontext.jsonld`

Maps compact DataCite JSON keys (e.g. `creator`, `resourceTypeGeneral`) to their full IRIs. Reference this in JSON-LD documents to make DataCite JSON interpretable as linked data:

```json
{
  "@context": "https://schema.stage.datacite.org/linked-data/context/fullcontext.jsonld",
  "@type": "Resource",
  "identifier": "10.1234/example"
}
```

### `manifest/datacite-4.6.json` / `manifest/datacite-4.7.json`

Versioned inventories of every class, property, and vocabulary term defined in this directory, one per DataCite schema version. Start with the relevant file to programmatically discover available resources for a given version.

---

## Namespace

All IRIs use the staging namespace `https://schema.stage.datacite.org/linked-data/`. The production namespace (`https://schema.datacite.org/linked-data/`) is generated separately via `../rdf-build-scripts/generate-production-namespace.sh`.

---

For full documentation — including the release upgrade pipeline, validation profiles, and crosswalk mappings — see the [root README](../README.md).
