def join_nonblank_parts(parts, separator: str = " ") -> str:
    cleaned_parts = []
    for part in parts:
        if part is None:
            continue

        cleaned = str(part).strip()
        if cleaned:
            cleaned_parts.append(cleaned)

    return separator.join(cleaned_parts)


def append_note_if_present(note_parts: list, label: str, value) -> None:
    if value is None:
        return

    cleaned = str(value).strip()
    if cleaned:
        note_parts.append(f"{label}: {cleaned}")


def build_clinical_notes(note_parts: list) -> str:
    return "\n".join(part for part in note_parts if part)
