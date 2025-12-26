# embedding_generator.py

from typing import List, Optional
from enum import Enum
import os
from pathlib import Path


class EmbeddingMode(Enum):
    """임베딩 모드"""

    LOCAL = "local"  # Ollama (bge-m3, nomic-embed-text 등)
    OPENAI = "openai"  # OpenAI API


class EmbeddingGenerator:
    """
    텍스트 임베딩 생성기

    지원 모드:
    - LOCAL: Ollama 로컬 모델 (bge-m3, nomic-embed-text)
    - OPENAI: OpenAI API (text-embedding-3-small)

    사용 예시:
    >>> generator = EmbeddingGenerator(mode="local", model="bge-m3")
    >>> embeddings = generator.embed_documents(["텍스트1", "텍스트2"])
    >>> len(embeddings[0])  # 차원 확인
    1024
    """

    # 지원하는 로컬 모델들
    SUPPORTED_LOCAL_MODELS = {
        "bge-m3": {
            "dimension": 1024,
            "max_tokens": 8192,
            "description": "다국어 최강, 한글 우수, 하이브리드 검색",
        },
        "nomic-embed-text": {
            "dimension": 768,
            "max_tokens": 8192,
            "description": "빠르고 가벼움, 범용",
        },
        "mxbai-embed-large": {
            "dimension": 1024,
            "max_tokens": 512,
            "description": "영어 특화, 짧은 컨텍스트",
        },
    }

    def __init__(
        self,
        mode: str = None,
        model: str = None,
        batch_size: int = 32,
        verbose: bool = True,
    ):
        """
        Args:
            mode: 'local' 또는 'openai' (None이면 환경변수 EMBEDDING_MODE 사용)
            model: 모델 이름 (LOCAL: bge-m3/nomic-embed-text, OPENAI: text-embedding-3-small)
            batch_size: 배치 처리 크기 (GPU 메모리 작으면 줄이기)
            verbose: 진행 상황 출력 여부
        """
        # 모드 결정 (환경변수 → 파라미터 → 기본값)
        self.mode = mode or os.getenv("EMBEDDING_MODE", "local")
        self.batch_size = batch_size
        self.verbose = verbose

        # 모델 초기화
        if self.mode == "local":
            self.model_name = model or os.getenv("EMBEDDING_MODEL", "bge-m3")
            self._init_local_embeddings()
        elif self.mode == "openai":
            self.model_name = model or "text-embedding-3-small"
            self._init_openai_embeddings()
        else:
            raise ValueError(f"지원하지 않는 모드: {self.mode}")

        if self.verbose:
            print(f"✓ 임베딩 생성기 초기화: {self.mode} 모드, 모델={self.model_name}")

    def _init_local_embeddings(self):
        """Ollama 로컬 임베딩 초기화"""
        from langchain_ollama import OllamaEmbeddings

        if self.model_name not in self.SUPPORTED_LOCAL_MODELS:
            print(f"⚠️  '{self.model_name}'는 테스트되지 않은 모델입니다.")

        # GPU 자동 감지
        num_gpu = self._detect_gpu()

        ollama_kwargs = {"model": self.model_name}
        if num_gpu > 0:
            ollama_kwargs["num_gpu"] = num_gpu
            if self.verbose:
                print(f"  ✓ GPU 감지됨: {num_gpu}개 GPU 사용")
        else:
            if self.verbose:
                print(f"  ⚠️  GPU 미감지: CPU 모드로 작동 (느릴 수 있음)")

        self.embeddings = OllamaEmbeddings(**ollama_kwargs)

        # 모델 정보
        model_info = self.SUPPORTED_LOCAL_MODELS.get(self.model_name, {})
        self.dimension = model_info.get("dimension", "unknown")
        self.max_tokens = model_info.get("max_tokens", "unknown")

        if self.verbose and model_info:
            print(f"  - 차원: {self.dimension}")
            print(f"  - 최대 토큰: {self.max_tokens}")

    def _detect_gpu(self) -> int:
        """
        GPU 자동 감지
        Returns:
            int: 사용 가능한 GPU 개수 (0이면 CPU만 사용)
        """
        try:
            import torch
            if torch.cuda.is_available():
                num_gpus = torch.cuda.device_count()
                return num_gpus
        except ImportError:
            pass

        # torch 없거나 CUDA 없으면 CPU
        return 0

    def _init_openai_embeddings(self):
        """OpenAI 임베딩 초기화"""
        from langchain_openai import OpenAIEmbeddings

        # API 키 확인
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY 환경변수가 설정되지 않았습니다.\n"
                ".env 파일에 OPENAI_API_KEY=sk-... 추가하세요."
            )

        self.embeddings = OpenAIEmbeddings(
            model=self.model_name, openai_api_key=api_key
        )

        # 모델별 차원
        dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }
        self.dimension = dimensions.get(self.model_name, 1536)
        self.max_tokens = 8191

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        문서 리스트를 임베딩 벡터로 변환

        Args:
            texts: 임베딩할 텍스트 리스트

        Returns:
            임베딩 벡터 리스트 [[0.1, 0.2, ...], ...]
        """
        if not texts:
            return []

        total = len(texts)
        all_embeddings = []

        if self.verbose:
            print(f"\n🔄 임베딩 생성 중... (총 {total}개)")

        # 배치 처리로 메모리 효율화
        for i in range(0, total, self.batch_size):
            batch = texts[i : i + self.batch_size]

            try:
                batch_embeddings = self.embeddings.embed_documents(batch)
                all_embeddings.extend(batch_embeddings)

                if self.verbose and (i + self.batch_size) % 100 == 0:
                    progress = min(i + self.batch_size, total)
                    print(f"  진행: {progress}/{total} ({progress/total*100:.1f}%)")

            except Exception as e:
                print(f"❌ 배치 {i}-{i+len(batch)} 임베딩 실패: {e}")
                # 실패한 배치는 0 벡터로 채우기
                all_embeddings.extend([[0.0] * self.dimension] * len(batch))

        if self.verbose:
            print(f"✓ 임베딩 생성 완료: {len(all_embeddings)}개\n")

        return all_embeddings

    def embed_query(self, text: str) -> List[float]:
        """
        단일 쿼리 텍스트를 임베딩 벡터로 변환

        Args:
            text: 임베딩할 쿼리 텍스트

        Returns:
            임베딩 벡터 [0.1, 0.2, ...]
        """
        return self.embeddings.embed_query(text)

    def get_info(self) -> dict:
        """임베딩 모델 정보 반환"""
        return {
            "mode": self.mode,
            "model": self.model_name,
            "dimension": self.dimension,
            "max_tokens": self.max_tokens,
            "batch_size": self.batch_size,
        }


# 편의 함수
def create_embeddings(
    texts: List[str], mode: str = "local", model: str = "bge-m3", verbose: bool = True
) -> List[List[float]]:
    """
    간단한 임베딩 생성 함수

    Args:
        texts: 임베딩할 텍스트 리스트
        mode: 'local' 또는 'openai'
        model: 모델 이름
        verbose: 진행 상황 출력

    Returns:
        임베딩 벡터 리스트
    """
    generator = EmbeddingGenerator(mode=mode, model=model, verbose=verbose)
    return generator.embed_documents(texts)


if __name__ == "__main__":
    # 테스트 코드
    print("=" * 70)
    print("🧪 임베딩 생성기 테스트")
    print("=" * 70)

    # 테스트 텍스트
    test_texts = [
        "인공지능은 현대 사회를 변화시키고 있습니다.",
        "Machine learning is a subset of artificial intelligence.",
        "딥러닝 기술의 발전으로 다양한 응용이 가능해졌습니다.",
    ]

    # LOCAL 모드 테스트
    print("\n[LOCAL 모드 - bge-m3]")
    generator = EmbeddingGenerator(mode="local", model="bge-m3")
    embeddings = generator.embed_documents(test_texts)

    print(f"생성된 임베딩 개수: {len(embeddings)}")
    print(f"임베딩 차원: {len(embeddings[0])}")
    print(f"첫 번째 벡터 샘플: {embeddings[0][:5]}...")

    # 단일 쿼리 테스트
    print("\n[쿼리 임베딩 테스트]")
    query = "AI 기술이란 무엇인가?"
    query_embedding = generator.embed_query(query)
    print(f"쿼리 임베딩 차원: {len(query_embedding)}")

    # 모델 정보
    print("\n[모델 정보]")
    info = generator.get_info()
    for key, value in info.items():
        print(f"  {key}: {value}")

    print("\n" + "=" * 70)
    print("✅ 테스트 완료!")
