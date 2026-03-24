from dotenv import load_dotenv

from app.logic.pipeline_runner import PipelineRunner
from app.models.pipeline_models import PipelineOptions
from app.utils.logger import get_logger


logger = get_logger(__name__)


load_dotenv()


def build_example_input() -> dict:
	return {
		"main_text": "iphone 13",
		"tags": ["apple", "smartphone"],
		"secondary_attributes": ["128gb"],
		"forbidden_words": ["broken"],
		"min_price": 50,
		"max_price": 5000,
		"is_free": False,
		"post_age": "24h",
		"require_image": True,
		"language": "he",
		"regions": ["center"],
		"manual_regions": [],
		"all_country": False,
		"group_mode": "all_groups",
		"groups": [],
		"group_sources": ["user_groups"],
		"group_urls": [],
		"select_all_groups": False,
	}


def main() -> None:
	runner = PipelineRunner()
	options = PipelineOptions(max_posts=20, continue_on_post_error=True)

	result = runner.run(build_example_input(), options=options)
	summary = result.presented_results

	logger.info("Pipeline status: %s", result.run_state.status.value)
	logger.info("Progress: %.2f%%", result.run_state.progress.percentage)
	logger.info("Post progress: %s", result.run_state.progress.post_counter)
	logger.info("Runtime seconds: %.3f", result.run_state.runtime.elapsed_seconds)
	logger.info("Total ranked posts: %s", len(result.ranked_posts))
	logger.info("Presented results: %s", summary)


if __name__ == "__main__":
	main()
