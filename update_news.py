#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI News Shorts - Batch Processing with 10-day Rolling Window
"""

import os
import re
import json
import time
import base64
import hmac
import hashlib
from datetime import datetime, timedelta
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
import requests

load_dotenv()

GLM_API_KEY = os.getenv('GLM_API_KEY')

RSS_SOURCES = [
    # 1. 에듀테크 특화 (국내/해외)
    {
        'name': 'Google News (EdTech)',
        'url': 'https://news.google.com/rss/search?q=%EC%97%90%EB%93%80%ED%85%8C%ED%81%AC|AI%EA%B5%90%EC%9C%A1|%EB%94%94%EC%A7%80%ED%84%B8%EA%B5%90%EA%B3%BC%EC%84%9C&hl=ko&gl=KR&ceid=KR:ko',
        'source': '에듀테크 검색'
    },
    {
        'name': 'EdSurge',
        'url': 'https://www.edsurge.com/articles_rss',
        'source': 'EdSurge'
    },
    {
        'name': 'eSchool News',
        'url': 'https://www.eschoolnews.com/feed/',
        'source': 'eSchoolNews'
    },
    
    # 2. 국내 AI/IT 트렌드 (전문지 및 기술동향)
    {
        'name': 'AI Times',
        'url': 'https://cdn.aitimes.com/rss/gn_rss_allArticle.xml',
        'source': 'AI타임스'
    },
    {
        'name': 'ITWorld Korea',
        'url': 'https://www.itworld.co.kr/feed/',
        'source': 'ITWorld'
    },
    
    # 3. 해외 AI 핵심 기술 및 투자 (원천기술/스타트업)
    {
        'name': 'OpenAI News',
        'url': 'https://openai.com/news/rss.xml',
        'source': 'OpenAI'
    },
    {
        'name': 'TechCrunch AI',
        'url': 'https://techcrunch.com/category/artificial-intelligence/feed/',
        'source': 'TechCrunch'
    },
    
    # 4. 오픈소스 AI 모델 트렌드
    {
        'name': 'HuggingFace Trending',
        'url': 'https://zernel.github.io/huggingface-trending-feed/feed.xml',
        'source': 'HuggingFace'
    }
]

DEFAULT_IMAGES = [
    'https://images.unsplash.com/photo-1677442136019-21780ecad995?w=1920&q=80',
    'https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=1920&q=80',
    'https://images.unsplash.com/photo-1555255707-c07966088b7b?w=1920&q=80',
    'https://images.unsplash.com/photo-1676299081847-c3c644878e36?w=1920&q=80',
    'https://images.unsplash.com/photo-1485827404703-89b55fcc595e?w=1920&q=80'
]

def log_message(message):
    timestamp = (datetime.now() + timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

def is_english_text(text):
    """Check if text is primarily English"""
    if not text:
        return False
    english_chars = sum(1 for c in text if ord(c) < 128)
    total_chars = len(text.strip())
    return total_chars > 0 and (english_chars / total_chars) > 0.5

def get_og_image(html_content):
    """Extract og:image from HTML content using regex"""
    if not html_content:
        return None
    
    patterns = [
        r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']',
        r'<meta\s+content=["\']([^"\']+)["\']\s+property=["\']og:image["\']',
        r'<meta\s+name=["\']twitter:image["\']\s+content=["\']([^"\']+)["\']',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, html_content, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None

def fetch_article_image(article_url, rss_image=None):
    """Fetch og:image from article URL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(article_url, headers=headers, timeout=10)
        if response.status_code == 200:
            og_image = get_og_image(response.text)
            if og_image:
                return og_image
    except Exception as e:
        pass
    
    return rss_image

def parse_rss_date(date_str, source):
    """Parse RSS date to YYYY-MM-DD format with timezone conversion"""
    date_formats = [
        '%a, %d %b %Y %H:%M:%S %Z',
        '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%dT%H:%M:%S%z',
        '%d %b %Y %H:%M:%S',
        '%Y-%m-%d %H:%M:%S'
    ]
    
    for fmt in date_formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            
            # Convert GMT/UTC to KST (UTC+9)
            tz_str = date_str.strip().split()[-1] if date_str else ''
            if tz_str in ['GMT', 'UTC'] or fmt.endswith('Z'):
                dt = dt + timedelta(hours=9)
            
            return dt.strftime('%Y-%m-%d')
        except:
            continue
    
    # If parsing fails, return None instead of today's date to avoid duplicates
    return None

def fetch_rss_news(source_info, target_date):
    """Fetch news from RSS source for a specific date"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'application/rss+xml, application/xml, text/xml, */*;q=0.9'
    }
    
    try:
        response = requests.get(source_info['url'], headers=headers, timeout=30)
        
        if response.status_code != 200:
            log_message(f"  HTTP {response.status_code}: {source_info['name']}")
            return []
        
        response.encoding = 'utf-8'
        
        if not response.content:
            return []
        
        try:
            root = ET.fromstring(response.content.strip())
        except ET.ParseError as e:
            log_message(f"  XML ParseError in {source_info['name']}: {str(e)[:50]}")
            return []
        
        items = root.findall('.//item')
        
        news_list = []
        seen_links = set()
        
        for item in items[:30]:
            link = item.find('link')
            if link is None or link.text is None:
                continue
            link = link.text.strip()
            
            if link in seen_links:
                continue
            seen_links.add(link)
            
            title = item.find('title')
            title = title.text.strip() if title is not None and title.text else 'No Title'
            
            pub_date = item.find('pubDate')
            pub_date = pub_date.text if pub_date is not None else ''
            news_date = parse_rss_date(pub_date, source_info['source'])
            
            # If date parsing failed or date doesn't match target, skip
            if not news_date or news_date != target_date:
                continue
            
            description = item.find('description')
            desc = description.text if description is not None else ''
            clean_desc = re.sub('<[^<]+?>', '', desc)[:500] if desc else ''
            
            enclosure = item.find('enclosure')
            image = None
            if enclosure is not None and enclosure.get('type', '').startswith('image'):
                image = enclosure.get('url')
            
            if not image:
                img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', desc or '')
                if img_match:
                    image = img_match.group(1)
            
            if not image:
                media_content = item.find('.//{http://search.yahoo.com/mrss/}content')
                if media_content is not None:
                    image = media_content.get('url')
            
            news_list.append({
                'title': title,
                'link': link,
                'date': news_date,
                'source': source_info['source'],
                'description': clean_desc,
                'image': image,
                'is_english': is_english_text(title)
            })
        
        return news_list
    except Exception as e:
        log_message(f"Error fetching {source_info['name']}: {e}")
        return []

def fetch_all_news_for_date(target_date, existing_links=None):
    """Fetch all news for a specific date from all sources"""
    all_news = []
    if existing_links is None:
        existing_links = set()
    
    for source in RSS_SOURCES:
        news = fetch_rss_news(source, target_date)
        
        # Filter out links that already exist in previous days
        new_items = []
        for item in news:
            if item['link'] not in existing_links:
                new_items.append(item)
        
        all_news.extend(new_items)
        log_message(f"  {source['name']}: {len(new_items)} new articles (found {len(news)})")
        time.sleep(1)
    
    seen = set()
    unique_news = []
    for item in all_news:
        if item['link'] not in seen:
            seen.add(item['link'])
            unique_news.append(item)
    
    return unique_news

def sort_by_source_priority(articles):
    """Sort articles by source priority: AI타임스 -> 에듀테크 검색 -> ITWorld -> 나머지"""
    source_priority = {
        'AI타임스': 0,
        '에듀테크 검색': 1,
        'ITWorld': 2,
        'HuggingFace': 3
    }
    
    def get_priority(article):
        source = article.get('source', '')
        return source_priority.get(source, 99)
    
    return sorted(articles, key=get_priority)

def curate_news_list(articles):
    """Curate news list using LLM - deduplicate and select top 30 important articles"""
    if not articles:
        return []
    
    if len(articles) <= 30:
        return sort_by_source_priority(articles)
    
    url = "https://api.z.ai/api/coding/paas/v4/chat/completions"
    headers = {
        'Authorization': f'Bearer {GLM_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    # 소스별로 균등하게 샘플링하여 큐레이션 (최대 100개)
    from collections import defaultdict
    source_articles = defaultdict(list)
    for article in articles:
        source_articles[article.get('source', 'Unknown')].append(article)
    
    # 각 소스에서 최대 20개씩 취하여 균등한 분포 확보
    sampled_articles = []
    for source, source_list in source_articles.items():
        sampled_articles.extend(source_list[:20])
    
    # 최대 100개만 LLM에 전달 (토큰 제한 고려)
    sampled_articles = sampled_articles[:100]
    
    prompt_parts = []
    for idx, article in enumerate(sampled_articles):
        original_title = article.get('title', '')
        original_summary = article.get('description', '')[:200]
        source = article.get('source', '')
        
        prompt_parts.append(f"""=== 기사 {idx + 1} ===
제목: {original_title}
출처: {source}
본문요약: {original_summary}""")
    
    prompt = f"""다음 {len(sampled_articles)}개의 AI/에듀테크 뉴스 기사를 분석하여 큐레이션해주세요.
 
 {chr(10).join(prompt_parts)}
 
 큐레이션 요구사항:
 1. 중복되거나 비슷한 내용의 기사는 제거하세요.
 2. AI 및 에듀테크 분야에서 가장 중요하고 영향력 있는 상위 30개 기사만 선별하세요.
 3. 선별 기준: 기술적 혁신성, 시장 영향력, 사용자 관련성, 뉴스 가치 등을 고려하세요.
 
 출력 형식 (숫자로만 답변, 쉼표로 구분):
 1,3,5,7,10,12,15,18,20,22,25,28,30,32,35,38,40,42,45,48,50,52,55,58,60,62,65,68,70,72
 
 반드시 1부터 {len(sampled_articles)} 사이의 숫자 30개만 출력하고, 다른 설명 없이 숫자만 쉼표로 구분해주세요."""

    data = {
        'model': 'glm-4.7',
        'messages': [
            {'role': 'system', 'content': '당신은 AI 및 에듀테크 뉴스 큐레이터입니다. 중복 제거와 중요 기사 선별에 능숙합니다. 반드시 숫자만 출력하세요.'},
            {'role': 'user', 'content': prompt}
        ],
        'max_tokens': 500,
        'temperature': 0.3,
        'thinking': {'type': 'disabled'}
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content'].strip()
                
                indices = []
                for num_str in content.split(','):
                    try:
                        num = int(num_str.strip())
                        if 1 <= num <= len(sampled_articles):
                            indices.append(num - 1)
                    except:
                        continue
                
                if len(indices) >= 30:
                    indices = indices[:30]
                    curated = [sampled_articles[i] for i in indices]
                    log_message(f"  Curated: {len(articles)} -> {len(curated)} articles")
                    return sort_by_source_priority(curated)
                else:
                    log_message(f"  Curation returned only {len(indices)} articles, using first 30")
                    return sort_by_source_priority(articles[:30])
        else:
            log_message(f"  Curation API error {response.status_code}, using first 30")
            return sort_by_source_priority(articles[:30])
    except Exception as e:
        log_message(f"  Curation error: {e}, using first 30")
        return sort_by_source_priority(articles[:30])
    
    return sort_by_source_priority(articles[:30])

def batch_summarize(articles):
    """Batch summarize 10 articles at a time using GLM API"""
    if not articles:
        return articles
    
    url = "https://api.z.ai/api/coding/paas/v4/chat/completions"
    headers = {
        'Authorization': f'Bearer {GLM_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    batch_size = 10
    processed = 0
    
    for i in range(0, len(articles), batch_size):
        batch = articles[i:i+batch_size]
        
        prompt_parts = []
        for idx, article in enumerate(batch):
            original_title = article.get('original_title', article.get('title', ''))
            original_summary = article.get('original_summary', article.get('description', '')[:300])
            language = 'EN' if article.get('is_english', False) else 'KO'
            
            prompt_parts.append(f"""=== 기사 {idx + 1} ===
제목: {original_title}
원본언어: {language}
본문요약: {original_summary}""")
        
        prompt = f"""다음 {len(batch)}개 기사를 한국어로 처리해주세요.
 
 {chr(10).join(prompt_parts)}
 
 처리 요구사항:
 1. 영문 기사는 제목과 본문 요약을 모두 자연스러운 한국어로 번역하세요.
 2. 각 기사의 핵심을 불렛 포인트(•) 4개로 구조화하여 요약하세요. 줄글보다 빠르게 파악할 수 있도록 각 핵심은 명확하고 간결하게 작성하세요.
 3. 기사의 핵심 키워드 1개를 추출하세요 (최대 5자).
 
 출력 형식:
 === 기사 1 ===
 번역된 제목: [영문인 경우 한국어 제목, 한글인 경우 기존 제목]
 요약: • 첫 번째 핵심 내용 (20자 내외)
 • 두 번째 핵심 내용 (20자 내외)
 • 세 번째 핵심 내용 (20자 내외)
 • 네 번째 핵심 내용 (20자 내외)
 키워드: [핵심 키워드]
 
 === 기사 2 ===
 ...
 (순서대로 답변)
 
 반드시 한국어로 답변하고, 모든 기사를 순서대로 처리해주세요."""

        data = {
            'model': 'glm-4.7',
            'messages': [
                {'role': 'system', 'content': '당신은 한국 IT 뉴스 에디터입니다. 모든 응답은 한국어로 작성하세요.'},
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': 2000,
            'temperature': 0.7,
            'thinking': {'type': 'disabled'}
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=120)
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    content = result['choices'][0]['message']['content']
                    log_message(f"  Batch {i//batch_size + 1}: API success")
                    parse_batch_response(batch, content)
            else:
                log_message(f"  Batch {i//batch_size + 1}: API error {response.status_code}")
        except Exception as e:
            log_message(f"  Batch {i//batch_size + 1}: Error - {e}")
        
        processed += len(batch)
        time.sleep(2)
    
    return articles

def parse_batch_response(articles, response):
    """Parse batch API response and update articles"""
    sections = re.split(r'===\s*기사\s*(\d+)\s*===', response)
    
    for i in range(1, len(sections), 2):
        try:
            idx = int(sections[i]) - 1
            if idx < 0 or idx >= len(articles):
                continue
            
            section_content = sections[i + 1]
            
            # Extract translated title
            title_match = re.search(r'번역된\s*제목:\s*(.+?)(?:\n|$)', section_content)
            if title_match:
                articles[idx]['translated_title'] = title_match.group(1).strip()
            
            # Extract summary (키워드: 라인 전까지만 추출)
            summary_match = re.search(r'요약:\s*(.+?)(?:키워드:|$)', section_content, re.DOTALL)
            if summary_match:
                summary_text = summary_match.group(1).strip()
                # 키워드 라인이 혼입된 경우 제거
                summary_text = re.sub(r'키워드:.*$', '', summary_text, flags=re.MULTILINE).strip()
                articles[idx]['summary'] = summary_text
            
            # Extract keyword
            keyword_match = re.search(r'키워드:\s*(.+?)(?:\n|$)', section_content)
            if keyword_match:
                articles[idx]['category_keyword'] = keyword_match.group(1).strip()
            
            # Update title if translated
            if articles[idx].get('translated_title'):
                articles[idx]['title'] = articles[idx]['translated_title']
            
            # Ensure summary exists
            if not articles[idx].get('summary'):
                articles[idx]['summary'] = '전체 기사 내용은 링크를 확인하세요.'
                
        except Exception as e:
            log_message(f"    Parse error for article {i}: {e}")

def load_all_news():
    """Load all news from JSON file"""
    try:
        with open('/root/first/all_news.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {'dates': []}
    except json.JSONDecodeError:
        return {'dates': []}

def save_all_news(data):
    """Save all news to JSON file"""
    with open('/root/first/all_news.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def maintain_10_day_window(data):
    """Keep only the last 10 days of data"""
    if len(data['dates']) <= 10:
        return data
    
    sorted_dates = sorted(data['dates'], key=lambda x: x['date'], reverse=True)
    data['dates'] = sorted_dates[:10]
    return data

def generate_html(news_items):
    """Generate HTML with all 10 days displayed - Fixed Version"""
    update_time = (datetime.now() + timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S')
    
    all_data = load_all_news()
    all_data = maintain_10_day_window(all_data)
    
    all_news_flat = []
    for date_entry in all_data['dates']:
        for news in date_entry['news']:
            n_copy = news.copy()
            n_copy['date'] = date_entry['date']
            all_news_flat.append(n_copy)
    
    all_news_by_date = []
    for date_entry in all_data['dates']:
        all_news_by_date.append({
            'date': date_entry['date'],
            'update_time': date_entry.get('update_time', ''),
            'news_count': len(date_entry['news'])
        })
    
    # 드롭다운 옵션 생성
    dates_options = ''.join(
        f'<option value="{item["date"]}">{item["date"]}</option>'
        for item in all_data['dates']
    )
    
    # JSON 변환
    all_news_by_date_json = json.dumps(all_news_by_date, ensure_ascii=False)
    all_news_flat_json = json.dumps(all_news_flat, ensure_ascii=False)
    
    # HTML 템플릿 작성
    html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>AI 뉴스 | 최신 소식</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;700&display=swap');
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
        }}
        
        html, body {{
            height: 100%;
            width: 100%;
            overflow: hidden;
            background: #000000;
            font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }}
        
        .reels-container {{
            height: 100vh;
            width: 100vw;
            overflow-y: scroll;
            scroll-snap-type: y mandatory;
            scroll-behavior: smooth;
            -webkit-overflow-scrolling: touch;
            scrollbar-width: none;
            -ms-overflow-style: none;
        }}
        
        .reels-container::-webkit-scrollbar {{
            display: none;
        }}
        
        .reel {{
            height: 100vh;
            width: 100vw;
            scroll-snap-align: start;
            scroll-snap-stop: always;
            position: relative;
            display: flex;
            flex-direction: column;
            justify-content: flex-end;
            overflow: hidden;
            background-color: #000000;
            transition: transform 0.3s ease;
        }}
        
        .reel-bg {{
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 70%;
            background-size: cover;
            background-position: center top;
            z-index: 0;
        }}
        
        .reel-bg::after {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(180deg, transparent 0%, transparent 40%, rgba(0,0,0,0.6) 70%, rgba(0,0,0,1) 100%);
            z-index: 1;
        }}
        
        .content-overlay {{
            position: relative;
            z-index: 2;
            padding: 24px;
            padding-bottom: 80px;
            width: 100%;
            max-width: 600px;
            animation: slideUp 0.5s ease-out;
        }}
        
        @keyframes slideUp {{
            from {{
                opacity: 0;
                transform: translateY(30px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}
        
        .reel-title {{
            color: #FFFFFF;
            font-size: 28px;
            font-weight: 800;
            line-height: 1.35;
            margin-bottom: 14px;
            text-shadow: 0 2px 12px rgba(0,0,0,0.8);
            word-wrap: break-word;
            letter-spacing: -0.5px;
        }}
        
        .reel-summary {{
            color: rgba(255, 255, 255, 0.95);
            font-size: 16px;
            line-height: 1.8;
            margin-bottom: 60px; /* Space for the button */
            text-shadow: 0 1px 2px rgba(0,0,0,0.8);
            white-space: pre-line;
            font-weight: 400;
        }}
        
        .reel-summary strong {{
            color: #FFFFFF;
            font-weight: 700;
            text-shadow: 0 0 10px rgba(255,255,255,0.3);
        }}
        
        .reel-meta {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 12px;
            white-space: nowrap;
        }}
        
        .reel-source {{
            background: #3B82F6;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 700;
            color: #FFFFFF;
            display: inline-flex;
            align-items: center;
        }}
        
        .meta-separator {{
            color: rgba(255, 255, 255, 0.4);
            font-size: 12px;
            font-weight: 300;
        }}
        
        .reel-date {{
            color: #E5E7EB;
            font-size: 13px;
            font-weight: 500;
        }}
        
        .reel-tag {{
            color: rgba(255, 255, 255, 0.8);
            font-size: 13px;
            font-weight: 400;
        }}
        
        .reel-link {{
            position: absolute;
            bottom: 80px;  /* 모바일 주소창 간섭 방지를 위해 상향 조정 */
            right: 20px;
            background: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 30px;
            padding: 10px 20px;
            color: #FFFFFF;
            font-size: 14px;
            font-weight: 600;
            text-decoration: none;
            display: flex;
            align-items: center;
            gap: 6px;
            z-index: 10;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        }}
        
        .reel-link:active {{
            transform: scale(0.95);
        }}

        @keyframes pulse-btn {{
            0% {{ box-shadow: 0 0 0 0 rgba(255, 255, 255, 0.4); }}
            70% {{ box-shadow: 0 0 0 10px rgba(255, 255, 255, 0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(255, 255, 255, 0); }}
        }}
        
        .reel-link {{
            animation: pulse-btn 3s infinite;
        }}
        
        .top-ui {{
            position: fixed;
            top: 16px;
            left: 16px;
            right: 16px;
            z-index: 1000;
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 10px;
            pointer-events: none;
        }}
        
        .top-ui > * {{
            pointer-events: auto;
        }}
        
        .go-latest-btn {{
            background: rgba(0,0,0,0.4);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 50px;
            padding: 8px 14px;
            color: #FFFFFF;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 5px;
            transition: all 0.3s ease;
        }}
        
        .date-selector {{
            background: rgba(0,0,0,0.4);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 12px;
            padding: 6px 10px;
            color: #FFFFFF;
            font-size: 13px;
        }}
        
        .date-selector select {{
            background: rgba(255,255,255,0.08);
            color: #FFFFFF;
            border: none;
            padding: 5px 10px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            min-width: 110px;
        }}
        
        .date-selector select option {{
            background: #000000;
            color: #FFFFFF;
        }}
        
        .top-ui > * {{
            pointer-events: auto;
        }}
        
        .top-left-ui {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        
        .go-latest-btn {{
            background: rgba(168, 85, 247, 0.9);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 50px;
            padding: 8px 16px;
            color: #FFFFFF;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 6px;
            transition: all 0.3s ease;
        }}
        
        .date-selector {{
            background: rgba(0,0,0,0.6);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 8px 12px;
            color: #FFFFFF;
            font-size: 14px;
        }}
        
        .date-selector select {{
            background: rgba(255,255,255,0.1);
            color: #FFFFFF;
            border: none;
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
        }}
        
        .date-selector select option {{
            background: #000000;
            color: #FFFFFF;
        }}
        
        .update-time {{
            color: #9CA3AF;
            font-size: 12px;
            font-weight: 500;
            background: rgba(0,0,0,0.4);
            backdrop-filter: blur(10px);
            padding: 8px 12px;
            border-radius: 8px;
        }}
        
        .nav-hint {{
            position: fixed;
            bottom: 24px;
            left: 50%;
            transform: translateX(-50%);
            color: #9CA3AF;
            font-size: 12px;
            font-weight: 500;
            opacity: 0.7;
            z-index: 100;
        }}
        
        .progress-container {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 3px;
            background: rgba(255,255,255,0.1);
            z-index: 1001;
        }}
        
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #A855F7 0%, #3B82F6 100%);
            width: 0%;
            transition: width 0.3s ease;
        }}
    </style>
</head>
<body>
    <div class="progress-container">
        <div class="progress-fill" id="progressFill"></div>
    </div>
    
    <div class="top-ui">
        <div class="go-latest-btn" onclick="goToLatest()">
            ⬆ 최신
        </div>
        <div class="date-selector">
            <select id="dateSelect" onchange="loadNewsForDate(this.value)">
                {dates_options}
            </select>
        </div>
    </div>
    
    <div class="reels-container" id="reelsContainer">
    </div>
    
    <div class="nav-hint">
        위/아래로 스크롤
    </div>
    
    <script>
        const allNewsFlat = {all_news_flat_json};
        
        const container = document.getElementById('reelsContainer');
        const progressFill = document.getElementById('progressFill');
        const dateSelect = document.getElementById('dateSelect');
        
        // 현재 보여줄 데이터: 처음부터 전체 데이터를 로드하여 스와이프 문제를 해결합니다.
        let currentData = allNewsFlat;
        let currentIndex = 0;
        
        function renderReels(newsItems, startIndex = 0) {{
            container.innerHTML = '';
            
            const defaultImages = [
                'https://images.unsplash.com/photo-1677442136019-21780ecad995',
                'https://images.unsplash.com/photo-1555255707-c07966088b7b',
                'https://images.unsplash.com/photo-1620712943543-bcc4688e7485'
            ];
            
            newsItems.forEach((item, index) => {{
                const reel = document.createElement('div');
                reel.className = 'reel';
                
                const bgImage = item.image 
                    ? item.image 
                    : defaultImages[(startIndex + index) % defaultImages.length];
                
                const keywordTag = item.category_keyword ? `<span class="meta-separator">|</span><span class="reel-tag">#${{item.category_keyword}}</span>` : '';
                const displayTitle = item.translated_title || item.title;
                
                // 날짜 불일치 해결: new Date() 사용을 피하고 문자열 앞 10자리(YYYY-MM-DD)를 그대로 사용
                const displayDate = item.date.substring(0, 10);
                
                let summaryText = item.summary || '전체 기사 내용을 확인하려면 아래 링크를 클릭하세요.';
                // 불렛 포인트를 이모지로 변경하여 가독성 개선
                summaryText = summaryText.replace(/•/g, '✔️');
                
                reel.innerHTML = `
                    <div class="reel-bg" style="background-image: url(${{bgImage}})"></div>
                    <div class="content-overlay">
                        <div class="reel-meta">
                            <span class="reel-source">${{item.source || 'Unknown'}}</span>
                            <span class="meta-separator">|</span>
                            <span class="reel-date">${{displayDate}}</span>
                            ${{keywordTag}}
                        </div>
                        <h2 class="reel-title">${{displayTitle}}</h2>
                        <div class="reel-summary">${{summaryText}}</div>
                    </div>
                    <a class="reel-link" href="${{item.link}}" target="_blank">자세히 보기 &gt;</a>
                `;
                
                container.appendChild(reel);
            }});
            
            updateProgress();
        }}
        
        function updateProgress() {{
            const reels = container.querySelectorAll('.reel');
            if (reels.length > 0) {{
                const progress = ((currentIndex + 1) / reels.length) * 100;
                progressFill.style.width = `${{progress}}%`;
            }}
        }}
        
        function loadNewsForDate(date) {{
            // 전체 데이터에서 해당 날짜가 시작되는 첫 인덱스를 찾습니다.
            const firstIndex = allNewsFlat.findIndex(item => item.date === date);
            if (firstIndex !== -1) {{
                // 전체 리스트를 다시 렌더링하되, 해당 위치로 스크롤을 이동시킵니다.
                // 이렇게 해야 위로 스와이프했을 때 이전 날짜 뉴스가 보입니다.
                renderReels(allNewsFlat, firstIndex);
                // 스크롤 위치 강제 이동 (화면 높이 * 인덱스)
                setTimeout(() => {{
                    container.scrollTop = firstIndex * window.innerHeight;
                }}, 10);
            }} else {{
                alert('해당 날짜의 뉴스가 없습니다.');
            }}
        }}
        
        function goToLatest() {{
            if (allNewsFlat.length > 0) {{
                loadNewsForDate(allNewsFlat[0].date);
            }}
        }}
        
        // 스크롤 시 현재 보고 있는 뉴스에 맞춰 드롭다운 날짜 변경
        container.addEventListener('scroll', () => {{
            const reelHeight = window.innerHeight;
            // 절반 이상 넘어갔을 때 인덱스 변경 인식
            currentIndex = Math.round(container.scrollTop / reelHeight);
            updateProgress();
            
            // 현재 보고 있는 릴스의 날짜로 드롭다운 업데이트
            if (allNewsFlat[currentIndex]) {{
                const currentDate = allNewsFlat[currentIndex].date;
                if (dateSelect.value !== currentDate) {{
                    dateSelect.value = currentDate;
                }}
            }}
        }}, {{ passive: true }});
        
        // [핵심 수정] 초기화 시 전체 데이터를 렌더링합니다.
        // 기존에는 20개만 렌더링해서 스와이프가 막혔던 문제를 해결함.
        renderReels(allNewsFlat);
        
        // [핵심 수정] 초기 로딩 시 드롭다운 값을 첫 번째 뉴스의 날짜로 강제 동기화
        if (allNewsFlat.length > 0) {{
            dateSelect.value = allNewsFlat[0].date;
        }}
        
        // 터치 스와이프 보조 기능 (필요시)
        let touchStartY = 0;
        container.addEventListener('touchstart', (e) => {{
            touchStartY = e.touches[0].clientY;
        }}, {{ passive: true }});
        
        container.addEventListener('touchend', (e) => {{
            const touchEndY = e.changedTouches[0].clientY;
            const diff = touchStartY - touchEndY;
            
            // 짧은 터치로도 페이지 넘김이 잘 되도록 보조
            if (Math.abs(diff) > 50) {{
                // 기본 스크롤 동작이 있으므로 추가 로직은 제거하여 충돌 방지
                // 필요한 경우 스냅 포인트 미세 조정 가능
            }}
        }}, {{ passive: true }});
    </script>
</body>
</html>'''
    
    return html

if __name__ == '__main__':
    try:
        log_message("=" * 50)
        log_message("AI News Shorts - Batch Processing Started")
        log_message("=" * 50)
        
        # Load existing data for 10-day rolling window
        all_data = load_all_news()
        existing_dates = {d['date']: d for d in all_data.get('dates', [])}
        
        # Collect all existing links for global deduplication (across all dates)
        existing_links = set()
        for date_entry in all_data.get('dates', []):
            for news in date_entry.get('news', []):
                if news.get('link'):
                    existing_links.add(news['link'])
        
        # Collect today's data only (rolling window will maintain 10 days)
        # UTC+9 (KST) 기준으로 오늘 날짜 설정
        today = (datetime.now() + timedelta(hours=9)).strftime('%Y-%m-%d')
        
        log_message(f"\nFetching news for {today}...")
        
        news_items = fetch_all_news_for_date(today, existing_links)
        log_message(f"  Total collected: {len(news_items)} articles")
        
        if news_items:
            # [최우선] 큐레이션 먼저 수행하여 상위 30개의 뉴스만 선별
            log_message("  Curating news (deduplicate & select top 30)...")
            news_items = curate_news_list(news_items)
            
            # Store original title/summary before translation (큐레이션 후 수행)
            for item in news_items:
                item['original_title'] = item.get('title', '')
                item['original_summary'] = item.get('description', '')[:300]
            
            # 큐레이션된 30개에 대해서만 이미지 크롤링 수행 (비용 절감)
            log_message("  Crawling og:image for curated articles...")
            for item in news_items:
                if item.get('link') and not item.get('image'):
                    source = item.get('source', '')
                    
                    if source not in ['Google News']:
                        item['image'] = fetch_article_image(item['link'], None)
                    else:
                        item['image'] = None
            
            # 큐레이션된 30개에 대해서만 요약/번역 수행 (비용 절감)
            log_message("  Batch summarizing curated articles (10 at a time)...")
            news_items = batch_summarize(news_items)
            
            # Merge with existing news for today if any
            existing_today_news = existing_dates.get(today, {}).get('news', [])
            combined_news = existing_today_news + news_items
            
            # Sort combined news by priority (optional but good for consistency)
            # combined_news = sort_by_source_priority(combined_news) # Assuming sort is stable
            
            existing_dates[today] = {
                'date': today,
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'news': combined_news
            }
            
            log_message(f"  Completed: {len(news_items)} new articles (Total for today: {len(combined_news)})")
        else:
            log_message("  No new articles found for today")
        
        # Sort by date descending and keep only last 10 days
        sorted_dates = sorted(existing_dates.values(), key=lambda x: x['date'], reverse=True)
        all_data['dates'] = sorted_dates[:10]
        
        save_all_news(all_data)
        log_message(f"\nSaved {len(all_data['dates'])} days of data (10-day rolling window)")
        
        # Generate HTML
        html_content = generate_html([])
        with open('/root/first/ai_news.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        log_message(f"\nGenerated ai_news.html")
        
        # Count total articles
        total_articles = sum(len(d['news']) for d in all_data['dates'])
        log_message(f"Total articles: {total_articles}")
        
        log_message("\n" + "=" * 50)
        log_message("Processing Complete!")
        log_message("=" * 50)
        
    except Exception as e:
        log_message(f"Error: {e}")
        import traceback
        traceback.print_exc()
