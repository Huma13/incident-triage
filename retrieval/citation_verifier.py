"""Validate citations against the local incident-triage corpus."""

import os
import re
from pathlib import Path


CORPUS_DIR = Path(os.getenv("CORPUS_DIR", "/app/corpus")).resolve()


def normalize(text: str) -> str:
    """Normalize whitespace and case for reliable text comparison."""
    return " ".join(text.casefold().split())


def extract_section(document: str, section_name: str):
    """Return the content of an exact Markdown heading and its section."""
    lines = document.splitlines()
    target = section_name.strip().casefold()

    for index, line in enumerate(lines):
        match = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if not match:
            continue

        level = len(match.group(1))
        heading = match.group(2).strip().casefold()

        if heading != target:
            continue

        section_lines = []

        for following_line in lines[index + 1:]:
            next_heading = re.match(r"^(#{1,6})\s+", following_line)

            if next_heading and len(next_heading.group(1)) <= level:
                break

            section_lines.append(following_line)

        return "\n".join(section_lines).strip()

    return None


def verify_citation(source_id: str, section: str, evidence: str) -> dict:
    """Verify that a source, heading, and supporting passage exist."""

    if not all(isinstance(value, str) and value.strip()
               for value in (source_id, section, evidence)):
        return {"valid": False, "reason": "Citation fields must be non-empty strings."}

    relative_path = Path(source_id)

    if relative_path.is_absolute() or ".." in relative_path.parts:
        return {"valid": False, "reason": "Invalid citation path."}

    source_path = (CORPUS_DIR / relative_path).resolve()

    if not source_path.is_relative_to(CORPUS_DIR):
        return {"valid": False, "reason": "Citation path escapes the corpus."}

    if not source_path.is_file() or source_path.suffix.lower() != ".md":
        return {"valid": False, "reason": "Citation source does not exist in the Markdown corpus."}

    document = source_path.read_text(encoding="utf-8")
    section_text = extract_section(document, section)

    if section_text is None:
        return {"valid": False, "reason": "Cited section heading was not found."}

    evidence_to_check = evidence.strip()
    first_line, separator, remaining = evidence_to_check.partition("\n")

    heading_match = re.match(
        r"^#{1,6}\s+(.+?)\s*#*\s*$",
        first_line,
    )

    if (
        heading_match
        and heading_match.group(1).strip().casefold()
        == section.strip().casefold()
    ):
        evidence_to_check = remaining.strip()

    if (
        not evidence_to_check
        or normalize(evidence_to_check) not in normalize(section_text)
    ):
        return {
            "valid": False,
            "reason": "Supporting evidence was not found in the cited section."
        }

    return {
        "valid": True,
        "source_id": relative_path.as_posix(),
        "section": section,
        "reason": "Source, section, and supporting evidence verified."
    }
