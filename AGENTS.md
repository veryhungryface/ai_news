# AI News Shorts 프로젝트 가이드 (AGENTS.md)

이 파일은 이 저장소에서 작업하는 AI 에이전트들을 위한 가이드라인입니다. 프로젝트의 일관성을 유지하고 효율적으로 작업하기 위해 다음 지침을 준수해 주세요.

---

## 1. 프로젝트 개요
이 프로젝트는 여러 RSS 소스로부터 AI 및 에듀테크 관련 뉴스를 수집하고, LLM(GLM-4.7)을 사용하여 큐레이션 및 요약한 뒤, 사용자에게 친화적인 Reels 스타일의 HTML 페이지를 생성하는 자동화 도구입니다.

---

## 2. 개발 환경 및 실행 명령

### 필수 의존성
- Python 3.8+
- 필요한 패키지: `requests`, `python-dotenv`

### 환경 설정
- 프로젝트 루트의 `.env` 파일에 다음 설정이 필요합니다:
  ```env
  GLM_API_KEY=your_api_key_here
  ```

### 실행 명령
- **뉴스 업데이트 실행**:
  ```bash
  python3 /root/first/update_news.py
  ```
- **의존성 설치**:
  ```bash
  pip install requests python-dotenv
  ```

### 테스트 및 린트
- 현재 별도의 테스트 프레임워크(pytest 등)나 린터(ruff, flake8 등)는 설정되어 있지 않습니다.
- 코드 수정 후에는 반드시 `update_news.py`를 직접 실행하여 `all_news.json`과 `ai_news.html`이 정상적으로 생성되는지 확인해야 합니다.

---

## 3. 코드 스타일 가이드라인

### 명명 규칙 (Naming Conventions)
- **함수 및 변수**: `snake_case`를 사용합니다. (예: `fetch_rss_news`, `news_items`)
- **상수**: `SCREAMING_SNAKE_CASE`를 사용합니다. (예: `RSS_SOURCES`, `DEFAULT_IMAGES`)
- **클래스**: (필요시) `PascalCase`를 사용합니다.

### 코드 구조 및 포맷팅
- **Imports**: 
  1. 표준 라이브러리 (os, re, json 등)
  2. 제3자 라이브러리 (requests, dotenv 등)
  3. 로컬 모듈 (현재는 없음)
  각 그룹 사이에는 빈 줄을 하나 추가합니다.
- **인덴트**: 공백 4칸(4 spaces)을 사용합니다.
- **최대 줄 길이**: 약 88~100자를 권장합니다.
- **Docstrings**: 모든 함수 상단에 해당 함수의 역할과 매개변수를 설명하는 Docstring을 작성합니다.

### 에러 처리 (Error Handling)
- 네트워크 호출(RSS 페칭, API 호출)이나 파일 입출력 시에는 반드시 `try-except` 블록을 사용합니다.
- 예외 발생 시 `log_message` 함수를 호출하여 로그를 남겨야 합니다.
- 무분별한 `pass` 사용은 지양하고, 최소한 로그를 남기도록 합니다.

### 로깅 (Logging)
- 표준 `print` 대신 프로젝트 내에 정의된 `log_message(message)` 함수를 사용합니다.
- 이 함수는 한국 시간(KST, UTC+9) 기준으로 타임스탬프를 자동 부착합니다.

---

## 4. 데이터 및 파일 구조

- **update_news.py**: 메인 로직 (수집, 요약, HTML 생성).
- **all_news.json**: 최근 10일간의 뉴스 데이터를 저장하는 JSON 파일.
- **ai_news.html**: 최종 출력물인 Reels 스타일의 웹 페이지.
- **news_data/**: (현재 비어 있음) 향후 확장성을 위한 데이터 디렉토리.
- **.env**: API 키 등 민감한 정보를 저장.

---

## 5. 주요 데이터 포맷

### all_news.json 구조
```json
{
  "dates": [
    {
      "date": "YYYY-MM-DD",
      "update_time": "YYYY-MM-DD HH:MM:SS",
      "news": [
        {
          "title": "기사 제목",
          "link": "URL",
          "source": "출처",
          "summary": "불렛 포인트 요약 내용",
          "category_keyword": "키워드",
          "image": "이미지 URL",
          "is_english": true/false
        }
      ]
    }
  ]
}
```

---

## 6. 주요 함수 설명

- **fetch_all_news_for_date(target_date)**: 모든 RSS 소스에서 특정 날짜의 뉴스를 수집합니다.
- **curate_news_list(articles)**: LLM을 사용하여 중복을 제거하고 상위 30개의 중요 기사를 선정합니다.
- **sort_by_source_priority(articles)**: 출처 우선순위에 따라 기사를 정렬합니다. (AI타임스 → 에듀테크 검색 → ITWorld → 나머지)
- **batch_summarize(articles)**: 10개 단위로 뉴스를 묶어 LLM에 요약을 요청합니다.
- **generate_html(news_items)**: `all_news.json`의 데이터를 기반으로 최종 HTML 페이지를 생성합니다.

---

## 7. 작업 시 주의사항 (Important Notes)

1. **파일 경로**: 스크립트 내에서 파일 경로를 참조할 때는 `/root/first/`로 시작하는 **절대 경로**를 사용하세요. 에이전트 작업 시 상대 경로는 오류를 유발할 수 있습니다.
2. **LLM 호출 비용**: `batch_summarize` 함수는 뉴스를 10개씩 묶어서 처리하여 API 호출 횟수를 최적화합니다. 이 구조를 유지하여 토큰 비용과 속도를 관리하세요.
3. **10일 윈도우**: `maintain_10_day_window` 함수는 `all_news.json`의 크기를 유지하기 위해 최근 10일치 데이터만 남깁니다. 데이터 수정 시 기존 데이터가 유실되지 않도록 주의하세요.
4. **HTML 템플릿**: `generate_html` 함수 내에는 복잡한 CSS와 JavaScript가 포함되어 있습니다. 특히 Reels 스타일의 수직 스크롤과 스냅 기능(`scroll-snap-type`)이 깨지지 않도록 DOM 구조 수정 시 주의가 필요합니다.
5. **시간대**: RSS 소스마다 날짜 형식이 다르며, 이를 KST(UTC+9)로 변환하는 로직이 `parse_rss_date`에 포함되어 있습니다. 시간 관련 로직 수정 시 한국 시간을 기준으로 일관성을 유지하세요.
6. **API 엔드포인트**: 현재 GLM API는 `https://api.z.ai/api/coding/paas/v4/chat/completions`를 사용하고 있습니다. 엔드포인트나 모델(`glm-4.7`) 변경 시 환경 변수가 아닌 코드 내 상수를 확인하세요.
7. **이미지 크롤링**: `fetch_article_image`는 Open Graph 태그를 분석합니다. 네트워크 타임아웃(현재 10초)과 User-Agent 설정을 적절히 유지하여 차단을 방지하세요.
8. **의존성 관리**: 새로운 패키지가 필요할 경우 에이전트는 먼저 가이드라인에 명시하고 설치 명령을 실행해야 합니다.

---

## 8. 추가 규칙 (External Rules)
- 현재 `.cursorrules`나 `.github/copilot-instructions.md`와 같은 외부 규칙 파일은 존재하지 않습니다.
- 향후 규칙이 추가될 경우 이 섹션에 해당 내용을 통합해 주세요.
- **Git 커밋 메시지**: 변경 사항을 명확히 설명하는 메시지를 작성하세요.
- **보안**: API 키가 코드나 로그에 직접 노출되지 않도록 항상 `.env` 파일과 환경 변수를 사용하세요.

---

이 가이드는 프로젝트의 성격에 맞춰 지속적으로 업데이트되어야 합니다. 새로운 기능이나 라이브러리가 추가될 경우 에이전트는 이 파일을 먼저 수정하여 다른 에이전트들이 참고할 수 있도록 하세요.

