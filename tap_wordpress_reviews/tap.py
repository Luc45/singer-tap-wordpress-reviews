"""WordPress Reviews tap."""
# -*- coding: utf-8 -*-
import logging
from argparse import Namespace

import pkg_resources
from singer import get_logger, utils
from singer.catalog import Catalog

from tap_wordpress_reviews.discover import discover
from tap_wordpress_reviews.sync import sync
from tap_wordpress_reviews.wordpress_reviews import WordpressReviews

VERSION: str = pkg_resources.get_distribution(
    'tap-wordpress-reviews',
).version
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
        state = args.state
        LOGGER.info(f'Loaded state: {state}')

    # Initialize WordPress client
    wp: WordpressReviews = WordpressReviews(
        args.config['plugins'],
        args.config.get('number', 30),  # Default to 30 if not specified
    )

    sync(wp, catalog, state)


if __name__ == '__main__':
    main()
