import re


def canonicalize_concept(concept_name):
    """
    Convert a specific concept name into a broader canonical concept.
    """

    canonical = concept_name.replace("\n", " ").strip()

    canonical = re.sub(
        r"\(\d+\s+credits?\)",
        "",
        canonical,
        flags=re.IGNORECASE,
    )

    canonical = re.sub(
        r"\b(Fall|Spring|Summer)\s+\d{4}\b",
        "",
        canonical,
        flags=re.IGNORECASE,
    )

    canonical = re.sub(r"\s+", " ", canonical).strip()

    return canonical