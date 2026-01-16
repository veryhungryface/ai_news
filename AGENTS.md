# AI News Shorts - Agent Guidelines

> RSS 기반 AI/에듀테크 뉴스 수집 → LLM 큐레이션 및 요약 → Reels 스타일 HTML 생성

---

## Quick Reference

| Action | Command |
|--------|---------|
| Run news update | `python3 /root/first/update_news.py` |
| Install deps | `pip install -r /root/first/requirements.txt` |
| Verify output | Check `all_news.json` and `ai_news.html` are generated |

---

## Project Structure

```
/root/first/
├── update_news.py      # Main script (RSS fetch, LLM calls, HTML generation)
├── all_news.json       # Rolling 10-day news data store
├── ai_news.html        # Generated Reels-style web page (output)
├── requirements.txt    # Python dependencies: requests, python-dotenv
├── .env                # GLM_API_KEY (required, never commit)
└── .gitignore          # Ignores .env, __pycache__, *.pyc
```

---

## Environment Setup

```bash
# Required: .env file at project root
GLM_API_KEY=your_api_key_here
```

**API Endpoint**: `https://api.z.ai/api/coding/paas/v4/chat/completions`  
**Model**: `glm-4.7`

---

## Code Style Guidelines

### Naming Conventions
- **Functions/Variables**: `snake_case` (e.g., `fetch_rss_news`, `news_items`)
- **Constants**: `SCREAMING_SNAKE_CASE` (e.g., `RSS_SOURCES`, `DEFAULT_IMAGES`)
- **Classes**: `PascalCase` (if needed)

### Import Order
```python
# 1. Standard library
import os
import re
import json

# 2. Third-party packages
from dotenv import load_dotenv
import requests

# 3. Local modules (none currently)
```
Separate groups with a blank line.

### Formatting
- **Indent**: 4 spaces (no tabs)
- **Line length**: 88-100 characters recommended
- **Docstrings**: Required for all functions

### Type Hints
- Not currently enforced, but encouraged for new functions
- Example: `def parse_rss_date(date_str: str, source: str) -> Optional[str]:`

---

## Error Handling

```python
# REQUIRED pattern for network/IO operations
try:
    response = requests.get(url, timeout=30)
    # process response
except Exception as e:
    log_message(f"Error description: {e}")
    return fallback_value  # Never use bare 'pass'
```

**Rules**:
1. Always use `try-except` for network calls, file I/O, and XML parsing
2. Log errors via `log_message()` (includes KST timestamp automatically)
3. Never suppress exceptions silently with bare `pass`

---

## Logging

```python
# DO NOT USE print() - use the project's log function:
log_message("Your message here")

# Output format: [2025-01-16 15:33:43] Your message here
# Automatically converts to KST (UTC+9)
```

---

## Testing & Verification

**No formal test framework** is configured. Verify changes by:

1. Run `python3 /root/first/update_news.py`
2. Check for:
   - No exceptions in console output
   - `all_news.json` updated with valid JSON structure
   - `ai_news.html` generated and renders correctly

---

## Critical Implementation Notes

### File Paths
**Always use absolute paths**: `/root/first/filename`  
Relative paths cause issues in agent execution contexts.

### Data Integrity
- `maintain_10_day_window()` keeps only 10 days of data
- Never delete or overwrite existing date entries without merging
- `existing_links` set prevents duplicate articles across dates

### LLM API Optimization
- `batch_summarize()` processes **10 articles per API call**
- `curate_news_list()` limits to **30 articles max** before summarization
- Keep this batching structure to manage costs and latency

### HTML Template
The `generate_html()` function contains complex CSS/JS for:
- **Scroll snap**: `scroll-snap-type: y mandatory` for Reels-like UX
- **Progress bar**: Tracks current position in feed
- **Date selector**: Jumps to specific date's news

**Do not break**:
- `.reel` element structure
- Scroll snap behavior
- `allNewsFlat` JSON embedding in script tag

### Timezone Handling
- All dates are **KST (UTC+9)**
- `parse_rss_date()` converts GMT/UTC sources to KST
- Use `datetime.now() + timedelta(hours=9)` for current KST time

### Image Crawling
- `fetch_article_image()` extracts Open Graph `og:image`
- Timeout: 10 seconds
- User-Agent header required to avoid blocks

---

## Key Functions Reference

| Function | Purpose |
|----------|---------|
| `fetch_rss_news(source, date)` | Fetch articles from single RSS source for specific date |
| `fetch_all_news_for_date(date)` | Aggregate from all RSS sources with deduplication |
| `curate_news_list(articles)` | LLM-powered dedup + top-30 selection |
| `batch_summarize(articles)` | LLM summarization in batches of 10 |
| `sort_by_source_priority(articles)` | Order: 정책브리핑 → 연합뉴스 → AI타임스/ITWorld → 해외 |
| `generate_html(news_items)` | Create Reels-style HTML from all_news.json |
| `load_all_news()` / `save_all_news(data)` | JSON persistence |
| `maintain_10_day_window(data)` | Prune old entries |

---

## Data Schema

### all_news.json
```json
{
  "dates": [
    {
      "date": "2025-01-16",
      "update_time": "2025-01-16 15:33:43",
      "news": [
        {
          "title": "한국어 제목",
          "link": "https://...",
          "source": "AI타임스",
          "summary": "• 첫 번째 요점\n• 두 번째 요점\n• 세 번째 요점\n• 네 번째 요점",
          "category_keyword": "GPT",
          "image": "https://...",
          "is_english": false
        }
      ]
    }
  ]
}
```

---

## Security

- **Never commit `.env`** - it's in `.gitignore`
- **Never log API keys** - verify `log_message()` calls don't expose secrets
- API key is accessed only via `os.getenv('GLM_API_KEY')`

---

## Git Commit Guidelines

- Write clear, descriptive commit messages
- Format: `[type] description` (e.g., `[fix] Handle XML parse errors gracefully`)
- Don't commit `all_news.json` or `ai_news.html` to version control (consider adding to .gitignore)

---

## External Rules

No `.cursorrules`, `.cursor/rules/`, or `.github/copilot-instructions.md` files exist.
