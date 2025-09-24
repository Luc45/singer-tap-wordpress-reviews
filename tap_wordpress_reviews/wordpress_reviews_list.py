"""Improved WordPress reviews list with date extraction."""

from typing import List, Tuple, Optional
from datetime import datetime
import logging
import re
import httpx
from bs4 import BeautifulSoup

from tap_wordpress_reviews.wordpress_review import WordpressReview

LOGGER = logging.getLogger(__name__)

SCHEME: str = 'https://'
BASE_URL: str = 'wordpress.org'


class WordpressReviewInfo:
    """Container for review info with approximate date."""

    def __init__(self, link: str, title: str, rating: int, approximate_date: Optional[datetime]):
        self.link = link
        self.title = title
        self.rating = rating
        self.approximate_date = approximate_date

    def get_review(self) -> WordpressReview:
        """Create a WordpressReview instance for this review."""
        review = WordpressReview(self.link)
        review.title = self.title
        review.rating = self.rating
        return review


class ImprovedWordpressReviewsList:
    """Enhanced reviews list that extracts approximate dates from the page."""

    def __init__(self, plugin: str):
        """Initialize with plugin name."""
        self.plugin = plugin

    def _get_html(self, page: int = 1) -> Optional[str]:
        """Get HTML content for a reviews page."""
        url = f"{SCHEME}{BASE_URL}/support/plugin/{self.plugin}/reviews/"
        if page > 1:
            url += f"page/{page}/"

        try:
            response = httpx.get(url, timeout=30)
            if response.status_code == 200:
                return response.text
        except Exception as e:
            LOGGER.warning(f"Failed to fetch page {page}: {e}")
        return None

    def _get_soup(self, html: str) -> BeautifulSoup:
        """Parse HTML into BeautifulSoup object."""
        return BeautifulSoup(html, 'html.parser')

    def load_page(self, page: int = 1) -> Tuple[List[WordpressReviewInfo], bool]:
        """Load a page and extract review info with approximate dates.

        Returns:
            Tuple of (list of WordpressReviewInfo, has_more_pages)
        """
        # Load the page HTML
        html = self._get_html(page)
        if not html:
            return [], False

        soup = self._get_soup(html)
        reviews_info = []

        # Find all review items
        review_items = soup.find_all('li', class_='bbp-body')

        for item in review_items:
            # Get the review link
            link_elem = item.find('a', class_='bbp-topic-permalink')
            if not link_elem:
                continue

            link = link_elem.get('href')
            title = link_elem.get_text(strip=True)

            # Extract rating from the title's stars
            rating = 1  # default
            rating_elem = item.find('div', class_='wporg-ratings')
            if rating_elem:
                # Count filled stars
                filled_stars = rating_elem.find_all('span', class_='star dashicons dashicons-star-filled')
                rating = len(filled_stars) if filled_stars else 1

            # Try to extract date from the "freshness" link
            approximate_date = None
            freshness_elem = item.find('a', class_='bbp-topic-freshness-link')
            if freshness_elem:
                time_text = freshness_elem.get_text(strip=True).lower()
                approximate_date = self._parse_relative_time(time_text)

            # Alternative: look for any time-related text
            if not approximate_date:
                for elem in item.find_all(text=True):
                    text = elem.strip().lower()
                    if any(word in text for word in ['ago', 'year', 'month', 'week', 'day', 'hour']):
                        approximate_date = self._parse_relative_time(text)
                        if approximate_date:
                            break

            reviews_info.append(WordpressReviewInfo(link, title, rating, approximate_date))

        # Check if there are more pages
        has_more = self._has_next_page(soup)

        return reviews_info, has_more

    def _parse_relative_time(self, time_text: str) -> Optional[datetime]:
        """Parse relative time text like '2 months ago' into a datetime.

        This is approximate but good enough for filtering.
        """
        from datetime import timedelta, timezone

        now = datetime.now(timezone.utc)
        time_text = time_text.lower().strip()

        # Patterns to match
        patterns = [
            (r'(\d+)\s*year', lambda n: timedelta(days=n*365)),
            (r'(\d+)\s*month', lambda n: timedelta(days=n*30)),
            (r'(\d+)\s*week', lambda n: timedelta(weeks=n)),
            (r'(\d+)\s*day', lambda n: timedelta(days=n)),
            (r'(\d+)\s*hour', lambda n: timedelta(hours=n)),
            (r'(\d+)\s*minute', lambda n: timedelta(minutes=n)),
        ]

        for pattern, delta_func in patterns:
            match = re.search(pattern, time_text)
            if match:
                number = int(match.group(1))
                return now - delta_func(number)

        # Special cases
        if 'yesterday' in time_text:
            return now - timedelta(days=1)
        elif 'today' in time_text or 'just now' in time_text:
            return now

        return None

    def _has_next_page(self, soup) -> bool:
        """Check if there's a next page link."""
        pagination = soup.find('div', class_='bbp-pagination')
        if pagination:
            next_link = pagination.find('a', class_='next')
            return next_link is not None
        return False