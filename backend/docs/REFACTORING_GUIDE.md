# 모듈 리팩토링 가이드

## 📋 개요

백엔드 코드를 평면적 구조에서 계층적 모듈 구조로 리팩토링했습니다.

## 🗂️ 새로운 디렉토리 구조

```
backend/
├── src/                          # 모든 소스 코드
│   ├── __init__.py
│   │
│   ├── api/                      # API 레이어
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI 앱
│   │   └── routes/              # API 라우트 (향후 확장)
│   │       └── __init__.py
│   │
│   ├── core/                     # 핵심 비즈니스 로직
│   │   ├── __init__.py
│   │   ├── chatbot.py           # RAG 챗봇
│   │   ├── config.py            # 환경 설정
│   │   ├── exceptions.py        # 커스텀 예외
│   │   └── user_config.py       # 사용자 설정
│   │
│   ├── services/                 # 서비스 레이어
│   │   ├── __init__.py
│   │   │
│   │   ├── document/            # 문서 처리 서비스
│   │   │   ├── __init__.py
│   │   │   ├── processor.py    # 문서 처리기
│   │   │   ├── loader.py       # PDF 로더
│   │   │   ├── toc_extractor.py # 목차 추출기
│   │   │   └── cache.py        # 문서 캐시
│   │   │
│   │   ├── retrieval/           # 검색 서비스
│   │   │   ├── __init__.py
│   │   │   ├── bm25_retriever.py    # BM25 검색
│   │   │   ├── embedding_generator.py # 임베딩 생성
│   │   │   └── reranker.py          # 리랭커
│   │   │
│   │   └── storage/             # 저장소 서비스
│   │       ├── __init__.py
│   │       └── qdrant_manager.py # Qdrant 관리
│   │
│   ├── utils/                    # 유틸리티
│   │   ├── __init__.py
│   │   └── tokenizer.py
│   │
│   └── scripts/                  # 스크립트
│       ├── __init__.py
│       ├── generate_dataset.py
│       └── deduplicate_dataset.py
│
├── tests/                        # 테스트
│   ├── __init__.py
│   ├── unit/                    # 단위 테스트
│   │   └── __init__.py
│   ├── integration/             # 통합 테스트
│   │   └── __init__.py
│   └── fixtures/                # 테스트 픽스처
│       └── __init__.py
│
├── main.py                      # CLI 진입점
├── .env                         # 환경 변수
├── pyproject.toml              # 프로젝트 설정
└── README.md
```

## 🔄 Import 경로 변경

### 기존 → 새 경로

| 기존 경로 | 새 경로 | 설명 |
|----------|---------|------|
| `from config import *` | `from src.core.config import *` | 설정 모듈 |
| `from exceptions import *` | `from src.core.exceptions import *` | 예외 모듈 |
| `from chatbot import DocumentChatbot` | `from src.core.chatbot import DocumentChatbot` | 챗봇 |
| `from document_processor import *` | `from src.services.document.processor import *` | 문서 처리 |
| `from pdf_loader import *` | `from src.services.document.loader import *` | PDF 로더 |
| `from toc_extractor import *` | `from src.services.document.toc_extractor import *` | 목차 추출 |
| `from document_cache import *` | `from src.services.document.cache import *` | 캐시 |
| `from bm25_retriever import *` | `from src.services.retrieval.bm25_retriever import *` | BM25 |
| `from embedding_generator import *` | `from src.services.retrieval.embedding_generator import *` | 임베딩 |
| `from optimized_reranker import *` | `from src.services.retrieval.reranker import *` | 리랭커 |
| `from qdrant_manager import *` | `from src.services.storage.qdrant_manager import *` | Qdrant |
| `from tokenizer import *` | `from src.utils.tokenizer import *` | 토크나이저 |

## 🚀 사용 방법

### 1. 챗봇 사용

```python
from src.core.chatbot import DocumentChatbot

# 챗봇 생성
chatbot = DocumentChatbot()

# 질문하기
result = chatbot.ask("질문 내용")
print(result['answer'])
```

### 2. API 서버 실행

```bash
# 옵션 1: API 모듈에서 직접 실행
cd backend
python -m src.api.main

# 옵션 2: uvicorn으로 실행
uvicorn src.api.main:app --reload
```

### 3. 문서 처리 파이프라인

```python
from main import DocumentPipeline

# 파이프라인 생성
pipeline = DocumentPipeline()

# PDF 처리
result = pipeline.process("./data/document.pdf")
```

### 4. 개별 서비스 사용

```python
# 문서 처리
from src.services.document.processor import DocumentProcessor
processor = DocumentProcessor()

# PDF 로딩
from src.services.document.loader import PDFLoader
loader = PDFLoader()

# 임베딩 생성
from src.services.retrieval.embedding_generator import EmbeddingGenerator
generator = EmbeddingGenerator(model="bge-m3")

# Qdrant 관리
from src.services.storage.qdrant_manager import QdrantManager
qdrant = QdrantManager()
```

## 📦 Python Path 설정

프로젝트 루트에서 실행 시 Python이 `src` 모듈을 찾을 수 있도록 설정이 필요합니다.

### 방법 1: PYTHONPATH 설정 (권장)

```bash
# Linux/Mac
export PYTHONPATH="${PYTHONPATH}:$(pwd)/backend"

# Windows (PowerShell)
$env:PYTHONPATH += ";$(pwd)\backend"

# Windows (CMD)
set PYTHONPATH=%PYTHONPATH%;%CD%\backend
```

### 방법 2: setup.py 또는 pyproject.toml 사용

`pyproject.toml`에 이미 설정되어 있습니다:

```toml
[tool.poetry]
packages = [{include = "src", from = "backend"}]
```

### 방법 3: IDE 설정

**VS Code**: `.vscode/settings.json`
```json
{
    "python.analysis.extraPaths": ["./backend"]
}
```

**PyCharm**:
- File → Settings → Project Structure
- `backend` 폴더를 Sources Root로 표시

## 🧪 테스트 실행

```bash
# 모든 테스트 실행
pytest backend/tests/

# 단위 테스트만
pytest backend/tests/unit/

# 통합 테스트만
pytest backend/tests/integration/

# 특정 파일 테스트
pytest backend/tests/unit/test_qdrant_manager.py
```

## 🔧 마이그레이션 체크리스트

기존 코드를 새 구조로 마이그레이션할 때:

- [ ] Import 문 모두 `src.*` 경로로 변경
- [ ] 상대 경로 import 제거 (절대 경로 사용)
- [ ] PYTHONPATH 설정 확인
- [ ] 테스트 실행하여 import 오류 확인
- [ ] API 서버 정상 동작 확인
- [ ] 챗봇 정상 동작 확인

## 💡 주요 이점

### 1. 명확한 책임 분리
- **API 레이어**: 외부 요청 처리
- **Core**: 핵심 비즈니스 로직
- **Services**: 재사용 가능한 서비스
- **Utils**: 공통 유틸리티

### 2. 유지보수성 향상
- 관련 코드가 그룹화되어 찾기 쉬움
- 의존성이 명확해짐
- 모듈 간 결합도 감소

### 3. 테스트 용이성
- 단위 테스트와 통합 테스트 분리
- Mock 객체 사용이 쉬워짐
- 테스트 픽스처 재사용 가능

### 4. 확장성
- 새로운 기능 추가 위치가 명확
- 마이크로서비스로 분리 시 용이
- 팀 협업 시 충돌 감소

## 🐛 트러블슈팅

### ImportError: No module named 'src'

**원인**: Python이 `src` 모듈을 찾을 수 없음

**해결**:
```bash
# backend 폴더에서 실행
cd backend
python -m src.api.main

# 또는 PYTHONPATH 설정
export PYTHONPATH="${PYTHONPATH}:$(pwd)/backend"
```

### ModuleNotFoundError: No module named 'src.core'

**원인**: `__init__.py` 파일이 없거나 경로가 잘못됨

**해결**:
1. 모든 폴더에 `__init__.py` 있는지 확인
2. import 경로가 `src.`로 시작하는지 확인

### 상대 경로 import 오류

**원인**: 기존 상대 경로 import 사용

**해결**: 절대 경로로 변경
```python
# 잘못된 예
from ..core import config

# 올바른 예
from src.core import config
```

## 📚 추가 참고 자료

- [Python Packaging Guide](https://packaging.python.org/)
- [FastAPI Project Structure](https://fastapi.tiangolo.com/tutorial/)
- [pytest Documentation](https://docs.pytest.org/)
