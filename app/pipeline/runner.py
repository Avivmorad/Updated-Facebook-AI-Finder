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
from app.utils.debugging import debug_error, debug_info, debug_step, debug_warning
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
        debug_step("Starting a new pipeline run.")
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
            debug_info(
                f"Pipeline completed. Processed {run_state.progress.processed_posts} posts and kept {len(ranked_posts)} final results."
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Pipeline failed")
            log_event(logger, 40, "pipeline_failed", error=str(exc))
            debug_error(f"The pipeline stopped because of an error: {str(exc)}")
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

            if result is not None and opts.save_run_history:
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
            debug_info(
                f"Run finished with status {run_state.status.value}. Total elapsed time: {run_state.runtime.elapsed_seconds} seconds."
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
        debug_step("Stage 1/8: validating the user input.")
        user_query, errors = self._query_service.validate_and_build(raw_user_input)
        if errors or user_query is None:
            message = "; ".join([f"{item['field']}: {item['message']}" for item in errors])
            raise ValueError(f"input_validation_failed: {message}")

        self._mark_stage_success(
            run_state,
            stage_name="receive_user_input",
            details={"query": user_query.query},
        )
        debug_info(f'The input is valid. Query accepted: "{user_query.query}".')
        return user_query

    def _stage_search_posts(
        self,
        user_query: UserQuery,
        options: PipelineOptions,
        run_state: PipelineRunState,
    ) -> List[Dict[str, Any]]:
        run_state.progress.current_stage = "search_posts"
        debug_step("Stage 2/8: scanning the Facebook groups feed for candidate posts.")
        posts = self._search_service.search_posts(user_query, max_posts=options.max_posts)
        self._mark_stage_success(
            run_state,
            stage_name="search_posts",
            details={"found": len(posts), "max_posts": options.max_posts},
        )
        debug_info(f"I found {len(posts)} candidate posts to inspect.")
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
        if posts:
            debug_step(f"Stage 3-6/8: opening, extracting, filtering, and analyzing up to {min(len(posts), options.max_posts)} posts.")
        else:
            debug_info("No candidate posts were found, so there is nothing to open or analyze.")

        for index, post in enumerate(posts[: options.max_posts]):
            if self._should_stop(options, run_state, post_errors):
                run_state.status = RunStatus.STOPPED
                if run_state.stop_reason is None:
                    run_state.stop_reason = "stop_condition_reached"
                debug_warning("The run stopped early because a stop condition was reached.")
                break

            run_state.progress.processed_posts = index + 1
            post_label = f"Post {index + 1}/{min(len(posts), options.max_posts)}"
            debug_step(f"{post_label}: opening the candidate post.")

            try:
                opened = self._search_service.open_post(post)
                open_success += 1

                collected = self._search_service.collect_post_data(opened)
                if not bool(collected.get("extraction_success", False)):
                    raise RuntimeError(str(collected.get("extraction_error") or "post_extraction_failed"))
                collect_success += 1
                debug_info(
                    f"{post_label}: extracted text={'yes' if collected.get('post_text') else 'no'}, "
                    f"images={len(collected.get('images', []))}, "
                    f"publish_date={'yes' if collected.get('publish_date') else 'no'}."
                )

                recent_posts, _ = self._time_filter.filter_posts_with_diagnostics([collected], user_query)
                if not recent_posts:
                    time_filter_rejected += 1
                    debug_info(f"{post_label}: rejected because the publish date is older than 24 hours or could not be understood.")
                    continue
                time_filter_retained += 1
                debug_info(f"{post_label}: passed the hard 24-hour filter.")

                debug_step(f"{post_label}: sending the post to AI for relevance and match scoring.")
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
                    debug_info(f"{post_label}: AI marked this post as not relevant.")
                    continue

                relevant_posts.append({"post": recent_posts[0], "ai_match": ai_match})
                debug_info(
                    f"{post_label}: AI kept the post with match score {ai_match.get('match_score', 0)}."
                )
            except Exception as exc:  # noqa: BLE001
                post_errors += 1
                message = f"post_index={index} error={str(exc)}"
                post_error_messages.append(message)
                log_event(logger, 30, "post_processing_error", index=index, error=str(exc))
                debug_warning(f"{post_label}: there was a problem, so I skipped this post. Reason: {str(exc)}")

                if not options.continue_on_post_error:
                    run_state.status = RunStatus.STOPPED
                    run_state.stop_reason = "post_error_and_continue_disabled"
                    debug_warning("Stopping now because continue_on_post_error is disabled.")
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
        debug_info(
            f"Post processing summary: opened={open_success}, extracted={collect_success}, recent={time_filter_retained}, relevant={len(relevant_posts)}."
        )

        return relevant_posts, post_error_messages

    def _stage_ranking(
        self,
        relevant_posts: List[Dict[str, Any]],
        run_state: PipelineRunState,
    ) -> List[Dict[str, Any]]:
        run_state.progress.current_stage = "ranking"
        debug_step("Stage 7/8: ranking the relevant posts by AI match score.")
        ranked = self._ranker.rank(relevant_posts)
        self._mark_stage_success(run_state, stage_name="ranking", details={"ranked": len(ranked)})
        debug_info(f"Ranking complete. There are {len(ranked)} ranked results.")
        return ranked

    def _stage_present_results(
        self,
        ranked_posts: List[Dict[str, Any]],
        run_state: PipelineRunState,
    ) -> Dict[str, Any]:
        run_state.progress.current_stage = "present_results"
        debug_step("Stage 8/8: preparing the final output for display and JSON export.")
        presented = self._presenter.present(ranked_posts)
        self._mark_stage_success(
            run_state,
            stage_name="present_results",
            details={"top_results": len(presented.get("top_results", []))},
        )
        debug_info(f"Prepared {presented.get('total_results', 0)} final results.")
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
