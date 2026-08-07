def resolve_section(heading, current_section):
    """
    Determines whether a heading begins a new section.
    """

    if not heading:
        return current_section

    return heading