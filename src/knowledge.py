# deterministic retrieval of evidence from notes and documents based on a topic
import json
from pathlib import Path


def retrieve_evidence(query):
    results = []

    if isinstance(query, dict):
        fallback_terms = query.get("search_terms", [])

        text_search_terms = query.get(
            "text_search_terms",
            fallback_terms,
        )

        record_search_terms = query.get(
            "record_search_terms",
            fallback_terms,
        )

        record_types = set(
            query.get("record_types", [])
        )

        record_filters = query.get(
            "record_filters",
            [],
        )
    else:
        text_search_terms = [query]
        record_search_terms = [query]
        record_types = set()
        record_filters = []

    normalized_text_terms = [
        term.lower().strip()
        for term in text_search_terms
        if term.strip()
    ]

    normalized_record_terms = [
        term.lower().strip()
        for term in record_search_terms
        if term.strip()
    ]
    
    records_requested = bool(
    record_types
    or record_filters
    or normalized_record_terms
    )

    notes_folder = Path("data/notes")

    for note_file in notes_folder.glob("*.txt"):
        with open(note_file, "r") as file:
            notes = file.readlines()

        for line in notes:
            normalized_line = line.lower()

            text_matches = any(
                term in normalized_line
                for term in normalized_text_terms
            )

            if text_matches:
                results.append(
                    {
                        "id": None,
                        "domain": note_file.stem,
                        "source": note_file.stem,
                        "heading": None,
                        "section": None,
                        "concepts": [],
                        "records": [],
                        "location": None,
                        "text": line.strip(),
                    }
                )

    documents_folder = Path("data/documents")

    for json_file in documents_folder.rglob("*.json"):
        with open(json_file, "r") as file:
            chunks = json.load(file)

        for chunk in chunks:
            chunk_text = chunk.get("text", "").lower()
            chunk_records = chunk.get("records", [])

            text_matches = any(
                term in chunk_text
                for term in normalized_text_terms
            )

            eligible_records = []

            if records_requested:
                eligible_records = [
                    record
                    for record in chunk_records
                    if not record_types
                    or record.get("type") in record_types
                ]

            matching_records = []

            for record in eligible_records:
                filters_match = all(
                    str(record.get(filter_item["field"], "")).lower()
                    == filter_item["value"].lower()
                    for filter_item in record_filters
                )

                searchable_record = " ".join(
                    str(value)
                    for value in record.values()
                    if value is not None
                ).lower()

                terms_match = (
                    not normalized_record_terms
                    or any(
                        term in searchable_record
                        for term in normalized_record_terms
                    )
                )

                if filters_match and terms_match:
                    matching_records.append(record)

            if (
                text_matches
                and not matching_records
                and not record_filters
            ):
                matching_records = eligible_records

            record_matches = bool(matching_records)

            if text_matches or record_matches:
                results.append(
                    {
                        "id": chunk["id"],
                        "domain": chunk["domain"],
                        "source": chunk["document"],
                        "heading": chunk.get("heading"),
                        "section": chunk.get("section"),
                        "concepts": chunk.get("concepts", []),
                        "records": matching_records,
                        "location": chunk["location"],
                        "text": chunk["text"],
                    }
                )

    return results