"""
최적화된 Cross-Encoder Reranker (수정)

bge-reranker-base 올바른 사용법 적용
"""

from typing import List, Dict, Optional
import torch
import time


class OptimizedReranker:
    """
    최적화된 Reranker

    수정 사항:
    - bge-reranker는 FlagEmbedding 사용
    - 다른 모델은 sentence-transformers 사용
    """

    def __init__(
        self, model_size: str = "auto", max_length: int = 256, verbose: bool = False
    ):
        """
        Args:
            model_size: 모델 크기
                - "auto": multilingual (기본)
                - "small": TinyBERT (영어 전용)
                - "medium": MiniLM (영어 전용)
                - "multilingual": bge-reranker (다국어)
            max_length: 최대 텍스트 길이 (토큰)
            verbose: 성능 로그 출력
        """
        self.max_length = max_length
        self.verbose = verbose

        # GPU 감지
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        has_gpu = self.device == "cuda"

        # 모델 선택 (항상 multilingual)
        if model_size == "auto":
            model_size = "multilingual"

        model_map = {
            "small": "cross-encoder/ms-marco-TinyBERT-L-2-v2",
            "medium": "cross-encoder/ms-marco-MiniLM-L-6-v2",
            "multilingual": "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",  # ← 변경
        }

        model_name = model_map.get(model_size, model_map["multilingual"])

        if verbose:
            print(f"\n{'='*70}")
            print(f"[Reranker] 초기화")
            print(f"{'='*70}")
            print(f"  모델: {model_name}")
            print(f"  크기: {model_size}")
            print(f"  장치: {self.device.upper()}")
            print(f"  최대 길이: {max_length} 토큰")
            print(f"{'='*70}\n")

        # 모델 로드 (CrossEncoder 사용)
        from sentence_transformers import CrossEncoder

        self.model = CrossEncoder(model_name, device=self.device, max_length=max_length)

        # 워밍업 추가 ⭐
        if verbose:
            print("  워밍업 중...")

        # 더미 입력으로 GPU 워밍업
        _ = self.model.predict([["warm", "up"]])

        if verbose:
            print("  워밍업 완료!")

        # 통계
        self.stats = {
            "total_queries": 0,
            "total_time": 0.0,
            "avg_time": 0.0,
        }

    def rerank(
        self,
        query: str,
        candidates: List[Dict],
        top_k: int = 5,
        max_candidates: Optional[int] = None,
    ) -> List[Dict]:
        """
        후보 문서 재정렬

        Args:
            query: 사용자 질문
            candidates: Vector Search 결과
            top_k: 최종 반환 개수
            max_candidates: 최대 처리 후보 수

        Returns:
            재정렬된 상위 k개
        """
        if not candidates:
            return []

        start_time = time.time()

        # 1. 후보 수 제한
        if max_candidates and len(candidates) > max_candidates:
            candidates = sorted(
                candidates, key=lambda x: x.get("score", 0), reverse=True
            )[:max_candidates]

        # 2. Query-Document 쌍 생성
        pairs = [
            [query[:512], self._truncate(cand["text"])]  # ← 리스트로!
            for cand in candidates
        ]

        # 3. Cross-Encoder 점수 계산
        try:
            # CrossEncoder 사용
            rerank_scores = self.model.predict(pairs)

        except Exception as e:
            print(f"\n⚠️  Reranking 오류: {e}")
            print(f"   Vector Search 점수를 사용합니다.")

            for i, cand in enumerate(candidates):
                cand["rerank_score"] = cand["score"]

            return sorted(candidates, key=lambda x: x["score"], reverse=True)[:top_k]

        # 4. 점수 추가 및 정렬
        for i, cand in enumerate(candidates):
            cand["rerank_score"] = float(rerank_scores[i])

        reranked = sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)[
            :top_k
        ]

        # 5. 통계 업데이트
        elapsed = time.time() - start_time
        self._update_stats(elapsed)

        # 6. 로깅
        if self.verbose:
            self._log_results(candidates, reranked, elapsed)

        return reranked

    def _truncate(self, text: str) -> str:
        """텍스트 길이 제한"""
        max_chars = self.max_length * 4
        return text[:max_chars]

    def _update_stats(self, elapsed: float):
        """통계 업데이트"""
        self.stats["total_queries"] += 1
        self.stats["total_time"] += elapsed
        self.stats["avg_time"] = self.stats["total_time"] / self.stats["total_queries"]

    def _log_results(
        self, candidates: List[Dict], reranked: List[Dict], elapsed: float
    ):
        """결과 로깅"""
        print(f"\n{'─'*70}")
        print(f"[Reranker] 처리 완료")
        print(f"{'─'*70}")
        print(f"  후보: {len(candidates)}개")
        print(f"  반환: {len(reranked)}개")
        print(f"  시간: {elapsed*1000:.1f}ms")
        print(f"  평균: {self.stats['avg_time']*1000:.1f}ms")

        print(f"\n  [순위 변화]")
        print(f"  {'순위':<4} {'Vector':<8} {'→ Rerank':<10} {'변화':<8} {'문서'}")
        print(f"  {'-'*66}")

        for i, result in enumerate(reranked[:5], 1):
            vec_score = result.get("score", 0)
            rerank_score = result["rerank_score"]

            # 원래 순위
            original_idx = None
            for j, cand in enumerate(candidates):
                if cand.get("metadata", {}).get("doc_name") == result.get(
                    "metadata", {}
                ).get("doc_name") and cand.get("metadata", {}).get(
                    "page"
                ) == result.get(
                    "metadata", {}
                ).get(
                    "page"
                ):
                    original_idx = j
                    break

            if original_idx is not None:
                change = original_idx - (i - 1)
            else:
                change = 0

            if change > 0:
                change_str = f"↑{change}"
            elif change < 0:
                change_str = f"↓{abs(change)}"
            else:
                change_str = "→"

            # 문서 정보
            doc_name = result.get("metadata", {}).get("doc_name", "Unknown")[:20]
            page = result.get("metadata", {}).get("page", "?")

            print(
                f"  {i:<4} {vec_score:.3f}    "
                f"→ {rerank_score:.3f}    "
                f"{change_str:<8} "
                f"{doc_name}... (p.{page})"
            )

        print(f"{'─'*70}\n")

    def get_stats(self) -> Dict:
        """통계 반환"""
        return self.stats.copy()


if __name__ == "__main__":
    # =============================================
    # 테스트 코드 (독립 실행 시만 동작)
    # import 시에는 실행되지 않음
    # =============================================
    print("설치 확인...")
    try:
        from FlagEmbedding import FlagReranker

        print("✅ FlagEmbedding 설치됨")
    except ImportError:
        print("❌ FlagEmbedding 없음!")
        print("   설치: pip install FlagEmbedding")
        exit(1)

    # Reranker 테스트
    reranker = OptimizedReranker(model_size="multilingual", verbose=True)

    query = "2004.04686v1 논문의 주요 기여는?"

    candidates = [
        {
            "text": "This paper introduces RAG (Retrieval-Augmented Generation), a novel approach that combines retrieval and generation.",
            "score": 0.476,
            "metadata": {"doc_name": "2004.04686v1.pdf", "page": 8},
        },
        {
            "text": "GPT-4는 질문 답변과 긴 형식 생성에서 가장 우수한 성능을 보였습니다.",
            "score": 0.440,
            "metadata": {"doc_name": "SPRI.pdf", "page": 19},
        },
    ]

    print("\n테스트 시작...")
    results = reranker.rerank(query, candidates, top_k=2)

    print("\n최종 결과:")
    for i, r in enumerate(results, 1):
        print(f"{i}. Rerank: {r['rerank_score']:.6f}")
        print(f"   Text: {r['text'][:50]}...")
