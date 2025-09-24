"""WordPress Reviews tap."""
# -*- coding: utf-8 -*-
import logging
from argparse import Namespace

from importlib.metadata import version

from singer import get_logger, utils
from singer.catalog import Catalog

from tap_wordpress_reviews.discover import discover
from tap_wordpress_reviews.sync import sync
from tap_wordpress_reviews.wordpress_reviews import WordpressReviews
from tap_wordpress_reviews.wordpress_support_threads import WordpressSupportThreads

VERSION: str = version('tap-wordpress-reviews')
LOGGER: logging.RootLogger = get_logger()
REQUIRED_CONFIG_KEYS: tuple = ('plugins',)


@utils.handle_top_exception(LOGGER)
def main() -> None:
    """Run tap."""
    # Parse command line arguments
    args: Namespace = utils.parse_args(REQUIRED_CONFIG_KEYS)

    LOGGER.info(f'>>> Running tap-wordpress-reviews v{VERSION}')

    # If discover flag was passed, run discovery mode and dump output to stdout
    if args.discover:
        catalog: Catalog = discover()
        catalog.dump()
        return

    # Otherwise run in sync mode
    if args.catalog:
        # Load command line catalog
        catalog = args.catalog
    else:
        # Load the catalog
        catalog = discover()

    # Load state if provided
    state = {}
    if args.state:
        # Extract the 'value' portion from Singer state format
        if isinstance(args.state, dict) and 'value' in args.state:
            state = args.state['value']
        else:
            state = args.state
        LOGGER.info(f'Loaded state: {args.state}')

    # Initialize WordPress clients based on selected streams
    wp_reviews = None
    wp_support = None

    # Check which streams are selected in the catalog
    selected_stream_ids = [stream.tap_stream_id for stream in catalog.get_selected_streams(state)]

    # Initialize reviews client if reviews stream is selected
    if 'reviews' in selected_stream_ids:
        wp_reviews = WordpressReviews(
            args.config['plugins'],
            args.config.get('number', 30),  # Default to 30 if not specified
        )
        LOGGER.info('Initialized WordPress Reviews client')

    # Initialize support threads client if support_threads stream is selected
    if 'support_threads' in selected_stream_ids:
        wp_support = WordpressSupportThreads(
            args.config['plugins'],
            args.config.get('number', 30),  # Default to 30 if not specified
            args.config.get('thread_filter', 'all'),  # Filter: all, active, unresolved
        )
        LOGGER.info(f'Initialized WordPress Support Threads client (filter: {args.config.get("thread_filter", "all")})')

    sync(wp_reviews=wp_reviews, wp_support=wp_support, catalog=catalog, state=state)


if __name__ == '__main__':
    main()
