# Assigns a score to each piece of evidence based on its relevance to the topic and the presence of key terms.

def rank_evidence(evidence, search_terms):
    """
    Score and order retrieved evidence by relevance.
    """

    normalized_terms = [
        term.lower().strip()
        for term in search_terms
        if term.strip()
    ]

    if not normalized_terms:
        return evidence

    ranked_evidence = []

    for item in evidence:
        score = 0

        heading = (item.get("heading") or "").lower()
        section = (item.get("section") or "").lower()
        text = (item.get("text") or "").lower()

        for term in normalized_terms:
            if heading == term:
                score += 5
            elif term in heading:
                score += 4

            if term in section:
                score += 3

            if term in text:
                score += 2

        ranked_item = {
            **item,
            "score": score,
        }

        ranked_evidence.append(ranked_item)

    return sorted(
        ranked_evidence,
        key=lambda item: item["score"],
        reverse=True,
    )