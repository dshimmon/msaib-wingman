# MSAIB Wingman
# Main application entry point

from interface import get_mission, show_completion, show_header, show_topic
from knowledge import retrieve_evidence
from reasoning import summarize_results


show_header()

mission = get_mission()
normalized_mission = mission.lower()

show_topic(mission)

evidence = retrieve_evidence(normalized_mission)
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