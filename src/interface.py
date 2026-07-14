def show_header():
    print("=" * 40)
    print("        MSAIB WINGMAN")
    print("=" * 40)
    print()
    print("Welcome aboard, Maverick.")
    print()


def get_mission():
    return input("What is today's mission? ")


def show_result(mission, course):
    print()
    print(f"Topic identified: {mission}")

    if course:
        print(f"Likely course: {course}")
    else:
        print("Course unknown.")
        print("Future versions of Wingman will search all course materials.")

    print()
    print(f"Mission '{mission}' acknowledged.")
    print(f"Preparing for: {mission}")
    print()
    print("Wingman standing by.")