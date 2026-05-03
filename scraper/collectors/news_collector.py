"""
Tech news article collector.

Fetches general tech news from RSS feeds for the "Relevant Tech News"
section on the homepage. Separated from the layoff-specific pipeline.
"""
import logging
import feedparser

logger = logging.getLogger(__name__)

# RSS feeds for general tech news
TECH_NEWS_FEEDS = [
    {
        'source_name': 'The Verge',
        'url': 'https://www.theverge.com/rss/index.xml',
    },
    {
        'source_name': 'TechCrunch',
        'url': 'https://techcrunch.com/feed/',
    },
    {
        'source_name': 'Ars Technica',
        'url': 'https://feeds.arstechnica.com/arstechnica/index',
    },
    {
        'source_name': 'Wired',
        'url': 'https://www.wired.com/feed/rss',
    },
]


def collect_tech_news(max_per_feed: int = 5) -> int:
    """
    Collect tech news articles from configured RSS feeds.

    Args:
        max_per_feed: Max articles to collect from each feed.

    Returns:
        Number of new articles created.
    """
    # Lazy imports to avoid Django config issues at module level
    from django.utils.timezone import now
    from news.models import NewsArticle

    created_count = 0

    for feed_config in TECH_NEWS_FEEDS:
        try:
            feed = feedparser.parse(feed_config['url'])
            entries = feed.entries[:max_per_feed]

            for entry in entries:
                url = entry.get('link', '')
                if not url:
                    continue

                # Skip if we already have this article
                if NewsArticle.objects.filter(source_url=url).exists():
                    continue

                title = (entry.get('title') or '')[:512]
                snippet = _extract_snippet(entry)
                published = _parse_date(entry)

                # Determine a topic tag from the feed category or tags
                topic_tag = _extract_topic_tag(entry)

                # Get thumbnail
                thumbnail = _extract_thumbnail(entry)

                NewsArticle.objects.create(
                    title=title,
                    snippet=snippet,
                    source=feed_config['source_name'],
                    source_url=url,
                    thumbnail_url=thumbnail,
                    topic_tag=topic_tag,
                    published_at=published,
                )
                created_count += 1

            logger.info(f'News collector: {len(entries)} entries from {feed_config["source_name"]}')

        except Exception as e:
            logger.error(f'News collector: failed to fetch {feed_config["source_name"]}: {e}')

    return created_count


def _extract_snippet(entry) -> str:
    """Extract a readable snippet from a feed entry."""
    summary = entry.get('summary', '') or ''
    # Strip HTML tags
    import re
    clean = re.sub(r'<[^>]+>', '', summary)
    return clean[:500]


def _parse_date(entry):
    """Parse published date from feed entry."""
    from datetime import datetime
    from django.utils.timezone import now
    for field in ('published_parsed', 'updated_parsed'):
        parsed = entry.get(field)
        if parsed:
            try:
                from time import mktime
                return datetime.fromtimestamp(mktime(parsed))
            except Exception:
                pass
    return now()


def _extract_topic_tag(entry) -> str | None:
    """Extract a topic/category tag from a feed entry."""
    tags = entry.get('tags', [])
    if tags:
        tag = tags[0]
        if isinstance(tag, dict):
            return tag.get('term', tag.get('label', ''))[:100]
        return str(tag)[:100]
    return None


def _extract_thumbnail(entry) -> str | None:
    """Extract thumbnail URL from a feed entry."""
    # Try media content
    media = entry.get('media_content', [])
    if media and isinstance(media, list):
        for m in media:
            url = m.get('url') or m.get('src', '')
            if url:
                return url

    # Try media thumbnail
    media_thumb = entry.get('media_thumbnail', [])
    if media_thumb and isinstance(media_thumb, list):
        url = media_thumb[0].get('url', '')
        if url:
            return url

    return None
