# XML ↔ JSON ↔ XML Roundtrip Experiment — Notes

Working notes documenting the commands used and the conclusions reached for the xml-js roundtrip approach.

Input XML source: https://schema.datacite.org/meta/kernel-4.6/example/datacite-example-full-v4.xml

---

## Step 1 — Create the XML-shaped JSON

```bash
xml-js ../examples/xml-roundtrip/datacite-example-full-v4.xml \
  --to-json \
  --compact true \
  --spaces 2 \
  --no-comment \
  --no-decl \
  --attributes-key "attrs" \
  --text-key "value" \
  ../examples/xml-roundtrip/XML-Shaped-JSON.json
```

---

## Step 2 — Convert back to XML

```bash
xml-js ../examples/xml-roundtrip/XML-Shaped-JSON.json \
  --to-xml \
  --compact true \
  --spaces 2 \
  --attributes-key "attrs" \
  --text-key "value" \
  ../examples/xml-roundtrip/roundtrip.xml
```

---

## Step 3 — Canonicalize both XML files and diff (removes whitespace noise)

```bash
xmllint --c14n \
  ../examples/xml-roundtrip/datacite-example-full-v4.xml \
  ../examples/xml-roundtrip/original.c14n.xml
```

```bash
xmllint --c14n \
  ../examples/xml-roundtrip/roundtrip.xml \
  ../examples/xml-roundtrip/roundtrip.c14n.xml
```

Beautify `original.c14n.xml` and `roundtrip.c14n.xml` using an online tool (e.g. https://jsonformatter.org/xml-formatter), then compare using https://codebeautify.org/xml-diff.

**Result: 0 changes found.**

---

## Step 4 — Validate against XSD

Used `roundtrip.c14n.xml` to validate against the DataCite XSD via bolognese (see `scripts/validate_xml.rb`).

**Result: ✓ XML is valid against DataCite (kernel-4) schema**

---

## Summary

XML → JSON → XML = valid against XSD.

`XML-Shaped-JSON.json` is a JSON instance file based on an XML that passes the XSD requirements. Using that JSON instance should be able to register a DOI.

---

## XML-Shaped-JSON structure conventions

| Key | Meaning |
|-----|---------|
| `attrs` | XML attributes (e.g. `<element attribute="value">`) |
| direct properties | XML child elements |
| `value` | XML element text content |

### Pattern 1 — Simple property with attributes and value

```json
"identifier": {
  "attrs": {
    "identifierType": "DOI"
  },
  "value": "10.82433/B09Z-4K37"
}
```

Represents: `<identifier identifierType="DOI">10.82433/B09Z-4K37</identifier>`

### Pattern 2 — Array of items

```json
"creators": {
  "creator": [
    { "creatorName": { ... } },
    { "creatorName": { ... } }
  ]
}
```

Represents multiple `<creator>` elements within `<creators>`.

### Pattern 3 — Nested objects with attributes

```json
"affiliation": {
  "attrs": {
    "affiliationIdentifier": "https://ror.org/04wxnsj81",
    "affiliationIdentifierScheme": "ROR",
    "schemeURI": "https://ror.org"
  },
  "value": "ExampleAffiliation"
}
```

---

## JavaScript accessor examples

```js
// Get the DOI
const doi = data.resource.identifier.value;
// Result: "10.82433/B09Z-4K37"

// Get first creator's name
const creatorName = data.resource.creators.creator[0].creatorName.value;
// Result: "ExampleFamilyName, ExampleGivenName"

// Get publisher info
const publisher = data.resource.publisher.value;
// Result: "Example Publisher"
```
