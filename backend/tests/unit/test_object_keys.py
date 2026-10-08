"""Object keys never keep a client-supplied path."""

import pytest

from app.storage.keys import UnsafeFilenameError, build_object_key, sanitize_filename


def test_path_traversal_is_reduced_to_a_filename() -> None:
    key, safe = build_object_key("abc123", "../../etc/passwd")

    assert safe == "passwd"
    assert key == f"documents/abc123/{safe}"
    assert ".." not in key
    assert key.count("/") == 2


def test_windows_and_nested_paths_keep_only_the_last_segment() -> None:
    assert sanitize_filename(r"..\\..\\secret.txt") == "secret.txt"
    assert sanitize_filename("folder/my notes.txt") == "my_notes.txt"


def test_empty_and_dot_names_are_rejected() -> None:
    for name in (None, "", ".", "..", "///", "..."):
        with pytest.raises(UnsafeFilenameError):
            sanitize_filename(name)


def test_document_id_cannot_add_a_directory() -> None:
    with pytest.raises(UnsafeFilenameError):
        build_object_key("../escape", "notes.txt")
