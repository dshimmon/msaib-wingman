# MSAIB Wingman
# Main application entry point

from interface import get_mission, show_completion, show_header, show_topic
from knowledge import retrieve_evidence
from reasoning import summarize_results
from query_interpreter import interpret_query
from concept_retrieval import retrieve_concept_occurrences
from evidence_ranker import rank_evidence


show_header()

mission = get_mission()

show_topic(mission)

query_plan = interpret_query(mission)
evidence = retrieve_evidence(query_plan)

memory_search_terms = query_plan.get(
    "memory_search_terms",
    [],
)

if memory_search_terms:
    memory_evidence = retrieve_concept_occurrences(
        memory_search_terms
    )
    evidence.extend(memory_evidence)

ranking_terms = query_plan.get(
    "text_search_terms",
    [],
)
evidence = rank_evidence(
    evidence,
    ranking_terms
)

summary = summarize_results(mission, evidence)

print()
print("Wingman's Summary")
print(summary)

if evidence:
    print()
    print("Supporting Sources")

    for item in evidence:
        print(f"[{item['source']}]")

        if item["location"]:
            print(item["location"])

        print(f"- {item['text']}")
        print()

show_completion(mission)