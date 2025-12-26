# 📂 Backend 새로운 모듈 구조

## ✅ 리팩토링 완료

평면적 구조에서 계층적 모듈 구조로 성공적으로 리팩토링되었습니다.

## 🎯 주요 변경사항

### Before (기존 구조)
```
backend/
├── api.py
├── chatbot.py
├── config.py
├── exceptions.py
├── user_config.py
├── document_processor.py
├── pdf_loader.py
├── toc_extractor.py
├── document_cache.py
├── bm25_retriever.py
├── embedding_generator.py
├── optimized_reranker.py
├── qdrant_manager.py
├── tokenizer.py
├── generate_dataset.py
├── deduplicate_dataset.py
└── ... (21개 Python 파일)
```

### After (새로운 구조)
```
backend/
├── src/
│   ├── api/
│   │   ├── main.py                    ✅ FastAPI 앱
│   │   └── routes/                    📁 라우트 (확장 가능)
│   │
│   ├── core/
│   │   ├── chatbot.py                 ✅ RAG 챗봇
│   │   ├── config.py                  ✅ 환경 설정
│   │   ├── exceptions.py              ✅ 예외 정의
│   │   └── user_config.py             ✅ 사용자 설정
│   │
│   ├── services/
│   │   ├── document/
│   │   │   ├── processor.py           ✅ 문서 처리
│   │   │   ├── loader.py              ✅ PDF 로더
│   │   │   ├── toc_extractor.py       ✅ 목차 추출
│   │   │   └── cache.py               ✅ 캐시
│   │   │
│   │   ├── retrieval/
│   │   │   ├── bm25_retriever.py      ✅ BM25 검색
│   │   │   ├── embedding_generator.py ✅ 임베딩
│   │   │   └── reranker.py            ✅ 리랭킹
│   │   │
│   │   └── storage/
│   │       └── qdrant_manager.py      ✅ Qdrant
│   │
│   ├── utils/
│   │   └── tokenizer.py               ✅ 토크나이저
│   │
│   └── scripts/
│       ├── generate_dataset.py        ✅ 데이터셋 생성
│       └── deduplicate_dataset.py     ✅ 중복 제거
│
├── tests/                              📁 테스트
│   ├── unit/                          ✅ 단위 테스트
│   ├── integration/                   ✅ 통합 테스트
│   └── fixtures/                      ✅ 픽스처
│
├── main.py                            ✅ CLI 진입점
└── REFACTORING_GUIDE.md              📖 마이그레이션 가이드
```

## 📋 파일 매핑

| 기존 파일 | 새 위치 | 상태 |
|----------|---------|------|
| `api.py` | `src/api/main.py` | ✅ 이동 및 import 수정 |
| `chatbot.py` | `src/core/chatbot.py` | ✅ 이동 및 import 수정 |
| `config.py` | `src/core/config.py` | ✅ 이동 |
| `exceptions.py` | `src/core/exceptions.py` | ✅ 이동 |
| `user_config.py` | `src/core/user_config.py` | ✅ 이동 |
| `document_processor.py` | `src/services/document/processor.py` | ✅ 이동 및 import 수정 |
| `pdf_loader.py` | `src/services/document/loader.py` | ✅ 이동 |
| `toc_extractor.py` | `src/services/document/toc_extractor.py` | ✅ 이동 |
| `document_cache.py` | `src/services/document/cache.py` | ✅ 이동 및 import 수정 |
| `bm25_retriever.py` | `src/services/retrieval/bm25_retriever.py` | ✅ 이동 및 import 수정 |
| `embedding_generator.py` | `src/services/retrieval/embedding_generator.py` | ✅ 이동 |
| `optimized_reranker.py` | `src/services/retrieval/reranker.py` | ✅ 이동 |
| `qdrant_manager.py` | `src/services/storage/qdrant_manager.py` | ✅ 이동 |
| `tokenizer.py` | `src/utils/tokenizer.py` | ✅ 이동 |
| `generate_dataset.py` | `src/scripts/generate_dataset.py` | ✅ 이동 및 import 수정 |
| `deduplicate_dataset.py` | `src/scripts/deduplicate_dataset.py` | ✅ 이동 |
| `test/*` | `tests/unit/*` | ✅ 이동 |

## 🚦 다음 단계

### 1. 테스트 실행
```bash
cd backend

# PYTHONPATH 설정
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 챗봇 테스트
python -c "from src.core.chatbot import DocumentChatbot; print('✅ Import OK')"

# API 서버 테스트
python -m src.api.main
```

### 2. 기존 파일 정리 (선택사항)
```bash
# 기존 파일들이 더 이상 필요없다면 삭제
# ⚠️ 주의: 백업 후 진행하세요!

# 기존 파일 목록 확인
ls -la *.py

# 백업
mkdir -p ../backup_old_structure
cp *.py ../backup_old_structure/

# 삭제 (선택)
# rm api.py chatbot.py config.py ...
```

### 3. Git 커밋
```bash
git add .
git commit -m "refactor: 모듈 구조 개선

- 평면 구조 → 계층 구조로 리팩토링
- src/ 폴더 아래 api, core, services, utils, scripts 분리
- 모든 import 경로를 새 구조에 맞게 수정
- tests/ 폴더 재구성 (unit, integration, fixtures)
"
```

## 📖 사용 예시

### API 서버 실행
```bash
# 방법 1: 모듈로 실행
python -m src.api.main

# 방법 2: uvicorn으로 실행
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 챗봇 사용
```python
from src.core.chatbot import DocumentChatbot

chatbot = DocumentChatbot()
result = chatbot.ask("질문 내용")
```

### 문서 처리
```python
from src.services.document.processor import DocumentProcessor

processor = DocumentProcessor()
chunks = processor.process("document.pdf")
```

## 🎨 아키텍처 개선 효과

### 1. 명확한 계층 분리
- **API Layer** (`src/api`): 외부 인터페이스
- **Core Layer** (`src/core`): 비즈니스 로직
- **Service Layer** (`src/services`): 재사용 가능한 서비스
- **Utils Layer** (`src/utils`): 공통 유틸리티

### 2. 의존성 방향
```
API Layer
   ↓
Core Layer
   ↓
Service Layer
   ↓
Utils Layer
```

### 3. 모듈 독립성
- 각 서비스는 독립적으로 테스트 가능
- Mock 객체 주입이 용이
- 향후 마이크로서비스 분리 가능

## 🔍 Import 검증

모든 파일의 import가 새 구조로 올바르게 변경되었는지 확인:

```bash
# src 폴더 내 모든 Python 파일에서 잘못된 import 검색
cd backend
grep -r "from backend\." src/
grep -r "from \.\." src/

# 결과가 없으면 ✅ 성공
```

## 💡 팁

### VS Code 설정
`.vscode/settings.json`:
```json
{
    "python.analysis.extraPaths": ["./backend"],
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests"]
}
```

### PyCharm 설정
1. File → Settings → Project Structure
2. `backend` 폴더를 **Sources Root**로 표시
3. `tests` 폴더를 **Test Sources Root**로 표시

## 📚 참고 문서

- [REFACTORING_GUIDE.md](./REFACTORING_GUIDE.md) - 상세한 마이그레이션 가이드
- [pyproject.toml](./pyproject.toml) - 프로젝트 설정
- [main.py](./main.py) - CLI 진입점

---

✅ **리팩토링 완료!** 이제 깔끔한 모듈 구조로 개발을 계속할 수 있습니다.
