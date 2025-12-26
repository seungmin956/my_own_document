# bm25_retriever.py

"""
BM25 Retriever for Document Search

Qdrant에 저장된 문서를 대상으로 BM25 키워드 검색 수행
"""

from typing import List, Dict, Optional
from rank_bm25 import BM25Okapi
from src.services.storage.qdrant_manager import QdrantManager
from src.utils.tokenizer import KoreanTokenizer


class BM25Retriever:
    """
    BM25 기반 키워드 검색기

    특징:
    - Qdrant에서 문서 로드
    - Kiwipiepy 형태소 분석 토큰화
    - BM25 알고리즘으로 스코어링
    """

    def __init__(self, qdrant_manager: QdrantManager, verbose: bool = False):
        """
        Args:
            qdrant_manager: Qdrant 매니저 인스턴스
            verbose: 디버깅 정보 출력
        """
        self.qdrant = qdrant_manager
        self.tokenizer = KoreanTokenizer()
        self.verbose = verbose

        # 캐시
        self._corpus = None  # List[str]: 전체 문서 텍스트
        self._metadata = None  # List[Dict]: 각 문서의 메타데이터
        self._bm25 = None  # BM25Okapi 인스턴스
        self._collection_names = None  # 현재 로드된 컬렉션

    def load_corpus(self, collection_names: Optional[List[str]] = None):
        """
        Qdrant에서 문서 corpus 로드

        Args:
            collection_names: 로드할 컬렉션 리스트 (None이면 전체)
        """
        if self.verbose:
            print(f"\n[BM25] Corpus 로딩 중...")

        # 캐시 확인
        if self._corpus is not None and self._collection_names == collection_names:
            if self.verbose:
                print(f"   캐시 사용: {len(self._corpus)}개 문서")
            return

        # 컬렉션 결정
        if collection_names is None:
            collection_names = self.qdrant.list_collections()

        # 전체 문서 로드
        all_docs = []
        all_metadata = []

        for collection_name in collection_names:
            try:
                # Qdrant에서 모든 포인트 가져오기
                points = self.qdrant.client.scroll(
                    collection_name=collection_name,
                    limit=10000,  # 충분히 큰 값
                    with_payload=True,
                    with_vectors=False,  # 벡터는 필요없음
                )[0]

                for point in points:
                    all_docs.append(point.payload["text"])
                    all_metadata.append(
                        {
                            "collection": collection_name,
                            "doc_name": point.payload.get("doc_name", ""),
                            "page": point.payload.get("page", 0),
                            "toc_section": point.payload.get("toc_section", "Unknown"),
                            "point_id": point.id,
                        }
                    )

            except Exception as e:
                if self.verbose:
                    print(f"   ⚠️  컬렉션 로드 실패: {collection_name} - {e}")
                continue

        if not all_docs:
            raise ValueError("로드된 문서가 없습니다")

        # Corpus 토큰화
        if self.verbose:
            print(f"   문서 수: {len(all_docs)}")
            print(f"   토큰화 중...")

        tokenized_corpus = [self.tokenizer.tokenize(doc) for doc in all_docs]

        # BM25 인덱스 생성
        self._bm25 = BM25Okapi(tokenized_corpus)
        self._corpus = all_docs
        self._metadata = all_metadata
        self._collection_names = collection_names

        if self.verbose:
            print(f"   ✅ BM25 인덱스 생성 완료: {len(self._corpus)}개 문서\n")

    def search(
        self, query: str, top_k: int = 10, collection_names: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        BM25 검색 수행

        Args:
            query: 검색 쿼리
            top_k: 반환할 결과 수
            collection_names: 검색할 컬렉션 (None이면 전체)

        Returns:
            검색 결과 리스트 (chatbot.py 형식과 호환)
        """
        # Corpus 로드 (캐시 있으면 스킵)
        self.load_corpus(collection_names)

        # 쿼리 토큰화
        tokenized_query = self.tokenizer.tokenize(query)

        if self.verbose:
            print(f"[BM25] 검색 쿼리: {query}")
            print(f"   토큰: {tokenized_query}")

        # BM25 스코어 계산
        scores = self._bm25.get_scores(tokenized_query)

        # Top-K 결과 추출
        import numpy as np

        top_indices = np.argsort(scores)[::-1][:top_k]

        # 결과 포맷팅 (chatbot.py와 동일한 형식)
        results = []
        for idx in top_indices:
            score = float(scores[idx])

            # 스코어가 0이면 무시
            if score <= 0:
                continue

            results.append(
                {
                    "text": self._corpus[idx],
                    "score": score,  # BM25 스코어
                    "metadata": self._metadata[idx],
                }
            )

        if self.verbose:
            print(f"   검색 결과: {len(results)}개")
            for i, result in enumerate(results[:3], 1):
                print(
                    f"   [{i}] BM25: {result['score']:.3f} | "
                    f"{result['metadata']['toc_section']} "
                    f"(p.{result['metadata']['page']})"
                )
            if len(results) > 3:
                print(f"   ... 외 {len(results) - 3}개")

        return results

    def clear_cache(self):
        """캐시 초기화"""
        self._corpus = None
        self._metadata = None
        self._bm25 = None
        self._collection_names = None


def hybrid_search(
    query: str,
    vector_results: List[Dict],
    bm25_results: List[Dict],
    vector_weight: float = 0.7,
    bm25_weight: float = 0.3,
    top_k: int = 10,
) -> List[Dict]:
    """
    벡터 검색 + BM25 검색 결과 결합

    정규화 전략:
    1. 각 검색 방식의 스코어를 0-1로 정규화
    2. 가중치 적용하여 합산
    3. 최종 스코어로 재정렬

    Args:
        query: 검색 쿼리
        vector_results: 벡터 검색 결과
        bm25_results: BM25 검색 결과
        vector_weight: 벡터 검색 가중치 (기본 0.7)
        bm25_weight: BM25 가중치 (기본 0.3)
        top_k: 반환할 결과 수

    Returns:
        하이브리드 검색 결과
    """
    import numpy as np

    # 문서 고유 키 생성 함수
    def _get_doc_key(result: Dict) -> str:
        """문서 고유 키 생성 (중복 제거용)"""
        metadata = result["metadata"]
        return f"{metadata['doc_name']}|{metadata['page']}|{metadata.get('toc_section', '')}"

    # 스코어 정규화 함수
    def normalize_scores(
        results: List[Dict], score_key: str = "score"
    ) -> Dict[str, float]:
        """결과 리스트의 스코어를 0-1로 정규화"""
        if not results:
            return {}

        scores = [r[score_key] for r in results]
        min_score = min(scores)
        max_score = max(scores)

        # 동일한 스코어면 1로 통일
        if max_score == min_score:
            return {_get_doc_key(r): 1.0 for r in results}

        # Min-Max 정규화
        normalized = {}
        for result in results:
            key = _get_doc_key(result)
            original = result[score_key]
            normalized[key] = (original - min_score) / (max_score - min_score)

        return normalized

    # 2. 스코어 정규화
    vector_normalized = normalize_scores(vector_results, "score")
    bm25_normalized = normalize_scores(bm25_results, "score")

    # 3. 결과 병합
    merged = {}

    # Vector 결과 추가
    for result in vector_results:
        key = _get_doc_key(result)
        merged[key] = {
            "result": result,
            "vector_score": vector_normalized.get(key, 0),
            "bm25_score": 0,
        }

    # BM25 결과 추가
    for result in bm25_results:
        key = _get_doc_key(result)

        if key in merged:
            # 이미 있으면 BM25 스코어만 추가
            merged[key]["bm25_score"] = bm25_normalized.get(key, 0)
        else:
            # 새로운 결과 추가
            merged[key] = {
                "result": result,
                "vector_score": 0,
                "bm25_score": bm25_normalized.get(key, 0),
            }

    # 4. 가중 합산
    for key in merged:
        item = merged[key]
        item["hybrid_score"] = (
            vector_weight * item["vector_score"] + bm25_weight * item["bm25_score"]
        )

    # 5. 정렬 및 Top-K
    sorted_results = sorted(
        merged.values(), key=lambda x: x["hybrid_score"], reverse=True
    )[:top_k]

    # 6. 결과 포맷팅
    final_results = []
    for item in sorted_results:
        result = item["result"].copy()
        result["hybrid_score"] = item["hybrid_score"]
        result["vector_score_normalized"] = item["vector_score"]
        result["bm25_score_normalized"] = item["bm25_score"]
        result["score"] = item["hybrid_score"]  # ⭐ 최종 점수를 hybrid_score로
        final_results.append(result)

    return final_results


if __name__ == "__main__":
    # 테스트 코드
    from src.services.storage.qdrant_manager import QdrantManager

    qdrant = QdrantManager(
        host=os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", "6333")),
        api_key=os.getenv("QDRANT_API_KEY"),
        embedding_dimension=1024,
    )

    retriever = BM25Retriever(qdrant, verbose=True)

    # 테스트 검색
    results = retriever.search(query="삼성전자 AI 전략", top_k=5)

    print(f"\n검색 결과: {len(results)}개")
    for i, result in enumerate(results, 1):
        print(f"[{i}] 스코어: {result['score']:.3f}")
        print(f"    {result['text'][:100]}...")
