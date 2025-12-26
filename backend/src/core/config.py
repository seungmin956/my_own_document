import os
from dotenv import load_dotenv
from pathlib import Path

# .env 파일 로드 (절대 경로로 명확히 지정)
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)
print(f"[DEBUG] .env path: {env_path}")
print(f"[DEBUG] BM25_VECTOR_WEIGHT: {os.getenv('BM25_VECTOR_WEIGHT', 'NOT FOUND')}")

# LangSmith 설정
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "document-assistant-rag")

# OpenAI 설정
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Qdrant 설정
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
if not QDRANT_API_KEY:
    raise ValueError("QDRANT_API_KEY must be set in .env file")
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

# Model Configuration
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "bge-m3")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2:3b")
RERANK_MODEL = os.getenv("RERANK_MODEL", "auto")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))

# BM25 Hybrid Search 설정
BM25_ENABLED = os.getenv("BM25_ENABLED", "true").lower() == "true"
BM25_VECTOR_WEIGHT = float(os.getenv("BM25_VECTOR_WEIGHT", "0.7"))
BM25_BM25_WEIGHT = float(os.getenv("BM25_BM25_WEIGHT", "0.3"))

print(f"[OK] Config loaded:")
print(f"   LangSmith: {'Enabled' if LANGCHAIN_TRACING_V2 else 'Disabled'}")
print(f"   Project: {LANGCHAIN_PROJECT}")
print(f"   Models: LLM={LLM_MODEL}, Embedding={EMBEDDING_MODEL}, Rerank={RERANK_MODEL}")
print(f"   BM25: {'Enabled' if BM25_ENABLED else 'Disabled'}")
