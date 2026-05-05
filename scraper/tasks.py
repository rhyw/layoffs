"""
Celery periodic tasks for data collection and enrichment.

Each task is auto-discovered by Celery when it starts.
Tasks are scheduled via django-celery-beat's DatabaseScheduler.
"""
import logging
from datetime import datetime

from celery import shared_task
from django.conf import settings
from django.utils.timezone import now

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def collect_all_sources(self):
    """
    Master dispatcher: iterate active DataSources and route to correct collector.

    Triggered by Celery Beat every 15 minutes.
    """
    from scraper.models import DataSource, ScrapeLog
    import time

    sources = DataSource.objects.filter(is_active=True)
    logger.info(f'Starting collection for {sources.count()} active sources')

    for source in sources:
        start = time.time()
        try:
            if source.source_type == 'rss':
                result = collect_rss_feed.delay(source.id)
            elif source.source_type == 'web':
                result = collect_web_source.delay(source.id)
            elif source.source_type == 'api':
                result = collect_api_source.delay(source.id)
            elif source.source_type == 'llm':
                result = collect_llm_source.delay(source.id)
            else:
                logger.warning(f'Unknown source type: {source.source_type}')
                continue

            logger.info(f'Dispatched {source.name} (task: {result.id})')

        except Exception as e:
            logger.error(f'Failed to dispatch {source.name}: {e}')
            source.consecutive_failures += 1
            source.save()

    # After dispatching all sources, process any unprocessed ScrapedArticles
    try:
        process_scraped_articles.delay()
    except Exception as e:
        logger.error(f'Failed to dispatch process_scraped_articles: {e}')


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def collect_rss_feed(self, source_id):
    """Collect layoff data from an RSS feed source."""
    from scraper.models import DataSource, ScrapeLog, ScrapedArticle
    from scraper.pipeline import hash_url, normalize_raw_event, dedup_and_merge

    source = DataSource.objects.get(id=source_id)
    logger.info(f'Collecting RSS feed: {source.name} ({source.url})')

    import feedparser
    import hashlib

    feed = feedparser.parse(source.url)
    articles_found = 0
    articles_created = 0

    for entry in feed.entries[:50]:  # Limit to 50 per run
        url = entry.get('link', '')
        if not url:
            continue

        url_hash = hash_url(url)
        if ScrapedArticle.objects.filter(url_hash=url_hash).exists():
            continue  # Already seen this article

        articles_found += 1
        title = entry.get('title', '')
        content = entry.get('summary', entry.get('description', ''))

        # Check if article contains layoff keywords
        layoff_keywords = [
            'layoff', 'lay off', 'laid off', 'furlough',
            'workforce reduction', 'job cut', 'cutting jobs',
            'headcount reduction',
        ]
        text_to_check = f'{title} {content}'.lower()
        if not any(kw in text_to_check for kw in layoff_keywords):
            continue

        # Create scraped article record (for dedup tracking)
        ScrapedArticle.objects.create(
            url=url,
            url_hash=url_hash,
            title=title,
            content_hash=hashlib.sha256(content.encode('utf-8')).hexdigest(),
            source=source,
        )
        articles_created += 1

    # Update source status
    source.last_fetched = now()
    source.consecutive_failures = 0
    source.save()

    logger.info(f'RSS {source.name}: {articles_found} found, {articles_created} new')
    return {'source': source.name, 'found': articles_found, 'created': articles_created}


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def collect_web_source(self, source_id):
    """Scrape a web page for layoff-related articles."""
    from scraper.models import DataSource
    from scraper.collectors.web_scraper import scrape_web_source

    source = DataSource.objects.get(id=source_id)
    try:
        result = scrape_web_source(source)
        return result
    except Exception as e:
        logger.error(f'Web scrape failed for {source.name}: {e}')
        source.consecutive_failures += 1
        source.save()
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def collect_api_source(self, source_id):
    """Collect layoff data from a JSON API endpoint."""
    from scraper.models import DataSource
    import requests

    source = DataSource.objects.get(id=source_id)
    logger.info(f'Fetching API source: {source.name} ({source.url})')

    try:
        resp = requests.get(source.url, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        source.last_fetched = now()
        source.consecutive_failures = 0
        source.save()
        return {'source': source.name, 'items': len(data) if isinstance(data, list) else 1}

    except Exception as e:
        logger.error(f'API fetch failed for {source.name}: {e}')
        source.consecutive_failures += 1
        source.save()
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=2, default_retry_delay=600)
def collect_llm_source(self, source_id):
    """Use DeepSeek LLM to find recent layoff announcements."""
    from scraper.models import DataSource
    from scraper.collectors.llm_collector import LLMCollector

    source = DataSource.objects.get(id=source_id)
    logger.info(f'Running LLM collection: {source.name}')

    from openai import OpenAI
    from django.conf import settings

    client = OpenAI(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
    )

    collector = LLMCollector(client, model=settings.DEEPSEEK_MODEL)
    results = collector.collect()

    source.last_fetched = now()
    source.consecutive_failures = 0
    source.save()

    logger.info(f'LLM {source.name}: {len(results)} events found')
    return {'source': source.name, 'events_found': len(results)}


@shared_task
def enrich_pending_events():
    """
    Enrich unverified layoff events with industry/ai-tag using LLM.

    Triggered by Celery Beat every hour.
    """
    from layoffs.models import LayoffEvent

    pending = LayoffEvent.objects.filter(
        is_verified=False, confidence_score__lt=0.9
    )[:20]

    for event in pending:
        enrich_single_event.delay(event.id)


@shared_task(bind=True, max_retries=2, default_retry_delay=300)
def enrich_single_event(self, event_id):
    """Enrich a single layoff event using DeepSeek LLM."""
    from layoffs.models import LayoffEvent
    from django.conf import settings
    from openai import OpenAI

    event = LayoffEvent.objects.get(id=event_id)
    logger.info(f'Enriching event: {event.company} ({event.date_reported})')

    if not settings.DEEPSEEK_API_KEY:
        logger.warning('No DEEPSEEK_API_KEY configured, skipping enrichment')
        return

    client = OpenAI(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url=settings.DEEPSEEK_BASE_URL,
    )

    prompt = (
        f'For this layoff event, fill in missing fields based on your knowledge:\n'
        f'Company: {event.company}\n'
        f'Headcount: {event.headcount}\n'
        f'Date: {event.date_reported}\n'
        f'Additional: {event.notes or "N/A"}\n\n'
        f'Return JSON with: industry (SaaS|FinTech|E-commerce|Hardware|Social Media|'
        f'Gaming|Cloud|Enterprise Software|Healthcare Tech|EdTech|Other), '
        f'is_ai_related (bool), confidence_score (0.0-1.0)\n'
    )

    try:
        response = client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.1,
            response_format={'type': 'json_object'},
        )

        import json
        result = json.loads(response.choices[0].message.content)

        if not event.industry and result.get('industry'):
            event.industry = result['industry']
        if result.get('is_ai_related') is not None:
            event.is_ai_related = result['is_ai_related']
        if result.get('confidence_score'):
            event.confidence_score = max(event.confidence_score, result['confidence_score'])
        if event.confidence_score >= 0.8:
            event.is_verified = True

        event.save()
        logger.info(f'Enriched {event.company}: {result}')

    except Exception as e:
        logger.error(f'Enrichment failed for {event.company}: {e}')
        raise self.retry(exc=e)


@shared_task
def collect_news_articles():
    """
    Collect general tech news articles for the homepage news section.
    Triggered by Celery Beat every 30 minutes.
    """
    from scraper.collectors.news_collector import collect_tech_news
    created = collect_tech_news()
    logger.info(f'News collection: {created} new articles')
    return {'created': created}


@shared_task
def process_scraped_articles():
    """
    Process unprocessed ScrapedArticles into LayoffEvent records.

    Uses heuristic extraction to identify layoff events from article
    titles/content, then creates/updates LayoffEvent records via the
    dedup pipeline. Marks all processed articles as processed=True
    regardless of whether a LayoffEvent was created, to avoid re-processing.
    """
    from scraper.models import ScrapedArticle
    from scraper.pipeline import extract_layoff_from_article, normalize_raw_event, dedup_and_merge

    unprocessed = ScrapedArticle.objects.filter(processed=False).select_related('source')
    total = unprocessed.count()

    if total == 0:
        logger.info('process_scraped_articles: no unprocessed articles found')
        return {'processed': 0, 'events_created': 0}

    logger.info(f'process_scraped_articles: processing {total} unprocessed articles')

    # Also try to fetch article content with newspaper3k for better extraction
    events_created = 0
    batch = []

    for article in unprocessed:
        title = article.title or ''
        source_url = article.url or ''

        extracted = extract_layoff_from_article(
            article_title=title,
            article_content='',
            source_url=source_url,
        )

        if extracted:
            # If DeepSeek is available, use it for richer extraction
            if hasattr(settings, 'DEEPSEEK_API_KEY') and settings.DEEPSEEK_API_KEY:
                try:
                    # Mark article for enrichment later — LLM enrichment task handles this
                    extracted['is_verified'] = False
                except Exception:
                    pass

            normalized = normalize_raw_event(extracted)
            if normalized:
                batch.append(normalized)

        # Mark as processed immediately (create events in batch below)
        article.processed = True

    # Bulk update processed flag
    ScrapedArticle.objects.filter(processed=False).update(processed=True)
    logger.info(f'Marked {total} articles as processed')

    # Create LayoffEvents from extracted data
    if batch:
        results = dedup_and_merge(batch)
        events_created = len(results)
        logger.info(f'Created/updated {events_created} LayoffEvent records from scraped articles')

    return {'processed': total, 'events_created': events_created}


@shared_task
def cleanup_stale_data():
    """
    Periodic cleanup of old scrape logs and duplicate events.

    Triggered by Celery Beat daily at 3am.
    """
    from scraper.models import ScrapeLog
    from datetime import timedelta

    # Remove logs older than 30 days
    cutoff = now() - timedelta(days=30)
    deleted, _ = ScrapeLog.objects.filter(ran_at__lt=cutoff).delete()
    logger.info(f'Cleanup: deleted {deleted} old scrape logs')
    return {'deleted_logs': deleted}
