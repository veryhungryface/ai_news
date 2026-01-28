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
import pytz

load_dotenv()

KST = pytz.timezone('Asia/Seoul')

def get_kst_now():
    return datetime.now(KST)

def get_kst_today():
    return get_kst_now().strftime('%Y-%m-%d')

def get_kst_timestamp():
    return get_kst_now().strftime('%Y-%m-%d %H:%M:%S')

GLM_API_KEY = os.getenv('GLM_API_KEY')

RSS_SOURCES = [
    # 1. 정부·공공 공식 채널 (정책 신뢰도 최상)
    {
        'name': 'Korea Policy Briefing',
        'url': 'https://www.korea.kr/rss/policy.xml',
        'source': '정책브리핑',
        'keywords': ['인공지능', 'AI', '디지털교과서', '에듀테크', '디지털 전환', 'AI 교육']
    },

    # 2. 주요 언론사 (시장·기업 흐름)
    {
        'name': 'Yonhap News',
        'url': 'https://www.yna.co.kr/rss/society.xml',
        'source': '연합뉴스',
        'keywords': ['인공지능', 'AI', '디지털교과서', '에듀테크', '디지털 전환', 'AI 교육', '소프트웨어 교육', '코딩 교육']
    },
    
    # 3. 전문 매체
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
    
    # 4. 해외 주요 매체
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
    {
        'name': 'KnowTechie AI',
        'url': 'https://knowtechie.com/category/ai/feed/',
        'source': 'KnowTechie'
    },
    {
        'name': 'AI Business',
        'url': 'https://aibusiness.com/rss.xml',
        'source': 'AI Business'
    },
    {
        'name': 'AIModels.fyi',
        'url': 'https://aimodels.substack.com/feed',
        'source': 'AIModels'
    },
    {
        'name': 'Science Daily AI',
        'url': 'https://www.sciencedaily.com/rss/computers_math/artificial_intelligence.xml',
        'source': 'Science Daily'
    },
    {
        'name': 'MIT AI News',
        'url': 'https://news.mit.edu/rss/topic/artificial-intelligence2',
        'source': 'MIT News'
    },
    
    # 5. 기업 AI 블로그
    {
        'name': 'Google AI Blog',
        'url': 'https://blog.google/technology/ai/rss/',
        'source': 'Google AI'
    },
    {
        'name': 'NVIDIA AI Blog',
        'url': 'https://blogs.nvidia.com/blog/category/deep-learning/feed/',
        'source': 'NVIDIA'
    },
    
    # 6. 커뮤니티
    {
        'name': 'Becoming Human',
        'url': 'https://becominghuman.ai/feed',
        'source': 'Medium AI'
    },
    {
        'name': 'AI Weirdness',
        'url': 'https://aiweirdness.com/rss',
        'source': 'AI Weirdness'
    }
]

DEFAULT_IMAGES = [
    'https://images.unsplash.com/photo-1677442136019-21780ecad995?w=1920&q=80',
    'https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=1920&q=80',
    'https://images.unsplash.com/photo-1555255707-c07966088b7b?w=1920&q=80',
    'https://images.unsplash.com/photo-1676299081847-c3c644878e36?w=1920&q=80',
    'https://images.unsplash.com/photo-1485827404703-89b55fcc595e?w=1920&q=80'
]

HUGGINGFACE_DEFAULT_IMAGES = [
    'https://images.unsplash.com/photo-1677442136019-21780ecad995?w=1920&q=80',
    'https://images.unsplash.com/photo-1676299081847-c3c644878e36?w=1920&q=80',
    'https://images.unsplash.com/photo-1535378917042-10a22c95931a?w=1920&q=80',
    'https://images.unsplash.com/photo-1518770660439-4636190af475?w=1920&q=80',
    'https://images.unsplash.com/photo-1507146153580-69a1fe6d8aa1?w=1920&q=80',
]

def log_message(message):
    timestamp = get_kst_timestamp()
    print(f"[{timestamp}] {message}")

def is_english_text(text):
    """Check if text is primarily English"""
    if not text:
        return False
    english_chars = sum(1 for c in text if ord(c) < 128)
    total_chars = len(text.strip())
    return total_chars > 0 and (english_chars / total_chars) > 0.5

# ============================================================
# HuggingFace Trending Models Pipeline
# ============================================================

def fetch_huggingface_trending(limit=20):
    """Fetch trending models from HuggingFace REST API"""
    url = 'https://huggingface.co/api/models'
    params = {'sort': 'trendingScore', 'direction': '-1', 'limit': limit}
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        if response.status_code == 200:
            models = response.json()
            log_message(f"  HuggingFace API: Fetched {len(models)} trending models")
            return models
        else:
            log_message(f"  HuggingFace API error: {response.status_code}")
            return []
    except Exception as e:
        log_message(f"  HuggingFace API exception: {e}")
        return []

def fetch_model_readme_and_image(model_id, model_data=None):
    """Fetch README.md content and extract first image from a HuggingFace model"""
    readme_url = f"https://huggingface.co/{model_id}/raw/main/README.md"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    readme_text = ""
    image_url = None
    
    try:
        response = requests.get(readme_url, headers=headers, timeout=15)
        if response.status_code == 200:
            readme_text = response.text[:3000]  # Limit to first 3000 chars
            
            # Extract first image from markdown
            # Pattern 1: ![alt](url)
            img_match = re.search(r'!\[[^\]]*\]\(([^)]+)\)', readme_text)
            if img_match:
                img_src = img_match.group(1)
                # Convert relative URLs to absolute
                if img_src.startswith('http'):
                    image_url = img_src
                elif not img_src.startswith('data:'):
                    image_url = f"https://huggingface.co/{model_id}/resolve/main/{img_src}"
            
            # Pattern 2: <img src="...">
            if not image_url:
                img_tag_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', readme_text)
                if img_tag_match:
                    img_src = img_tag_match.group(1)
                    if img_src.startswith('http'):
                        image_url = img_src
                    elif not img_src.startswith('data:'):
                        image_url = f"https://huggingface.co/{model_id}/resolve/main/{img_src}"
        elif response.status_code in [401, 403] and model_data:
            # Gated model - build description from API data
            tags = model_data.get('tags', [])
            pipeline_tag = model_data.get('pipeline_tag', '')
            downloads = model_data.get('downloads', 0)
            likes = model_data.get('likes', 0)
            
            tag_str = ', '.join([t for t in tags if not t.startswith('license') and ':' not in t][:5])
            readme_text = f"Model: {model_id}\nPipeline: {pipeline_tag}\nTags: {tag_str}\nDownloads: {downloads:,}\nLikes: {likes}"
    except Exception as e:
        log_message(f"    README fetch error for {model_id}: {e}")
    
    # Fallback image: HuggingFace model card thumbnail
    if not image_url:
        image_url = f"https://huggingface.co/{model_id}/resolve/main/thumbnail.png"
    
    return readme_text, image_url

def summarize_model_with_glm(model_id, readme_text):
    """Generate 4-line summary for a HuggingFace model using GLM API"""
    if not readme_text or len(readme_text.strip()) < 50:
        model_name = model_id.split('/')[-1]
        return [
            f"{model_name} AI 모델 공개",
            "HuggingFace에서 트렌딩 중",
            "다운로드 및 상세 정보는 링크에서",
            "최신 오픈소스 AI 기술"
        ]
    
    url = "https://api.z.ai/api/coding/paas/v4/chat/completions"
    headers = {
        'Authorization': f'Bearer {GLM_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    prompt = f"""다음은 HuggingFace 모델 '{model_id}'의 README 문서입니다:

{readme_text[:2000]}

위 문서를 분석해서 일반인이 이해하기 쉬운 4개의 핵심 문장으로 요약해주세요.

[필수 제약 사항]
- 반드시 JSON Format으로 출력: {{"summary": ["문장1", "문장2", "문장3", "문장4"]}}
- 각 문장은 30자 내외로 간결하게 작성
- 문체는 '~함', '~제공', '~공개' 등 뉴스 헤드라인 스타일(명사형 종결) 유지
- 이모지 사용 금지
- 반드시 한국어로 작성"""

    data = {
        'model': 'glm-4.7',
        'messages': [
            {'role': 'system', 'content': '너는 IT 트렌드 뉴스 에디터야. 기술 문서를 간결한 뉴스 형식으로 요약하는 전문가야.'},
            {'role': 'user', 'content': prompt}
        ],
        'max_tokens': 500,
        'temperature': 0.5,
        'thinking': {'type': 'disabled'}
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content'].strip()
                
                # Parse JSON response
                json_match = re.search(r'\{[^{}]*"summary"[^{}]*\}', content, re.DOTALL)
                if json_match:
                    try:
                        parsed = json.loads(json_match.group())
                        if 'summary' in parsed and isinstance(parsed['summary'], list):
                            return parsed['summary'][:4]
                    except json.JSONDecodeError:
                        pass
                
                # Fallback: extract bullet points or lines
                lines = [l.strip() for l in content.split('\n') if l.strip() and not l.startswith('{')]
                if len(lines) >= 4:
                    return lines[:4]
    except Exception as e:
        log_message(f"    GLM API error for {model_id}: {e}")
    
    # Default fallback
    return [
        f"{model_id.split('/')[-1]} 모델 공개",
        "HuggingFace 트렌딩 모델",
        "최신 AI 기술 적용",
        "상세 정보는 링크 참조"
    ]

def process_huggingface_models(existing_links=None):
    """Main pipeline: Fetch trending models, get README, summarize with GLM
    
    Args:
        existing_links: Set of existing article links to skip (for deduplication)
    """
    log_message("Processing HuggingFace Trending Models...")
    
    if existing_links is None:
        existing_links = set()
    
    models = fetch_huggingface_trending(limit=20)
    if not models:
        log_message("  No models fetched from HuggingFace")
        return []
    
    today = get_kst_today()
    processed_models = []
    skipped_count = 0
    
    for i, model in enumerate(models):
        model_id = model.get('modelId', '')
        if not model_id:
            continue
        
        model_link = f'https://huggingface.co/{model_id}'
        if model_link in existing_links:
            log_message(f"  [{i+1}/{len(models)}] Skipping (already exists): {model_id}")
            skipped_count += 1
            continue
        
        log_message(f"  [{i+1}/{len(models)}] Processing: {model_id}")
        
        # Fetch README and image (pass model data for gated models fallback)
        readme_text, image_url = fetch_model_readme_and_image(model_id, model)
        
        if not image_url or 'thumbnail.png' in image_url:
            image_url = HUGGINGFACE_DEFAULT_IMAGES[i % len(HUGGINGFACE_DEFAULT_IMAGES)]
        
        summary_list = summarize_model_with_glm(model_id, readme_text)
        summary_text = '\n'.join([f'• {s}' for s in summary_list])
        
        # Build news-compatible data structure
        model_data = {
            'title': model_id,
            'link': f'https://huggingface.co/{model_id}',
            'date': today,
            'source': 'HuggingFace',
            'description': summary_text,
            'image': image_url,
            'is_english': True,
            'summary': summary_text,
            'translated_title': model_id,
            'category_keyword': 'AI Model',
            'category': 'AI Model'  # For frontend filtering
        }
        
        processed_models.append(model_data)
        time.sleep(1)
    
    log_message(f"  Processed {len(processed_models)} new models, skipped {skipped_count} existing")
    return processed_models

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
        '%a, %d %b %Y %H:%M:%S %z',  # Added for Yonhap (+0900)
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

def fetch_rss_news(source_info, target_date, include_yesterday=False):
    """Fetch news from RSS source for a specific date (optionally include yesterday)"""
    # Simple headers often work better for RSS feeds
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'application/rss+xml, application/xml, text/xml, */*'
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
            
            if not news_date:
                continue
            
            target_dt = datetime.strptime(target_date, '%Y-%m-%d')
            yesterday = (target_dt - timedelta(days=1)).strftime('%Y-%m-%d')
            tomorrow = (target_dt + timedelta(days=1)).strftime('%Y-%m-%d')
            valid_dates = {target_date, tomorrow}
            if include_yesterday:
                valid_dates.add(yesterday)
            if news_date not in valid_dates:
                continue
            
            description = item.find('description')
            desc = description.text if description is not None else ''
            clean_desc = re.sub('<[^<]+?>', '', desc)[:500] if desc else ''
            
            # Keyword filtering (if specified in source config)
            keywords = source_info.get('keywords', [])
            if keywords:
                # Check if any keyword matches
                # For keywords with spaces (e.g. "AI 교육"), require ALL words to be present (AND condition)
                text_to_check = (title + " " + clean_desc).lower()
                
                match_found = False
                for k in keywords:
                    sub_keywords = k.lower().split()
                    # Check if all sub-keywords are present in text
                    if all(sub_k in text_to_check for sub_k in sub_keywords):
                        match_found = True
                        break
                
                if not match_found:
                    continue
            
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

def fetch_all_news_for_date(target_date, existing_links=None, include_yesterday=False):
    """Fetch all news for a specific date from all sources"""
    all_news = []
    if existing_links is None:
        existing_links = set()
    
    for source in RSS_SOURCES:
        news = fetch_rss_news(source, target_date, include_yesterday)
        
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
    """Sort articles by source priority: Policy -> Tech -> Global"""
    source_priority = {
        # 1. 정책 (Policy)
        '대한민국 정책브리핑': 0,
        '정책브리핑': 0,
        
        # 2. 기술/트렌드 (Tech) - Domestic
        '연합뉴스': 1,
        'AI타임스': 2,
        'ITWorld': 2,
        
        # 3. 해외 (Global)
        'OpenAI': 3,
        'HuggingFace': 3,
        'TechCrunch': 3
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
        
        # Pre-fill summary with description as fallback
        for article in batch:
            if not article.get('summary'):
                article['summary'] = article.get('description', '')[:300]
        
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
        
        retries = 3
        for attempt in range(retries):
            try:
                response = requests.post(url, headers=headers, json=data, timeout=120)
                if response.status_code == 200:
                    result = response.json()
                    if 'choices' in result and len(result['choices']) > 0:
                        content = result['choices'][0]['message']['content']
                        log_message(f"  Batch {i//batch_size + 1}: API success")
                        parse_batch_response(batch, content)
                        break
                else:
                    log_message(f"  Batch {i//batch_size + 1}: API error {response.status_code} (Attempt {attempt+1}/{retries})")
            except Exception as e:
                log_message(f"  Batch {i//batch_size + 1}: Error - {e} (Attempt {attempt+1}/{retries})")
            
            if attempt < retries - 1:
                time.sleep(5) # Wait before retry
        
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
        with open('all_news.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {'dates': []}
    except json.JSONDecodeError:
        return {'dates': []}

def save_all_news(data):
    """Save all news to JSON file"""
    with open('all_news.json', 'w', encoding='utf-8') as f:
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
    update_time = get_kst_timestamp()
    
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
        f'<option value="{item["date"]}">{item["date"][5:]}</option>'
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
        
        /* Intro Screen Styles */
        .intro-screen {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: #000000;
            z-index: 9999;
            display: flex;
            justify-content: center;
            align-items: center;
            transition: opacity 0.8s ease-out;
        }}

        .intro-text {{
            color: #FFFFFF;
            font-family: 'Courier New', Courier, monospace;
            font-size: 2.2rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .intro-typing-wrapper {{
            overflow: hidden;
            border-right: .15em solid #FFFFFF;
            white-space: nowrap;
            margin: 0 auto;
            letter-spacing: 0.1em;
            animation: 
                typing 2s steps(11, end),
                blink-caret .75s step-end infinite;
            width: 0;
            animation-fill-mode: forwards;
        }}

        .intro-shorts {{
            display: inline-flex;
            align-items: baseline;
            vertical-align: bottom;
            transition: color 0.6s ease, padding-left 0.6s cubic-bezier(0.25, 1, 0.5, 1);
        }}

        .intro-short-part {{
            display: inline-block;
            overflow: hidden;
            width: 5.5ch; /* 'short' length + buffer */
            text-align: right; /* Ensure text sticks to the right (near 's') */
            margin-right: 0.1em; /* Restore letter-spacing between t and s */
            transition: width 0.6s cubic-bezier(0.25, 1, 0.5, 1), margin-right 0.6s cubic-bezier(0.25, 1, 0.5, 1);
            white-space: nowrap;
        }}

        .intro-shorts.collapsed {{
            color: #FF0000;
            padding-left: calc(5.5ch + 0.1em); /* Compensate for width + margin reduction */
        }}

        .intro-shorts.collapsed .intro-short-part {{
            width: 0 !important;
            margin-right: 0 !important;
        }}

        .intro-news {{
            color: #FFFFFF;
        }}

        @keyframes typing {{
            from {{ width: 0 }}
            to {{ width: 12ch }}
        }}

        @keyframes blink-caret {{
            from, to {{ border-color: transparent }}
            50% {{ border-color: #FFFFFF }}
        }}

        .intro-hidden {{
            opacity: 0;
            pointer-events: none;
        }}

        /* Landscape Warning */
        .landscape-warning {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: #000000;
            z-index: 10000;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            color: #FFFFFF;
            text-align: center;
        }}

        .landscape-warning .icon {{
            font-size: 48px;
            margin-bottom: 20px;
            animation: rotate-phone 2s infinite ease-in-out;
        }}

        .landscape-warning p {{
            font-size: 18px;
            font-weight: 600;
        }}

        @keyframes rotate-phone {{
            0% {{ transform: rotate(0deg); }}
            50% {{ transform: rotate(-90deg); }}
            100% {{ transform: rotate(0deg); }}
        }}

        @media screen and (orientation: landscape) {{
            .landscape-warning {{
                display: flex;
            }}
            .reels-container, .top-ui, .nav-hint, .progress-container {{
                display: none !important;
            }}
        }}

        /* Desktop: Show as phone-sized container centered with black background */
        @media screen and (min-width: 768px) {{
            .landscape-warning {{
                display: none !important;
            }}
            
            .reels-container, .nav-hint, .progress-container {{
                display: block !important;
            }}
            
            .top-ui {{
                display: flex !important;
            }}
            
            html, body {{
                background: #000000;
            }}
            
            .reels-container {{
                max-width: 430px;
                margin: 0 auto;
                box-shadow: 0 0 60px rgba(255, 255, 255, 0.08);
                border-left: 1px solid rgba(255, 255, 255, 0.1);
                border-right: 1px solid rgba(255, 255, 255, 0.1);
            }}
            
            .reel {{
                max-width: 430px;
            }}
            
            .top-ui {{
                max-width: 430px;
                left: 50% !important;
                transform: translateX(-50%);
                right: auto !important;
            }}
            
            .progress-container {{
                max-width: 430px;
                left: 50%;
                transform: translateX(-50%);
            }}
            
            .nav-hint {{
                max-width: 430px;
                left: 50%;
                transform: translateX(-50%);
            }}
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
        
        .reel-bg-blur {{
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 60%;
            background-size: cover;
            background-position: center;
            filter: blur(25px);
            opacity: 0.5;
            transform: scale(1.1);
            z-index: 0;
        }}
        
        .reel-img-container {{
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 60%;
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 1;
            overflow: hidden;
            background: rgba(0,0,0,0.1);
        }}

        .reel-main-img {{
            width: 100%;
            height: 100%;
            object-fit: contain;
            position: relative;
            z-index: 1;
            transition: transform 0.5s ease;
        }}
        
        .reel-gradient-overlay {{
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 150px;
            background: linear-gradient(to bottom, rgba(0,0,0,0.8) 0%, transparent 100%);
            z-index: 2;
            pointer-events: none;
        }}
        
        .content-overlay {{
            position: absolute;
            top: 60%;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: #000000;
            z-index: 10;
            padding: 24px;
            padding-top: 0; /* Title starts right at the top of this container */
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
            animation: slideUp 0.5s ease-out;
            overflow: visible; /* Allow gradient to extend upwards */
        }}
        
        .content-overlay::before {{
            content: '';
            position: absolute;
            top: -150px; /* Gradient height */
            left: 0;
            right: 0;
            height: 150px;
            background: linear-gradient(to bottom, transparent, #000000);
            pointer-events: none;
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
            word-wrap: break-word;
            letter-spacing: -0.5px;
        }}
        
        .reel-summary {{
            color: rgba(255, 255, 255, 0.95);
            font-size: 16px;
            line-height: 1.8;
            margin-bottom: 60px; /* Space for the button */
            white-space: pre-line;
            font-weight: 400;
        }}
        
        .reel-summary strong {{
            color: #FFFFFF;
            font-weight: 700;
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
            justify-content: space-between;
            align-items: center;
            pointer-events: none;
        }}
        
        .top-ui > * {{
            pointer-events: auto;
        }}
        
        .header-logo {{
            font-family: 'Courier New', Courier, monospace;
            font-size: 20px;
            font-weight: bold;
            display: flex;
            align-items: center;
            text-shadow: 0 2px 4px rgba(0,0,0,0.5);
            cursor: default;
        }}
        
        .logo-shorts {{
            color: #FF0000;
        }}
        
        .logo-news {{
            color: #FFFFFF;
        }}
        
        .header-capsule {{
            background: rgba(0,0,0,0.6);
            backdrop-filter: blur(20px);
            border-radius: 999px;
            border: 1px solid rgba(255,255,255,0.15);
            display: flex;
            align-items: center;
            height: 40px;
            padding: 0 4px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }}

        .capsule-btn {{
            color: #FFFFFF;
            font-size: 14px;
            font-weight: 600;
            padding: 0 16px;
            cursor: pointer;
            height: 100%;
            display: flex;
            align-items: center;
            transition: opacity 0.2s;
        }}

        .capsule-btn:active {{
            opacity: 0.7;
        }}

        .capsule-btn.active {{
            background: rgba(255,255,255,0.2);
            border-radius: 999px;
        }}

        .capsule-divider {{
            width: 1px;
            height: 14px;
            background: rgba(255,255,255,0.2);
        }}

        .capsule-select {{
            position: relative;
            height: 100%;
            display: flex;
            align-items: center;
        }}

        .capsule-select select {{
            background: transparent;
            border: none;
            color: #FFFFFF;
            font-size: 14px;
            font-weight: 500;
            padding: 0 16px;
            padding-right: 30px; /* Space for arrow */
            cursor: pointer;
            outline: none;
            appearance: none;
            -webkit-appearance: none;
        }}

        .capsule-select::after {{
            content: '▼';
            position: absolute;
            right: 12px;
            font-size: 8px;
            color: rgba(255,255,255,0.5);
            pointer-events: none;
        }}

        .capsule-select select option {{
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
    <!-- Landscape Warning -->
    <div class="landscape-warning">
        <div class="icon">📱</div>
        <p>세로 모드로 봐주세요</p>
    </div>

    <!-- Intro Screen -->
    <div id="introScreen" class="intro-screen">
        <div class="intro-text">
            <div class="intro-typing-wrapper">
                <span id="introShorts" class="intro-shorts"><span class="intro-short-part">short</span>s</span><span class="intro-news">News</span>
            </div>
        </div>
    </div>

    <div class="progress-container">
        <div class="progress-fill" id="progressFill"></div>
    </div>
    
    <div class="top-ui">
        <div class="header-logo">
            <span class="logo-shorts">s</span><span class="logo-news">News</span>
        </div>
        
        <div class="header-capsule" id="dateSelectWrapper">
            <div class="capsule-select">
                <select id="dateSelect" onchange="loadNewsForDate(this.value)">
                    {dates_options}
                </select>
            </div>
        </div>

        <div class="header-capsule">
            <div class="capsule-btn active" id="tabNews" onclick="switchTab('news')">News</div>
            <div class="capsule-divider"></div>
            <div class="capsule-btn" id="tabModel" onclick="switchTab('model')">AI Model</div>
        </div>
    </div>
    
    <div class="reels-container" id="reelsContainer">
    </div>
    
    <div class="nav-hint">
        위/아래로 스크롤
    </div>
    
    <script>
        // Intro Animation Logic
        document.addEventListener('DOMContentLoaded', () => {{
            // 1. Typing animation runs via CSS (2s)
            
            // 2. Collapse animation start (at 2.5s -> 0.5s wait after typing)
            setTimeout(() => {{
                const shortsText = document.getElementById('introShorts');
                if (shortsText) {{
                    shortsText.classList.add('collapsed');
                }}
            }}, 2500);

            // 3. Fade out intro screen (at 3.8s)
            setTimeout(() => {{
                const intro = document.getElementById('introScreen');
                if (intro) {{
                    intro.classList.add('intro-hidden');
                    setTimeout(() => {{
                        intro.style.display = 'none';
                    }}, 800);
                }}
            }}, 3800);
        }});

        const allNewsFlat = {all_news_flat_json};
        
        const container = document.getElementById('reelsContainer');
        const progressFill = document.getElementById('progressFill');
        const dateSelect = document.getElementById('dateSelect');
        
        let currentData = allNewsFlat;
        let currentIndex = 0;
        let currentTab = 'news';
        
        function switchTab(tab) {{
            currentTab = tab;
            const tabNews = document.getElementById('tabNews');
            const tabModel = document.getElementById('tabModel');
            const dateSelectWrapper = document.getElementById('dateSelectWrapper');
            
            if (tab === 'news') {{
                tabNews.classList.add('active');
                tabModel.classList.remove('active');
                if (dateSelectWrapper) dateSelectWrapper.style.display = 'flex';
                currentDateIndex = 0;
                const selectedDate = allDates[0] || '';
                dateSelect.value = selectedDate;
                currentData = allNewsFlat.filter(item => item.category !== 'AI Model' && item.date === selectedDate);
            }} else {{
                tabNews.classList.remove('active');
                tabModel.classList.add('active');
                if (dateSelectWrapper) dateSelectWrapper.style.display = 'none';
                currentData = allNewsFlat.filter(item => item.category === 'AI Model').slice(0, 20);
            }}
            
            currentIndex = 0;
            renderReels(currentData);
            container.scrollTop = 0;
        }}
        
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
                const displayDate = item.date.substring(5, 10);
                
                let summaryText = item.summary || '전체 기사 내용을 확인하려면 아래 링크를 클릭하세요.';
                // 불렛 포인트를 이모지로 변경하여 가독성 개선
                summaryText = summaryText.replace(/•/g, '✔️');
                
                reel.innerHTML = `
                    <div class="reel-bg-blur" style="background-image: url(${{bgImage}})"></div>
                    <div class="reel-img-container">
                        <img class="reel-main-img" src="${{bgImage}}" alt="News Image">
                        <div class="reel-gradient-overlay"></div>
                    </div>
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
            if (currentTab === 'model') return;
            
            currentDateIndex = allDates.indexOf(date);
            if (currentDateIndex === -1) currentDateIndex = 0;
            
            currentData = allNewsFlat.filter(item => item.category !== 'AI Model' && item.date === date);
            currentIndex = 0;
            renderReels(currentData);
            container.scrollTop = 0;
        }}
        
        function goToLatest() {{
            if (currentData.length > 0) {{
                currentIndex = 0;
                renderReels(currentData);
                container.scrollTop = 0;
            }}
        }}
        
        const allDates = [...new Set(allNewsFlat.filter(item => item.category !== 'AI Model').map(item => item.date))].sort().reverse();
        let currentDateIndex = 0;
        
        function loadNextDate() {{
            if (currentTab !== 'news') return false;
            if (currentDateIndex >= allDates.length - 1) return false;
            
            currentDateIndex++;
            const nextDate = allDates[currentDateIndex];
            const nextDateNews = allNewsFlat.filter(item => item.category !== 'AI Model' && item.date === nextDate);
            
            nextDateNews.forEach(item => {{
                currentData.push(item);
            }});
            
            renderReels(currentData);
            dateSelect.value = nextDate;
            return true;
        }}
        
        container.addEventListener('scroll', () => {{
            const reelHeight = window.innerHeight;
            currentIndex = Math.round(container.scrollTop / reelHeight);
            updateProgress();
            
            if (currentTab === 'news' && currentData[currentIndex]) {{
                const currentDate = currentData[currentIndex].date;
                if (dateSelect.value !== currentDate) {{
                    dateSelect.value = currentDate;
                }}
            }}
            
            const isAtBottom = container.scrollTop + container.clientHeight >= container.scrollHeight - 10;
            if (currentTab === 'news' && isAtBottom && currentIndex >= currentData.length - 1) {{
                loadNextDate();
            }}
        }}, {{ passive: true }});
        
        // 초기화: News 탭의 첫 번째 날짜 데이터만 렌더링
        const firstDate = allNewsFlat.length > 0 ? allNewsFlat[0].date : '';
        currentData = allNewsFlat.filter(item => item.category !== 'AI Model' && item.date === firstDate);
        renderReels(currentData);
        
        if (firstDate) {{
            dateSelect.value = firstDate;
        }}
        
        let touchStartY = 0;
        let isAtLastItem = false;
        
        container.addEventListener('touchstart', (e) => {{
            touchStartY = e.touches[0].clientY;
            const reelHeight = window.innerHeight;
            const currentIdx = Math.round(container.scrollTop / reelHeight);
            isAtLastItem = currentIdx >= currentData.length - 1;
        }}, {{ passive: true }});
        
        container.addEventListener('touchend', (e) => {{
            const touchEndY = e.changedTouches[0].clientY;
            const diff = touchStartY - touchEndY;
            
            // 마지막 아이템에서 위로 스와이프 (diff > 50) 하면 다음 날짜 로드
            if (currentTab === 'news' && isAtLastItem && diff > 50) {{
                const loaded = loadNextDate();
                if (loaded) {{
                    // 새로 로드된 첫 번째 아이템으로 스크롤
                    setTimeout(() => {{
                        const reelHeight = window.innerHeight;
                        container.scrollTop = currentIndex * reelHeight + reelHeight;
                    }}, 100);
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
        
        all_data = load_all_news()
        existing_dates = {d['date']: d for d in all_data.get('dates', [])}
        
        existing_links = set()
        for date_entry in all_data.get('dates', []):
            for news in date_entry.get('news', []):
                if news.get('link'):
                    existing_links.add(news['link'])
        
        today = get_kst_today()
        
        log_message(f"\nFetching news for {today}...")
        
        news_items = fetch_all_news_for_date(today, existing_links, include_yesterday=True)
        log_message(f"  Total collected: {len(news_items)} articles")
        
        if news_items:
            log_message("  Curating news (deduplicate & select top 30)...")
            news_items = curate_news_list(news_items)
            
            for item in news_items:
                item['original_title'] = item.get('title', '')
                item['original_summary'] = item.get('description', '')[:300]
            
            log_message("  Crawling og:image for curated articles...")
            for item in news_items:
                if item.get('link') and not item.get('image'):
                    source = item.get('source', '')
                    
                    if source not in ['Google News']:
                        item['image'] = fetch_article_image(item['link'], None)
                    else:
                        item['image'] = None
            
            log_message("  Batch summarizing curated articles (10 at a time)...")
            news_items = batch_summarize(news_items)
            
            from collections import defaultdict
            news_by_date = defaultdict(list)
            for item in news_items:
                item_date = item.get('date', today)
                news_by_date[item_date].append(item)
            
            for news_date, date_news_items in news_by_date.items():
                existing_date_news = existing_dates.get(news_date, {}).get('news', [])
                # Only filter out AI Models for TODAY (they get re-added by HuggingFace processing)
                # Preserve AI Models on past dates
                if news_date == today:
                    existing_date_news_filtered = [n for n in existing_date_news if n.get('category') != 'AI Model']
                else:
                    existing_date_news_filtered = existing_date_news
                combined_news = date_news_items + existing_date_news_filtered
                
                existing_dates[news_date] = {
                    'date': news_date,
                    'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'news': combined_news
                }
                log_message(f"  Added {len(date_news_items)} articles to {news_date}")
            
            log_message(f"  Completed: {len(news_items)} new articles across {len(news_by_date)} date(s)")
        else:
            log_message("  No new articles found for today")
        
        # ============================================================
        # HuggingFace Trending Models Integration
        # ============================================================
        log_message("\n" + "=" * 50)
        hf_models = process_huggingface_models(existing_links)
        
        if hf_models:
            existing_today_entry = existing_dates.get(today, {'date': today, 'update_time': '', 'news': []})
            existing_news = [n for n in existing_today_entry.get('news', []) if n.get('category') != 'AI Model']
            existing_models = [n for n in existing_today_entry.get('news', []) if n.get('category') == 'AI Model']
            combined_news = existing_news + hf_models + existing_models
            
            existing_dates[today] = {
                'date': today,
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'news': combined_news
            }
            log_message(f"  Added {len(hf_models)} HuggingFace models to today's feed")
        
        sorted_dates = sorted(existing_dates.values(), key=lambda x: x['date'], reverse=True)
        all_data['dates'] = sorted_dates[:10]
        
        save_all_news(all_data)
        log_message(f"\nSaved {len(all_data['dates'])} days of data (10-day rolling window)")
        
        html_content = generate_html([])
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        log_message(f"\nGenerated index.html")
        
        total_articles = sum(len(d['news']) for d in all_data['dates'])
        log_message(f"Total articles: {total_articles}")
        
        log_message("\n" + "=" * 50)
        log_message("Processing Complete!")
        log_message("=" * 50)
        
    except Exception as e:
        log_message(f"Error: {e}")
        import traceback
        traceback.print_exc()
