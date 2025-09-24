"""Streams."""
# -*- coding: utf-8 -*-

from types import MappingProxyType

# Streams metadata - properly structured for discover.py
STREAMS: MappingProxyType = MappingProxyType({
    'reviews': {
        'key_properties': ['path'],  # Using path as the unique identifier (must be a list)
        'replication_method': 'INCREMENTAL',
        'replication_key': 'date',  # The date field from schema will be the bookmark
        'bookmark': 'date',  # Legacy field for backward compatibility
        'replication_keys': ['date'],  # List format for metadata.get_standard_metadata
    },
    'support_threads': {
        'key_properties': ['path'],  # Using path as the unique identifier (must be a list)
        'replication_method': 'INCREMENTAL',
        'replication_key': 'date',  # The date field from schema will be the bookmark
        'bookmark': 'date',  # Legacy field for backward compatibility
        'replication_keys': ['date'],  # List format for metadata.get_standard_metadata
    },
})
