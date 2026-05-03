"""
Dedup & merge pipeline for scraped layoff events.

Takes raw extracted data from collectors, normalizes it, checks for
duplicates in the database, and creates/updates LayoffEvent records.
"""
import hashlib
import logging
import re
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


# ── Heuristic extraction from scraped article titles ──

# Well-known tech companies for title matching
KNOWN_TECH_COMPANIES = [
    'Google', 'Alphabet', 'Meta', 'Facebook', 'Amazon', 'Apple', 'Microsoft',
    'Netflix', 'Twitter', 'X Corp', 'Snap', 'Snapchat', 'Uber', 'Lyft',
    'Airbnb', 'PayPal', 'Stripe', 'Square', 'Block', 'Shopify', 'Spotify',
    'Salesforce', 'Oracle', 'IBM', 'Intel', 'AMD', 'Nvidia', 'Cisco',
    'Dell', 'HP', 'HPE', 'Tesla', 'Rivian', 'Lucid', 'Peloton',
    'Zoom', 'Slack', 'Palantir', 'Twilio', 'DoorDash', 'Robinhood',
    'Coinbase', 'Pinterest', 'Reddit', 'Dropbox', 'DocuSign',
    'Snowflake', 'Datadog', 'Cloudflare', 'Atlassian', 'GitLab',
    'Unity', 'Roblox', 'Electronic Arts', 'Activision', 'Blizzard',
    'Take-Two', 'Epic Games', 'Unity Technologies',
    'Peloton Interactive', 'Wayfair', 'Etsy', 'Groupon', 'Yelp',
    'Zillow', 'Redfin', 'Compass', 'WeWork', 'Toast', 'BlockFi',
    'Gemini', 'Kraken', 'OpenSea', 'Bumble', 'Match Group', 'Tinder',
    'Hewlett Packard', 'Lenovo', 'Samsung', 'Sony', 'LG',
    'TikTok', 'ByteDance', 'Tencent', 'Alibaba', 'Baidu', 'JD.com',
    'Meituan', 'Didi', 'Infosys', 'TCS', 'Wipro', 'Tech Mahindra',
    'Accenture', 'Cognizant', 'Capgemini',
    'AMD', 'Qualcomm', 'Broadcom', 'Micron', 'Texas Instruments',
    'ASML', 'Applied Materials', 'Lam Research', 'KLA',
    'Adobe', 'Autodesk', 'Intuit', 'ServiceNow', 'Workday',
    'SAP', 'VMware', 'Red Hat', 'MongoDB', 'Elastic',
    'Okta', 'CrowdStrike', 'Palo Alto Networks', 'Fortinet',
    'Zscaler', 'Datadog', 'New Relic', 'Splunk', 'Dynatrace',
    'HashiCorp', 'Confluent', 'Fastly', 'Cloudinary',
]

# Key layoff-related headline patterns
LAYOFF_PATTERNS = [
    r'\b(lay off|layoff|laid off|laying off|furlough)\b',
    r'\b(workforce reduction|job cut|cutting jobs|headcount reduction)\b',
    r'\b(reduce|slash|cuts?)\s+(workforce|staff|headcount|jobs)\b',
    r'\b(downsizing|restructuring)\b',
]


def _find_company_in_title(title: str) -> Optional[str]:
    """Try to find a known tech company name in an article title."""
    # Check known tech companies first (longest match first to avoid partial matches)
    for company in sorted(KNOWN_TECH_COMPANIES, key=len, reverse=True):
        pattern = re.compile(re.escape(company), re.IGNORECASE)
        if pattern.search(title):
            return company
    return None


def _extract_headcount(text: str) -> Optional[int]:
    """
    Extract headcount figure near layoff-related context.
    Handles patterns like: "lays off 200", "200 jobs cut", "nearly 500 employees", "1,200 people".
    """
    text_lower = text.lower()

    patterns = [
        # "laid off 200", "cutting 500 jobs", "lays off 1,200"
        r'(?:laid off|layoff|laying off|cutting|cuts?|eliminating|axing|slashing|shedding)\s+'
        r'(?:about|around|nearly|approximately|over|more than|some|roughly|up to)?\s*'
        r'(\d{1,3}(?:,\d{3})*)\s*'
        r'(?:jobs?|employees?|workers?|positions?|staff|people|roles?|workers?)',
        # "200 jobs cut", "500 employees laid off"
        r'(\d{1,3}(?:,\d{3})*)\s*'
        r'(?:jobs?|employees?|workers?|positions?|staff|people)\s+'
        r'(?:cut|eliminated|axed|slashed|laid off|affected|impacted)',
        # "cut 10% of workforce"
        r'(?:cut|reduce|slash|trim)\s+(?:about|around|nearly)?\s*(\d{1,3})\s*%',
        # "10% of workforce"
        r'(\d{1,3})\s*%\s+of\s+(?:its|their|the)\s+(?:workforce|staff)',
    ]

    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            try:
                return int(match.group(1).replace(',', ''))
            except (ValueError, IndexError):
                pass
    return None


def extract_layoff_from_article(article_title: str, article_content: str = "", source_url: str = "") -> Optional[dict]:
    """
    Try to extract layoff event data from a scraped article using heuristics.

    Returns a normalized event dict (ready for dedup_and_merge) or None.
    """
    text = f"{article_title} {article_content[:2000]}"
    text_lower = text.lower()

    # Must contain layoff-related keywords
    if not any(re.search(p, text_lower) for p in LAYOFF_PATTERNS):
        return None

    # Try to find a known tech company
    company = _find_company_in_title(article_title)

    # If no known company, try heuristics: capitalized word before "layoff/lay off" etc.
    if not company:
        # Pattern: "<Company> (announces|reports|plans) layoffs"
        m = re.search(
            r'([A-Z][A-Za-z0-9]+(?:[\s.&][A-Z][A-Za-z0-9]+){0,3})'
            r'\s+(?:announces?|reports?|plans?|confirms?|is laying|to lay off|lays off)',
            article_title
        )
        if m:
            company = m.group(1).strip()
        else:
            # Pattern: "layoffs at <Company>"
            m = re.search(r'layoffs?\s+(?:at|for|hit)\s+([A-Z][A-Za-z0-9]+(?:[\s.&][A-Z][A-Za-z0-9]+){0,3})', article_title)
            if m:
                company = m.group(1).strip()

    confidence = 0.3  # Low confidence by default for heuristic extraction

    # Extract headcount
    headcount = _extract_headcount(text)
    if headcount:
        confidence = 0.5  # Higher confidence if we have a number

    if not company and not headcount:
        return None

    # Parse date from content if possible, otherwise use today
    date_reported = date.today()
    date_match = re.search(
        r'(?:on|announced|reported)\s+'
        r'(January|February|March|April|May|June|July|August|September|October|November|December)'
        r'\s+(\d{1,2})(?:th|st|nd|rd)?,?\s+(\d{4})',
        text
    )
    if date_match:
        from calendar import month_name
        month_str = date_match.group(1)
        day = int(date_match.group(2))
        year = int(date_match.group(3))
        month = {v.lower(): k for k, v in enumerate(month_name)}.get(month_str.lower(), 1)
        try:
            date_reported = date(year, month, day)
        except ValueError:
            pass

    return {
        'company': company or 'Unknown',
        'headcount': headcount,
        'percentage': None,
        'date_reported': date_reported,
        'source_url': source_url,
        'source_name': '',
        'is_ai_related': False,
        'industry': None,
        'notes': article_title[:500],
        'confidence_score': confidence,
    }
