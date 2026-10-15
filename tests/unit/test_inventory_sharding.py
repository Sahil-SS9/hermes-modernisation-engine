from hermes_modernisation.store import Store


def test_large_inventory_is_sharded_not_silently_dropped(tmp_path):
    store = Store(tmp_path / "private")
    assessment = {
        "source_digest": "a" * 64,
        "file_count": 1,
        "symbols": [
            {
                "path": "a.py",
                "line": index + 1,
                "name": "function",
                "kind": "FunctionDef",
            }
            for index in range(6000)
        ],
    }
    first = store.create("one", "/repo", "upgrade", assessment)
    assert first["assessment"]["detail_counts"]["symbols"] == 6000
    assert "symbols" not in first["assessment"]
    page = store.details(first["job_id"], "symbols", 59)
    assert len(page["items"]) == 100 and page["items"][-1]["line"] == 6000
    assert page["has_more"] is False
    assert store.details(first["job_id"], "symbols", 0)["has_more"] is True
    assert Store(tmp_path / "private").get(first["job_id"]) == first
    assert store.create("one", "/repo", "upgrade", assessment) == first
