import tempfile
import unittest
from pathlib import Path

from app.config.presentation import RunHistoryConfig
from app.domain.pipeline import PipelineResult, PipelineRunState, RunStatus, RuntimeState
from app.presentation.run_history_store import RunHistoryStore


def _build_result(started_at: str) -> PipelineResult:
    state = PipelineRunState(
        status=RunStatus.COMPLETED,
        runtime=RuntimeState(started_at=started_at, finished_at=started_at, elapsed_seconds=1.0),
    )
    return PipelineResult(
        run_state=state,
        request_payload={"query": "iphone"},
        ranked_posts=[{"id": 1}],
        presented_results={"total_results": 1},
    )


class RunHistoryStoreTests(unittest.TestCase):
    def test_save_and_load_sorted_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            history_file = Path(tmp) / "run_history.json"
            store = RunHistoryStore(config=RunHistoryConfig(history_file_path=str(history_file), max_saved_runs=10))

            store.save_run(_build_result("2026-03-24T10:00:00+00:00"))
            store.save_run(_build_result("2026-03-24T11:00:00+00:00"))

            runs = store.load_runs()
            self.assertEqual(len(runs), 2)
            self.assertGreaterEqual(runs[0].get("saved_at", ""), runs[1].get("saved_at", ""))

            first_id = runs[0]["run_id"]
            self.assertIsNotNone(store.load_run(first_id))

    def test_bad_history_payload_falls_back_to_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            history_file = Path(tmp) / "run_history.json"
            history_file.write_text("{broken-json", encoding="utf-8")

            store = RunHistoryStore(config=RunHistoryConfig(history_file_path=str(history_file), max_saved_runs=10))
            self.assertEqual(store.load_runs(), [])

    def test_save_run_raises_on_non_serializable_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            history_file = Path(tmp) / "run_history.json"
            store = RunHistoryStore(
                config=RunHistoryConfig(
                    history_file_path=str(history_file), max_saved_runs=10
                )
            )

            result = _build_result("2026-03-24T12:00:00+00:00")
            result.presented_results = {"bad": object()}

            with self.assertRaises(ValueError):
                store.save_run(result)

    def test_get_checked_post_urls_returns_urls_from_saved_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            history_file = Path(tmp) / "run_history.json"
            store = RunHistoryStore(
                config=RunHistoryConfig(
                    history_file_path=str(history_file), max_saved_runs=10
                )
            )

            result = _build_result("2026-03-24T12:00:00+00:00")
            result.ranked_posts = [
                {
                    "post": {
                        "url": "https://www.facebook.com/groups/1/posts/2",
                        "post_url": "",
                    }
                },
                {
                    "post": {
                        "url": "",
                        "post_url": "https://www.facebook.com/groups/3/posts/4",
                    }
                },
            ]
            store.save_run(result)

            urls = store.get_checked_post_urls()
            self.assertIn("https://www.facebook.com/groups/1/posts/2", urls)
            self.assertIn("https://www.facebook.com/groups/3/posts/4", urls)


if __name__ == "__main__":
    unittest.main()
