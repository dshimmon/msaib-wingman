# MSAIB Wingman
# Main application entry point

from interface import get_mission, show_header, show_result
from knowledge import load_topics


show_header()

mission = get_mission()
normalized_mission = mission.lower()

topics = load_topics()
course = topics.get(normalized_mission)

show_result(mission, course)