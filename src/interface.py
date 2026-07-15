def show_header():
    print("=" * 40)
    print("        MSAIB WINGMAN")
    print("=" * 40)
    print()
    print("Welcome aboard, Maverick.")
    print()


def get_mission():
    return input("What is today's mission? ")


def show_topic(mission):
    print()
    print(f"Topic confirmed: {mission}")


def show_completion(mission):
    print()
    print(f"Mission '{mission}' complete.")
    print("Wingman standing by.")