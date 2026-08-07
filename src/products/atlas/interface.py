from wingman.shared.product_contract import ProductContext


def show_header(configuration=None):
    product = (
        configuration.product
        if isinstance(configuration, ProductContext)
        else configuration
    )
    title = (
        product.terminal_title
        if product is not None
        else "MSAIB WINGMAN"
    )
    welcome = (
        product.terminal_welcome
        if product is not None
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
