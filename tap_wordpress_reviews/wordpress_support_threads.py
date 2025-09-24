"""WordPress Support Threads main orchestrator."""

from typing import Dict, Generator, List, Union, Optional
from datetime import datetime
import singer

from tap_wordpress_reviews.wordpress_support_threads_list import WordpressSupportThreadsList

LOGGER = singer.get_logger()


class WordpressSupportThreads(object):
    """Main logic for WordPress support threads."""

    def __init__(
        self,
        plugins: Union[List[str], str],
        number: int = 30,
        thread_filter: str = 'all',
    ) -> None:
        """Initialize support threads API.

        Arguments:
            plugins {Union[List[str], str]} -- Name of the plugins
            number {int} -- Number of threads to yield (default: {30})
            thread_filter {str} -- Filter: 'all', 'active', 'unresolved' (default: 'all')
        """
        # Set plugin or plugins
        if isinstance(plugins, str):
            self.plugins = [plugins]
        else:
            self.plugins = plugins

        self.number = number
        self.thread_filter = thread_filter

        # Initialize thread lists
        self.threads_lists: Dict[str, WordpressSupportThreadsList] = {}
        for plugin in self.plugins:
            self.threads_lists[plugin] = WordpressSupportThreadsList(
                plugin, thread_filter
            )

    def threads(self, since_date: Optional[str] = None, backfill_info: Optional[dict] = None) -> Generator:
        """Get support threads with optional date filtering and backfill support.

        Arguments:
            since_date {Optional[str]} -- Only return threads after this date (for incremental)
                                         Format: ISO 8601 string (YYYY-MM-DDTHH:MM:SSZ)
            backfill_info {Optional[dict]} -- Backfill state information
                                             - is_backfilling: True if in backfill mode
                                             - oldest_seen: Oldest date we've seen (resume boundary)
                                             - total_fetched: Total records fetched so far

        Returns:
            Generator -- Object list of support threads
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
                LOGGER.info(f"Filtering support threads since: {filter_date}")
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
            LOGGER.info(f"Processing support threads for plugin: {plugin} (filter: {self.thread_filter})")
            threads_count = 0
            skipped_count = 0

            try:
                # Fetch more threads than needed to account for filtering
                for _ in range(0, self.number * 10):
                    try:
                        thread_item = next(self.threads_lists[plugin])
                        record: dict = thread_item.to_dict()
                        record['plugin'] = plugin
                        record['filter_type'] = self.thread_filter

                        # Check if we should include this thread based on date
                        if 'date' in record and record['date']:
                            try:
                                # Parse the thread date
                                thread_date_str = record['date']
                                if isinstance(thread_date_str, str):
                                    # Handle various date formats
                                    if 'T' in thread_date_str:
                                        thread_date = datetime.fromisoformat(
                                            thread_date_str.replace('Z', '+00:00')
                                        )
                                    else:
                                        thread_date = datetime.fromisoformat(thread_date_str)

                                    # In backfill mode: skip threads newer or equal to boundary
                                    if backfill_boundary and thread_date >= backfill_boundary:
                                        skipped_count += 1
                                        continue

                                    # In incremental mode: skip threads older or equal to bookmark
                                    elif filter_date and thread_date <= filter_date:
                                        skipped_count += 1
                                        continue
                            except (ValueError, TypeError) as e:
                                LOGGER.warning(f"Could not parse date for thread: {e}")
                                # Include thread if we can't parse its date

                        yield record
                        threads_count += 1

                        # Stop if we've yielded enough threads
                        if threads_count >= self.number:
                            break

                    except StopIteration:
                        LOGGER.info(f"No more support threads available for plugin: {plugin}")
                        break

                if skipped_count > 0:
                    if backfill_boundary:
                        LOGGER.info(f"Skipped {skipped_count} already-fetched threads for plugin: {plugin}")
                    else:
                        LOGGER.info(f"Skipped {skipped_count} old threads for plugin: {plugin}")

                if backfill_info:
                    LOGGER.info(f"Backfill progress: Yielded {threads_count} support threads for plugin: {plugin}")
                else:
                    LOGGER.info(f"Yielded {threads_count} support threads for plugin: {plugin}")

            except StopIteration:
                LOGGER.info(f"Finished processing all support threads for plugin: {plugin}")
                continue