def show_header(configuration=None):
    title = (
        configuration.terminal_title
        if configuration is not None
        else "MSAIB WINGMAN"
    )
    welcome = (
        configuration.terminal_welcome
        if configuration is not None
        else "Welcome aboard, Maverick."
    )

    print("=" * 40)
    print(f"        {title}")
    print("=" * 40)
    print()
    print(welcome)
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
