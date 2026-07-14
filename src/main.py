# MSAIB Wingman
# Main application entry point

print("=" * 40)
print("        MSAIB WINGMAN")
print("=" * 40)
print()

print("Welcome aboard, Maverick.")
print()

mission = input("What is today's mission? ")
normalized_mission = mission.lower()

topics = {"python": "Programming", "regression": "Managerial Statistics"}

print()

if normalized_mission in topics:
    print(f"Topic identified: {mission}")
    print(f"Likely course: {topics[normalized_mission]}")
else:
    print(f"Topic identified: {mission}")
    print("Course unknown.")
    print("Future versions of Wingman will search all course materials.")

print()
print(f"Mission '{mission}' acknowledged.")
print(f"Preparing for: {mission}")
print()
print("Wingman standing by.")