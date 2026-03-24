import json
from pathlib import Path

from app.logic.saved_searches import SavedSearchStore
from app.models.input_models import RawSearchInput


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_store(tmp_path: Path) -> SavedSearchStore:
    return SavedSearchStore(file_path=str(tmp_path / "searches.json"))


def _minimal_raw_input(main_text: str = "iPhone") -> RawSearchInput:
    return RawSearchInput(
        main_text=main_text,
        all_country=True,
        group_sources=["user_groups"],
    )


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------


class TestSavedSearchStoreInit:
    def test_creates_file_when_missing(self, tmp_path: Path):
        _make_store(tmp_path)
        storage_file = tmp_path / "searches.json"
        assert storage_file.exists()

    def test_new_file_contains_empty_list(self, tmp_path: Path):
        _make_store(tmp_path)
        storage_file = tmp_path / "searches.json"
        content = json.loads(storage_file.read_text(encoding="utf-8"))
        assert content == []

    def test_creates_parent_directory(self, tmp_path: Path):
        nested_path = tmp_path / "deep" / "dir" / "searches.json"
        SavedSearchStore(file_path=str(nested_path))
        assert nested_path.exists()


# ---------------------------------------------------------------------------
# load_previous_searches
# ---------------------------------------------------------------------------


class TestLoadPreviousSearches:
    def test_empty_file_returns_empty_list(self, tmp_path: Path):
        store = _make_store(tmp_path)
        result = store.load_previous_searches()
        assert result == []

    def test_loads_valid_saved_search(self, tmp_path: Path):
        store = _make_store(tmp_path)
        raw = _minimal_raw_input("MacBook")
        store.save_search("My Search", raw)

        loaded = store.load_previous_searches()
        assert len(loaded) == 1
        assert loaded[0].name == "My Search"
        assert loaded[0].input_payload["main_text"] == "MacBook"

    def test_loads_multiple_searches_in_insertion_order(self, tmp_path: Path):
        store = _make_store(tmp_path)
        store.save_search("Search A", _minimal_raw_input("iPhone"))
        store.save_search("Search B", _minimal_raw_input("iPad"))

        loaded = store.load_previous_searches()
        assert len(loaded) == 2
        assert loaded[0].name == "Search A"
        assert loaded[1].name == "Search B"

    def test_skips_invalid_records(self, tmp_path: Path):
        storage_file = tmp_path / "searches.json"
        storage_file.write_text(
            json.dumps(
                [
                    {
                        "name": "Good",
                        "created_at": "2024-01-01T00:00:00+00:00",
                        "input_payload": {},
                    },
                    {
                        "name": 123,
                        "created_at": "invalid",
                        "input_payload": "not_a_dict",
                    },
                ]
            ),
            encoding="utf-8",
        )
        store = SavedSearchStore(file_path=str(storage_file))
        loaded = store.load_previous_searches()
        assert len(loaded) == 1
        assert loaded[0].name == "Good"

    def test_non_list_json_returns_empty_list(self, tmp_path: Path):
        storage_file = tmp_path / "searches.json"
        storage_file.write_text(json.dumps({"not": "a list"}), encoding="utf-8")
        store = SavedSearchStore(file_path=str(storage_file))
        result = store.load_previous_searches()
        assert result == []

    def test_invalid_json_returns_empty_list(self, tmp_path: Path):
        storage_file = tmp_path / "searches.json"
        storage_file.write_text("this is not json {{{{", encoding="utf-8")
        store = SavedSearchStore(file_path=str(storage_file))
        result = store.load_previous_searches()
        assert result == []

    def test_empty_content_returns_empty_list(self, tmp_path: Path):
        storage_file = tmp_path / "searches.json"
        storage_file.write_text("", encoding="utf-8")
        store = SavedSearchStore(file_path=str(storage_file))
        result = store.load_previous_searches()
        assert result == []


# ---------------------------------------------------------------------------
# save_search
# ---------------------------------------------------------------------------


class TestSaveSearch:
    def test_save_returns_saved_search_with_name(self, tmp_path: Path):
        store = _make_store(tmp_path)
        saved = store.save_search("Best Search", _minimal_raw_input())
        assert saved.name == "Best Search"

    def test_saved_search_has_utc_timestamp(self, tmp_path: Path):
        store = _make_store(tmp_path)
        saved = store.save_search("Timestamped", _minimal_raw_input())
        assert "+00:00" in saved.created_at or "Z" in saved.created_at

    def test_save_strips_search_name(self, tmp_path: Path):
        store = _make_store(tmp_path)
        saved = store.save_search("  Padded Name  ", _minimal_raw_input())
        assert saved.name == "Padded Name"

    def test_saved_search_persisted_to_file(self, tmp_path: Path):
        store = _make_store(tmp_path)
        store.save_search("Persist Test", _minimal_raw_input("Galaxy"))

        # Reload from disk
        store2 = _make_store(tmp_path)
        loaded = store2.load_previous_searches()
        assert len(loaded) == 1
        assert loaded[0].name == "Persist Test"

    def test_multiple_saves_accumulate(self, tmp_path: Path):
        store = _make_store(tmp_path)
        store.save_search("First", _minimal_raw_input("iPhone"))
        store.save_search("Second", _minimal_raw_input("iPad"))
        store.save_search("Third", _minimal_raw_input("Mac"))

        loaded = store.load_previous_searches()
        assert len(loaded) == 3

    def test_save_stores_all_raw_input_fields(self, tmp_path: Path):
        store = _make_store(tmp_path)
        raw = RawSearchInput(
            main_text="Laptop",
            tags=["dell", "gaming"],
            min_price=500.0,
            max_price=2000.0,
            all_country=True,
            group_sources=["user_groups"],
        )
        store.save_search("Laptop Search", raw)

        loaded = store.load_previous_searches()
        payload = loaded[0].input_payload
        assert payload["main_text"] == "Laptop"
        assert payload["tags"] == ["dell", "gaming"]
        assert payload["min_price"] == 500.0
        assert payload["max_price"] == 2000.0
