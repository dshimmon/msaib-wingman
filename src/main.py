# MSAIB Wingman
# Main application entry point

from interface import get_mission, show_completion, show_header, show_topic
from knowledge import search_notes
from reasoning import summarize_results


show_header()

mission = get_mission()
normalized_mission = mission.lower()

show_topic(mission)

results = search_notes(normalized_mission)
summary = summarize_results(mission, results)

print()
print("Wingman's Summary")
print(summary)

if results:
    print()
    print("Sources")

    for source, result in results:
        print(f"[{source}]")
        print(f"- {result}")
        print()

show_completion(mission)