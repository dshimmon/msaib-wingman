def summarize_results(topic, results):
    if not results:
        return (
            f"I couldn't find any notes related to '{topic}'. "
            "Try another topic or expand the knowledge base."
        )

    return (
        f"I found {len(results)} relevant note(s) about '{topic}'. "
        "These notes may help you understand the topic before reviewing the original material."
    )