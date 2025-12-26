# document_cache.py

import pickle
from pathlib import Path
from typing import Dict, List, Tuple
from src.services.document.loader import load_pdf


class DocumentCache:
    """PDF 로딩 및 분류 결과 캐싱"""

    def __init__(self, cache_dir: str = "./cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.memory_cache: Dict = {}
        self.classification_cache: Dict = {}  # 분류 결과 캐시 추가

    def _get_cache_path(self, file_path: str, cache_type: str = "pdf") -> Path:
        """파일 경로를 캐시 파일명으로 변환"""
        file_name = Path(file_path).stem
        return self.cache_dir / f"{file_name}_{cache_type}.pkl"

    def load_with_cache(self, file_path: str) -> Tuple[List, str]:
        """PDF 로딩 캐시"""
        # 1. 메모리 캐시 확인
        if file_path in self.memory_cache:
            print(f"[OK] 메모리 캐시에서 로드: {Path(file_path).name}")
            return self.memory_cache[file_path]

        # 2. 파일 캐시 확인
        cache_path = self._get_cache_path(file_path, "pdf")
        if cache_path.exists():
            print(f"[OK] 파일 캐시에서 로드: {cache_path.name}")
            with open(cache_path, "rb") as f:
                cached_data = pickle.load(f)
                self.memory_cache[file_path] = cached_data
                return cached_data

        # 3. 새로 로드
        print(f"[OK] PDF 새로 로드 중...")
        docs, loader_name = load_pdf(file_path)

        # 캐시 저장
        cached_data = (docs, loader_name)
        self.memory_cache[file_path] = cached_data

        with open(cache_path, "wb") as f:
            pickle.dump(cached_data, f)
        print(f"[OK] PDF 캐시 저장: {cache_path.name}")

        return cached_data

    def load_classification_with_cache(
        self, file_path: str, classifier, sample_length: int = 500
    ):
        """분류 결과 캐싱"""
        # 1. 메모리 캐시 확인
        if file_path in self.classification_cache:
            print(f"[OK] 분류 결과 캐시에서 로드")
            return self.classification_cache[file_path]

        # 2. 파일 캐시 확인
        cache_path = self._get_cache_path(file_path, "classification")
        if cache_path.exists():
            print(f"[OK] 분류 캐시에서 로드: {cache_path.name}")
            with open(cache_path, "rb") as f:
                cached_data = pickle.load(f)
                self.classification_cache[file_path] = cached_data
                return cached_data

        # 3. 새로 분류
        print(f"[OK] 문서 분류 중...")
        docs, _ = self.load_with_cache(file_path)  # PDF는 캐시 사용
        doc_type, confidence, reasoning = classifier.classify(docs, sample_length)

        # 캐시 저장
        cached_data = (doc_type, confidence, reasoning)
        self.classification_cache[file_path] = cached_data

        with open(cache_path, "wb") as f:
            pickle.dump(cached_data, f)
        print(f"[OK] 분류 캐시 저장: {cache_path.name}")

        return cached_data

    def clear_cache(self, file_path: str = None, cache_type: str = None):
        """캐시 삭제"""
        if file_path:
            # 특정 파일 캐시만 삭제
            if cache_type in [None, "pdf"]:
                self.memory_cache.pop(file_path, None)
                cache_path = self._get_cache_path(file_path, "pdf")
                if cache_path.exists():
                    cache_path.unlink()

            if cache_type in [None, "classification"]:
                self.classification_cache.pop(file_path, None)
                cache_path = self._get_cache_path(file_path, "classification")
                if cache_path.exists():
                    cache_path.unlink()

            print(f"[OK] 캐시 삭제 완료")
        else:
            # 전체 캐시 삭제
            self.memory_cache.clear()
            self.classification_cache.clear()
            for cache_file in self.cache_dir.glob("*.pkl"):
                cache_file.unlink()
            print(f"[OK] 전체 캐시 삭제 완료")
