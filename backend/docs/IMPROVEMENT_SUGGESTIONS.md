# 🚀 Backend 구조 개선 제안

## ✅ 즉시 적용 완료

### 1. .gitignore 보완
- Python 캐시 파일 (`__pycache__/`, `*.pyc`) 추가
- 가상환경 (`.venv/`) 추가
- IDE 설정 파일 추가
- 백업 폴더 (`_old_structure_backup/`) 추가
- 캐시/데이터 폴더 추가

---

## 🎯 권장 개선사항

### 2. 폴더 구조 정리

#### A. 중복 test 폴더 제거 ⚠️
현재 상태:
```
backend/
├── test/          # 기존 폴더 (비어있음)
└── tests/         # 새 폴더 (사용 중)
```

**제안:**
```bash
# test/ 폴더 삭제
rm -rf backend/test/
```

#### B. evaluation 폴더 재배치
현재: `backend/evaluation/`
제안: `backend/tests/evaluation/` 또는 별도 `benchmarks/` 폴더

```
backend/
├── src/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── fixtures/
│   └── evaluation/          # 이동
│       ├── evaluate_rag.py
│       ├── test_dataset.json
│       └── results/          # 결과 파일 분리
```

#### C. 데이터 폴더 구조화
현재:
```
backend/
├── data/     # 샘플 PDF
└── cache/    # 처리 캐시
```

제안:
```
backend/
└── data/
    ├── samples/           # 샘플 PDF
    ├── uploads/          # 사용자 업로드
    ├── cache/            # 처리 캐시
    └── .gitkeep         # Git 추적용
```

---

### 3. 설정 파일 개선

#### A. pytest.ini 추가
테스트 설정을 명확히 정의:

```ini
# backend/pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --tb=short
    --strict-markers
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow running tests
```

#### B. pyproject.toml 개선
현재 프로젝트명이 generic합니다:

```toml
[tool.poetry]
name = "document-assistant-backend"  # 더 명확하게
version = "0.1.0"
description = "RAG-based Document QA System Backend"
authors = ["seungmin956 <seungminlee956@gmail.com>"]
readme = "README.md"
packages = [{include = "src"}]  # ⭐ src 패키지 명시

[tool.poetry.scripts]
# CLI 명령어 추가
doc-assistant = "main:main"
api-server = "src.api.main:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"

[tool.black]
line-length = 88
target-version = ['py311']
include = '\.pyi?$'

[tool.isort]
profile = "black"
```

---

### 4. 코드 품질 도구 추가

#### A. pre-commit 설정
`.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort
```

#### B. Makefile 추가
개발 작업 자동화:

```makefile
# backend/Makefile

.PHONY: install test lint format clean

install:
	poetry install

test:
	pytest tests/ -v

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

lint:
	black --check src/ tests/
	isort --check src/ tests/
	flake8 src/ tests/

format:
	black src/ tests/
	isort src/ tests/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage

run-api:
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

run-chatbot:
	python -m src.core.chatbot chat
```

---

### 5. 환경 관리 개선

#### A. .env.example 추가
`.env` 템플릿 제공:

```bash
# backend/.env.example
# LangSmith
LANGCHAIN_API_KEY=your_api_key_here
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=document-assistant-rag

# OpenAI (선택)
OPENAI_API_KEY=your_openai_key_here

# Qdrant
QDRANT_API_KEY=my-secure-portfolio-key-2025
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Application
APP_ENV=development
DEBUG=false

# BM25 Hybrid Search
BM25_ENABLED=true
BM25_VECTOR_WEIGHT=0.7
BM25_BM25_WEIGHT=0.3
```

#### B. config 분리
개발/프로덕션 설정 분리:

```
backend/src/core/
├── config/
│   ├── __init__.py
│   ├── base.py          # 기본 설정
│   ├── development.py   # 개발 설정
│   └── production.py    # 프로덕션 설정
```

---

### 6. 문서화 개선

#### A. API 문서 자동화
FastAPI Swagger 커스터마이징:

```python
# src/api/main.py
app = FastAPI(
    title="Document Assistant API",
    description="""
    RAG 기반 문서 QA 시스템 API

    ## Features
    - PDF 문서 업로드 및 처리
    - 의미 기반 문서 검색
    - LLM 기반 질의응답

    ## Architecture
    - Vector Search (BGE-M3)
    - BM25 Hybrid Search
    - Cross-Encoder Reranking
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "Document Assistant Team",
        "email": "seungminlee956@gmail.com",
    },
)
```

#### B. README 계층화
```
backend/
├── README.md                    # 전체 개요
├── docs/
│   ├── ARCHITECTURE.md         # 아키텍처 설명
│   ├── API.md                  # API 문서
│   ├── DEPLOYMENT.md           # 배포 가이드
│   └── DEVELOPMENT.md          # 개발 가이드
├── REFACTORING_GUIDE.md
└── README_NEW_STRUCTURE.md
```

---

### 7. 성능 및 모니터링

#### A. 로깅 구조화
```python
# src/core/logger.py
import logging
from pathlib import Path

def setup_logger(name: str, log_file: str = None):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    )
    logger.addHandler(console_handler)

    # 파일 핸들러 (선택)
    if log_file:
        log_path = Path("logs") / log_file
        log_path.parent.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        )
        logger.addHandler(file_handler)

    return logger
```

#### B. 메트릭 수집
```python
# src/core/metrics.py
from typing import Dict
import time

class MetricsCollector:
    """성능 메트릭 수집"""

    def __init__(self):
        self.metrics: Dict = {}

    def track_latency(self, operation: str):
        """지연시간 추적 데코레이터"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                start = time.time()
                result = func(*args, **kwargs)
                elapsed = time.time() - start

                if operation not in self.metrics:
                    self.metrics[operation] = []
                self.metrics[operation].append(elapsed)

                return result
            return wrapper
        return decorator
```

---

### 8. 보안 강화

#### A. API 키 검증
```python
# src/api/security.py
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != os.getenv("API_SECRET_KEY"):
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return api_key
```

#### B. Rate Limiting
```python
# src/api/middleware.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/ask")
@limiter.limit("10/minute")
async def ask_question(request: Request, ...):
    ...
```

---

### 9. Docker 지원

#### Dockerfile
```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Poetry 설치
RUN pip install poetry

# 의존성 복사 및 설치
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# 소스 코드 복사
COPY . .

# 포트 노출
EXPOSE 8000

# 실행
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### docker-compose.yml
```yaml
# backend/docker-compose.yml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
    depends_on:
      - qdrant
    volumes:
      - ./data:/app/data
      - ./cache:/app/cache

  qdrant:
    image: qdrant/qdrant
    ports:
      - "6333:6333"
    volumes:
      - qdrant_storage:/qdrant/storage

volumes:
  qdrant_storage:
```

---

## 📊 우선순위

### 🔴 High Priority (즉시 적용 권장)
1. ✅ .gitignore 보완 (완료)
2. pytest.ini 추가
3. .env.example 추가
4. 중복 test/ 폴더 삭제
5. Makefile 추가

### 🟡 Medium Priority (단계적 적용)
6. pyproject.toml 개선
7. 데이터 폴더 재구조화
8. 로깅 시스템 추가
9. evaluation 폴더 이동

### 🟢 Low Priority (향후 고려)
10. pre-commit hooks
11. Docker 지원
12. API 키 검증
13. Rate Limiting
14. 문서 계층화

---

## 💡 적용 방법

### 즉시 적용 가능한 명령어
```bash
cd backend

# 1. 중복 폴더 삭제
rm -rf test/

# 2. pytest.ini 생성
cat > pytest.ini << 'EOF'
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -v --tb=short
EOF

# 3. .env.example 생성
cp .env .env.example
# (민감 정보는 수동으로 제거)

# 4. Makefile 생성
# (위 내용 참고)

# 5. 캐시 정리
make clean  # 또는
find . -type d -name "__pycache__" -exec rm -rf {} +
```

---

이 개선사항들을 단계적으로 적용하면 더욱 전문적이고 유지보수하기 쉬운 프로젝트가 됩니다.
