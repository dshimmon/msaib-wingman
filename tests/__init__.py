"""Wingman repository test packages."""

import os


OFFLINE_OPENAI_API_KEY = "wingman-offline-tests-no-credential"

# Some production modules construct the shared client during import. Give the
# test package a clearly fake credential before discovery imports those modules,
# while preserving any value explicitly supplied by the caller.
os.environ.setdefault("PYTHON_DOTENV_DISABLED", "1")
os.environ.setdefault("OPENAI_API_KEY", OFFLINE_OPENAI_API_KEY)
