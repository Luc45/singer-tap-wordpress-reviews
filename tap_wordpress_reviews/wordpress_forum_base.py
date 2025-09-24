"""Base classes for WordPress forum threads (reviews or support)."""

import logging
import time
import random
from abc import ABC, abstractmethod
from math import ceil
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from bs4.element import Tag

SCHEME: str = 'https://'
BASE_URL: str = 'wordpress.org'
WORDPRESS_THREADS_PER_PAGE: int = 30
CONNECTION_OK: int = 200

logger: logging.Logger = logging.getLogger('wordpress-forum')
logger.setLevel(logging.INFO)


class WordpressForumThread(ABC):
    """Base class for a WordPress forum thread (review or support)."""

    def __init__(self, url: str, autoload: bool = False) -> None:
        """Initialize WordpressForumThread.

        Arguments:
            url {str} -- The url of the thread
            autoload {bool} -- Whether to load the thread (default: {False})
        """
        self.path = self._parse_url(url)
        self.loaded = False

        # Common fields
        self.title: Optional[str] = None
        self.date: Optional[str] = None
        self.author: Optional[str] = None
        self.text: Optional[str] = None
        self.replies: Optional[int] = None
        self.participants: Optional[int] = None
        self.comments: Optional[list] = []

        if autoload:
            self.load()

    def _parse_url(self, url: str) -> str:
        """Return the path of the URL."""
        parsed_url = urlparse(url)
        return parsed_url.path

    def load(self) -> None:
        """Load the thread."""
        logging.info(f'Loading thread: {self.path}')
        url: str = f'{SCHEME}{BASE_URL}{self.path}'

        # Polite delay between requests (1-2 seconds)
        time.sleep(random.uniform(1.0, 2.0))

        client: httpx.Client = httpx.Client(
            http2=False,
            timeout=httpx.Timeout(30.0)  # 30 second timeout for slow pages
        )
        response: httpx._models.Response = client.get(url, follow_redirects=True)

        if response.status_code != CONNECTION_OK:
            raise ConnectionError(f'Connection failed: {response.status_code}')

        self._parse(response.text)
        self.loaded = True
        logging.debug(f'Loaded thread: {self.path}')

    @abstractmethod
    def _parse(self, html: str) -> None:
        """Parse the HTML and extract thread data.

        Must be implemented by subclasses to handle specific thread types.
        """
        pass

    def _find_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract thread title."""
        object_title: Tag = soup.find('h1', class_='page-title')
        if not object_title:
            return None
        return object_title.get_text()

    def _find_date(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract thread creation date."""
        object_date: Tag = soup.find('a', class_='bbp-topic-permalink')
        if not object_date:
            return None
        date_text: str = object_date.get('title', '')

        try:
            reply_date: Optional[datetime] = (
                datetime.strptime(date_text, '%B %d, %Y at %I:%M %p')
            )
        except ValueError:
            return None

        if reply_date:
            return reply_date.replace(tzinfo=timezone.utc).isoformat()
        return None

    def _find_author(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract thread author."""
        object_author: Tag = soup.find('span', class_='bbp-author-name')
        if object_author:
            return object_author.get_text()
        return None

    def _find_text(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract thread text content."""
        object_p: Tag = soup.find(
            'div',
            class_='bbp-topic-content',
        ).find_all('p')
        if not object_p:
            return None

        object_text: list = [text.get_text() for text in object_p]
        return '\n'.join(object_text)

    def _find_replies_num(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract number of replies."""
        object_replies: Tag = soup.find('li', class_='reply-count')
        if not object_replies:
            return None
        return int(object_replies.get_text().partition(' ')[0])

    def _find_participants_num(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract number of participants."""
        object_replies: Tag = soup.find('li', class_='voice-count')
        if not object_replies:
            return None
        return int(object_replies.get_text().partition(' ')[0])

    def _find_replies(self, soup: BeautifulSoup) -> Optional[List[dict]]:
        """Extract all replies/comments."""
        replies: Tag = soup.find_all('div', 'reply')
        comments: list = []

        if not replies:
            return None

        for reply in replies:
            comment: dict = {}
            # Author
            object_reply_author: Tag = reply.find('span', 'bbp-author-name')
            if object_reply_author:
                comment['author'] = object_reply_author.get_text()

            # Reply text
            object_reply_content: Tag = reply.find(
                'div',
                class_='bbp-reply-content',
            )
            if object_reply_content:
                object_text: list = [
                    text.get_text() for text in object_reply_content.find_all('p')
                ]
                comment['comment'] = '\n'.join(object_text)

            # Date
            object_reply_date: Tag = reply.find(
                'p',
                class_='bbp-reply-post-date',
            )
            if object_reply_date:
                date_object: Tag = object_reply_date.find('a')
                if date_object:
                    date_text: str = date_object.get('title', '')
                    try:
                        reply_date: Optional[datetime] = (
                            datetime.strptime(
                                date_text,
                                '%B %d, %Y at %I:%M %p',
                            )
                        )
                    except ValueError:
                        reply_date = None
                    comment['date'] = (
                        reply_date.isoformat() if reply_date else None
                    )

            comments.append(comment)

        return comments

    @abstractmethod
    def to_dict(self) -> dict:
        """Convert thread to dictionary. Must be implemented by subclasses."""
        pass


class WordpressForumThreadsList(ABC):
    """Base class for listing WordPress forum threads."""

    def __init__(self, plugin: str) -> None:
        """Initialize thread list.

        Arguments:
            plugin {str} -- Name of WordPress plugin
        """
        self.plugin = plugin
        self.thread_no = 1
        self.page_html: Dict[int, list] = {}
        self.threads: list = []
        self.more: bool = False
        self.loaded: bool = False

    def __iter__(self):
        """Iterate object."""
        return self

    def __next__(self) -> WordpressForumThread:
        """Iterate to next thread."""
        thread_no: int = self.thread_no
        self.thread_no += 1
        return self._get_thread(thread_no)

    def load(self, page: int) -> List[WordpressForumThread]:
        """Load a page of threads."""
        path: str = self._link(page)

        logger.info(f'Loading threads page: {BASE_URL}{path}')
        url: str = f'{SCHEME}{BASE_URL}{path}'

        # Polite delay between requests (1-2 seconds)
        time.sleep(random.uniform(1.0, 2.0))

        client: httpx.Client = httpx.Client(
            http2=False,
            timeout=httpx.Timeout(30.0)  # 30 second timeout for slow pages
        )
        response: httpx._models.Response = client.get(url, follow_redirects=True)

        if response.status_code != CONNECTION_OK:
            raise ConnectionError(f'Connection failed: {response.status_code}')

        self._parse(response.text)
        self.loaded = True
        logger.debug(f'Loaded threads page: {BASE_URL}{path}')
        return self.threads

    def _get_thread(self, number: int) -> WordpressForumThread:
        """Get thread by number, loading pages as needed."""
        page: int = ceil(number / WORDPRESS_THREADS_PER_PAGE)
        if page not in self.page_html:
            self.page_html[page] = self.load(page)

        thread_no = number - (page * WORDPRESS_THREADS_PER_PAGE)
        if len(self.page_html[page]) < WORDPRESS_THREADS_PER_PAGE:
            thread_no += WORDPRESS_THREADS_PER_PAGE - len(self.page_html[page])

        if thread_no > 0:
            raise StopIteration

        thread = self.page_html[page][thread_no - 1]
        thread.load()
        return thread

    @abstractmethod
    def _link(self, page: int) -> str:
        """Create URL path for the given page. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def _parse(self, html: str) -> None:
        """Parse HTML of thread list page. Must be implemented by subclasses."""
        pass