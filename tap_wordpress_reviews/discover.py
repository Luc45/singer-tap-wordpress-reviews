"""Discover."""
# -*- coding: utf-8 -*-
from singer import metadata
from singer.catalog import Catalog, CatalogEntry

from tap_wordpress_reviews.schema import load_schemas
from tap_wordpress_reviews.streams import STREAMS


def discover(config: dict = None) -> Catalog:  # noqa: WPS210
    """Load the Stream catalog.

    Args:
        config: Configuration dict with support_threads setting

    Returns:
        Catalog -- The catalog
    """
    raw_schemas: dict = load_schemas()
    streams: list = []

    # Check if support_threads is disabled in config
    include_support = True
    if config and not config.get('support_threads', True):
        include_support = False

    # Parse every schema
    for stream_id, schema in raw_schemas.items():
        # Skip support_threads if disabled in config
        if stream_id == 'support_threads' and not include_support:
            continue
        # Get stream metadata from STREAMS config
        stream_config = STREAMS.get(stream_id, {})

        # Fix: Use 'path' as key property for both reviews and support_threads, not 'id'
        if stream_id in ['reviews', 'support_threads']:
            key_properties = ['path']
        else:
            key_properties = stream_config.get('key_properties', ['id'])

        # Build the stream metadata dict with replication info
        stream_meta: dict = {
            'key_properties': key_properties,
            'replication_method': stream_config.get('replication_method', 'FULL_TABLE'),
            'replication_key': stream_config.get('replication_key', None),
        }

        # Create metadata with proper replication settings
        mdata: list = metadata.get_standard_metadata(
            schema=schema.to_dict(),
            key_properties=stream_meta.get('key_properties', None),
            valid_replication_keys=[stream_meta.get('replication_key')] if stream_meta.get('replication_key') else None,
            replication_method=stream_meta.get('replication_method', None),
        )

        # Add replication key to metadata if incremental
        if stream_meta.get('replication_method') == 'INCREMENTAL' and stream_meta.get('replication_key'):
            mdata = metadata.to_map(mdata)
            mdata = metadata.write(
                mdata,
                (),
                'replication-key',
                stream_meta.get('replication_key')
            )
            mdata = metadata.write(
                mdata,
                (),
                'forced-replication-method',
                'INCREMENTAL'
            )
            # Mark replication key as automatic inclusion
            mdata = metadata.write(
                mdata,
                ('properties', stream_meta.get('replication_key')),
                'inclusion',
                'automatic'
            )
            mdata = metadata.to_list(mdata)

        # Create a catalog entry with proper replication settings
        streams.append(
            CatalogEntry(
                tap_stream_id=stream_id,
                stream=stream_id,
                schema=schema,
                key_properties=stream_meta.get('key_properties', None),
                metadata=mdata,
                replication_key=stream_meta.get('replication_key', None),
                replication_method=stream_meta.get('replication_method', None),
            ),
        )
    return Catalog(streams)
