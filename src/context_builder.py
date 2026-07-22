# Convert retrieved evidence into organized context for the LLM.
import json

def build_context(evidence):
    """
    Convert retrieved evidence into organized context
    for the language model.
    """

    evidence_by_domain = {}

    for item in evidence:
        domain = item["domain"]

        context_item = item["text"]

        if item["records"]:
            context_item += (
                "\n\nStructured Records:\n"
                + json.dumps(item["records"], indent=2)
            )

        evidence_by_domain.setdefault(domain, []).append(context_item)

    domain_sections = []

    for domain, texts in evidence_by_domain.items():
        section = f"Course/Domain: {domain}\n" + "\n".join(texts)
        domain_sections.append(section)

    return "\n\n".join(domain_sections)