# Phase 4: Data Collection Strategies

## Goal
Implement multiple data collection pipelines to gather layoff data from various sources.

## Collection Strategies

### 4.1 RSS Feed Collector (`scraper/collectors/rss_collector.py`)

**Sources to configure in DB:**
| Name | URL | Interval |
|------|-----|----------|
| TechCrunch | https://techcrunch.com/feed/ | 15 min |
| Reuters Tech | https://www.reutersagency.com/feed/?best-topics=tech | 15 min |
| CNBC Tech | https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147 | 15 min |
| Google News (Layoffs) | https://news.google.com/rss/search?q=layoffs&hl=en-US&gl=US&ceid=US:en | 15 min |

**Pipeline:**
1. Fetch RSS XML via `feedparser`
2. For each entry, check title/summary for layoff keywords
3. If relevant, fetch full article via `newspaper3k`
4. Extract structured data: company name, headcount, percentage, date
5. Send to dedup → save pipeline

**Keyword matching:**
```python
LAYOFF_KEYWORDS = ['layoff', 'lay off', 'laid off', 'furlough',
                   'reduction in force', 'workforce reduction',
                   'job cut', 'cutting jobs', 'restructuring',
                   'downsize', 'headcount reduction']
```

### 4.2 Web Scraper (`scraper/collectors/web_scraper.py`)

**Targets:**
- `layoffs.fyi` — known layoff tracker (respect robots.txt)
- Company press release pages (Apple, Google, Meta, etc.)

**Technique:**
- `requests` with rotating User-Agent headers
- `beautifulsoup4` for HTML parsing
- 1-3 second random delay between requests
- Cache HTTP responses for 30 minutes to avoid hammering

**Example extraction logic:**
```python
def parse_layoff_table(soup):
    rows = soup.select('table tr')
    for row in rows:
        cells = row.find_all('td')
        if len(cells) >= 3:
            company = cells[0].get_text(strip=True)
            count = parse_number(cells[1].get_text(strip=True))
            date = parse_date(cells[2].get_text(strip=True))
            # ...
```

### 4.3 LLM-Powered Collector (`scraper/collectors/llm_collector.py`)

**Provider:** DeepSeek (via OpenAI-compatible API)

**Config:**
```python
DEEPSEEK_API_KEY = env('DEEPSEEK_API_KEY')
DEEPSEEK_MODEL = env('DEEPSEEK_MODEL', default='deepseek-chat')
DEEPSEEK_BASE_URL = 'https://api.deepseek.com/v1'
```

**Strategy A — Direct Query (every 4 hours):**
```
System: You are a layoff data collection assistant. Today's date is {date}.
Return ONLY a valid JSON array. Each object must have fields:
company, headcount (int or null), percentage (float or null),
date (YYYY-MM-DD), source_url, source_name, is_ai_related (bool).

User: Find all technology company layoffs announced in the last 24 hours.
Search your knowledge for recent reports.
```

**Strategy B — Article Analysis (on-demand):**
```
Given the following article text, extract any layoff information
as a valid JSON object. If no layoff info is found, return null.

Fields: company, headcount, percentage, date, is_ai_related, confidence

Article: {article_text}
```

**Strategy C — Enrichment (every hour):**
```
For this layoff event, fill in missing fields based on your knowledge:
- industry: one of [SaaS, FinTech, E-commerce, Hardware, Social Media,
  Gaming, Cloud, Enterprise Software, Healthcare Tech, EdTech, Other]
- is_ai_related: true/false
- confidence_score: 0.0-1.0

Company: {company}
Additional context: {notes}
```

### 4.4 Dedup & Merge Pipeline (`scraper/pipeline.py`)

```python
def dedup_and_merge(new_events: list[dict]) -> list[LayoffEvent]:
    """
    1. Hash each event by (company.lower(), date, headcount)
    2. Check against existing DB entries
    3. If exists: keep the one with higher confidence_score
    4. If new: create LayoffEvent
    5. Return list of created/updated events
    """
```

### 4.5 News Article Collector (`scraper/collectors/news_collector.py`)

- Separate from layoff-specific data
- Collects general tech news for the "Tech News" section
- Sources: RSS feeds from The Verge, Bloomberg, Forbes, Wired
- No LLM needed — just title, snippet, source, thumbnail

### 4.6 Rate Limiting & Politeness
- All HTTP requests go through a shared rate limiter
- Default: 1 request per 3 seconds per domain
- Custom rate limits per DataSource config
- All requests include `User-Agent` header identifying the project
