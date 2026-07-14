# MSAIB Wingman
# Main application entry point

from interface import get_mission, show_header, show_result
from knowledge import load_topics, search_notes
from reasoning import summarize_results

show_header()

mission = get_mission()
normalized_mission = mission.lower()

topics = load_topics()
course = topics.get(normalized_mission)

show_result(mission, course)

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