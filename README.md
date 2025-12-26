# Document Assistant

AI 기반 문서 질의응답 시스템 (RAG)

## 주요 기능

- PDF 문서 업로드 및 임베딩
- Hybrid Search (Vector + BM25)
- Cross-Encoder Reranking
- GPU 자동 감지 및 활성화
- 다중 파일 동시 업로드 (최대 5개)

## 시스템 요구사항

### 필수
- Python 3.11+
- Node.js 18+
- Ollama
- Qdrant

### 권장
- NVIDIA GPU (CUDA 지원)
- 8GB+ RAM
- 8코어 이상 CPU

## 설치 방법

### 1. 저장소 클론

```bash
git clone <repository-url>
cd document-assistant
```

### 2. 환경 설정

**Backend 설정:**

```bash
cd backend
cp .env.example .env
```

`.env` 파일을 열고 본인의 설정으로 수정:

```bash
# Model Configuration
EMBEDDING_MODEL=bge-m3          # 또는 nomic-embed-text
LLM_MODEL=llama3.2:3b          # 또는 llama3.2:1b (더 빠름)
RERANK_MODEL=auto

# Qdrant (필수 변경!)
QDRANT_API_KEY=your-api-key-here    # 본인의 Qdrant API 키
QDRANT_HOST=localhost
QDRANT_PORT=6333

# OpenAI (선택사항)
OPENAI_API_KEY=your-openai-key-here

# LangSmith (선택사항)
LANGCHAIN_API_KEY=your-langsmith-key-here
LANGCHAIN_TRACING_V2=false
```

### 3. Ollama 모델 다운로드

```bash
ollama pull bge-m3
ollama pull llama3.2:3b
```

### 4. Qdrant 실행

**Docker 사용:**
```bash
docker run -p 6333:6333 -p 6334:6334 \
  -e QDRANT__SERVICE__API_KEY=your-api-key-here \
  -v $(pwd)/qdrant_storage:/qdrant/storage:z \
  qdrant/qdrant
```

### 5. Backend 실행

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

### 6. Frontend 실행

```bash
cd frontend
npm install
npm start
```

## GPU 설정 (선택사항, 성능 향상)

### NVIDIA 드라이버 업데이트

1. https://www.nvidia.com/Download/index.aspx
2. GPU 선택 후 최신 드라이버 다운로드
3. 설치 후 재부팅

### GPU 확인

```bash
nvidia-smi
```

### Ollama GPU 병렬 처리 활성화

**Windows:**
```powershell
[Environment]::SetEnvironmentVariable('OLLAMA_NUM_PARALLEL', '5', 'User')
```

**Linux/Mac:**
```bash
export OLLAMA_NUM_PARALLEL=5
```

Ollama 재시작 필요.

## 성능 최적화

### CPU 사용자

- `LLM_MODEL=llama3.2:1b` 로 변경
- 파일당 업로드 시간: 2-3분

### GPU 사용자

- NVIDIA 드라이버 최신 버전 설치
- `OLLAMA_NUM_PARALLEL=5` 설정
- 파일당 업로드 시간: 10-30초

### 시스템 사양별 권장 설정

| CPU 코어 | OLLAMA_NUM_PARALLEL | 예상 성능 (5개 파일) |
|---------|-------------------|-------------------|
| 4코어 이하 | 2 | ~40초 |
| 6-8코어 | 3 | ~20초 |
| 8코어 이상 | 5 | ~10초 |

## 모델 변경

`.env` 파일에서 모델 변경 후 백엔드 재시작:

```bash
# 빠른 응답 (품질 약간 감소)
LLM_MODEL=llama3.2:1b

# 높은 품질 (응답 느림)
LLM_MODEL=llama3.2:3b

# 가벼운 임베딩 (빠름)
EMBEDDING_MODEL=nomic-embed-text

# 높은 품질 임베딩 (느림)
EMBEDDING_MODEL=bge-m3
```

## 문제 해결

### "CUDA not available"
- NVIDIA 드라이버 업데이트
- PyTorch CUDA 버전 확인

### "Qdrant connection failed"
- Qdrant 서버 실행 확인
- `.env`의 `QDRANT_API_KEY` 확인

### "Ollama connection failed"
- Ollama 서비스 실행 확인: `ollama serve`
- 모델 다운로드 확인: `ollama list`

## 라이선스

MIT License
