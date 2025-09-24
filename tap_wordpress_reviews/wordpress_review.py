"""Wordpress review model."""

import datetime
import logging
from typing import List, Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from bs4.element import Tag

SCHEME: str = 'https://'
BASE_URL: str = 'wordpress.org'
STATUS_OK: int = 200
CONNECTION_OK: int = 200


class WordpressReview(object):  # noqa: WPS214, WPS230
    """A wordpress review."""

    def __init__(self, url: str, autoload: bool = False) -> None:
        """Initialize WordpressReview.

        Arguments:
            url {str} -- The url of the review

        Keyword Arguments:
            autoload {bool} -- Whether to load the review (default: {False})
        """
        self.path = self._parse_url(url)
        if autoload:
            self.load()

        self.title: Optional[str] = None
        self.date: Optional[str] = None
        self.tags: Optional[list] = []
        self.rating: Optional[int] = None
        self.author: Optional[str] = None
        self.text: Optional[str] = None
        self.replies: Optional[int] = None
        self.participants: Optional[int] = None
        self.comments: Optional[list] = []
        self.support: Optional[str] = None
        self.support_comment: Optional[str] = None

    def __str__(self) -> str:
        """Create a string from the object.

        Returns:
            [str] -- String of the object
        """
        return (
            f'{self.path}\n'  # noqa: WPS221
            f'{self.title}\n'
            f'{self.date}\n'
            f'Tags: {self.tags}\n'
            f'{self.rating} stars\n'
            f'by {self.author}\n'
            f'{self.text}\n'
            f'Replies: {self.replies}\n'
            f'Participants: {self.participants}\n'
            f'Support: {self.support}\n'
            f'Support comment: {self.support_comment}'
        )

    def load(self) -> None:
        """Load the review.

        Raises:
            ConnectionError: When the connection to the url fails
        """
        logging.info(f'Loading review: {self.path}')
        url: str = f'{SCHEME}{BASE_URL}{self.path}'

        client: httpx.Client = httpx.Client(http2=False)
        response: httpx._models.Response = client.get(url, follow_redirects=True)  # noqa: WPS437

        if response.status_code != CONNECTION_OK:
            raise ConnectionError(f'Connection failed: {response.status_code}')

        self._parse(response.text)
        self.loaded = True
        logging.debug(f'Loaded review: {self.path}')

    def to_dict(self) -> dict:
        """Create a dictionary from the WordpressReview object.

        Returns:
            dict -- A dictionary of the WordpressReview object
        """
        return {
            'path': self.path,
            'title': self.title,
            'date': self.date,
            'tags': self.tags,
            'rating': self.rating,
            'author': self.author,
            'text': self.text,
            'replies': self.replies,
            'participants': self.participants,
            'comments': self.comments,
            'support': self.support,
            'support_comment': self.support_comment,
        }

    def tag(self, number: int) -> Optional[str]:
        """Return the nth tag from the tag list.

        Arguments:
            number {int} -- Tag n

        Returns:
            Optional[str] -- The nth tag in the tag list
        """
        if self.tags:
            if number > len(self.tags):
                return None
            return self.tags[number - 1]
        return None

    def _parse_url(self, url: str) -> str:
        """Return the path of the URL.

        Arguments:
            url {str} -- Input URL

        Returns:
            str -- Path of the URL
        """
        parsed_url = urlparse(url)
        return parsed_url.path

    def _parse(self, html: str) -> None:
        """Parse the HTML and create an object.

        Arguments:
            html {str} -- The HTML returned from the connection
        """
        soup: BeautifulSoup = BeautifulSoup(html, 'html.parser')

        self.title = self._find_title(soup)
        self.date = self._find_date(soup)
        self.tags = self._find_tags(soup)
        self.rating = self._find_rating(soup)
        self.author = self._find_author(soup)
        self.text = self._find_text(soup)
        self.replies = self._find_replies_num(soup)
        self.participants = self._find_participants_num(soup)
        self.comments = self._find_replies(soup)
        self.support = self._find_support(soup)
        self.support_comment = self._find_support_comment(soup)

    def _find_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Title of the review.

        Arguments:
            soup {BeautifulSoup} -- Soup object

        Returns:
            str -- Title of review
        """
        object_title: Tag = soup.find('h1', class_='page-title')

        if not object_title:
            return None

        return object_title.get_text()

    def _find_date(self, soup) -> Optional[str]:
        """Return the  date the review was posted."""
        object_date: Tag = soup.find('a', class_='bbp-topic-permalink')
        if not object_date:
            return None
        date_text: str = object_date.get('title', '')

        try:
            reply_date: Optional[datetime.datetime] = (
                datetime.datetime.strptime(date_text, '%B %d, %Y at %I:%M %p')
            )
        except ValueError:
            reply_date = None

        if reply_date:
            return reply_date.astimezone(
                datetime.timezone.utc,
            ).isoformat()
        return None

    def _find_tags(self, soup: BeautifulSoup) -> Optional[list]:
        """Find tags of the review.

        Arguments:
            soup {BeautifulSoup} -- Soup object

        Returns:
            Optional[list] -- List of tags
        """
        object_tags: Tag = soup.find('ul', class_='topic-tags')

        if not object_tags:
            return None

        tags_list: list = object_tags.find_all('a')
        return [tag.get_text() for tag in tags_list]

    def _find_rating(self, soup: BeautifulSoup) -> Optional[int]:
        """Return rating of review.

        Arguments:
            soup {BeautifulSoup} -- Soup object

        Returns:
            int -- Review rating
        """
        object_rating: Tag = soup.find('div', class_='wporg-ratings')

        if not object_rating:
            return None

        rating_string: str = object_rating.get('title')

        return int(int(rating_string[0]))

    def _find_author(self, soup: BeautifulSoup) -> Optional[str]:
        """Return author of review.

        Arguments:
            Soup {[type]} -- Soup object

        Returns:
            [type] -- Author of review
        """
        object_author: Tag = soup.find('span', class_='bbp-author-name')

        if object_author:
            return object_author.get_text()
        return None

    def _find_text(self, soup: BeautifulSoup) -> Optional[str]:
        """Review text.

        Arguments:
            soup {BeautifulSoup} -- Soup object

        Returns:
            str -- Text of review
        """
        object_p: Tag = soup.find(
            'div',
            class_='bbp-topic-content',
        ).find_all('p')
        if not object_p:
            return None

        object_text: list = [text.get_text() for text in object_p]
        return '\n'.join(object_text)

    def _find_replies_num(self, soup: BeautifulSoup) -> Optional[int]:
        """Return number of replies in the thread.

        Arguments:
            soup {BeautifulSoup} -- Soup object

        Returns:
            int -- Number of replies
        """
        object_replies: Tag = soup.find('li', class_='reply-count')

        if not object_replies:
            return None

        return int(object_replies.get_text().partition(' ')[0])

    def _find_participants_num(self, soup: BeautifulSoup) -> Optional[int]:
        """Return number of participants.

        Arguments:
            soup {BeautifulSoup} -- Soup object

        Returns:
            int -- Number of participants in the thread
        """
        object_replies: Tag = soup.find('li', class_='voice-count')

        if not object_replies:
            return None

        return int(object_replies.get_text().partition(' ')[0])

    def _find_replies(  # noqa: WPS210, WPS231
        self,
        soup: BeautifulSoup,
    ) -> Optional[List[dict]]:
        """Return a tuple of replies.

        Arguments:
            soup {BeautifulSoup} -- Soup object

        Returns:
            Optional[str] -- Name of the support worker
        """
        replies: Tag = soup.find_all('div', 'reply')
        comments: list = []

        if not replies:
            return None

        for reply in replies:
            comment: dict = {}
            # Author
            object_reply_author: Tag = reply.find('span', 'bbp-author-name')
            if object_reply_author:
                reply_author: str = object_reply_author.get_text()
                comment['author'] = reply_author

            # Reply
            object_reply_content: Tag = reply.find(
                'div',
                class_='bbp-reply-content',
            )

            if object_reply_content:
                # Find paragraphs
                object_text: list = [
                    text.get_text() for text in object_reply_content.find_all(
                        'p',
                    )
                ]
                reply_text: str = '\n'.join(object_text)

                comment['comment'] = reply_text

            # Find date
            object_reply_date: Tag = reply.find(
                'p',
                class_='bbp-reply-post-date',
            )

            if object_reply_date:
                date_object: Tag = object_reply_date.find('a')
                if date_object:
                    date_text: str = date_object.get('title', '')
                    try:
                        reply_date: Optional[datetime.datetime] = (
                            datetime.datetime.strptime(
                                date_text,
                                '%B %d, %Y at %I:%M %p',
                            )
                        )
                    except ValueError:
                        reply_date = None  # noqa: WPS220
                    comment['date'] = (
                        reply_date.isoformat() if reply_date else None
                    )

            # Save to list
            comments.append(comment)

        return comments

    def _find_support(self, soup: BeautifulSoup) -> Optional[str]:
        """Return name of the support worker if available.

        Arguments:
            soup {BeautifulSoup} -- Soup object

        Returns:
            Optional[str] -- Name of the support worker
        """
        object_support_comment: Tag = soup.find('div', 'by-plugin-support-rep')

        if not object_support_comment:
            return None

        object_support: Tag = object_support_comment.find(
            'span',
            'bbp-author-name',
        )
        if not object_support:
            return None
        return object_support.get_text()

    def _find_support_comment(self, soup: BeautifulSoup) -> Optional[str]:
        """Support worker comment if available.

        Arguments:
            soup {[BeautifulSoup]} -- Soup object

        Returns:
            Optional[str] -- Comment by support worker
        """
        object_support_comment: Tag = soup.find('div', 'by-plugin-support-rep')

        if not object_support_comment:
            return None

        object_support_comment_block: Tag = object_support_comment.find(
            'div',
            class_='bbp-reply-content',
        )

        if not object_support_comment_block:
            return None

        object_text: list = [
            text.get_text() for text in object_support_comment_block.find_all(
                'p',
            )
        ]
        return '\n'.join(object_text)
