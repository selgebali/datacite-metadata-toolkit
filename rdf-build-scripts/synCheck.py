#!/usr/bin/env python3
"""
Sync check between the bundled profile's $defs enums and the vocab term files.

For each $defs entry that has both `enum` and `iriMap`:
  1) The set of terms in $defs.enum == set($defs.iriMap.keys()).
  2) The vocab folder referenced by iriMap contains a term file for each enum value.
  3) Each iriMap value uses the expected base URL and the term-name segment matches.

Schemes that have no vocab folder in rdf-vocabulary-staging/vocab/ (e.g. titleType,
funderIdentifierType at time of writing) are skipped with a warning rather than
treated as errors, so the script reports real drift without blocking on
not-yet-published vocabularies.

Exit code: 0 when all checks pass, 1 otherwise.
"""

import argparse
import json
import os
import sys
from urllib.parse import urlparse, unquote

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_PROFILE_PATH = os.path.join(
    ROOT, "validation-and-conversion", "schemas", "schema-profiles", "datacite4.6-profile.json"
)
VOCAB_DIR = os.path.join(ROOT, "rdf-vocabulary-staging", "vocab")
EXPECTED_BASE = "https://schema.stage.datacite.org/linked-data/vocab/"

ALIAS_FRAGMENTS = {"CrossrefFunderID": "Crossref Funder ID"}

errors = []
warnings = []


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def scheme_and_term_from_iri(iri: str):
    """Parse `<base>vocab/<scheme>/<term>` → (scheme, term)."""
    p = urlparse(iri)
    parts = [seg for seg in p.path.split("/") if seg]
    if len(parts) < 4 or parts[-3] != "vocab":
        raise ValueError(f"IRI does not match …/vocab/<scheme>/<term>: {iri}")
    return parts[-2], unquote(parts[-1])


def terms_in_vocab_folder(scheme_dir: str):
    """Return the set of term names from <scheme>/*.jsonld, excluding the scheme file itself."""
    scheme_name = os.path.basename(scheme_dir)
    terms = set()
    for fname in os.listdir(scheme_dir):
        if not fname.endswith(".jsonld"):
            continue
        stem = fname[: -len(".jsonld")]
        if stem in (scheme_name, "context"):
            continue
        terms.add(stem)
    return terms


def check_defs_enum(def_key: str, def_obj: dict):
    enum_terms = def_obj.get("enum")
    iri_map = def_obj.get("iriMap")
    if not isinstance(enum_terms, list) or not isinstance(iri_map, dict):
        return

    enum_set = set(enum_terms)
    iri_keys = set(iri_map.keys())

    if enum_set != iri_keys:
        if enum_set - iri_keys:
            errors.append(f"[{def_key}] iriMap missing terms: {sorted(enum_set - iri_keys)}")
        if iri_keys - enum_set:
            errors.append(f"[{def_key}] enum missing terms: {sorted(iri_keys - enum_set)}")

    try:
        sample_iri = next(iter(iri_map.values()))
    except StopIteration:
        errors.append(f"[{def_key}] iriMap is empty")
        return

    try:
        scheme, _ = scheme_and_term_from_iri(sample_iri)
    except ValueError as e:
        errors.append(f"[{def_key}] {e}")
        return

    scheme_dir = os.path.join(VOCAB_DIR, scheme)
    if not os.path.isdir(scheme_dir):
        warnings.append(f"[{def_key}] no vocab folder for scheme '{scheme}' — skipping file check")
    else:
        folder_terms = terms_in_vocab_folder(scheme_dir)
        normalized_enum = {ALIAS_FRAGMENTS.get(t, t) for t in enum_set}
        # Compare with alias normalization: profile may use "Crossref Funder ID" but folder file is CrossrefFunderID
        folder_norm = {ALIAS_FRAGMENTS.get(t, t) for t in folder_terms}
        if normalized_enum != folder_norm:
            missing_in_folder = normalized_enum - folder_norm
            missing_in_enum = folder_norm - normalized_enum
            if missing_in_folder:
                errors.append(
                    f"[{def_key}] vocab/{scheme}/ missing files for: {sorted(missing_in_folder)}"
                )
            if missing_in_enum:
                errors.append(
                    f"[{def_key}] $defs missing terms present in vocab/{scheme}/: {sorted(missing_in_enum)}"
                )

    for term, iri in iri_map.items():
        if not iri.startswith(EXPECTED_BASE):
            errors.append(
                f"[{def_key}] unexpected base for term '{term}':\n"
                f"  got:      {iri}\n  expected: {EXPECTED_BASE}{scheme}/<term>"
            )
            continue
        try:
            iri_scheme, iri_term = scheme_and_term_from_iri(iri)
        except ValueError as e:
            errors.append(f"[{def_key}] {e}")
            continue
        if iri_scheme != scheme:
            errors.append(f"[{def_key}] inconsistent scheme for term '{term}': {iri_scheme} ≠ {scheme}")
        term_norm = ALIAS_FRAGMENTS.get(iri_term, iri_term)
        expected_term = ALIAS_FRAGMENTS.get(term, term)
        if term_norm != expected_term:
            errors.append(f"[{def_key}] IRI term '{iri_term}' does not match enum term '{term}'.")


def main():
    parser = argparse.ArgumentParser(description="Verify schema profile $defs are in sync with vocab term files.")
    parser.add_argument(
        "--profile",
        default=DEFAULT_PROFILE_PATH,
        help=f"Path to a schema profile JSON (default: {os.path.relpath(DEFAULT_PROFILE_PATH, ROOT)})",
    )
    args = parser.parse_args()
    profile_path = args.profile

    if not os.path.isfile(profile_path):
        print(f"ERROR: profile not found at {profile_path}")
        sys.exit(1)
    if not os.path.isdir(VOCAB_DIR):
        print(f"ERROR: vocab dir not found at {VOCAB_DIR}")
        sys.exit(1)

    print(f"Checking profile: {os.path.relpath(profile_path, ROOT)}")
    profile = load_json(profile_path)
    for key, obj in profile.get("$defs", {}).items():
        check_defs_enum(key, obj)

    for w in warnings:
        print(f"WARN: {w}")

    if errors:
        print("\nSync check FAILED:\n")
        for e in errors:
            print(" - ", e)
        sys.exit(1)
    print("Sync check passed: $defs enums and vocab term files are consistent.")
    sys.exit(0)


if __name__ == "__main__":
    main()
