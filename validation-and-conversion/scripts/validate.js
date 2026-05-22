// validate.js
const fs       = require("fs");
const { validate } = require("jskos-validate");

// Accept either a JSON object containing arrays (e.g. {"mappings": [...]})
// or NDJSON (one JSON object per line).
const filePath = process.argv[2] || "mappings/jskos-mappings.json";
const text     = fs.readFileSync(filePath, "utf8");

let items = [];
try {
  const parsed = JSON.parse(text);
  if (Array.isArray(parsed)) {
    items = parsed;
  } else if (parsed && typeof parsed === "object") {
    if (Array.isArray(parsed.mappings)) {
      items = items.concat(parsed.mappings);
    }
    if (Array.isArray(parsed.concepts)) {
      items = items.concat(parsed.concepts);
    }
    if (Array.isArray(parsed.schemes)) {
      items = items.concat(parsed.schemes);
    }
    if (items.length === 0) {
      // Best-effort: collect any top-level array values.
      for (const value of Object.values(parsed)) {
        if (Array.isArray(value)) items = items.concat(value);
      }
    }
    if (items.length === 0) {
      // Single object — treat the whole document as one item.
      items = [parsed];
    }
  }
} catch (_e) {
  // Fall back to NDJSON parsing.
  items = text
    .trim()
    .split(/\r?\n/)
    .filter(Boolean)
    .map(line => JSON.parse(line));
}

let countValid = 0, countInvalid = 0;

items.forEach((item, idx) => {
  const typeField = item.type || item["@type"];
  let isValid, errors;

  if (item.from && item.to) {
    isValid = validate.mapping(item);
    errors  = validate.mapping.errorMessages;
  }
  else if (typeField && typeField.includes("skos:Concept")) {
    isValid = validate.concept(item);
    errors  = validate.concept.errorMessages;
  }
  else if (typeField && typeField.includes("ConceptScheme")) {
    isValid = validate.scheme(item);
    errors  = validate.scheme.errorMessages;
  }
  else {
    console.warn(`Skipping unknown item ${idx}`);
    return;
  }

  if (isValid) {
    console.log(`[${typeField}] Item ${idx} valid.`);
    countValid++;
  } else {
    console.log(`[${typeField}] Item ${idx} INVALID:`);
    errors.forEach(e => console.log("  -", e));
    countInvalid++;
  }
});

console.log(`\nSummary: ${countValid} valid, ${countInvalid} invalid (of ${items.length} total).`);
