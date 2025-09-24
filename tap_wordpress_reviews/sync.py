"""Sync data."""
# -*- coding: utf-8 -*-
import logging
from datetime import datetime, timezone

import singer
from singer.catalog import Catalog
from singer import metadata

from tap_wordpress_reviews.wordpress_reviews import WordpressReviews
from tap_wordpress_reviews.wordpress_support_threads import WordpressSupportThreads

LOGGER: logging.RootLogger = singer.get_logger()


def sync(  # noqa: WPS210, WPS213
    wp_reviews: WordpressReviews = None,
    wp_support: WordpressSupportThreads = None,
    catalog: Catalog = None,
    state: dict = None,
) -> None:
    """Sync data from tap source.

    Arguments:
        wp_reviews {WordpressReviews} -- WordpressReviews client (optional)
        wp_support {WordpressSupportThreads} -- WordpressSupportThreads client (optional)
        catalog {Catalog} -- Stream catalog
        state {dict} -- Current state with bookmarks
    """
    # Initialize state if not provided
    if state is None:
        state = {}

    # For every stream in the catalog
    LOGGER.info('Sync')

    # Only selected streams are synced, whether a stream is selected is
    # determined by whether the key-value: "selected": true is in the schema
    # file.
    for stream in catalog.get_selected_streams(state):
        LOGGER.info(f'Syncing stream: {stream.tap_stream_id}')

        # Get the bookmark for this stream
        stream_metadata = metadata.to_map(stream.metadata)
        # Try multiple possible locations for replication key
        replication_key = (
            stream_metadata.get((), {}).get('replication-key') or
            stream.replication_key or
            'date'  # Fallback to 'date' for reviews stream
        )

        # Get the bookmark value and backfill state
        bookmark_value = None
        oldest_seen = None
        is_backfilling = False
        backfill_total = 0

        if stream.tap_stream_id in state:
            stream_state = state[stream.tap_stream_id]
            bookmark_value = stream_state.get('replication_key_value')

            # Check if we're in backfill mode
            if 'backfill' in stream_state:
                backfill = stream_state['backfill']
                is_backfilling = not backfill.get('complete', False)
                oldest_seen = backfill.get('oldest_seen')
                backfill_total = backfill.get('total_fetched', 0)

                if is_backfilling:
                    LOGGER.info(f'Resuming backfill from oldest: {oldest_seen}, already fetched: {backfill_total}')
            elif bookmark_value:
                LOGGER.info(f'Resuming incremental from bookmark: {bookmark_value}')

        # First time running - start backfill
        if not bookmark_value and not oldest_seen:
            is_backfilling = True
            LOGGER.info('Starting initial backfill')

        # Write the schema
        singer.write_schema(
            stream_name=stream.tap_stream_id,
            schema=stream.schema.to_dict(),
            key_properties=stream.key_properties,
        )

        # Track the max and min bookmark values seen
        max_bookmark = bookmark_value
        min_bookmark = oldest_seen
        record_count = 0

        # Pass backfill state to the reviews generator
        backfill_info = {
            'is_backfilling': is_backfilling,
            'oldest_seen': oldest_seen,
            'total_fetched': backfill_total
        } if is_backfilling else None

        # The tap_data method yields rows of data from the API
        # Use the appropriate client based on stream type
        if stream.tap_stream_id == 'reviews' and wp_reviews:
            data_generator = wp_reviews.reviews(since_date=bookmark_value, backfill_info=backfill_info)
        elif stream.tap_stream_id == 'support_threads' and wp_support:
            data_generator = wp_support.threads(since_date=bookmark_value, backfill_info=backfill_info)
        else:
            LOGGER.warning(f'No client available for stream: {stream.tap_stream_id}')
            continue

        for row in data_generator:
            # Get the bookmark value from this record
            if replication_key and replication_key in row:
                current_bookmark = row[replication_key]

                # Update max bookmark if this record is newer
                if max_bookmark is None or current_bookmark > max_bookmark:
                    max_bookmark = current_bookmark

                # Update min bookmark if this record is older (for backfill tracking)
                if min_bookmark is None or current_bookmark < min_bookmark:
                    min_bookmark = current_bookmark

            # Write a row to the stream
            singer.write_record(
                stream.tap_stream_id,
                row,
                time_extracted=datetime.now(timezone.utc),
            )
            record_count += 1

            # Periodically write state (every 100 records)
            if record_count % 100 == 0:
                if is_backfilling:
                    # During backfill, track both boundaries
                    state[stream.tap_stream_id] = {
                        'replication_key': replication_key,
                        'replication_key_value': max_bookmark,
                        'backfill': {
                            'oldest_seen': min_bookmark,
                            'total_fetched': backfill_total + record_count,
                            'complete': False
                        }
                    }
                else:
                    # During incremental, just track newest
                    state[stream.tap_stream_id] = {
                        'replication_key': replication_key,
                        'replication_key_value': max_bookmark
                    }

                singer.write_state(state)
                LOGGER.info(f'Written {record_count} records, bookmark: {max_bookmark}, oldest: {min_bookmark}')

        # Write final state for this stream
        if record_count > 0:
            # Check if backfill might be complete (got fewer records than requested)
            # Use the appropriate client's number setting
            expected_count = wp_reviews.number if stream.tap_stream_id == 'reviews' and wp_reviews else \
                           wp_support.number if stream.tap_stream_id == 'support_threads' and wp_support else 100
            backfill_complete = is_backfilling and record_count < expected_count

            if is_backfilling:
                state[stream.tap_stream_id] = {
                    'replication_key': replication_key,
                    'replication_key_value': max_bookmark,
                    'backfill': {
                        'oldest_seen': min_bookmark,
                        'total_fetched': backfill_total + record_count,
                        'complete': backfill_complete
                    }
                }
                if backfill_complete:
                    LOGGER.info(f'Backfill complete! Total fetched: {backfill_total + record_count}')
            else:
                state[stream.tap_stream_id] = {
                    'replication_key': replication_key,
                    'replication_key_value': max_bookmark
                }

            singer.write_state(state)
            LOGGER.info(f'Finished syncing {stream.tap_stream_id}. Records: {record_count}, Newest: {max_bookmark}, Oldest: {min_bookmark}')
        else:
            LOGGER.info(f'Finished syncing {stream.tap_stream_id}. No new records.')