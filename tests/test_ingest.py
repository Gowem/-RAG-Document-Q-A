import os
import tempfile
import pytest



# ── Test: document loading ────────────────────────────────────

def test_load_txt_file():
    """TXT files should load and chunk correctly."""
    # Import inline to avoid side effects at collection time
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False, encoding="utf-8") as f:
        f.write("Hello world. " * 100)
        tmp_path = f.name

    try:
        from app import load_and_chunk
        chunks = load_and_chunk(tmp_path, "test.txt")
        assert len(chunks) > 0
        assert all(hasattr(c, "page_content") for c in chunks)
        assert all(c.metadata["source_file"] == "test.txt" for c in chunks)
    finally:
        os.unlink(tmp_path)


def test_unsupported_file_type():
    """Unsupported file types should raise ValueError."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from app import load_and_chunk

    with pytest.raises(ValueError, match="Unsupported file type"):
        load_and_chunk("document.xyz", "document.xyz")


def test_chunk_metadata_set():
    """Each chunk should have source_file metadata."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from app import load_and_chunk

    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False, encoding="utf-8") as f:
        f.write("Test content. " * 50)
        tmp_path = f.name

    try:
        chunks = load_and_chunk(tmp_path, "myfile.txt")
        for chunk in chunks:
            assert chunk.metadata.get("source_file") == "myfile.txt"
    finally:
        os.unlink(tmp_path)


# ── Test: clear vectorstore ───────────────────────────────────

def test_clear_vectorstore_nonexistent_dir():
    """clear_vectorstore should not crash on empty/missing dir."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from app import clear_vectorstore, VECTORSTORE_DIR

    # Should run without raising even if dir is empty
    os.makedirs(VECTORSTORE_DIR, exist_ok=True)
    clear_vectorstore()  # no exception = pass
