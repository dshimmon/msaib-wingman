# MSAIB Wingman
# Main application entry point

from interface import get_mission, show_completion, show_header, show_topic
from reasoning import summarize_results
from retrieval_pipeline import retrieve_question_evidence


show_header()

mission = get_mission()

show_topic(mission)

query_plan, evidence = retrieve_question_evidence(mission)

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