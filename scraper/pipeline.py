"""
Dedup & merge pipeline for scraped layoff events.

Takes raw extracted data from collectors, normalizes it, checks for
duplicates in the database, and creates/updates LayoffEvent records.
"""
import hashlib
import logging
from datetime import datetime, date
from typing import Optional

from dateutil import parser as dateparser
from django.utils.timezone import now

from layoffs.models import LayoffEvent

logger = logging.getLogger(__name__)


def hash_url(url: str) -> str:
    """SHA-256 hash of a URL for dedup lookups."""
    return hashlib.sha256(url.encode('utf-8')).hexdigest()


def normalize_raw_event(raw: dict) -> Optional[dict]:
    """
    Normalize a raw event dict into a clean format for DB insertion.

    Expected input keys:
        company (str, required)
        headcount (int or None)
        percentage (float or None)
        date_reported (str or date, required)
        source_url (str, required)
        source_name (str, optional)
        is_ai_related (bool, optional)
        industry (str, optional)
        notes (str, optional)

    Returns cleaned dict or None if required fields are missing.
    """
    company = (raw.get('company') or '').strip()
    if not company:
        logger.warning('Skipping event with no company name')
        return None

    source_url = (raw.get('source_url') or '').strip()
    if not source_url:
        logger.warning(f'Skipping event for {company} with no source_url')
        return None

    # Parse date
    date_reported = raw.get('date_reported')
    if isinstance(date_reported, str):
        try:
            date_reported = dateparser.parse(date_reported).date()
        except (ValueError, TypeError):
            logger.warning(f'Could not parse date for {company}: {date_reported}')
            date_reported = now().date()
    elif not isinstance(date_reported, date):
        date_reported = now().date()

    return {
        'company': company,
        'headcount': raw.get('headcount'),
        'percentage': raw.get('percentage'),
        'date_reported': date_reported,
        'source_url': source_url,
        'source_name': (raw.get('source_name') or '').strip(),
        'is_ai_related': bool(raw.get('is_ai_related', False)),
        'industry': (raw.get('industry') or '').strip() or None,
        'notes': (raw.get('notes') or '').strip() or None,
        'confidence_score': float(raw.get('confidence_score', 0.5)),
    }


def dedup_and_merge(normalized_events: list[dict]) -> list[LayoffEvent]:
    """
    Deduplicate and merge a list of normalized events into the database.

    Dedup key: (company_lower, date_reported, headcount).
    If an existing event matches, keep the one with higher confidence_score.
    Returns list of created/updated LayoffEvent instances.
    """
    results = []

    for event_data in normalized_events:
        company = event_data['company']
        date_reported = event_data['date_reported']
        headcount = event_data['headcount']

        existing = LayoffEvent.objects.filter(
            company__iexact=company,
            date_reported=date_reported,
            headcount=headcount,
        ).first()

        if existing:
            # Keep existing if it has higher confidence, otherwise update
            new_confidence = event_data.get('confidence_score', 0.0)
            if new_confidence > existing.confidence_score:
                for field, value in event_data.items():
                    if value is not None and value != '':
                        setattr(existing, field, value)
                existing.save()
                results.append(existing)
            else:
                results.append(existing)
        else:
            event = LayoffEvent.objects.create(**event_data)
            results.append(event)

    return results
