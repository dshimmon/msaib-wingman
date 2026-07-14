# MSAIB Wingman
# Main application entry point

import json

print("=" * 40)
print("        MSAIB WINGMAN")
print("=" * 40)
print()

print("Welcome aboard, Maverick.")
print()

mission = input("What is today's mission? ")
normalized_mission = mission.lower()

with open("data/topics.json", "r") as file:
    topics = json.load(file)

print()

print(f"Topic identified: {mission}")

if normalized_mission in topics:
    print(f"Likely course: {topics[normalized_mission]}")
else:
    print("Course unknown.")
    print("Future versions of Wingman will search all course materials.")

print()
print(f"Mission '{mission}' acknowledged.")
print(f"Preparing for: {mission}")
print()
print("Wingman standing by.")