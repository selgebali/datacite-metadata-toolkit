"""Offline checks and deterministic projections of curated SSSOM mapping sets.

These checks enforce documented invariants and known semantic regressions; they
cannot establish semantic truth. Conversion rules are specifications, not code.
"""

import csv
import io
import json
from collections import defaultdict

import yaml

BASE = "https://w3id.org/tib/datacite/"
SKOS = "http://www.w3.org/2004/02/skos/core#"
SCHEMA = "https://schema.org/"
DCTERMS = "http://purl.org/dc/terms/"
MATCHES = {SKOS + name for name in ("exactMatch", "closeMatch", "broadMatch", "narrowMatch", "relatedMatch")}
TARGETS = {"schemaorg", "dcterms", "dcat", "wikidata"}
EXPORTS = ("SKOS_crosswalks.jsonld", "jskos-mappings.json")
SKOS_CONTEXT = {"skos": SKOS, "rdfs": "http://www.w3.org/2000/01/rdf-schema#", "dcterms": DCTERMS}

# JSKOS schemes use BARTOC registry URIs, which is how Cocoda identifies vocabularies.
DATACITE_SCHEME = {"uri": "http://bartoc.org/en/node/21149", "notation": ["datacite"]}
SCHEMES = {
    SCHEMA: {"uri": "http://bartoc.org/en/node/18250", "notation": ["schema"]},
    DCTERMS: {"uri": "http://bartoc.org/en/node/725", "notation": ["dcterms"]},
    "http://purl.org/dc/dcmitype/": {"uri": "http://bartoc.org/en/node/17909"},
    "http://www.w3.org/ns/dcat#": {"uri": "http://bartoc.org/en/node/1691"},
    "http://www.wikidata.org/entity/": {"uri": "http://bartoc.org/en/node/1940", "notation": ["WD"]},
}


class MappingError(ValueError):
    """A mapping artifact violates a checked invariant."""


def require(condition, message):
    if not condition:
        raise MappingError(message)


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise MappingError(f"{path}: {error}") from error


def canonical_sources(root):
    """Read published identifiers, excluding contexts and vocabulary schemes."""
    result = set()
    for group in ("class", "property", "vocab"):
        for path in sorted((root / "production-namespace" / group).rglob("*.jsonld")):
            data = read_json(path)
            identifier = data.get("@id", data.get("id"))
            kind = data.get("@type", data.get("type"))
            if not identifier or (group == "vocab" and kind not in ("Concept", "skos:Concept", SKOS + "Concept")):
                continue
            require(identifier.startswith(BASE + group + "/"), f"{path}: noncanonical source IRI {identifier}")
            require(identifier not in result, f"{path}: duplicate source term {identifier}")
            result.add(identifier)
    require(result, "No canonical terms found in production-namespace")
    return result


def expand(value, prefixes, location):
    require(isinstance(value, str) and value and not any(c.isspace() for c in value) and "|" not in value,
            f"{location}: invalid single entity reference {value!r}")
    if value.startswith(("https://", "http://")):
        return value
    prefix, separator, local = value.partition(":")
    require(separator and local and prefix in prefixes, f"{location}: undefined prefix or empty CURIE {value!r}")
    return prefixes[prefix] + local


def strict_tsv(text, location):
    """Reject bare quotes accepted by csv.reader; allow quoted multiline cells."""
    state = "start"
    line = 1
    for character in text:
        if state == "quoted":
            if character == '"':
                state = "closed"
        elif state == "closed":
            if character == '"':
                state = "quoted"
            elif character in "\t\r\n":
                state = "start"
            else:
                raise MappingError(f"{location}: TSV line {line}: text after closing quote")
        elif character == '"':
            require(state == "start", f"{location}: TSV line {line}: unescaped quote in unquoted cell")
            state = "quoted"
        elif character in "\t\r\n":
            state = "start"
        else:
            state = "unquoted"
        if character == "\n":
            line += 1
    require(state != "quoted", f"{location}: unterminated quoted TSV cell")
    try:
        return list(csv.reader(io.StringIO(text), delimiter="\t", strict=True))
    except csv.Error as error:
        raise MappingError(f"{location}: {error}") from error


def read_sssom(path):
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    metadata_lines = []
    while lines and lines[0].startswith("#"):
        metadata_lines.append(lines.pop(0)[1:].removeprefix(" "))
    try:
        metadata = yaml.safe_load("".join(metadata_lines))
    except yaml.YAMLError as error:
        raise MappingError(f"{path}: invalid YAML metadata: {error}") from error
    require(isinstance(metadata, dict), f"{path}: missing YAML metadata")
    for slot in ("mapping_set_id", "mapping_set_description", "license", "subject_source_version"):
        require(metadata.get(slot), f"{path}: missing metadata {slot}")
    require(str(metadata["subject_source_version"]) == "4.7", f"{path}: expected subject_source_version 4.7")
    prefixes = metadata.get("curie_map")
    require(isinstance(prefixes, dict) and all(isinstance(v, str) and v.startswith(("http://", "https://")) for v in prefixes.values()),
            f"{path}: invalid curie_map")
    for slot in ("subject_source", "object_source"):
        if slot in metadata:
            expand(metadata[slot], prefixes, f"{path}: {slot}")
    table = strict_tsv("".join(lines), path)
    require(len(table) > 1, f"{path}: empty mapping table")
    header = table[0]
    require(len(header) == len(set(header)), f"{path}: duplicate TSV columns")
    required = {"subject_id", "predicate_id", "object_id", "mapping_justification"}
    # Labels are required because the JSKOS export (Cocoda) displays them.
    columns = required | {"subject_label", "object_label", "author_id", "author_label"}
    require(columns <= set(header), f"{path}: missing required columns {sorted(columns - set(header))}")
    rows = []
    for line, values in enumerate(table[1:], len(metadata_lines) + 2):
        location = f"{path}:{line}"
        require(len(values) == len(header), f"{location}: expected {len(header)} cells, got {len(values)}")
        row = dict(zip(header, values))
        for slot in required:
            row[slot] = expand(row[slot], prefixes, f"{location}: {slot}")
        for slot in ("subject_label", "object_label", "author_label"):
            require(row[slot].strip(), f"{location}: missing {slot}")
        # Multivalued SSSOM slots are separated by "|".
        authors = [expand(a, prefixes, f"{location}: author_id") for a in row["author_id"].split("|")]
        names = row["author_label"].split("|")
        require(len(authors) == len(names), f"{location}: author_id and author_label counts differ")
        row["authors"] = list(zip(authors, names))
        row["mapping_date"] = str(row.get("mapping_date") or metadata.get("mapping_date") or "")
        row["location"] = location
        rows.append(row)
    return metadata, rows


def check_semantics(subject, predicate, obj, location):
    """Small regression list, independent of whether target terms exist."""
    relation = subject.removeprefix(BASE + "vocab/relationType/")
    wrong_direction = {
        "Reviews": {SCHEMA + "review", SCHEMA + "reviews"},
        "IsReviewedBy": {SCHEMA + "itemReviewed"},
        "IsCitedBy": {SCHEMA + "citation", DCTERMS + "references"},
        "IsReferencedBy": {SCHEMA + "citation", DCTERMS + "references"},
        "References": {DCTERMS + "isReferencedBy"},
        "Cites": {DCTERMS + "isReferencedBy"},
        "IsPartOf": {SCHEMA + "hasPart", DCTERMS + "hasPart"},
        "HasPart": {SCHEMA + "isPartOf", DCTERMS + "isPartOf"},
        "IsSourceOf": {SCHEMA + "isBasedOn"},
    }
    require(obj not in wrong_direction.get(relation, set()),
            f"{location}: wrong relationship direction; use an explicit inverse conversion rule")
    require(obj != SCHEMA + "isRelatedTo", f"{location}: isRelatedTo is a product/service relation, not a research-resource fallback")
    require(not (subject in {BASE + "vocab/numberType/Article", BASE + "vocab/numberType/Report"} and obj == SCHEMA + "issueNumber"),
            f"{location}: article/report number is not an issue number")
    if predicate in {SKOS + "exactMatch", SKOS + "closeMatch"}:
        require(not (subject == BASE + "vocab/resourceTypeGeneral/Model" and obj == SCHEMA + "3DModel"),
                f"{location}: a general model cannot be equated to a 3D model")


def check_rules(path, target, sources, terms):
    if not path.exists():
        return {}
    document = read_json(path)
    require(document.get("target") == target and document.get("source_version") == "4.7", f"{path}: incorrect target/source_version")
    require(isinstance(document.get("rules"), list), f"{path}: expected rules array")
    rules = {}
    for rule in document["rules"]:
        require(isinstance(rule, dict), f"{path}: rule must be an object")
        identifier = rule.get("id")
        require(isinstance(identifier, str) and identifier and identifier not in rules, f"{path}: missing/duplicate rule id {identifier}")
        location = f"{path}: rule {identifier}"
        subjects = rule.get("subject_ids")
        require(isinstance(subjects, list) and subjects and all(isinstance(s, str) and s in sources for s in subjects), f"{location}: unknown/missing subject_ids")
        require(len(subjects) == len(set(subjects)), f"{location}: duplicate subject_ids")
        for field in ("condition", "source_path", "target_path", "notes"):
            require(isinstance(rule.get(field), str) and rule[field].strip(), f"{location}: missing {field}")
        require(rule.get("operation") in {"copy", "inverse", "construct", "conditional", "preserve"}, f"{location}: invalid operation")
        require(rule.get("lossiness") in {"none", "conditional", "lossy"}, f"{location}: invalid lossiness")
        if "target_ids" in rule:
            require(isinstance(rule["target_ids"], list) and all(isinstance(t, str) and t in terms for t in rule["target_ids"]), f"{location}: undefined target_ids")
        rules[identifier] = rule
    return rules


def check_coverage(path, target, sources, mapped, rules):
    document = read_json(path)
    require(document.get("target") == target and document.get("source_version") == "4.7", f"{path}: incorrect target/source_version")
    require(isinstance(document.get("records"), list), f"{path}: expected records array")
    seen = set()
    for record in document["records"]:
        require(isinstance(record, dict), f"{path}: coverage record must be an object")
        subject = record.get("subject_id")
        location = f"{path}: {subject}"
        require(isinstance(subject, str) and subject in sources, f"{location}: unknown canonical source")
        require(subject not in seen, f"{location}: duplicate coverage record")
        seen.add(subject)
        status = record.get("status")
        require(status in {"mapped", "conversion_only", "no_equivalent", "out_of_scope"}, f"{location}: invalid status {status}")
        require((status == "mapped") == (subject in mapped), f"{location}: status and SSSOM mappings disagree")
        require(isinstance(record.get("reason"), str) and record["reason"].strip(), f"{location}: missing rationale")
        identifiers = record.get("rule_ids", [])
        require(isinstance(identifiers, list) and all(isinstance(i, str) for i in identifiers), f"{location}: invalid rule_ids")
        require(status != "conversion_only" or identifiers, f"{location}: conversion_only requires rule_ids")
        for identifier in identifiers:
            require(identifier in rules and subject in rules[identifier]["subject_ids"], f"{location}: unknown/inapplicable rule {identifier}")
    require(seen == sources, f"{path}: missing coverage for {len(sources - seen)} source terms: {', '.join(sorted(sources - seen)[:5])}")


def validate_sources(root):
    sources = canonical_sources(root)
    directory = root / "mappings"
    inventory = read_json(directory / "target-vocabularies.json")
    require(inventory.get("version") == 1 and isinstance(inventory.get("terms"), dict), "Invalid target-vocabularies.json inventory")
    # DCAT reuses DCTERMS terms; read it last so shared triples keep the DCTERMS row.
    files = sorted(directory.glob("datacite-*.sssom.tsv"), key=lambda p: (p.name == "datacite-dcat.sssom.tsv", p.name))
    targets = {path.name[len("datacite-"):-len(".sssom.tsv")] for path in files}
    require(targets == TARGETS, f"Expected target sets {sorted(TARGETS)}, found {sorted(targets)}")
    records = {}
    sets = []
    pairs = defaultdict(set)
    counts = {}
    for path in files:
        target = path.name[len("datacite-"):-len(".sssom.tsv")]
        metadata, rows = read_sssom(path)
        sets.append(metadata)
        local = set()
        for row in rows:
            subject, predicate, obj = (row[key] for key in ("subject_id", "predicate_id", "object_id"))
            location = row["location"]
            require(subject in sources, f"{location}: unknown canonical source {subject}")
            require(predicate in MATCHES, f"{location}: unsupported mapping predicate {predicate}")
            require(obj in inventory["terms"], f"{location}: undefined target {obj}")
            require(not inventory["terms"][obj].get("deprecated"), f"{location}: deprecated target {obj}")
            namespaces = {
                "schemaorg": (SCHEMA,),
                "dcterms": (DCTERMS, "http://purl.org/dc/dcmitype/"),
                "wikidata": ("http://www.wikidata.org/entity/", "http://www.wikidata.org/prop/direct/"),
            }
            require(target not in namespaces or obj.startswith(namespaces[target]), f"{location}: target outside {target} scope: {obj}")
            check_semantics(subject, predicate, obj, location)
            triple = (subject, predicate, obj)
            require(triple not in local, f"{location}: duplicate mapping triple")
            local.add(triple)
            records.setdefault(triple, row)
            pairs[(subject, obj)].add(predicate)
            require(len(pairs[(subject, obj)]) == 1, f"{location}: conflicting SKOS predicates for {subject} → {obj}")
        rules = check_rules(directory / "conversion" / f"{target}.json", target, sources, inventory["terms"])
        check_coverage(directory / "coverage" / f"{target}.json", target, sources, {s for s, _, _ in local}, rules)
        counts[target] = len(local)
    return records, sets, counts, len(sources)


def scheme_for(uri):
    for namespace, scheme in SCHEMES.items():
        if uri.startswith(namespace):
            return scheme
    raise MappingError(f"No JSKOS scheme configured for {uri}")


def notation(uri):
    """Short code shown by Cocoda: the path after the vocabulary namespace."""
    if uri.startswith(BASE):
        return uri[len(BASE):].removeprefix("vocab/")
    return uri[len(next(n for n in SCHEMES if uri.startswith(n))):]


def concept(uri, label):
    return {"uri": uri, "notation": [notation(uri)], "prefLabel": {"en": label}}


def set_metadata(sets):
    licenses = {m["license"] for m in sets}
    require(len(licenses) == 1, f"Mapping sets use different licenses: {sorted(licenses)}")
    creators = sorted({expand(c, m["curie_map"], "creator_id") for m in sets for c in m.get("creator_id") or []})
    return licenses.pop(), creators, sorted(m["mapping_set_id"] for m in sets)


def projections(records, sets):
    license_uri, creators, set_ids = set_metadata(sets)
    labels = {}
    for (subject, _, obj), row in sorted(records.items()):
        labels.setdefault(subject, row["subject_label"])
        labels.setdefault(obj, row["object_label"])
    graph = {}
    mappings = []
    for (subject, predicate, obj), row in sorted(records.items()):
        node = graph.setdefault(subject, {"@id": subject, "rdfs:label": labels[subject]})
        node.setdefault("skos:" + predicate.removeprefix(SKOS), []).append({"@id": obj})
        mapping = {
            "from": {"memberSet": [concept(subject, labels[subject])]},
            "to": {"memberSet": [concept(obj, labels[obj])]},
            "fromScheme": DATACITE_SCHEME,
            "toScheme": scheme_for(obj),
            "type": [predicate],
            "creator": [{"uri": uri, "prefLabel": {"en": name}} for uri, name in row["authors"]],
            "justification": row["mapping_justification"],
        }
        if row["mapping_date"]:
            mapping["created"] = row["mapping_date"]
        if row.get("comment", "").strip():
            mapping["note"] = {"en": [row["comment"].strip()]}
        mappings.append(mapping)
    targets = sorted({obj for _, _, obj in records} - set(graph))
    header = {
        "@id": BASE + "mappings/" + EXPORTS[0],
        "dcterms:title": "DataCite 4.7 crosswalks (generated SKOS view)",
        "dcterms:license": {"@id": license_uri},
        "dcterms:creator": [{"@id": c} for c in creators],
        "dcterms:source": [{"@id": s} for s in set_ids],
    }
    skos = {
        "@context": SKOS_CONTEXT,
        "@graph": [header, *graph.values(), *({"@id": o, "rdfs:label": labels[o]} for o in targets)],
    }
    # JSKOS is a plain array of mappings, the format jskos-server (Cocoda) imports.
    return {name: json.dumps(doc, ensure_ascii=False, indent=2) + "\n" for name, doc in zip(EXPORTS, (skos, mappings))}


def export_triples(directory):
    skos = read_json(directory / EXPORTS[0])
    require(skos.get("@context") == SKOS_CONTEXT, "SKOS export must have its self-contained local context")
    skos_rows = []
    for node in skos.get("@graph", []):
        for predicate, values in node.items():
            if predicate == "@id" or predicate == "rdfs:label" or predicate.startswith("dcterms:"):
                continue
            require(predicate.startswith("skos:") and SKOS + predicate[5:] in MATCHES, f"Unexpected SKOS export predicate {predicate}")
            require(isinstance(values, list), "SKOS targets must be arrays of @id objects")
            for value in values:
                require(isinstance(value, dict) and set(value) == {"@id"}, "SKOS target must be an @id object")
                skos_rows.append((node["@id"], SKOS + predicate[5:], value["@id"]))
    jskos = read_json(directory / EXPORTS[1])
    require(isinstance(jskos, list), "JSKOS export must be an array of mappings")
    jskos_rows = []
    for row in jskos:
        try:
            require(len(row["type"]) == len(row["from"]["memberSet"]) == len(row["to"]["memberSet"]) == 1,
                    "JSKOS export requires one-to-one concept bundles")
            require(row["fromScheme"]["uri"] and row["toScheme"]["uri"], "JSKOS mappings need fromScheme and toScheme")
            members = row["from"]["memberSet"] + row["to"]["memberSet"]
            require(all(m["prefLabel"].get("en") for m in members), "JSKOS concepts need English labels")
            jskos_rows.append((row["from"]["memberSet"][0]["uri"], row["type"][0], row["to"]["memberSet"][0]["uri"]))
        except (KeyError, TypeError) as error:
            raise MappingError("JSKOS export has invalid concept bundles") from error
    require(len(skos_rows) == len(set(skos_rows)), "Duplicate triples in SKOS export")
    require(len(jskos_rows) == len(set(jskos_rows)), "Duplicate triples in JSKOS export")
    return set(skos_rows), set(jskos_rows)


def build(root, check=False):
    records, sets, counts, source_count = validate_sources(root)
    triples = set(records)
    expected = projections(records, sets)
    directory = root / "mappings"
    if check:
        for name, text in expected.items():
            path = directory / name
            require(path.exists() and path.read_text(encoding="utf-8") == text,
                    f"Stale export {path}; run python3 rdf-build-scripts/build-mappings.py")
    else:
        for name, text in expected.items():
            (directory / name).write_text(text, encoding="utf-8")
    skos, jskos = export_triples(directory)
    require(triples == skos == jskos, "SSSOM, SKOS, and JSKOS mapping triples differ")
    if check:
        check_published_copy(root)
    return counts, len(triples), source_count


def check_published_copy(root):
    """The production bundle serves mapping_set_id IRIs; its copies must be current."""
    published = root / "production-namespace" / "mappings"
    require(published.is_dir(), f"Missing {published}; run bash rdf-build-scripts/generate-production-namespace.sh")
    source = root / "mappings"
    names = [p.name for p in source.glob("datacite-*.sssom.tsv")]
    names += [*EXPORTS, "target-sources.json"]
    names += [f"{group}/{p.name}" for group in ("conversion", "coverage") for p in (source / group).glob("*.json")]
    for name in sorted(names):
        copy = published / name
        require(copy.is_file() and copy.read_bytes() == (source / name).read_bytes(),
                f"Stale published mapping {copy}; run bash rdf-build-scripts/generate-production-namespace.sh")
