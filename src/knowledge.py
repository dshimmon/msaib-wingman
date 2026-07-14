import json


def load_topics():
    with open("data/topics.json", "r") as file:
        return json.load(file)