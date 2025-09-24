"""All-or-nothing WordPress reviews sync per plugin."""

from datetime import datetime, timezone
from typing import Generator, List, Optional, Dict
import logging

from tap_wordpress_reviews.wordpress_reviews_list import ImprovedWordpressReviewsList

LOGGER = logging.getLogger(__name__)


class WordpressReviews:
    """WordPress reviews with all-or-nothing approach per plugin.

    Logic:
    - If a plugin is marked complete: only check page 1 for new reviews
    - If a plugin is incomplete: fetch ALL reviews for that plugin
    - No partial syncs - either you have all history or none
    """

    def __init__(self, plugins: List[str], number: int = 500):
        self.plugins = plugins
        self.number = number
        self.reviews_lists = {}

    def reviews(self, since_date: Optional[str] = None,
                backfill_info: Optional[dict] = None,
                plugin_states: Optional[Dict] = None) -> Generator:
        """Get reviews with all-or-nothing approach per plugin.

        Args:
            since_date: Boundary date for incremental sync
            backfill_info: Legacy backfill info (for compatibility)
            plugin_states: Per-plugin state tracking (preferred)
                Format: {
                    'mailpoet': {
                        'reviews': {'complete': True, 'newest_seen': '2025-09-24...'},
                        'support_threads': {...}
                    }
                }

        Yields:
            Review dictionaries
        """
        # Parse since_date
        filter_date = None
        if since_date:
            try:
                if 'T' in since_date:
                    filter_date = datetime.fromisoformat(since_date.replace('Z', '+00:00'))
                else:
                    filter_date = datetime.fromisoformat(since_date)
                LOGGER.info(f"All-or-nothing mode with boundary: {filter_date}")
            except ValueError as e:
                LOGGER.warning(f"Invalid date format: {since_date}. Error: {e}")

        # If no plugin states provided, treat all as incomplete
        if not plugin_states:
            plugin_states = {}

        for plugin in self.plugins:
            LOGGER.info(f"\n{'='*60}")
            LOGGER.info(f"Processing plugin: {plugin}")

            # Check plugin state - ignore "complete" flag, only use newest_seen
            plugin_state = plugin_states.get(plugin, {})
            reviews_state = plugin_state.get('reviews', {})
            newest_seen = reviews_state.get('newest_seen')

            if newest_seen:
                # We have previous data - always fetch ALL pages until we hit known reviews
                LOGGER.info(f"📊 {plugin} has previous sync (newest: {newest_seen})")
                LOGGER.info(f"   → Fetching ALL reviews (up to {self.number}) until we hit known data")
            else:
                # No previous sync - fetch everything
                LOGGER.info(f"🆕 {plugin} is NEW - no previous sync")
                LOGGER.info(f"   → Fetching ALL reviews (up to {self.number})")

            # Always fetch all reviews - the fetch function will stop at known data
            yield from self._fetch_all_reviews(plugin)

    def _fetch_new_reviews_only(self, plugin: str, boundary_date: datetime) -> Generator:
        """Only check page 1 for new reviews since boundary_date.

        This is very efficient - stops as soon as we hit an old review.
        """
        if plugin not in self.reviews_lists:
            self.reviews_lists[plugin] = ImprovedWordpressReviewsList(plugin)

        reviews_list = self.reviews_lists[plugin]
        new_count = 0
        old_count = 0

        # Only load page 1
        reviews_info, _ = reviews_list.load_page(1)

        for info in reviews_info:
            # Check approximate date first
            approx_date = info.approximate_date

            if approx_date and approx_date <= boundary_date:
                # This review is old, and since reviews are ordered newest first,
                # all remaining reviews will be old too
                old_count += 1
                LOGGER.debug(f"Hit old review, stopping (approx date: {approx_date})")
                break

            # Load the review to get exact date
            review = info.get_review()
            review.load()
            record = review.to_dict()
            record['plugin'] = plugin

            # Double-check with exact date
            if 'date' in record:
                try:
                    review_date_str = record['date']
                    if isinstance(review_date_str, str):
                        if 'T' in review_date_str:
                            review_date = datetime.fromisoformat(
                                review_date_str.replace('Z', '+00:00')
                            )
                        else:
                            review_date = datetime.fromisoformat(review_date_str)

                        if review_date <= boundary_date:
                            # Old review, stop here
                            old_count += 1
                            LOGGER.debug(f"Hit old review, stopping (exact date: {review_date})")
                            break
                except (ValueError, TypeError) as e:
                    LOGGER.warning(f"Could not parse date: {e}")

            # This is a new review
            yield record
            new_count += 1

        LOGGER.info(f"   {plugin}: {new_count} new reviews (stopped at first old)")

    def _fetch_all_reviews(self, plugin: str) -> Generator:
        """Fetch ALL reviews for a plugin (for incomplete plugins)."""
        if plugin not in self.reviews_lists:
            self.reviews_lists[plugin] = ImprovedWordpressReviewsList(plugin)

        reviews_list = self.reviews_lists[plugin]
        total_count = 0
        page = 1

        while total_count < self.number:
            reviews_info, has_more = reviews_list.load_page(page)

            if not reviews_info:
                LOGGER.info(f"   No more reviews at page {page}")
                break

            for info in reviews_info:
                review = info.get_review()
                review.load()
                record = review.to_dict()
                record['plugin'] = plugin

                yield record
                total_count += 1

                if total_count >= self.number:
                    break

            if not has_more:
                LOGGER.info(f"   No more pages after page {page}")
                break

            page += 1

            if page > 50:
                LOGGER.warning(f"   Reached page limit")
                break

        LOGGER.info(f"   {plugin}: Fetched {total_count} reviews (full sync)")


def create_all_or_nothing_tap():
    """Create an all-or-nothing tap configuration.

    This is the simplest and most reliable approach:
    1. Check unified_state.json for each plugin's status
    2. If complete: only check page 1 for new reviews
    3. If incomplete: sync ALL reviews for that plugin
    """
    import json

    # Load unified state to check plugin statuses
    try:
        with open('unified_state.json', 'r') as f:
            state = json.load(f)
        plugin_states = state.get('value', {}).get('plugin_states', {})
    except FileNotFoundError:
        LOGGER.warning("No unified_state.json found - treating all plugins as incomplete")
        plugin_states = {}

    # Load config
    with open('woo_ecosystem_config.json', 'r') as f:
        config = json.load(f)

    # Create the reviews client
    client = WordpressReviews(
        plugins=config['plugins'],
        number=config.get('number', 500)
    )

    # Return client with plugin states
    return client, plugin_states