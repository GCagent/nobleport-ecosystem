from core.gateway import compression


def test_roundtrip_small_object():
    obj = {"a": 1, "b": "two"}
    assert compression.unpack(compression.pack(obj)) == obj


def test_roundtrip_large_object_compresses():
    obj = {"items": ["repeat" for _ in range(500)]}
    st = compression.stats(obj)
    assert st.compressed is True
    assert st.packet_bytes < st.raw_bytes
    assert st.ratio < 1.0
    assert compression.unpack(compression.pack(obj)) == obj


def test_small_payload_stored_raw():
    st = compression.stats({"x": 1})
    assert st.compressed is False  # below threshold, no zlib overhead


def test_b64_roundtrip_for_redis():
    obj = {"findings": list(range(300))}
    text = compression.pack_b64(obj)
    assert isinstance(text, str)
    assert compression.unpack_b64(text) == obj


def test_rejects_foreign_bytes():
    import pytest
    with pytest.raises(ValueError):
        compression.unpack(b"NOTAPACKETxxxx")


def test_saved_bytes_non_negative():
    st = compression.stats({"k": "v" * 1000})
    assert st.saved_bytes >= 0
