"""Wordpress Reviews List model."""

import logging
from math import ceil
from typing import List

import httpx
from bs4 import BeautifulSoup

from tap_wordpress_reviews.wordpress_review import WordpressReview

SCHEME: str = 'https://'
BASE_URL: str = 'wordpress.org'
WORDPRESS_REVIEWS_PER_PAGE: int = 30
CONNECTION_OK: int = 200


logger: logging.Logger = logging.getLogger('review-downloader')
logger.setLevel(logging.INFO)


logging.basicConfig(
    level=logging.INFO,
    format=(
        '%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s] '  # noqa: WPS
        '%(message)s'
    ),
    handlers=[
        logging.StreamHandler(),
    ],
)


class WordpressReviewsList(object):
    """Object list of Wordpress reviews."""

    def __init__(self, plugin: str) -> None:
        """Initialize list of Wordpress reviews.

        Arguments:
            plugin {str} -- Name of Wordpress plugin
        """
        self.plugin = plugin
        self.review_no = 1
        self.page_html: dict = {}
        self.reviews: list = []
        self.more: bool
        self.loaded: bool

    def __iter__(self):
        """Iterate object.

        Returns:
            WordpressReviewsList -- The current object
        """
        return self

    def __next__(self) -> WordpressReview:
        """Iterate object.

        Returns:
            WordpressReview -- Review object
        """
        review_no: int = self.review_no
        self.review_no += 1
        return self._wp_review(review_no)

    def load(self, page: int) -> List[WordpressReview]:
        """Load the review page.

        Arguments:
            page {[int]} -- Wordpress page path

        Raises:
            ConnectionError: When the connection fails

        Returns:
            [List[WordpressReview]] -- A list of reviews
        """
        path: str = self._link(page)

        logger.info(f'Loading reviews page: {BASE_URL}{path}')
        url: str = f'{SCHEME}{BASE_URL}{path}'

        client: httpx.Client = httpx.Client(http2=False)
        response: httpx._models.Response = client.get(url, follow_redirects=True)  # noqa: WPS437

        if response.status_code != CONNECTION_OK:
            raise ConnectionError(f'Connection failed: {response.status_code}')

        self._parse(response.text)
        self.loaded = True
        logger.debug(f'Loaded reviews page: {BASE_URL}{path}')
        return self.reviews

    def _wp_review(self, number: int) -> WordpressReview:
        """Find the correct page on Wordpress.

        Arguments:
            no {int} -- Review number

        Returns:
            WordpressReview -- Wordpress review
        """
        page: int = ceil(number / WORDPRESS_REVIEWS_PER_PAGE)
        if page not in self.page_html:
            # load page
            self.page_html[page] = self.load(page)

        review_no = number - (page * WORDPRESS_REVIEWS_PER_PAGE)
        if len(self.page_html[page]) < WORDPRESS_REVIEWS_PER_PAGE:
            review_no += WORDPRESS_REVIEWS_PER_PAGE - len(self.page_html[page])

        # No more reviews
        if review_no > 0:
            raise StopIteration

        review = self.page_html[page][review_no - 1]
        review.load()
        return review

    def _link(self, page: int) -> str:
        """Create a valid plugin link.

        Arguments:
            page {int} -- Page number

        Returns:
            str -- URL path
        """
        if page == 1:
            return f'/support/plugin/{self.plugin}/reviews/'
        return f'/support/plugin/{self.plugin}/reviews/page/{page}/'

    def _parse(self, html: str) -> None:
        """Parse the html of the review page list.

        Arguments:
            html {str} -- HTML of the wordpress reviews list
        """
        soup: BeautifulSoup = BeautifulSoup(html, 'html.parser')

        reviews: list = soup.find_all('ul', class_='topic')

        review_objects: list = [
            topic.find('a', class_='bbp-topic-permalink') for topic in reviews
        ]

        review_urls: list = [topic.get('href') for topic in review_objects]

        self.reviews = [WordpressReview(url) for url in review_urls]

        self.more = soup.find('a', class_='next page-numbers') is not None
