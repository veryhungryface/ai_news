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
    {
        'name': 'Google News (AI)',
        'url': 'https://news.google.com/rss/search?q=AI&hl=ko&gl=KR&ceid=KR:ko',
        'source': 'Google News'
    },
    {
        'name': 'OpenAI News',
        'url': 'https://openai.com/news/rss.xml',
        'source': 'OpenAI'
    },
    {
        'name': 'MIT News AI',
        'url': 'https://news.mit.edu/rss/topic/artificial-intelligence2',
        'source': 'MIT News'
    },
    {
        'name': 'AI News',
        'url': 'https://www.artificialintelligence-news.com/feed/',
        'source': 'AI News'
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
    """Parse RSS date to YYYY-MM-DD format"""
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
            return dt.strftime('%Y-%m-%d')
        except:
            continue
    
    if source in ['OpenAI', 'MIT News', 'AI News']:
        return datetime.now().strftime('%Y-%m-%d')
    
    return datetime.now().strftime('%Y-%m-%d')

def fetch_rss_news(source_info, target_date):
    """Fetch news from RSS source for a specific date"""
    try:
        response = requests.get(source_info['url'], timeout=30)
        response.encoding = 'utf-8'
        
        root = ET.fromstring(response.content)
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
            
            if news_date != target_date:
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

def fetch_all_news_for_date(target_date):
    """Fetch all news for a specific date from all sources"""
    all_news = []
    
    for source in RSS_SOURCES:
        news = fetch_rss_news(source, target_date)
        all_news.extend(news)
        log_message(f"  {source['name']}: {len(news)} articles")
        time.sleep(1)
    
    seen = set()
    unique_news = []
    for item in all_news:
        if item['link'] not in seen:
            seen.add(item['link'])
            unique_news.append(item)
    
    return unique_news

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
        
        # Build batch prompt
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
2. 각 기사의 핵심을 서술형으로 200자 내외로 요약하세요.
3. 기사의 핵심 키워드 1개를 추출하세요 (최대 5자).

출력 형식:
=== 기사 1 ===
번역된 제목: [영문인 경우 한국어 제목, 한글인 경우 기존 제목]
요약: [서술형 200자 요약]
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
            
            # Extract summary
            summary_match = re.search(r'요약:\s*(.+?)(?:\n===|$)', section_content, re.DOTALL)
            if summary_match:
                articles[idx]['summary'] = summary_match.group(1).strip()
            
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
    """Generate HTML with all 10 days displayed"""
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
    
    dates_options = ''.join(
        f'<option value="{item["date"]}" {"selected" if item["date"] == datetime.now().strftime("%Y-%m-%d") else ""}>{item["date"]}</option>'
        for item in all_data['dates']
    )
    
    initial_news = all_news_flat[:20]
    
    all_news_by_date_json = json.dumps(all_news_by_date, ensure_ascii=False)
    all_news_flat_json = json.dumps(all_news_flat, ensure_ascii=False)
    initial_news_json = json.dumps(initial_news, ensure_ascii=False)
    
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
            background-size: cover;
            background-position: center;
            transition: transform 0.3s ease;
        }}
        
        .reel::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(180deg, transparent 40%, rgba(0,0,0,0.6) 70%, rgba(0,0,0,0.9) 100%);
            z-index: 1;
        }}
        
        .content-overlay {{
            position: relative;
            z-index: 2;
            padding: 24px;
            padding-bottom: 48px;
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
            font-size: 26px;
            font-weight: 700;
            line-height: 1.4;
            margin-bottom: 12px;
            text-shadow: 0 2px 8px rgba(0,0,0,0.5);
            word-wrap: break-word;
        }}
        
        .reel-summary {{
            color: #FFFFFF;
            font-size: 16px;
            line-height: 1.6;
            margin-bottom: 16px;
            text-shadow: 0 1px 4px rgba(0,0,0,0.5);
            white-space: pre-line;
        }}
        
        .reel-meta {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 12px;
            flex-wrap: wrap;
        }}
        
        .reel-source {{
            background: rgba(59, 130, 246, 0.9);
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            color: #FFFFFF;
        }}
        
        .reel-date {{
            color: #9CA3AF;
            font-size: 13px;
            font-weight: 500;
        }}
        
        .reel-keyword {{
            display: inline-block;
            background: rgba(168, 85, 247, 0.9);
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 700;
            color: #FFFFFF;
            margin-bottom: 14px;
            box-shadow: 0 2px 8px rgba(168, 85, 247, 0.3);
        }}
        
        .reel-link {{
            display: inline-block;
            background: linear-gradient(135deg, #3B82F6 0%, #8B5CF6 100%);
            color: #FFFFFF;
            padding: 12px 24px;
            border-radius: 10px;
            text-decoration: none;
            font-weight: 600;
            font-size: 14px;
            transition: all 0.3s ease;
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
        }}
        
        .reel-link:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(59, 130, 246, 0.4);
        }}
        
        .top-ui {{
            position: fixed;
            top: 16px;
            left: 16px;
            right: 16px;
            z-index: 1000;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 16px;
            pointer-events: none;
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
        
        .go-latest-btn:hover {{
            background: #A855F7;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(168, 85, 247, 0.4);
        }}
        
        .go-latest-btn::before {{
            content: '⬆';
            font-size: 14px;
            font-weight: 700;
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
        <div class="top-left-ui">
            <div class="go-latest-btn" onclick="goToLatest()">
                최신 뉴스
            </div>
            <div class="date-selector">
                <select id="dateSelect" onchange="loadNewsForDate(this.value)">
                    {dates_options}
                </select>
            </div>
        </div>
        <div class="update-time">
            {update_time}
        </div>
    </div>
    
    <div class="reels-container" id="reelsContainer">
    </div>
    
    <div class="nav-hint">
        위/아래로 스크롤
    </div>
    
    <script>
        const allNewsByDate = {all_news_by_date_json};
        const allNewsFlat = {all_news_flat_json};
        const initialNews = {initial_news_json};
        
        const container = document.getElementById('reelsContainer');
        const progressFill = document.getElementById('progressFill');
        const dateSelect = document.getElementById('dateSelect');
        
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
                reel.style.backgroundImage = `url(${{bgImage}})`;
                
                const keyword = item.category_keyword ? `<div class="reel-keyword">#${{item.category_keyword}}</div>` : '';
                const displayTitle = item.translated_title || item.title;
                
                reel.innerHTML = `
                    <div class="content-overlay">
                        <div class="reel-meta">
                            <span class="reel-source">${{item.source || 'Unknown'}}</span>
                            <span class="reel-date">${{item.date}}</span>
                        </div>
                        ${{keyword}}
                        <h2 class="reel-title">${{displayTitle}}</h2>
                        <p class="reel-summary">${{item.summary || '전체 기사 내용을 확인하려면 아래 링크를 클릭하세요.'}}</p>
                        <a class="reel-link" href="${{item.link}}" target="_blank">자세히 보기</a>
                    </div>
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
            const firstIndex = allNewsFlat.findIndex(item => item.date === date);
            if (firstIndex !== -1) {{
                currentData = allNewsFlat;
                renderReels(allNewsFlat, firstIndex);
                container.scrollTop = firstIndex * window.innerHeight;
            }} else {{
                alert('해당 날짜의 뉴스가 없습니다.');
            }}
        }}
        
        function goToLatest() {{
            loadNewsForDate(allNewsFlat[0]?.date);
        }}
        
        container.addEventListener('scroll', () => {{
            const reelHeight = window.innerHeight;
            currentIndex = Math.round(container.scrollTop / reelHeight);
            updateProgress();
            
            if (currentData[currentIndex]) {{
                const currentDate = currentData[currentIndex].date;
                if (dateSelect.value !== currentDate) {{
                    dateSelect.value = currentDate;
                }}
            }}
        }}, {{ passive: true }});
        
        renderReels(initialNews);
        
        let touchStartY = 0;
        container.addEventListener('touchstart', (e) => {{
            touchStartY = e.touches[0].clientY;
        }}, {{ passive: true }});
        
        container.addEventListener('touchend', (e) => {{
            const touchEndY = e.changedTouches[0].clientY;
            const diff = touchStartY - touchEndY;
            
            if (Math.abs(diff) > 50) {{
                const reelHeight = window.innerHeight;
                if (diff > 0) {{
                    container.scrollTop += reelHeight;
                }} else {{
                    container.scrollTop -= reelHeight;
                }}
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
        
        # Collect today's data only (rolling window will maintain 10 days)
        today = datetime.now().strftime('%Y-%m-%d')
        
        log_message(f"\nFetching news for {today}...")
        
        news_items = fetch_all_news_for_date(today)
        log_message(f"  Total collected: {len(news_items)} articles")
        
        if news_items:
            # Crawl og:image for each article
            log_message("  Crawling og:image for each article...")
            for item in news_items:
                if item.get('link') and not item.get('image'):
                    source = item.get('source', '')
                    
                    # For non-Google sources, crawl og:image from article URL
                    if source not in ['Google News']:
                        item['image'] = fetch_article_image(item['link'], None)
                    else:
                        # For Google News, don't crawl (can't get original article URL)
                        # Will use default image instead
                        item['image'] = None
            
            # Store original title/summary before translation
            for item in news_items:
                item['original_title'] = item.get('title', '')
                item['original_summary'] = item.get('description', '')[:300]
            
            # Batch summarize
            log_message("  Batch summarizing (10 at a time)...")
            news_items = batch_summarize(news_items)
            
            # Add/Replace today's data
            existing_dates[today] = {
                'date': today,
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'news': news_items
            }
            
            log_message(f"  Completed: {len(news_items)} articles")
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
