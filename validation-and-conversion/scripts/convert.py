#!/usr/bin/env python3
"""
Utility to transform a DataCite XML record into the JSON representation
accepted by the DataCite REST API.  The script reads an XML file that
conforms to the DataCite Metadata Schema (kernel‑4) and produces a JSON
document mirroring the structure exposed by DataCite's API.  It is designed
around the example XML (https://schema.datacite.org/meta/kernel-4/example/datacite-example-full-v4.xml)
and the corresponding JSON representation (https://api.test.datacite.org/dois/10.82433/B09Z-4K37?publisher=true&affiliation=true).

The converter performs the following steps:

* Parse the XML document using ``xml.etree.ElementTree``.  Namespace handling
  is simplified by registering the DataCite namespace and stripping it when
  building the result.
* Walk through each major element (identifier, creators, titles, etc.) and
  assemble Python dictionaries/lists corresponding to DataCite JSON fields.
* Convert attribute names from camelCase in XML to the lowerCamelCase used
  by DataCite JSON (e.g. ``rightsURI`` → ``rightsUri``, ``schemeURI`` →
  ``schemeUri``).  Where the JSON specification expects plural lists
  (``creators.affiliation``), the code collects all values.
* Derive additional pieces of information not explicitly stored in the
  XML.  For example, the DOI prefix/suffix are extracted from the
  ``identifier`` element.  For ``types``, generic mappings are provided
  from the ``resourceTypeGeneral`` value to the RIS, BibTeX, CiteProc and
  Schema.org type constants.
* Base64‐encode the original XML and include it in the ``xml`` field of
  ``attributes``.  This mirrors the behaviour of DataCite's API and
  ensures that the original metadata can be reconstructed from the JSON.

The script writes its output as pretty‑printed JSON to stdout by default,
but can write to a file when the ``--output`` option is used.

Example usage:

    python xml_to_datacite_json.py datacite-example-full-v4.xml --output record.json

"""

import argparse
import base64
import json
import os
import sys
from typing import Any, Dict, List, Optional
import xml.etree.ElementTree as ET


# Namespace for DataCite Kernel‑4 XML.  When parsing, we need to prefix
# element names with this namespace.  Register it globally to ease lookups.
DC_NS = "http://datacite.org/schema/kernel-4"
NSMAP = {"d": DC_NS}


def get_text(element: Optional[ET.Element]) -> Optional[str]:
    """Return the text content of an element or None if missing."""
    if element is not None and element.text is not None:
        return element.text.strip() or None
    return None


def convert_name_identifier(elem: ET.Element) -> Dict[str, Any]:
    """Convert a <nameIdentifier> element into a JSON object."""
    return {
        "nameIdentifier": get_text(elem),
        "nameIdentifierScheme": elem.attrib.get("nameIdentifierScheme"),
        "schemeUri": elem.attrib.get("schemeURI"),
    }


def convert_affiliation(elem: ET.Element) -> Dict[str, Any]:
    """Convert an <affiliation> element into a JSON object."""
    return {
        "name": get_text(elem),
        "affiliationIdentifier": elem.attrib.get("affiliationIdentifier"),
        "affiliationIdentifierScheme": elem.attrib.get("affiliationIdentifierScheme"),
        "schemeUri": elem.attrib.get("schemeURI"),
    }


def convert_creator(elem: ET.Element) -> Dict[str, Any]:
    """Convert a <creator> element into a JSON object."""
    # Creator name may appear as <creatorName> with nameType attribute
    creator_name_elem = elem.find("d:creatorName", NSMAP)
    name = get_text(creator_name_elem)
    name_type = creator_name_elem.attrib.get("nameType") if creator_name_elem is not None else None
    given = get_text(elem.find("d:givenName", NSMAP))
    family = get_text(elem.find("d:familyName", NSMAP))
    # Name identifiers
    name_ids = []
    for ni in elem.findall("d:nameIdentifier", NSMAP):
        name_ids.append(convert_name_identifier(ni))
    # Affiliations
    affiliations = []
    for aff in elem.findall("d:affiliation", NSMAP):
        affiliations.append(convert_affiliation(aff))
    # When building the JSON, DataCite's examples sometimes use a list of
    # simple strings for affiliation.  To preserve richer information we
    # provide objects with name and identifiers.  If no attributes beyond
    # name are present, collapse to just the name string.
    aff_output: List[Any] = []
    for a in affiliations:
        # collapse if only name is present
        if a and a.get("name") and not any([a.get("affiliationIdentifier"), a.get("affiliationIdentifierScheme"), a.get("schemeUri")]):
            aff_output.append(a["name"])
        else:
            aff_output.append(a)
    creator_obj: Dict[str, Any] = {
        "name": name,
        "nameType": name_type,
        "givenName": given,
        "familyName": family,
    }
    if name_ids:
        creator_obj["nameIdentifiers"] = name_ids
    if aff_output:
        creator_obj["affiliation"] = aff_output
    return creator_obj


def convert_contributor(elem: ET.Element) -> Dict[str, Any]:
    """Convert a <contributor> element into a JSON object."""
    obj = convert_creator(elem)  # share name parsing logic
    contributor_type = elem.attrib.get("contributorType")
    if contributor_type:
        obj["contributorType"] = contributor_type
    return obj


def convert_title(elem: ET.Element) -> Dict[str, Any]:
    """Convert a <title> element into a JSON object."""
    obj: Dict[str, Any] = {"title": get_text(elem)}
    # xml:lang is stored with namespace xlm; in ElementTree it's an attribute with full name
    lang = elem.attrib.get("{http://www.w3.org/XML/1998/namespace}lang")
    if lang:
        obj["lang"] = lang
    title_type = elem.attrib.get("titleType")
    if title_type:
        obj["titleType"] = title_type
    return obj


def convert_subject(elem: ET.Element) -> Dict[str, Any]:
    """Convert a <subject> element into a JSON object."""
    obj: Dict[str, Any] = {"subject": get_text(elem)}
    lang = elem.attrib.get("{http://www.w3.org/XML/1998/namespace}lang")
    if lang:
        obj["lang"] = lang
    # Additional attributes
    for xml_attr, json_key in [
        ("subjectScheme", "subjectScheme"),
        ("schemeURI", "schemeUri"),
        ("valueURI", "valueUri"),
        ("classificationCode", "classificationCode"),
    ]:
        val = elem.attrib.get(xml_attr)
        if val is not None:
            obj[json_key] = val
    return obj


def convert_name_identifiers(parent: ET.Element) -> List[Dict[str, Any]]:
    """Convert nested <nameIdentifier> elements found under contributors/creators."""
    result = []
    for elem in parent.findall("d:nameIdentifier", NSMAP):
        result.append(convert_name_identifier(elem))
    return result


def convert_dates(root: ET.Element) -> List[Dict[str, Any]]:
    dates = []
    for d_elem in root.findall("d:dates/d:date", NSMAP):
        date_obj: Dict[str, Any] = {"date": get_text(d_elem)}
        dt = d_elem.attrib.get("dateType")
        if dt:
            date_obj["dateType"] = dt
        di = d_elem.attrib.get("dateInformation")
        if di:
            date_obj["dateInformation"] = di
        dates.append(date_obj)
    return dates


def convert_related_identifier(elem: ET.Element) -> Dict[str, Any]:
    """Convert a <relatedIdentifier> element into a JSON object."""
    obj: Dict[str, Any] = {"relatedIdentifier": get_text(elem)}
    # Map attributes to JSON keys
    for xml_attr, json_key in [
        ("relatedIdentifierType", "relatedIdentifierType"),
        ("relationType", "relationType"),
        ("relatedMetadataScheme", "relatedMetadataScheme"),
        ("schemeURI", "schemeUri"),
        ("schemeType", "schemeType"),
        ("resourceTypeGeneral", "resourceTypeGeneral"),
    ]:
        val = elem.attrib.get(xml_attr)
        if val is not None:
            obj[json_key] = val
    return obj


def convert_related_item(elem: ET.Element) -> Dict[str, Any]:
    """Convert a <relatedItem> element into a JSON object."""
    obj: Dict[str, Any] = {}
    # Attributes
    for xml_attr, json_key in [
        ("relatedItemType", "relatedItemType"),
        ("relationType", "relationType"),
    ]:
        val = elem.attrib.get(xml_attr)
        if val is not None:
            obj[json_key] = val
    # Related item identifier
    rid = elem.find("d:relatedItemIdentifier", NSMAP)
    if rid is not None:
        rid_obj: Dict[str, Any] = {"relatedItemIdentifier": get_text(rid)}
        for xml_attr, json_key in [
            ("relatedItemIdentifierType", "relatedItemIdentifierType"),
            ("relatedMetadataScheme", "relatedMetadataScheme"),
            ("schemeURI", "schemeUri"),
            ("schemeType", "schemeType"),
        ]:
            val = rid.attrib.get(xml_attr)
            if val is not None:
                rid_obj[json_key] = val
        obj["relatedItemIdentifier"] = rid_obj
    # Creators
    creators_elem = elem.find("d:creators", NSMAP)
    if creators_elem is not None:
        rel_creators: List[Dict[str, Any]] = []
        for c in creators_elem.findall("d:creator", NSMAP):
            rel_creators.append(convert_creator(c))
        if rel_creators:
            obj["creators"] = rel_creators
    # Titles
    titles_elem = elem.find("d:titles", NSMAP)
    if titles_elem is not None:
        rel_titles: List[Dict[str, Any]] = []
        for t in titles_elem.findall("d:title", NSMAP):
            rel_titles.append(convert_title(t))
        if rel_titles:
            obj["titles"] = rel_titles
    # Publication year
    pub_year = get_text(elem.find("d:publicationYear", NSMAP))
    if pub_year is not None:
        obj["publicationYear"] = pub_year
    # Additional simple fields
    for tag, key in [
        ("volume", "volume"),
        ("issue", "issue"),
        ("number", "number"),
        ("firstPage", "firstPage"),
        ("lastPage", "lastPage"),
        ("publisher", "publisher"),
        ("edition", "edition"),
    ]:
        val = get_text(elem.find(f"d:{tag}", NSMAP))
        if val is not None:
            obj[key] = val
        # For <number>, capture numberType
        if tag == "number":
            number_elem = elem.find("d:number", NSMAP)
            if number_elem is not None:
                nt = number_elem.attrib.get("numberType")
                if nt:
                    obj["numberType"] = nt
    # Contributors inside related item
    rel_contribs_elem = elem.find("d:contributors", NSMAP)
    if rel_contribs_elem is not None:
        rel_contribs: List[Dict[str, Any]] = []
        for c in rel_contribs_elem.findall("d:contributor", NSMAP):
            rel_contribs.append(convert_contributor(c))
        if rel_contribs:
            obj["contributors"] = rel_contribs
    return obj


def resource_type_mappings(resource_type_general: str) -> Dict[str, str]:
    """Return mapping of RIS, BibTeX, CiteProc, and Schema.org types for a given resourceTypeGeneral.

    DataCite provides recommended mappings from their resourceTypeGeneral values
    to other classification schemes.  This function covers the most common
    types; unknown types default to generic placeholders.
    """
    general = (resource_type_general or "").lower()
    mappings = {
        "dataset": {"ris": "DATA", "bibtex": "misc", "citeproc": "dataset", "schemaOrg": "Dataset"},
        "collection": {"ris": "GEN", "bibtex": "misc", "citeproc": "dataset", "schemaOrg": "Collection"},
        "text": {"ris": "GEN", "bibtex": "article", "citeproc": "article", "schemaOrg": "ScholarlyArticle"},
        "audiovisual": {"ris": "AV", "bibtex": "misc", "citeproc": "motion_picture", "schemaOrg": "VideoObject"},
        "image": {"ris": "IMAGE", "bibtex": "misc", "citeproc": "graphic", "schemaOrg": "ImageObject"},
        "software": {"ris": "COMP", "bibtex": "software", "citeproc": "software", "schemaOrg": "SoftwareSourceCode"},
        "other": {"ris": "GEN", "bibtex": "misc", "citeproc": "other", "schemaOrg": "CreativeWork"},
    }
    return mappings.get(general, {"ris": "GEN", "bibtex": "misc", "citeproc": "other", "schemaOrg": "CreativeWork"})


def convert_geolocation(elem: ET.Element) -> Dict[str, Any]:
    """Convert a <geoLocation> element into a JSON object."""
    obj: Dict[str, Any] = {}
    place = get_text(elem.find("d:geoLocationPlace", NSMAP))
    if place is not None:
        obj["geoLocationPlace"] = place
    # Point
    point_elem = elem.find("d:geoLocationPoint", NSMAP)
    if point_elem is not None:
        point_obj: Dict[str, Any] = {}
        lat = get_text(point_elem.find("d:pointLatitude", NSMAP))
        lon = get_text(point_elem.find("d:pointLongitude", NSMAP))
        if lat is not None:
            point_obj["pointLatitude"] = lat
        if lon is not None:
            point_obj["pointLongitude"] = lon
        if point_obj:
            obj["geoLocationPoint"] = point_obj
    # Box
    box_elem = elem.find("d:geoLocationBox", NSMAP)
    if box_elem is not None:
        box_obj: Dict[str, Any] = {}
        for tag in [
            ("westBoundLongitude", "westBoundLongitude"),
            ("eastBoundLongitude", "eastBoundLongitude"),
            ("southBoundLatitude", "southBoundLatitude"),
            ("northBoundLatitude", "northBoundLatitude"),
        ]:
            val = get_text(box_elem.find(f"d:{tag[0]}", NSMAP))
            if val is not None:
                box_obj[tag[1]] = val
        if box_obj:
            obj["geoLocationBox"] = box_obj
    # Polygon
    polygon_elem = elem.find("d:geoLocationPolygon", NSMAP)
    if polygon_elem is not None:
        polygon_points = []
        for p in polygon_elem.findall("d:polygonPoint", NSMAP):
            pt_obj: Dict[str, Any] = {}
            lat = get_text(p.find("d:pointLatitude", NSMAP))
            lon = get_text(p.find("d:pointLongitude", NSMAP))
            if lat is not None:
                pt_obj["pointLatitude"] = lat
            if lon is not None:
                pt_obj["pointLongitude"] = lon
            if pt_obj:
                polygon_points.append({"polygonPoint": pt_obj})
        if polygon_points:
            obj["geoLocationPolygon"] = polygon_points
    return obj


def build_json_from_xml(xml_str: str) -> Dict[str, Any]:
    """Parse a DataCite XML string and build the corresponding JSON structure."""
    # Parse the XML document
    root = ET.fromstring(xml_str)
    # The DOI identifier
    identifier_elem = root.find("d:identifier", NSMAP)
    doi = get_text(identifier_elem) if identifier_elem is not None else None
    # Build basic id/prefix/suffix
    prefix, suffix = (None, None)
    if doi and "/" in doi:
        prefix, suffix = doi.split("/", 1)
    attributes: Dict[str, Any] = {}
    # DOI
    attributes["doi"] = doi
    if prefix:
        attributes["prefix"] = prefix
    if suffix:
        attributes["suffix"] = suffix
    # Identifiers – DataCite JSON allows for extra local identifiers
    # In this example, the "identifier" element holds the DOI.  To populate
    # identifiers we look at alternateIdentifiers and also create a copy of
    # these as identifiers.  This matches the API example where the local
    # accession number appears both in identifiers and alternateIdentifiers.
    identifiers: List[Dict[str, Any]] = []
    alternate_identifiers: List[Dict[str, Any]] = []
    for alt in root.findall("d:alternateIdentifiers/d:alternateIdentifier", NSMAP):
        alt_id = get_text(alt)
        alt_type = alt.attrib.get("alternateIdentifierType")
        alt_obj = {
            "alternateIdentifier": alt_id,
            "alternateIdentifierType": alt_type,
        }
        alternate_identifiers.append(alt_obj)
        # Mirror into identifiers list
        identifiers.append({"identifier": alt_id, "identifierType": alt_type})
    if identifiers:
        attributes["identifiers"] = identifiers
    if alternate_identifiers:
        attributes["alternateIdentifiers"] = alternate_identifiers
    # Creators
    creators_elem = root.find("d:creators", NSMAP)
    creators: List[Dict[str, Any]] = []
    if creators_elem is not None:
        for c in creators_elem.findall("d:creator", NSMAP):
            creators.append(convert_creator(c))
    if creators:
        attributes["creators"] = creators
    # Titles
    titles_elem = root.find("d:titles", NSMAP)
    titles: List[Dict[str, Any]] = []
    if titles_elem is not None:
        for t in titles_elem.findall("d:title", NSMAP):
            titles.append(convert_title(t))
    if titles:
        attributes["titles"] = titles
    # Publisher
    publisher_elem = root.find("d:publisher", NSMAP)
    if publisher_elem is not None:
        publisher_obj: Dict[str, Any] = {"name": get_text(publisher_elem)}
        lang = publisher_elem.attrib.get("{http://www.w3.org/XML/1998/namespace}lang")
        if lang:
            publisher_obj["lang"] = lang
        # Additional identifiers
        if publisher_elem.attrib.get("publisherIdentifier"):
            publisher_obj["publisherIdentifier"] = publisher_elem.attrib.get("publisherIdentifier")
        if publisher_elem.attrib.get("publisherIdentifierScheme"):
            publisher_obj["publisherIdentifierScheme"] = publisher_elem.attrib.get("publisherIdentifierScheme")
        if publisher_elem.attrib.get("schemeURI"):
            publisher_obj["schemeUri"] = publisher_elem.attrib.get("schemeURI")
        attributes["publisher"] = publisher_obj
    # Container – derive from relatedIdentifier of type PURL and description of type SeriesInformation
    container_obj: Dict[str, Any] = {}
    # Determine container type from resourceTypeGeneral
    resource_type_elem = root.find("d:resourceType", NSMAP)
    resource_type_general = resource_type_elem.attrib.get("resourceTypeGeneral") if resource_type_elem is not None else None
    if resource_type_general:
        # Use a generic container type for dataset
        if resource_type_general.lower() == "dataset":
            container_obj["type"] = "DataRepository"
    # Find first relatedIdentifier with type PURL
    purl_elem = None
    for ri in root.findall("d:relatedIdentifiers/d:relatedIdentifier", NSMAP):
        if ri.attrib.get("relatedIdentifierType") == "PURL":
            purl_elem = ri
            break
    if purl_elem is not None:
        container_obj["identifier"] = get_text(purl_elem)
        container_obj["identifierType"] = purl_elem.attrib.get("relatedIdentifierType")
    # Container title from description of type SeriesInformation
    for desc in root.findall("d:descriptions/d:description", NSMAP):
        if desc.attrib.get("descriptionType") == "SeriesInformation":
            container_obj["title"] = get_text(desc)
            break
    if container_obj:
        attributes["container"] = container_obj
    # Publication year
    pub_year = get_text(root.find("d:publicationYear", NSMAP))
    if pub_year is not None:
        # Convert to int where possible
        try:
            attributes["publicationYear"] = int(pub_year)
        except ValueError:
            attributes["publicationYear"] = pub_year
    # Subjects
    subjects_elem = root.find("d:subjects", NSMAP)
    subjects: List[Dict[str, Any]] = []
    if subjects_elem is not None:
        for s in subjects_elem.findall("d:subject", NSMAP):
            subjects.append(convert_subject(s))
    if subjects:
        attributes["subjects"] = subjects
    # Contributors
    contrib_elem = root.find("d:contributors", NSMAP)
    contributors: List[Dict[str, Any]] = []
    if contrib_elem is not None:
        for c in contrib_elem.findall("d:contributor", NSMAP):
            contributors.append(convert_contributor(c))
    if contributors:
        attributes["contributors"] = contributors
    # Dates
    date_objs = convert_dates(root)
    if date_objs:
        attributes["dates"] = date_objs
    # Language
    lang_elem = root.find("d:language", NSMAP)
    if lang_elem is not None and get_text(lang_elem) is not None:
        attributes["language"] = get_text(lang_elem)
    # Types
    types_obj: Dict[str, Any] = {}
    if resource_type_elem is not None:
        rt_text = get_text(resource_type_elem)
        rt_general = resource_type_general
        if rt_text is not None:
            types_obj["resourceType"] = rt_text
        if rt_general is not None:
            types_obj["resourceTypeGeneral"] = rt_general
            # Add crosswalks
            types_obj.update(resource_type_mappings(rt_general))
    if types_obj:
        attributes["types"] = types_obj
    # Related identifiers
    related_identifiers: List[Dict[str, Any]] = []
    for ri in root.findall("d:relatedIdentifiers/d:relatedIdentifier", NSMAP):
        related_identifiers.append(convert_related_identifier(ri))
    if related_identifiers:
        attributes["relatedIdentifiers"] = related_identifiers
    # Related items
    related_items: List[Dict[str, Any]] = []
    for ritem in root.findall("d:relatedItems/d:relatedItem", NSMAP):
        related_items.append(convert_related_item(ritem))
    if related_items:
        attributes["relatedItems"] = related_items
    # Sizes
    size_list: List[str] = []
    for s_elem in root.findall("d:sizes/d:size", NSMAP):
        val = get_text(s_elem)
        if val is not None:
            size_list.append(val)
    if size_list:
        attributes["sizes"] = size_list
    # Formats
    format_list: List[str] = []
    for f_elem in root.findall("d:formats/d:format", NSMAP):
        val = get_text(f_elem)
        if val is not None:
            format_list.append(val)
    if format_list:
        attributes["formats"] = format_list
    # Version
    version = get_text(root.find("d:version", NSMAP))
    if version is not None:
        attributes["version"] = version
    # Rights list
    rights_objects: List[Dict[str, Any]] = []
    for r_elem in root.findall("d:rightsList/d:rights", NSMAP):
        r_obj: Dict[str, Any] = {"rights": get_text(r_elem)}
        lang = r_elem.attrib.get("{http://www.w3.org/XML/1998/namespace}lang")
        if lang:
            r_obj["lang"] = lang
        if r_elem.attrib.get("rightsURI"):
            r_obj["rightsUri"] = r_elem.attrib.get("rightsURI")
        if r_elem.attrib.get("schemeURI"):
            r_obj["schemeUri"] = r_elem.attrib.get("schemeURI")
        if r_elem.attrib.get("rightsIdentifier"):
            r_obj["rightsIdentifier"] = r_elem.attrib.get("rightsIdentifier")
        if r_elem.attrib.get("rightsIdentifierScheme"):
            r_obj["rightsIdentifierScheme"] = r_elem.attrib.get("rightsIdentifierScheme")
        rights_objects.append(r_obj)
    if rights_objects:
        attributes["rightsList"] = rights_objects
    # Descriptions
    desc_objects: List[Dict[str, Any]] = []
    for d_elem in root.findall("d:descriptions/d:description", NSMAP):
        d_obj: Dict[str, Any] = {"description": get_text(d_elem)}
        lang = d_elem.attrib.get("{http://www.w3.org/XML/1998/namespace}lang")
        if lang:
            d_obj["lang"] = lang
        desc_type = d_elem.attrib.get("descriptionType")
        if desc_type:
            d_obj["descriptionType"] = desc_type
        desc_objects.append(d_obj)
    if desc_objects:
        attributes["descriptions"] = desc_objects
    # Geolocations
    geolocations: List[Dict[str, Any]] = []
    for gl in root.findall("d:geoLocations/d:geoLocation", NSMAP):
        geolocations.append(convert_geolocation(gl))
    if geolocations:
        attributes["geoLocations"] = geolocations
    # Funding references
    funding_refs: List[Dict[str, Any]] = []
    for fr in root.findall("d:fundingReferences/d:fundingReference", NSMAP):
        fr_obj: Dict[str, Any] = {}
        # funderName
        val = get_text(fr.find("d:funderName", NSMAP))
        if val is not None:
            fr_obj["funderName"] = val
        funder_id = fr.find("d:funderIdentifier", NSMAP)
        if funder_id is not None:
            fr_obj["funderIdentifier"] = get_text(funder_id)
            if funder_id.attrib.get("funderIdentifierType"):
                fr_obj["funderIdentifierType"] = funder_id.attrib.get("funderIdentifierType")
            if funder_id.attrib.get("schemeURI"):
                fr_obj["schemeUri"] = funder_id.attrib.get("schemeURI")
        # Award number (with URI)
        award_number = fr.find("d:awardNumber", NSMAP)
        if award_number is not None:
            fr_obj["awardNumber"] = get_text(award_number)
            if award_number.attrib.get("awardURI"):
                fr_obj["awardUri"] = award_number.attrib.get("awardURI")
        # Award title
        award_title = get_text(fr.find("d:awardTitle", NSMAP))
        if award_title is not None:
            fr_obj["awardTitle"] = award_title
        if fr_obj:
            funding_refs.append(fr_obj)
    if funding_refs:
        attributes["fundingReferences"] = funding_refs
    # Encode the original XML as base64 and include as xml attribute
    xml_b64 = base64.b64encode(xml_str.encode("utf-8")).decode("ascii")
    attributes["xml"] = xml_b64
    # Assemble final JSON object
    record = {
        "data": {
            "id": doi.lower() if doi else None,
            "type": "dois",
            "attributes": attributes,
        }
    }
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert DataCite XML to JSON.")
    parser.add_argument("xml_file", help="Path to the DataCite XML file to convert")
    parser.add_argument("--output", "-o", help="Write JSON output to this file instead of stdout")
    args = parser.parse_args()
    with open(args.xml_file, "r", encoding="utf-8") as f:
        xml_data = f.read()
    json_obj = build_json_from_xml(xml_data)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as out:
            json.dump(json_obj, out, ensure_ascii=False, indent=2)
            out.write("\n")
    else:
        json.dump(json_obj, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")


if __name__ == "__main__":
    main()