"""Wordpress Reviews model."""

from typing import Dict, Generator, List, Union, Optional
from datetime import datetime
import singer

from tap_wordpress_reviews.wordpress_reviews_list import WordpressReviewsList

LOGGER = singer.get_logger()


class WordpressReviews(object):
    """Main logic for Wordpress reviws."""

    def __init__(
        self,
        plugins: Union[List[str], str],
        number: int = 30,
    ) -> None:
        """Initialize plugin reviews api.

        Arguments:
            plugins {Union[List[str], str]} -- Name of the plugins
            number {int} -- Number of reviews to yield (default: {30})
        """
        # Set plugin or plugins
        if isinstance(plugins, str):
            self.plugins = [plugins]
        else:
            self.plugins = plugins

        self.number = number

        # Initialize lists
        self.reviews_lists: Dict[str, WordpressReviewsList] = {}
        for plugin in self.plugins:
            self.reviews_lists[plugin] = WordpressReviewsList(plugin)

    def reviews(self, since_date: Optional[str] = None, backfill_info: Optional[dict] = None) -> Generator:
        """Reviews property with optional date filtering and backfill support.

        Arguments:
            since_date {Optional[str]} -- Only return reviews after this date (for incremental)
                                         Format: ISO 8601 string (YYYY-MM-DDTHH:MM:SSZ)
            backfill_info {Optional[dict]} -- Backfill state information
                                             - is_backfilling: True if in backfill mode
                                             - oldest_seen: Oldest date we've seen (resume boundary)
                                             - total_fetched: Total records fetched so far

        Returns:
            Generator -- Object list of reviews
        """
        # Parse since_date if provided (for incremental mode)
        filter_date = None
        if since_date and not backfill_info:
            try:
                # Handle various date formats
                if 'T' in since_date:
                    filter_date = datetime.fromisoformat(since_date.replace('Z', '+00:00'))
                else:
                    filter_date = datetime.fromisoformat(since_date)
                LOGGER.info(f"Filtering reviews since: {filter_date}")
            except ValueError as e:
                LOGGER.warning(f"Invalid date format for bookmark: {since_date}. Error: {e}")
                filter_date = None

        # Parse backfill boundary if in backfill mode
        backfill_boundary = None
        if backfill_info and backfill_info.get('oldest_seen'):
            try:
                oldest = backfill_info['oldest_seen']
                if 'T' in oldest:
                    backfill_boundary = datetime.fromisoformat(oldest.replace('Z', '+00:00'))
                else:
                    backfill_boundary = datetime.fromisoformat(oldest)
                LOGGER.info(f"Backfill mode: Continuing from oldest boundary: {backfill_boundary}")
            except ValueError as e:
                LOGGER.warning(f"Invalid date format for backfill boundary: {oldest}. Error: {e}")
                backfill_boundary = None

        for plugin in self.plugins:
            LOGGER.info(f"Processing reviews for plugin: {plugin}")
            reviews_count = 0
            skipped_count = 0

            try:
                # Keep track of all reviews to handle the number limit properly
                for _ in range(0, self.number * 10):  # Fetch more to account for filtering
                    try:
                        review_item = next(self.reviews_lists[plugin])
                        record: dict = review_item.to_dict()
                        record['plugin'] = plugin

                        # Check if we should include this review based on date
                        if 'date' in record:
                            try:
                                # Parse the review date
                                review_date_str = record['date']
                                if isinstance(review_date_str, str):
                                    # Handle various date formats from WordPress
                                    if 'T' in review_date_str:
                                        review_date = datetime.fromisoformat(
                                            review_date_str.replace('Z', '+00:00')
                                        )
                                    else:
                                        review_date = datetime.fromisoformat(review_date_str)

                                    # In backfill mode: skip reviews newer or equal to boundary (already have them)
                                    if backfill_boundary and review_date >= backfill_boundary:
                                        skipped_count += 1
                                        continue

                                    # In incremental mode: skip reviews older or equal to bookmark
                                    elif filter_date and review_date <= filter_date:
                                        skipped_count += 1
                                        continue
                            except (ValueError, TypeError) as e:
                                LOGGER.warning(f"Could not parse date for review: {e}")
                                # Include review if we can't parse its date

                        yield record
                        reviews_count += 1

                        # Stop if we've yielded enough reviews
                        if reviews_count >= self.number:
                            break

                    except StopIteration:
                        LOGGER.info(f"No more reviews available for plugin: {plugin}")
                        break

                if skipped_count > 0:
                    if backfill_boundary:
                        LOGGER.info(f"Skipped {skipped_count} already-fetched reviews for plugin: {plugin}")
                    else:
                        LOGGER.info(f"Skipped {skipped_count} old reviews for plugin: {plugin}")

                if backfill_info:
                    LOGGER.info(f"Backfill progress: Yielded {reviews_count} reviews for plugin: {plugin}")
                else:
                    LOGGER.info(f"Yielded {reviews_count} reviews for plugin: {plugin}")

            except StopIteration:
                LOGGER.info(f"Finished processing all reviews for plugin: {plugin}")
                continue
