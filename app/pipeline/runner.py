from datetime import datetime, timezone
import shutil
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List, Optional

from app.ai.ai_service import AIAnalysisService
from app.browser.step_debug import reset_step_debug_workspace
from app.config.browser import BrowserConfig
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
from app.utils.app_errors import AppError, make_app_error, normalize_app_error
from app.utils.debugging import (
    debug_app_error,
    debug_found,
    debug_info,
    debug_missing,
    debug_result,
    debug_step,
    debug_warning,
)
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
        debug_step("DBG_PIPELINE_START", "Starting a new pipeline run.")
        reset_step_debug_workspace(BrowserConfig())
        self._reset_screenshot_workspace()
        start = perf_counter()

        try:
            user_query = self._stage_receive_user_input(raw_user_input, run_state)
            posts = self._stage_search_posts(user_query, opts, run_state)
            relevant_posts, post_error_messages, post_failures = self._stage_process_posts(posts, user_query, opts, run_state)
            ranked_posts = self._stage_ranking(relevant_posts, run_state)
            presented = self._stage_present_results(ranked_posts, run_state)
            presented["post_failures"] = post_failures
            presented["post_failure_count"] = len(post_failures)
            if run_state.status != RunStatus.STOPPED:
                run_state.status = RunStatus.COMPLETED
            result = PipelineResult(
                run_state=run_state,
                request_payload=user_query.to_dict(),
                ranked_posts=ranked_posts,
                presented_results=presented,
            )
            debug_result(
                "DBG_PIPELINE_DONE",
                (
                    f"Pipeline completed. Processed {run_state.progress.processed_posts} posts, "
                    f"kept {len(ranked_posts)} result(s)."
                ),
            )
        except Exception as exc:  # noqa: BLE001
            app_error = normalize_app_error(
                exc,
                default_code="ERR_PIPELINE_UNEXPECTED",
                default_summary_he="Pipeline stopped due to an unexpected error",
                default_cause_he="An internal exception was raised without explicit mapping",
                default_action_he="Check debug trace and app.log, then retry",
            )
            logger.exception("Pipeline failed")
            log_event(logger, 40, "pipeline_failed", error=app_error.code)
            debug_app_error(app_error)
            run_state.status = RunStatus.FAILED
            run_state.stop_reason = app_error.code
            run_state.add_stage_result(
                StageResult(
                    stage_name=run_state.progress.current_stage or "pipeline",
                    status=StageStatus.FAILED,
                    errors=[app_error.code],
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
                    history_error = normalize_app_error(
                        exc,
                        default_code="ERR_RUN_HISTORY_SAVE_FAILED",
                        default_summary_he="Failed to save run history",
                        default_cause_he="An error occurred while writing run_history.json",
                        default_action_he="Check write permissions in the data directory",
                    )
                    logger.warning("Failed to save run history: %s", str(history_error))
                    debug_app_error(history_error)

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
            debug_result(
                "DBG_PIPELINE_SUMMARY",
                (
                    f"Final status: {run_state.status.value} | "
                    f"Elapsed: {run_state.runtime.elapsed_seconds}s | "
                    f"Post errors: {len(post_error_messages)}"
                ),
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
        debug_step("DBG_STAGE_1_INPUT", "Stage 1/8: validating user input.")
        user_query, errors = self._query_service.validate_and_build(raw_user_input)
        if errors or user_query is None:
            raise self._build_input_error(errors)

        self._mark_stage_success(
            run_state,
            stage_name="receive_user_input",
            details={"query": user_query.query},
        )
        debug_found("DBG_INPUT_OK", f'Input is valid. Accepted query: "{user_query.query}".')
        return user_query

    def _stage_search_posts(
        self,
        user_query: UserQuery,
        options: PipelineOptions,
        run_state: PipelineRunState,
    ) -> List[Dict[str, Any]]:
        run_state.progress.current_stage = "search_posts"
        debug_step("DBG_STAGE_2_SEARCH", "Stage 2/8: scanning groups feed for candidate posts.")
        posts = self._search_service.search_posts(user_query, max_posts=options.max_posts)
        self._mark_stage_success(
            run_state,
            stage_name="search_posts",
            details={"found": len(posts), "max_posts": options.max_posts},
        )
        if posts:
            debug_found("DBG_SEARCH_RESULTS", f"Found {len(posts)} candidate post(s) to inspect.")
        else:
            missing_error = make_app_error(code="ERR_NO_POST_LINKS_FOUND")
            debug_missing(missing_error.code, missing_error.summary_he)
        return posts

    def _stage_process_posts(
        self,
        posts: List[Dict[str, Any]],
        user_query: UserQuery,
        options: PipelineOptions,
        run_state: PipelineRunState,
    ) -> tuple[List[Dict[str, Any]], List[str], List[Dict[str, str]]]:
        relevant_posts: List[Dict[str, Any]] = []
        post_errors = 0
        post_error_messages: List[str] = []
        post_failures: List[Dict[str, str]] = []
        open_success = 0
        collect_success = 0
        time_filter_retained = 0
        time_filter_rejected = 0
        ai_success = 0
        ai_rejected = 0
        ai_not_recent_rejected = 0
        time_rejected_reasons: Dict[str, int] = {}
        target_posts = min(len(posts), options.max_posts)

        if posts:
            debug_step(
                "DBG_STAGE_3_6_PROCESS",
                f"Stages 3-6/8: processing up to {target_posts} posts (open, extract, time-filter, AI).",
            )
            debug_info("DBG_CANDIDATES_COUNT", f"Candidate posts queued for processing: {target_posts}.")
        else:
            debug_missing("DBG_NO_CANDIDATES", "No candidate posts available for stages 3-6.")

        for index, post in enumerate(posts[: options.max_posts]):
            if self._should_stop(options, run_state, post_errors):
                run_state.status = RunStatus.STOPPED
                if run_state.stop_reason is None:
                    run_state.stop_reason = "stop_condition_reached"
                debug_warning("DBG_RUN_STOPPED", "Run stopped early due to configured stop condition.")
                break

            run_state.progress.processed_posts = index + 1
            post_label = f"Post {index + 1}/{target_posts}"
            post_link = str(post.get("post_link") or "").strip()
            debug_step("DBG_POST_OPEN", f"{post_label}: opening for inspection. Link: {post_link or 'missing'}")

            try:
                opened = self._search_service.open_post(post)
                open_success += 1

                collected = self._search_service.collect_post_data(opened)
                if not bool(collected.get("extraction_success", False)):
                    extraction_code = str(collected.get("extraction_error") or "").strip() or "ERR_POST_PAGE_LOAD_FAILED"
                    raise make_app_error(
                        code=extraction_code,
                        technical_details=str(collected.get("extraction_error") or ""),
                    )
                collect_success += 1
                debug_info(
                    "DBG_POST_EXTRACT_DATA",
                    (
                        f"{post_label}: text={'yes' if collected.get('post_text') else 'no'}, "
                        f"images={len(collected.get('images', []))}, "
                        f"publish_date={'yes' if collected.get('publish_date') else 'no'}, "
                        f"quality={collected.get('extraction_quality', 'unknown')}."
                    ),
                )

                recent_posts, rejected = self._time_filter.filter_posts_with_diagnostics([collected], user_query)
                if recent_posts:
                    time_filter_retained += 1
                    collected["parser_time_reason"] = "recent"
                    debug_found("DBG_POST_TIME_PARSE", f"{post_label}: parser hint says publish date appears recent.")
                else:
                    time_filter_rejected += 1
                    reason = str(rejected[0].get("reason") if rejected else "").strip()
                    normalized_reason = reason or "unknown"
                    time_rejected_reasons[normalized_reason] = time_rejected_reasons.get(normalized_reason, 0) + 1
                    collected["parser_time_reason"] = normalized_reason
                    debug_warning(
                        "DBG_POST_TIME_PARSE",
                        f"{post_label}: parser hint says not recent ({normalized_reason}). AI date decision will be used.",
                    )

                screenshot_path = str(collected.get("post_screenshot_path") or "").strip()
                if not screenshot_path:
                    raise make_app_error(code="ERR_POST_SCREENSHOT_MISSING")

                debug_step("DBG_POST_AI_SEND", f"{post_label}: sending post to AI analysis.")
                envelope = self._ai_service.analyze(post_data=collected, user_query=user_query)
                if not envelope.success or envelope.result is None:
                    ai_error_code = self._infer_ai_failure_code(envelope.validation_errors)
                    raise make_app_error(
                        code=ai_error_code,
                        technical_details=";".join(envelope.validation_errors),
                    )
                ai_match = {
                    **envelope.result.to_dict(),
                    "raw_ai_response": envelope.raw_response_text,
                    "raw_ai_response_data": envelope.raw_response_data,
                    "ai_validation_errors": envelope.validation_errors,
                    "ai_success": envelope.success,
                }
                ai_success += 1
                if not bool(ai_match.get("is_recent_24h", False)):
                    ai_not_recent_rejected += 1
                    not_recent = make_app_error(code="ERR_AI_MARKED_NOT_RECENT")
                    debug_missing(not_recent.code, f"{post_label}: {not_recent.summary_he}.")
                    continue
                debug_found("DBG_POST_TIME_OK", f"{post_label}: AI marked post as within 24 hours.")

                if not bool(ai_match.get("is_relevant", False)):
                    ai_rejected += 1
                    not_relevant = make_app_error(code="ERR_AI_MARKED_NOT_RELEVANT")
                    debug_missing(not_relevant.code, f"{post_label}: {not_relevant.summary_he}.")
                    continue

                relevant_posts.append({"post": collected, "ai_match": ai_match})
                debug_found(
                    "DBG_POST_AI_KEEP",
                    f"{post_label}: kept with match score {ai_match.get('match_score', 0)}.",
                )
            except Exception as exc:  # noqa: BLE001
                app_error = normalize_app_error(
                    exc,
                    default_code="ERR_PIPELINE_UNEXPECTED",
                    default_summary_he="Post processing failed",
                    default_cause_he="An unexpected error occurred while processing a post",
                    default_action_he="Pipeline will skip to next post when continue_on_post_error is enabled",
                )
                post_errors += 1
                post_error_messages.append(app_error.code)
                post_failures.append(
                    {
                        "post_link": post_link,
                        "post_index": str(index + 1),
                        "error_code": app_error.code,
                    }
                )
                log_event(logger, 30, "post_processing_error", index=index, error=app_error.code)
                debug_app_error(app_error)

                if not options.continue_on_post_error:
                    run_state.status = RunStatus.STOPPED
                    run_state.stop_reason = "post_error_and_continue_disabled"
                    debug_warning("DBG_STOP_ON_POST_ERROR", "Stopping run because CONTINUE_ON_POST_ERROR=False.")
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
                "parser_recent": time_filter_retained,
                "parser_not_recent": time_filter_rejected,
                "parser_rejected_reasons": time_rejected_reasons,
                "attempted": collect_success,
            },
        )
        self._mark_stage_success(
            run_state,
            stage_name="ai_analysis",
            details={
                "successful": ai_success,
                "relevant": len(relevant_posts),
                "ai_rejected": ai_rejected,
                "ai_not_recent_rejected": ai_not_recent_rejected,
                "attempted": collect_success,
            },
        )
        debug_result(
            "DBG_POSTS_SUMMARY",
            (
                f"Post processing summary: candidates={target_posts}, opened={open_success}, extracted={collect_success}, "
                f"parser_not_recent={time_filter_rejected}, ai_not_recent={ai_not_recent_rejected}, "
                f"ai_rejected={ai_rejected}, kept={len(relevant_posts)}."
            ),
        )

        return relevant_posts, post_error_messages, post_failures

    def _stage_ranking(
        self,
        relevant_posts: List[Dict[str, Any]],
        run_state: PipelineRunState,
    ) -> List[Dict[str, Any]]:
        run_state.progress.current_stage = "ranking"
        debug_step("DBG_STAGE_7_RANK", "Stage 7/8: ranking by AI match_score only.")
        ranked = self._ranker.rank(relevant_posts)
        self._mark_stage_success(run_state, stage_name="ranking", details={"ranked": len(ranked)})
        debug_found("DBG_RANK_DONE", f"Ranking complete. Ranked results: {len(ranked)}.")
        return ranked

    def _stage_present_results(
        self,
        ranked_posts: List[Dict[str, Any]],
        run_state: PipelineRunState,
    ) -> Dict[str, Any]:
        run_state.progress.current_stage = "present_results"
        debug_step("DBG_STAGE_8_PRESENT", "Stage 8/8: preparing final output and JSON payload.")
        presented = self._presenter.present(ranked_posts)
        self._mark_stage_success(
            run_state,
            stage_name="present_results",
            details={"top_results": len(presented.get("top_results", []))},
        )
        debug_result("DBG_PRESENT_DONE", f"Prepared {presented.get('total_results', 0)} result(s) for presentation.")
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

    def _build_input_error(self, errors: List[Dict[str, str]]) -> AppError:
        serialized = "; ".join(f"{item.get('field')}:{item.get('message')}" for item in errors)
        for item in errors:
            if str(item.get("field")) == "query":
                return make_app_error(
                    code="ERR_INPUT_QUERY_MISSING",
                    technical_details=serialized,
                )
        return make_app_error(
            code="ERR_INPUT_JSON_INVALID",
            technical_details=serialized,
        )

    def _build_time_filter_error(self, reason: str) -> AppError:
        normalized_reason = reason.strip().lower()
        if normalized_reason == "missing_publish_date":
            return make_app_error(code="ERR_POST_PUBLISH_DATE_MISSING")
        if normalized_reason == "unparseable_publish_date":
            return make_app_error(code="ERR_POST_PUBLISH_DATE_UNPARSEABLE")
        if normalized_reason == "older_than_24_hours":
            return make_app_error(code="ERR_POST_TOO_OLD")
        return make_app_error(
            code="ERR_POST_PUBLISH_DATE_UNPARSEABLE",
            technical_details=f"reason={reason}",
        )

    def _infer_ai_failure_code(self, validation_errors: List[str]) -> str:
        for item in validation_errors:
            if item == "ERR_POST_SCREENSHOT_MISSING":
                return "ERR_POST_SCREENSHOT_MISSING"
            if item == "ERR_POST_SCREENSHOT_CAPTURE_FAILED":
                return "ERR_POST_SCREENSHOT_CAPTURE_FAILED"
            if item == "ERR_AI_RESPONSE_EMPTY":
                return "ERR_AI_RESPONSE_EMPTY"
            if item == "ERR_AI_RESPONSE_INVALID_JSON":
                return "ERR_AI_RESPONSE_INVALID_JSON"
            if item == "ERR_AI_RESPONSE_SCHEMA_INVALID":
                return "ERR_AI_RESPONSE_SCHEMA_INVALID"
            if item == "ERR_AI_VISION_MODEL_MISSING":
                return "ERR_AI_VISION_MODEL_MISSING"
            if item == "ERR_AI_VISION_MODEL_DECOMMISSIONED":
                return "ERR_AI_VISION_MODEL_DECOMMISSIONED"
            if item == "ERR_AI_VISION_PROVIDER_UNSUPPORTED":
                return "ERR_AI_VISION_PROVIDER_UNSUPPORTED"
            if item == "ERR_AI_REQUEST_FAILED":
                return "ERR_AI_REQUEST_FAILED"
        return "ERR_AI_REQUEST_FAILED"

    def _reset_screenshot_workspace(self) -> None:
        screenshots_dir = Path(BrowserConfig().screenshots_dir).expanduser()
        try:
            if screenshots_dir.exists():
                shutil.rmtree(screenshots_dir)
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            debug_info("DBG_SCREENSHOT_DIR", f"Prepared screenshot workspace: {screenshots_dir}")
        except OSError as exc:
            warn_error = make_app_error(
                code="ERR_POST_SCREENSHOT_CAPTURE_FAILED",
                technical_details=f"path={screenshots_dir} error={exc}",
            )
            debug_app_error(warn_error)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
