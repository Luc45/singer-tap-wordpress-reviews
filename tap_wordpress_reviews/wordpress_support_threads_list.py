"""WordPress Support Threads List model."""

from typing import List
from bs4 import BeautifulSoup

from tap_wordpress_reviews.wordpress_forum_base import WordpressForumThreadsList
from tap_wordpress_reviews.wordpress_support_thread import WordpressSupportThread


class WordpressSupportThreadsList(WordpressForumThreadsList):
    """Object list of WordPress support threads."""

    def __init__(self, plugin: str, thread_filter: str = 'all') -> None:
        """Initialize list of WordPress support threads.

        Arguments:
            plugin {str} -- Name of WordPress plugin
            thread_filter {str} -- Filter type: 'all', 'active', 'unresolved' (default: 'all')
        """
        super().__init__(plugin)
        self.thread_filter = thread_filter

    def _link(self, page: int) -> str:
        """Create a valid plugin support thread link.

        Arguments:
            page {int} -- Page number

        Returns:
            str -- URL path
        """
        # Build base path based on filter
        if self.thread_filter == 'active':
            base_path = f'/support/plugin/{self.plugin}/active'
        elif self.thread_filter == 'unresolved':
            base_path = f'/support/plugin/{self.plugin}/unresolved'
        else:
            base_path = f'/support/plugin/{self.plugin}'

        # Add page number if not first page
        if page == 1:
            return f'{base_path}/'
        return f'{base_path}/page/{page}/'

    def _parse(self, html: str) -> None:
        """Parse the HTML of the support threads list page.

        Arguments:
            html {str} -- HTML of the WordPress support threads list
        """
        soup: BeautifulSoup = BeautifulSoup(html, 'html.parser')

        # Find all thread entries (same structure as reviews)
        threads: list = soup.find_all('ul', class_='topic')

        thread_objects: list = [
            topic.find('a', class_='bbp-topic-permalink') for topic in threads
        ]

        thread_urls: list = [topic.get('href') for topic in thread_objects if topic]

        # Extract additional metadata from the list page
        self.threads = []
        for i, url in enumerate(thread_urls):
            thread = WordpressSupportThread(url)

            # Try to extract status from list page (if marked as resolved)
            if i < len(threads):
                topic_html = threads[i]
                # Check for resolved indicator
                if topic_html.find('span', class_='resolved') or \
                   topic_html.find('generic', string='Resolved'):
                    thread.status = 'resolved'

            self.threads.append(thread)

        # Check if there are more pages
        self.more = soup.find('a', class_='next page-numbers') is not None