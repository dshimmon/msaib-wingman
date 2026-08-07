"""Atlas terminal application."""

from interface import (
    get_mission,
    show_completion,
    show_header,
    show_topic,
)
from product_config import create_atlas_context
from wingman_service import ask_wingman


def main():
    product_context = create_atlas_context()
    show_header(product_context)

    mission = get_mission()
    show_topic(mission)
    result = ask_wingman(
        mission,
        product_context=product_context,
    )

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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
