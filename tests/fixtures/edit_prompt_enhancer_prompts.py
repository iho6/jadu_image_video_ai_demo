"""Representative prompts for the edit prompt enhancer tests."""

from __future__ import annotations

PROMPTS: list[str] = [
    # Add / insert
    "Add a light-gray cat in the bottom-right corner, sitting and facing the camera.",
    # Replace
    "Replace the mug with a clear glass bottle on the same table position.",
    # Delete
    "Remove the person in the background; keep the foreground subject unchanged.",
    # Text editing
    "Replace the sign text with \"OPEN 24/7\".",
    # Human/ID edit
    "Make the person smile subtly; keep identity, hairstyle, and outfit unchanged.",
    # Style conversion
    "Convert the image to watercolor style; preserve composition and subject identity.",
    # Lighting / color / enhancement
    "Enhance detail and lighting while preserving the subject's identity and pose.",
    # Vague (formatter-only)
    "Make it better.",
]

