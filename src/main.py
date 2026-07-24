# MSAIB Wingman
# Main application entry point

from interface import (
    get_mission,
    show_completion,
    show_header,
    show_topic,
)
from wingman_service import ask_wingman


show_header()

mission = get_mission()

show_topic(mission)

result = ask_wingman(mission)

print()
print("Wingman's Summary")
print(result["answer"])

if result["evidence"]:
    print()
    print("Supporting Sources")

    for item in result["evidence"]:
        print(f"[{item['source']}]")

        if item["location"]:
            print(item["location"])

        print(f"- {item['text']}")
        print()

show_completion(mission)