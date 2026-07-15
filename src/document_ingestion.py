import json
from pathlib import Path

from pptx import Presentation


def extract_powerpoint_chunks(file_path, domain):
    presentation = Presentation(file_path)
    chunks = []

    for slide_number, slide in enumerate(presentation.slides, start=1):
        slide_text = []

        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text.strip():
                slide_text.append(shape.text.strip())

        combined_text = "\n".join(slide_text)

        if combined_text:
            chunks.append(
                {
                    "document": Path(file_path).stem,
                    "domain": domain,
                    "slide": slide_number,
                    "text": combined_text,
                }
            )

    return chunks


def save_chunks(chunks, output_path):
    with open(output_path, "w") as file:
        json.dump(chunks, file, indent=2)


if __name__ == "__main__":
    chunks = extract_powerpoint_chunks(
        "data/documents/onboarding/msaib-onboarding-2026.pptx",
        "Onboarding"
    )

    save_chunks(
        chunks,
        "data/documents/onboarding/msaib-onboarding-2026.json"
    )

    print(f"Saved {len(chunks)} chunks.")