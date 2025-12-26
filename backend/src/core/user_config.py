"""
user_config.py

데스크톱 앱용 사용자별 설정 관리
"""

import json
from pathlib import Path
from typing import Optional


class UserConfig:
    """
    사용자별 설정 관리

    저장 위치:
    - Windows: C:/Users/{user}/.document-assistant/config.json
    - Mac: /Users/{user}/.document-assistant/config.json
    - Linux: /home/{user}/.document-assistant/config.json

    개발 vs 프로덕션:
    - 개발: backend/.env 사용 (config.py)
    - 프로덕션: ~/.document-assistant/ 사용 (user_config.py)
    """

    def __init__(self, config_dir: Optional[Path] = None):
        if config_dir is None:
            self.config_dir = Path.home() / ".document-assistant"
        else:
            self.config_dir = Path(config_dir)

        self.config_file = self.config_dir / "config.json"

        # 디렉토리 생성
        self._init_directories()

        # 설정 로드/생성
        self.settings = self._load_or_create()

    def _init_directories(self):
        """필요한 디렉토리 생성"""
        dirs = [
            self.config_dir,
            self.config_dir / "qdrant_data",
            self.config_dir / "cache",
            self.config_dir / "uploads",
        ]

        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    def _load_or_create(self) -> dict:
        """설정 로드 또는 생성"""
        if self.config_file.exists():
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            settings = self._default_settings()
            self._save(settings)
            return settings

    def _default_settings(self) -> dict:
        """기본 설정"""
        return {
            "qdrant": {
                "host": "localhost",
                "port": 6333,
                "api_key": None,  # 로컬은 키 불필요
            },
            "embedding": {
                "model": "bge-m3",
                "dimension": 1024,
            },
            "llm": {
                "model": "qwen2.5:1.5b",
                "temperature": 0.3,
            },
            "search": {
                "top_k": 5,
                "score_threshold": 0.4,
                # Reranking 설정 추가 ⭐
                "rerank_enabled": True,
                "rerank_model": "multilingual",
                "rerank_max_candidates": 10,  # Vector Search 후보 수
                "rerank_top_k": 3,  # 최종 반환 수
                # BM25 Hybrid Search 설정 ⭐
                "bm25_enabled": True,
                "bm25_vector_weight": 0.7,
                "bm25_weight": 0.3,
            },
        }

    def _save(self, settings: dict):
        """설정 저장"""
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)

    def get(self, key: str, default=None):
        """값 가져오기 (점 표기법)"""
        keys = key.split(".")
        value = self.settings

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    # 기본 속성
    @property
    def qdrant_host(self) -> str:
        return self.get("qdrant.host")

    @property
    def qdrant_port(self) -> int:
        return self.get("qdrant.port")

    @property
    def qdrant_api_key(self) -> Optional[str]:
        return self.get("qdrant.api_key")

    @property
    def embedding_model(self) -> str:
        return self.get("embedding.model")

    @property
    def llm_model(self) -> str:
        return self.get("llm.model")

    @property
    def top_k(self) -> int:
        return self.get("search.top_k")

    @property
    def score_threshold(self) -> float:
        return self.get("search.score_threshold")

    # Reranking 속성 추가 ⭐
    @property
    def rerank_enabled(self) -> bool:
        return self.get("search.rerank_enabled", True)

    @property
    def rerank_model(self) -> str:
        return self.get("search.rerank_model", "auto")

    @property
    def rerank_max_candidates(self) -> int:
        return self.get("search.rerank_max_candidates", 10)

    @property
    def rerank_top_k(self) -> int:
        return self.get("search.rerank_top_k", 5)

    # BM25 속성 추가 ⭐
    @property
    def bm25_enabled(self) -> bool:
        return self.get("search.bm25_enabled", True)

    @property
    def bm25_vector_weight(self) -> float:
        return self.get("search.bm25_vector_weight", 0.7)

    @property
    def bm25_weight(self) -> float:
        return self.get("search.bm25_weight", 0.3)
