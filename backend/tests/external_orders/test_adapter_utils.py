import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")


def test_join_nonblank_parts_strips_skips_blank_and_joins():
    from app.external_orders.adapters.utils import join_nonblank_parts

    assert join_nonblank_parts(["  Maria ", None, "", " Garcia "]) == "Maria Garcia"
    assert join_nonblank_parts(["600mg", " Every 6 Months "], separator="; ") == "600mg; Every 6 Months"


def test_append_note_if_present_appends_labeled_nonblank_value_only():
    from app.external_orders.adapters.utils import append_note_if_present

    note_parts = []

    append_note_if_present(note_parts, "Facility", " HF_WEST ")
    append_note_if_present(note_parts, "NDC", " ")
    append_note_if_present(note_parts, "Weight", None)

    assert note_parts == ["Facility: HF_WEST"]


def test_build_clinical_notes_joins_existing_parts_with_newlines():
    from app.external_orders.adapters.utils import build_clinical_notes

    assert build_clinical_notes(["first", "", None, "second"]) == "first\nsecond"
