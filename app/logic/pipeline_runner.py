from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Dict, List, Optional

from app.ai.ai_analyzer import AIAnalyzer
from app.logic.initial_filter import InitialFilter
from app.logic.input_service import InputService
from app.logic.logic_analyzer import LogicAnalyzer
from app.models.input_models import SearchRequest
from app.models.pipeline_models import (
    PipelineOptions,
    PipelineResult,
    PipelineRunState,
    ProgressState,
    RunStatus,
    RuntimeState,
    StageResult,
    StageStatus,
)
from app.scoring.ranker import PostRanker
from app.scraper.search_scraper import SearchScraper
from app.ui.result_presenter import ResultPresenter
from app.ui.run_history_store import RunHistoryStore
from app.utils.logger import get_logger, log_event


logger = get_logger(__name__)


class PipelineRunner:
    STAGES = [
        "receive_user_input",
        "search_posts",
        "initial_filtering",
        "open_post",
        "collect_data",
        "logic_analysis",
        "ai_analysis",
        "ranking",
        "present_results",
    ]

    def __init__(self, input_service: Optional[InputService] = None) -> None:
        self._input_service = input_service or InputService()
        self._scraper = SearchScraper()
        self._filter = InitialFilter()
        self._logic_analyzer = LogicAnalyzer()
        self._ai_analyzer = AIAnalyzer()
        self._ranker = PostRanker()
        self._presenter = ResultPresenter()
        self._history_store = RunHistoryStore()

    def run(
        self,
        raw_user_input: Dict[str, Any],
        options: Optional[PipelineOptions] = None,
    ) -> PipelineResult:
        opts = options or PipelineOptions()
        result: Optional[PipelineResult] = None
        post_error_messages: List[str] = []
        run_state = PipelineRunState(
            status=RunStatus.RUNNING,
            progress=ProgressState(total_stages=len(self.STAGES), max_posts=opts.max_posts),
            runtime=RuntimeState(started_at=_utc_now_iso()),
        )

        log_event(
            logger,
            20,
            "pipeline_started",
            max_posts=opts.max_posts,
            continue_on_post_error=opts.continue_on_post_error,
            stop_after_post_errors=opts.stop_after_post_errors,
        )

        if hasattr(self._logic_analyzer, "reset_session"):
            self._logic_analyzer.reset_session()

        start = perf_counter()

        try:
            request = self._stage_receive_user_input(raw_user_input, run_state)
            posts = self._stage_search_posts(request, opts, run_state)
            filtered_posts = self._stage_initial_filter(posts, request, run_state)

            post_processing, post_error_messages = self._stage_process_posts(filtered_posts, request, opts, run_state)

            ranked_posts = self._stage_ranking(post_processing, run_state)
            presented = self._stage_present_results(ranked_posts, run_state)
            presented["pipeline_notices"] = self._build_pipeline_notices(
                run_state=run_state,
                post_error_messages=post_error_messages,
            )

            if run_state.status != RunStatus.STOPPED:
                run_state.status = RunStatus.COMPLETED
            result = PipelineResult(
                run_state=run_state,
                request_payload=request.to_dict(),
                ranked_posts=ranked_posts,
                presented_results=presented,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Pipeline failed")
            log_event(logger, 40, "pipeline_failed", error=str(exc))
            run_state.status = RunStatus.FAILED
            run_state.stop_reason = str(exc)
            run_state.add_stage_result(
                StageResult(
                    stage_name=run_state.progress.current_stage or "pipeline",
                    status=StageStatus.FAILED,
                    errors=[str(exc)],
                )
            )
            result = PipelineResult(run_state=run_state)
        finally:
            elapsed = perf_counter() - start
            run_state.runtime.finished_at = _utc_now_iso()
            run_state.runtime.elapsed_seconds = round(elapsed, 3)

            if result is not None:
                try:
                    self._history_store.save_run(result)
                    if isinstance(result.presented_results, dict):
                        notices = result.presented_results.setdefault("pipeline_notices", [])
                        notices.append("run_history_saved")
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Failed to save run history: %s", str(exc))
                    if isinstance(result.presented_results, dict):
                        notices = result.presented_results.setdefault("pipeline_notices", [])
                        notices.append(f"run_history_save_failed:{str(exc)}")

            log_event(
                logger,
                20,
                "pipeline_finished",
                status=run_state.status.value,
                processed_posts=run_state.progress.processed_posts,
                stop_reason=run_state.stop_reason,
                elapsed_seconds=run_state.runtime.elapsed_seconds,
            )

        return result if result is not None else PipelineResult(run_state=run_state)

    def load_previous_runs(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        return self._history_store.load_runs(limit=limit)

    def load_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        return self._history_store.load_run(run_id=run_id)

    def _stage_receive_user_input(
        self,
        raw_user_input: Dict[str, Any],
        run_state: PipelineRunState,
    ) -> SearchRequest:
        run_state.progress.current_stage = "receive_user_input"
        request, errors = self._input_service.validate_and_build(raw_user_input)
        if errors or request is None:
            message = "; ".join([f"{item['field']}: {item['message']}" for item in errors])
            raise ValueError(f"input_validation_failed: {message}")

        self._mark_stage_success(
            run_state,
            stage_name="receive_user_input",
            details={"query": request.query_text},
        )
        return request

    def _stage_search_posts(
        self,
        request: SearchRequest,
        options: PipelineOptions,
        run_state: PipelineRunState,
    ) -> List[Dict[str, Any]]:
        run_state.progress.current_stage = "search_posts"
        posts = self._scraper.search_posts(request, max_posts=options.max_posts)

        self._mark_stage_success(
            run_state,
            stage_name="search_posts",
            details={"found": len(posts), "max_posts": options.max_posts},
        )
        return posts

    def _stage_initial_filter(
        self,
        posts: List[Dict[str, Any]],
        request: SearchRequest,
        run_state: PipelineRunState,
    ) -> List[Dict[str, Any]]:
        run_state.progress.current_stage = "initial_filtering"
        filtered = self._filter.filter_posts(posts, request)

        self._mark_stage_success(
            run_state,
            stage_name="initial_filtering",
            details={"before": len(posts), "after": len(filtered)},
        )
        return filtered

    def _stage_process_posts(
        self,
        posts: List[Dict[str, Any]],
        request: SearchRequest,
        options: PipelineOptions,
        run_state: PipelineRunState,
    ) -> tuple[List[Dict[str, Any]], List[str]]:
        processed: List[Dict[str, Any]] = []
        post_errors = 0
        post_error_messages: List[str] = []

        open_success = 0
        collect_success = 0
        logic_success = 0
        ai_success = 0

        for index, post in enumerate(posts[: options.max_posts]):
            if self._should_stop(options, run_state, post_errors):
                run_state.status = RunStatus.STOPPED
                if run_state.stop_reason is None:
                    run_state.stop_reason = "stop_condition_reached"
                break

            run_state.progress.processed_posts = index + 1

            try:
                opened = self._scraper.open_post(post)
                open_success += 1

                collected = self._scraper.collect_post_data(opened)
                collect_success += 1

                logic_analysis = self._logic_analyzer.analyze(collected, request)
                logic_success += 1

                ai_analysis = self._ai_analyzer.analyze(collected, request)
                ai_success += 1

                processed.append(
                    {
                        "post": collected,
                        "logic_analysis": logic_analysis,
                        "ai_analysis": ai_analysis,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                post_errors += 1
                message = f"post_index={index} error={str(exc)}"
                post_error_messages.append(message)
                log_event(logger, 30, "post_processing_error", index=index, error=str(exc))

                if not options.continue_on_post_error:
                    run_state.status = RunStatus.STOPPED
                    run_state.stop_reason = "post_error_and_continue_disabled"
                    break

        self._mark_stage_success(
            run_state,
            stage_name="open_post",
            details={"successful": open_success, "attempted": run_state.progress.processed_posts},
        )
        self._mark_stage_success(
            run_state,
            stage_name="collect_data",
            details={"successful": collect_success, "attempted": run_state.progress.processed_posts},
        )
        self._mark_stage_success(
            run_state,
            stage_name="logic_analysis",
            details={"successful": logic_success, "attempted": run_state.progress.processed_posts},
        )
        self._mark_stage_success(
            run_state,
            stage_name="ai_analysis",
            details={"successful": ai_success, "attempted": run_state.progress.processed_posts},
        )

        return processed, post_error_messages

    def _build_pipeline_notices(
        self,
        run_state: PipelineRunState,
        post_error_messages: List[str],
    ) -> List[str]:
        notices: List[str] = []
        if post_error_messages:
            notices.append(f"non_fatal_post_errors={len(post_error_messages)}")
            notices.extend(post_error_messages[:5])

        if run_state.stop_reason:
            notices.append(f"stop_reason={run_state.stop_reason}")

        return notices

    def _stage_ranking(
        self,
        processed_posts: List[Dict[str, Any]],
        run_state: PipelineRunState,
    ) -> List[Dict[str, Any]]:
        run_state.progress.current_stage = "ranking"
        ranked = self._ranker.rank(processed_posts)
        self._mark_stage_success(
            run_state,
            stage_name="ranking",
            details={"ranked": len(ranked)},
        )
        return ranked

    def _stage_present_results(
        self,
        ranked_posts: List[Dict[str, Any]],
        run_state: PipelineRunState,
    ) -> Dict[str, Any]:
        run_state.progress.current_stage = "present_results"
        presented = self._presenter.present(ranked_posts)
        self._mark_stage_success(
            run_state,
            stage_name="present_results",
            details={"top_results": len(presented.get('top_results', []))},
        )
        return presented

    def _mark_stage_success(
        self,
        run_state: PipelineRunState,
        stage_name: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        run_state.add_stage_result(
            StageResult(
                stage_name=stage_name,
                status=StageStatus.SUCCESS,
                details=details or {},
            )
        )
        run_state.progress.completed_stages += 1
        run_state.progress.current_stage = stage_name
        run_state.progress.update_stage_progress()

    def _should_stop(
        self,
        options: PipelineOptions,
        run_state: PipelineRunState,
        post_errors: int,
    ) -> bool:
        if run_state.progress.processed_posts >= options.max_posts:
            run_state.stop_reason = "max_posts_reached"
            return True

        if options.stop_after_post_errors is not None and post_errors >= options.stop_after_post_errors:
            run_state.stop_reason = "post_error_limit_reached"
            return True

        return False


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
