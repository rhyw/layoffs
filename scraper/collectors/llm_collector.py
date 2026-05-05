"""
LLM-powered layoff data collector.

Uses DeepSeek (OpenAI-compatible API) to proactively find and extract
layoff announcements from the model's training data / knowledge.
"""
import json
import logging
from datetime import date, datetime
from typing import Optional

from openai import OpenAI

from scraper.pipeline import normalize_raw_event, dedup_and_merge

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    'You are a layoff data collection assistant. Your task is to find and extract '
    'information about technology company layoffs. '
    'Return ONLY a valid JSON array. No markdown, no explanation.\n\n'
    'Each object must have these exact fields:\n'
    '- company (string, required)\n'
    '- headcount (integer or null, number of employees laid off)\n'
    '- percentage (float or null, percentage of workforce, e.g., 10.0 for 10%%)\n'
    '- date (string, YYYY-MM-DD format, the date the layoff was announced)\n'
    '- source_url (string, URL to the news article or announcement)\n'
    '- source_name (string, e.g., "Reuters", "CNBC", "TechCrunch")\n'
    '- is_ai_related (boolean, whether this layoff is related to AI/automation)\n'
    '- industry (string or null, e.g., "SaaS", "FinTech", "E-commerce", "Hardware")\n'
    '- notes (string or null, brief context about the layoff)\n'
    '- confidence_score (float, 0.0-1.0, how confident you are the data is accurate)\n\n'
    'Only include layoffs you are confident actually occurred. '
    'Set confidence_score lower for unverified reports.'
)


class LLMCollector:
    """Collects layoff data by prompting an LLM."""

    def __init__(self, client: OpenAI, model: str = 'deepseek-chat'):
        self.client = client
        self.model = model

    def collect(self, lookback_days: int = 7) -> list:
        """
        Query the LLM for recent layoff announcements.

        Args:
            lookback_days: How many days back to search for layoffs.

        Returns:
            List of created/updated LayoffEvent instances.
        """
        today = date.today()
        user_prompt = (
            f'Today is {today.isoformat()}. '
            f'Find all technology company layoffs announced in the last '
            f'{lookback_days} days (since '
            f'{(today - __import__("datetime").timedelta(days=lookback_days)).isoformat()}).'
        )

        logger.info(f'LLM collector: querying {self.model} for recent layoffs')

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': SYSTEM_PROMPT},
                    {'role': 'user', 'content': user_prompt},
                ],
                temperature=0.1,
                response_format={'type': 'json_object'},
            )

            content = response.choices[0].message.content
            data = json.loads(content)

            # Handle both array and { "layoffs": [...] } formats
            events = data if isinstance(data, list) else data.get('layoffs', data.get('events', []))

            normalized = []
            for raw in events:
                raw['source_url'] = raw.get('source_url') or ''
                raw['date_reported'] = raw.pop('date', None) or today.isoformat()
                normalized_event = normalize_raw_event(raw)
                if normalized_event:
                    normalized.append(normalized_event)

            if normalized:
                return dedup_and_merge(normalized)

            logger.info('LLM collector: no events found')
            return []

        except json.JSONDecodeError as e:
            logger.error(f'LLM collector: JSON parse error: {e}')
            logger.debug(f'Raw response: {content}')
            return []
        except Exception as e:
            logger.error(f'LLM collector: API error: {e}')
            return []

    def extract_from_article(self, article_text: str, source_url: str = '') -> Optional[dict]:
        """
        Given an article's full text, extract structured layoff data.

        Args:
            article_text: Full text of the article.
            source_url: URL of the source article (optional).

        Returns:
            Normalized event dict or None if no layoff info found.
        """
        prompt = (
            'Given the following article text, extract any layoff information '
            'as a valid JSON object. If no layoff info is found, return null.\n\n'
            f'Article:\n{article_text[:8000]}\n\n'
            'Return JSON with: company, headcount, percentage, date, '
            'is_ai_related, confidence_score'
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{'role': 'user', 'content': prompt}],
                temperature=0.1,
                response_format={'type': 'json_object'},
            )

            result = json.loads(response.choices[0].message.content)
            if result and result.get('company'):
                result['source_url'] = source_url
                result['date_reported'] = result.pop('date', None) or date.today().isoformat()
                return normalize_raw_event(result)

            return None

        except Exception as e:
            logger.error(f'Article extraction error: {e}')
            return None
