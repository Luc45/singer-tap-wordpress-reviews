"""WordPress support thread model."""

from typing import Optional
from bs4 import BeautifulSoup
from bs4.element import Tag

from tap_wordpress_reviews.wordpress_forum_base import WordpressForumThread


class WordpressSupportThread(WordpressForumThread):
    """A WordPress support thread."""

    def __init__(self, url: str, autoload: bool = False) -> None:
        """Initialize WordpressSupportThread.

        Arguments:
            url {str} -- The url of the thread
            autoload {bool} -- Whether to load the thread (default: {False})
        """
        super().__init__(url, autoload)

        # Support-specific fields
        self.status: Optional[str] = None  # resolved, unresolved
        self.thread_type: Optional[str] = None  # bug, question, feature request
        self.last_activity: Optional[str] = None
        self.plugin_author_response: Optional[bool] = False
        self.tags: Optional[list] = []

    def _parse(self, html: str) -> None:
        """Parse the HTML and extract support thread data."""
        soup: BeautifulSoup = BeautifulSoup(html, 'html.parser')

        # Use base class methods for common fields
        self.title = self._find_title(soup)
        self.date = self._find_date(soup)
        self.author = self._find_author(soup)
        self.text = self._find_text(soup)
        self.replies = self._find_replies_num(soup)
        self.participants = self._find_participants_num(soup)
        self.comments = self._find_replies(soup)

        # Support-specific parsing
        self.status = self._find_status(soup)
        self.thread_type = self._find_thread_type(soup)
        self.last_activity = self._find_last_activity(soup)
        self.plugin_author_response = self._check_plugin_author_response(soup)
        self.tags = self._find_tags(soup)

    def _find_status(self, soup: BeautifulSoup) -> str:
        """Determine if thread is resolved or not."""
        # Check for resolved indicator in the title or status area
        status_indicator = soup.find('span', class_='resolved')
        if status_indicator:
            return 'resolved'

        # Check in topic status
        status_list = soup.find('li', string=lambda text: text and 'Status:' in text)
        if status_list:
            status_text = status_list.get_text().lower()
            if 'resolved' in status_text:
                return 'resolved'
            elif 'not resolved' in status_text:
                return 'unresolved'

        # Default to unresolved
        return 'unresolved'

    def _find_thread_type(self, soup: BeautifulSoup) -> Optional[str]:
        """Determine the type of support thread based on content or tags."""
        title_lower = (self.title or '').lower()
        text_lower = (self.text or '').lower()

        # Check for bug indicators
        if any(word in title_lower or word in text_lower for word in
               ['bug', 'error', 'broken', 'not working', 'issue', 'problem']):
            return 'bug'

        # Check for feature request indicators
        if any(word in title_lower or word in text_lower for word in
               ['feature request', 'suggestion', 'would be nice', 'please add']):
            return 'feature_request'

        # Check for how-to questions
        if any(word in title_lower for word in ['how to', 'how do i', 'how can']):
            return 'how_to'

        # Default to general question
        return 'question'

    def _find_last_activity(self, soup: BeautifulSoup) -> Optional[str]:
        """Find the last activity timestamp."""
        # Look for last activity in the meta information
        last_activity = soup.find('li', string=lambda text: text and 'Last activity:' in text)
        if last_activity:
            activity_link = last_activity.find('a')
            if activity_link:
                return activity_link.get_text()
        return None

    def _check_plugin_author_response(self, soup: BeautifulSoup) -> bool:
        """Check if plugin author has responded to the thread."""
        # Look for plugin support representative responses
        plugin_support = soup.find('div', class_='by-plugin-support-rep')
        if plugin_support:
            return True

        # Check for specific known authors (can be expanded)
        if self.comments:
            for comment in self.comments:
                author = comment.get('author', '').lower()
                # Check if author is likely a plugin maintainer
                if any(indicator in author for indicator in
                       ['plugin author', 'plugin support', 'developer']):
                    return True

        return False

    def _find_tags(self, soup: BeautifulSoup) -> Optional[list]:
        """Find tags associated with the thread."""
        object_tags: Tag = soup.find('ul', class_='topic-tags')
        if not object_tags:
            # Try alternative location for tags
            tag_area = soup.find('div', class_='bbp-topic-tags')
            if tag_area:
                object_tags = tag_area.find('ul')

        if object_tags:
            tags_list: list = object_tags.find_all('a')
            return [tag.get_text() for tag in tags_list]
        return []

    def to_dict(self) -> dict:
        """Create a dictionary from the WordpressSupportThread object."""
        return {
            'path': self.path,
            'title': self.title,
            'date': self.date,
            'author': self.author,
            'text': self.text,
            'status': self.status,
            'thread_type': self.thread_type,
            'replies': self.replies,
            'participants': self.participants,
            'last_activity': self.last_activity,
            'plugin_author_response': self.plugin_author_response,
            'tags': self.tags,
            'comments': self.comments,
        }