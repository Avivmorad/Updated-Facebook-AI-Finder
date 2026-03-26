from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Dict, List, Optional

from app.ai.ai_service import AIAnalysisService
from app.domain.input import UserQuery
from app.domain.pipeline import (
    PipelineOptions,
    PipelineResult,
    PipelineRunState,
    ProgressState,
    RunStatus,
    RuntimeState,
    StageResult,
    StageStatus,
)
from app.pipeline.query_service import QueryService
from app.pipeline.search_service import SearchService
from app.pipeline.time_filter import RecentPostFilter
from app.presentation.result_presenter import ResultPresenter
from app.presentation.run_history_store import RunHistoryStore
from app.ranking.ranker import PostRanker
from app.utils.logger import get_logger, log_event


logger = get_logger(__name__)


class PipelineRunner:
    STAGES = [
        "receive_user_input",
        "search_posts",
        "open_post",
        "collect_data",
        "time_filter",
        "ai_analysis",
        "ranking",
        "present_results",
    ]

    def __init__(self, query_service: Optional[QueryService] = None) -> None:
        self._query_service = query_service or QueryService()
        self._search_service = SearchService()
        self._time_filter = RecentPostFilter()
        self._ai_service = AIAnalysisService()
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

        log_event(logger, 20, "pipeline_started", max_posts=opts.max_posts)
        start = perf_counter()

        try:
            user_query = self._stage_receive_user_input(raw_user_input, run_state)
            posts = self._stage_search_posts(user_query, opts, run_state)
            relevant_posts, post_error_messages = self._stage_process_posts(posts, user_query, opts, run_state)
            ranked_posts = self._stage_ranking(relevant_posts, run_state)
            presented = self._stage_present_results(ranked_posts, run_state)
            if run_state.status != RunStatus.STOPPED:
                run_state.status = RunStatus.COMPLETED
            result = PipelineResult(
                run_state=run_state,
                request_payload=user_query.to_dict(),
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
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Failed to save run history: %s", str(exc))

            log_event(
                logger,
                20,
                "pipeline_finished",
                status=run_state.status.value,
                processed_posts=run_state.progress.processed_posts,
                stop_reason=run_state.stop_reason,
                elapsed_seconds=run_state.runtime.elapsed_seconds,
                post_errors=len(post_error_messages),
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
    ) -> UserQuery:
        run_state.progress.current_stage = "receive_user_input"
        user_query, errors = self._query_service.validate_and_build(raw_user_input)
        if errors or user_query is None:
            message = "; ".join([f"{item['field']}: {item['message']}" for item in errors])
            raise ValueError(f"input_validation_failed: {message}")

        self._mark_stage_success(
            run_state,
            stage_name="receive_user_input",
            details={"query": user_query.query},
        )
        return user_query

    def _stage_search_posts(
        self,
        user_query: UserQuery,
        options: PipelineOptions,
        run_state: PipelineRunState,
    ) -> List[Dict[str, Any]]:
        run_state.progress.current_stage = "search_posts"
        posts = self._search_service.search_posts(user_query, max_posts=options.max_posts)
        self._mark_stage_success(
            run_state,
            stage_name="search_posts",
            details={"found": len(posts), "max_posts": options.max_posts},
        )
        return posts

    def _stage_process_posts(
        self,
        posts: List[Dict[str, Any]],
        user_query: UserQuery,
        options: PipelineOptions,
        run_state: PipelineRunState,
    ) -> tuple[List[Dict[str, Any]], List[str]]:
        relevant_posts: List[Dict[str, Any]] = []
        post_errors = 0
        post_error_messages: List[str] = []
        open_success = 0
        collect_success = 0
        time_filter_retained = 0
        time_filter_rejected = 0
        ai_success = 0

        for index, post in enumerate(posts[: options.max_posts]):
            if self._should_stop(options, run_state, post_errors):
                run_state.status = RunStatus.STOPPED
                if run_state.stop_reason is None:
                    run_state.stop_reason = "stop_condition_reached"
                break

            run_state.progress.processed_posts = index + 1

            try:
                opened = self._search_service.open_post(post)
                open_success += 1

                collected = self._search_service.collect_post_data(opened)
                if not bool(collected.get("extraction_success", False)):
                    raise RuntimeError(str(collected.get("extraction_error") or "post_extraction_failed"))
                collect_success += 1

                recent_posts, _ = self._time_filter.filter_posts_with_diagnostics([collected], user_query)
                if not recent_posts:
                    time_filter_rejected += 1
                    continue
                time_filter_retained += 1

                envelope = self._ai_service.analyze(post_data=recent_posts[0], user_query=user_query)
                if not envelope.success or envelope.result is None:
                    errors = ";".join(envelope.validation_errors) or "ai_analysis_failed"
                    raise RuntimeError(errors)
                ai_match = {
                    **envelope.result.to_dict(),
                    "raw_ai_response": envelope.raw_response_text,
                    "raw_ai_response_data": envelope.raw_response_data,
                    "ai_validation_errors": envelope.validation_errors,
                    "ai_success": envelope.success,
                }
                ai_success += 1
                if not bool(ai_match.get("is_relevant", False)):
                    continue

                relevant_posts.append({"post": recent_posts[0], "ai_match": ai_match})
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
            stage_name="time_filter",
            details={
                "retained": time_filter_retained,
                "rejected": time_filter_rejected,
                "attempted": collect_success,
            },
        )
        self._mark_stage_success(
            run_state,
            stage_name="ai_analysis",
            details={
                "successful": ai_success,
                "relevant": len(relevant_posts),
                "attempted": time_filter_retained,
            },
        )

        return relevant_posts, post_error_messages

    def _stage_ranking(
        self,
        relevant_posts: List[Dict[str, Any]],
        run_state: PipelineRunState,
    ) -> List[Dict[str, Any]]:
        run_state.progress.current_stage = "ranking"
        ranked = self._ranker.rank(relevant_posts)
        self._mark_stage_success(run_state, stage_name="ranking", details={"ranked": len(ranked)})
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
            details={"top_results": len(presented.get("top_results", []))},
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
