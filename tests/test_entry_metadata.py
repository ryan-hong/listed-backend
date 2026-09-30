import json
import unittest

from pydantic import ValidationError

from listed_backend.models.list_entry import EntryType
from listed_backend.schemas.entry_metadata import METADATA_SCHEMAS, validate_metadata


class EntryMetadataTests(unittest.TestCase):
    def test_registry_covers_every_type_and_empty_metadata(self):
        self.assertEqual(set(METADATA_SCHEMAS), set(EntryType))
        for entry_type in EntryType:
            self.assertEqual(validate_metadata(entry_type, None), {})
            self.assertEqual(validate_metadata(entry_type, {}), {})

    def test_spec_examples(self):
        # Representative payloads for every built-in type.
        examples = {
            "RESTAURANT": {"cuisines": ["Italian"], "price_range": 2},
            "MOVIE": {"directors": ["Example Director"], "release_year": 2025, "runtime_minutes": 110},
            "PLACE": {"place_category": "museum", "latitude": 44.6488, "longitude": -63.5752},
            "MEAL": {"ingredients": ["200 g pasta"], "recipe": "Boil.\nServe.", "servings": 2, "prep_minutes": 0},
            "BOOK": {"authors": ["Example Author"], "isbn": "9780306406157", "page_count": 320},
            "TV_SHOW": {"release_year": 2022, "end_year": 2024, "season_count": 3},
            "VIDEO_GAME": {"developers": ["Example Studio"], "platforms": ["PC"]},
            "PODCAST": {"hosts": ["Example Host"], "feed_url": "https://example.com/feed.xml"},
            "EVENT": {"starts_at": "2027-06-12T22:00:00Z", "ends_at": "2027-06-13T00:00:00Z", "timezone": "America/Halifax"},
        }
        for entry_type, meta in examples.items():
            with self.subTest(entry_type=entry_type):
                self.assertEqual(validate_metadata(entry_type, meta), meta)

    def test_normalization(self):
        self.assertEqual(
            validate_metadata("MOVIE", {"directors": [" Alice ", "alice", "Bob"], "genres": [], "tags": [" Drama ", "DRAMA"], "description": None}),
            {"directors": ["Alice", "Bob"], "genres": [], "tags": ["Drama"]},
        )
        self.assertEqual(validate_metadata("BOOK", {"isbn": "0-8044-2957-x"}), {"isbn": "080442957X"})
        self.assertEqual(validate_metadata("BOOK", {"isbn": "978-0-306-40615-7"}), {"isbn": "9780306406157"})
        self.assertEqual(validate_metadata("EVENT", {"starts_at": "2027-06-12T19:00:00-03:00"}), {"starts_at": "2027-06-12T22:00:00Z"})

    def test_invalid_types_and_fields(self):
        invalid = [
            ("movie", {}), ("UNKNOWN", {}),
            ("MOVIE", {"unknown": None}), ("MOVIE", {"note": "experience"}),
            ("MOVIE", {"release_year": "2025"}), ("MOVIE", {"release_year": True}),
            ("MOVIE", {"release_year": 2025.0}), ("MOVIE", {"release_year": 0}),
            ("MOVIE", {"release_year": 10000}), ("MOVIE", {"runtime_minutes": 0}),
            ("MOVIE", {"genres": "Drama"}), ("MOVIE", {"genres": [" "]}),
            ("MOVIE", {"genres": ["x"] * 51}), ("MOVIE", {"genres": ["x" * 65]}),
            ("MOVIE", {"description": "x" * 10001}),
            ("MOVIE", {"website_url": "ftp://example.com"}),
            ("MOVIE", {"website_url": "/relative"}),
            ("MOVIE", {"website_url": "http:/example.com"}),
            ("PLACE", {"latitude": True, "longitude": 0}),
            ("PLACE", {"latitude": 91, "longitude": 0}),
            ("PLACE", {"latitude": 0, "longitude": -181}),
            ("RESTAURANT", {"price_range": 5}),
            ("MEAL", {"prep_minutes": -1}), ("MEAL", {"ingredients": ["x"] * 101}),
            ("MEAL", {"servings": 2147483648}),
            ("BOOK", {"isbn": "9780306406158"}), ("BOOK", {"isbn": "0804429570"}),
            ("EVENT", {"starts_at": "2027-06-12T19:00:00"}),
            ("EVENT", {"timezone": "Not/AZone"}),
        ]
        for entry_type, meta in invalid:
            with self.subTest(entry_type=entry_type, meta=meta):
                with self.assertRaises((ValidationError, ValueError)):
                    validate_metadata(entry_type, meta)

    def test_conditional_error_paths(self):
        invalid = [
            ("PLACE", {"latitude": 0}, "longitude"),
            ("PLACE", {"longitude": 0}, "latitude"),
            ("TV_SHOW", {"release_year": 2025, "end_year": 2024}, "end_year"),
            ("EVENT", {"ends_at": "2027-01-01T00:00:00Z"}, "starts_at"),
            ("EVENT", {"starts_at": "2027-01-02T00:00:00Z", "ends_at": "2027-01-01T00:00:00Z"}, "ends_at"),
        ]
        for entry_type, meta, field in invalid:
            with self.subTest(entry_type=entry_type):
                with self.assertRaises(ValidationError) as raised:
                    validate_metadata(entry_type, meta)
                self.assertEqual(raised.exception.errors()[0]["loc"], (field,))

    def test_custom_preserves_values_and_requires_json(self):
        meta = {" Mixed Key ": " value ", "tags": 42, "null": None, "nested": [{"boolean": True}]}
        self.assertEqual(validate_metadata("CUSTOM", meta), meta)
        for value in (float("nan"), float("inf"), {1: "value"}, ("tuple",), object()):
            with self.subTest(value=value):
                with self.assertRaises((ValidationError, ValueError)):
                    validate_metadata("CUSTOM", {"nested": value})
        for value in ([], "value", 1):
            with self.assertRaises(ValueError):
                validate_metadata("CUSTOM", value)

    def test_normalized_utf8_size_limit(self):
        # {"x":"..."} adds eight UTF-8 bytes.
        self.assertEqual(len(json.dumps({"x": "a" * 65528}, separators=(",", ":")).encode()), 65536)
        validate_metadata("CUSTOM", {"x": "a" * 65528})
        for text in ("a" * 65529, "é" * 32765):
            with self.assertRaises(ValueError):
                validate_metadata("CUSTOM", {"x": text})
        validate_metadata("MOVIE", {"description": " " * 70000 + "trimmed"})


if __name__ == "__main__":
    unittest.main()
