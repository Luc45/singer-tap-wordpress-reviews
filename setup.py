"""Setup."""
# -*- coding: utf-8 -*-
from setuptools import find_packages, setup

setup(
    name='tap-wordpress-reviews',
    version='0.2.0',
    description='Singer.io tap for extracting data from WordPress Reviews and Support Threads',
    author='Yoast',
    url='https://github.com/Yoast/singer-tap-wordpress-reviews',
    classifiers=['Programming Language :: Python :: 3 :: Only'],
    py_modules=['tap_wordpress_reviews'],
    install_requires=[
        'beautifulsoup4>=4.13.0,<5.0',
        'httpx>=0.28.0,<0.29.0',
        'singer-python>=6.0.0,<7.0',
    ],
    entry_points="""
        [console_scripts]
        tap-wordpress-reviews=tap_wordpress_reviews:main
    """,
    packages=find_packages(),
    package_data={
        'tap_wordpress_reviews': [
            'schemas/*.json',
        ],
    },
    include_package_data=True,
)
