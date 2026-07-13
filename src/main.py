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

print()

if normalized_mission == "python":
    print("Topic identified: Python")
    print("Likely course: Programming")

elif normalized_mission == "regression":
    print("Topic identified: Regression")
    print("Likely course: Managerial Statistics")

else:
    print(f"Topic identified: {mission}")
    print("Course unknown.")
    print("Future versions of Wingman will search all course materials.")

print()
print(f"Mission '{mission}' acknowledged.")
print(f"Preparing for: {mission}")
print()
print("Wingman standing by.")