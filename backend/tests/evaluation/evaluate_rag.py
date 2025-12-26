# evaluate_rag.py

"""
RAG 시스템 성능 평가

평가 메트릭:
1. Retrieval Metrics: Precision@K, Recall@K, MRR
2. Answer Quality: 정확성, 관련성
3. Performance: 응답 시간
"""

import json
import time
from pathlib import Path
from typing import List, Dict
from tqdm import tqdm
import argparse

# chatbot import
import sys

sys.path.append(str(Path(__file__).parent.parent))
from src.core.chatbot import DocumentChatbot


class RAGEvaluator:
    """RAG 시스템 평가기"""

    def __init__(self, chatbot: DocumentChatbot):
        self.chatbot = chatbot

    def evaluate_dataset(self, test_file: str, verbose: bool = True) -> Dict:
        """
        테스트 데이터셋 전체 평가

        Args:
            test_file: 테스트 데이터셋 JSON 파일
            verbose: 진행 상황 출력

        Returns:
            평가 결과 딕셔너리
        """
        # 테스트 데이터 로드
        with open(test_file, "r", encoding="utf-8") as f:
            test_data = json.load(f)

        if verbose:
            print(f"\n{'='*70}")
            print(f"[EVALUATION] RAG 시스템 평가 시작")
            print(f"{'='*70}")
            print(f"테스트셋: {Path(test_file).name}")
            print(f"질문 수: {len(test_data)}")
            print(
                f"검색 전략: {'Hybrid (Vector + BM25)' if self.chatbot.bm25_enabled else 'Vector Only'}"
            )
            print(
                f"Reranking: {'Enabled' if self.chatbot.rerank_enabled else 'Disabled'}"
            )
            print(f"{'='*70}\n")

        results = []
        total_time = 0

        # 각 질문 평가
        for i, item in enumerate(tqdm(test_data, desc="평가 진행"), 1):
            question = item["question"]
            expected_doc = item.get("expected_document", None)

            # 시간 측정
            start_time = time.time()

            # 질문 실행 (verbose=False)
            result = self.chatbot.ask(question=question, doc_name=None, verbose=False)

            elapsed = time.time() - start_time
            total_time += elapsed

            # 결과 저장
            eval_result = {
                "question_id": i,
                "question": question,
                "answer": result["answer"],
                "sources": result["sources"],
                "time": elapsed,
                "expected_document": expected_doc,
                "error": result.get("error", None),
            }

            results.append(eval_result)

        # 통계 계산
        stats = self._calculate_statistics(results, total_time)

        if verbose:
            self._print_statistics(stats, len(test_data))

        return {
            "results": results,
            "statistics": stats,
            "config": {
                "bm25_enabled": self.chatbot.bm25_enabled,
                "rerank_enabled": self.chatbot.rerank_enabled,
                "vector_weight": getattr(self.chatbot, "bm25_vector_weight", None),
                "bm25_weight": getattr(self.chatbot, "bm25_weight", None),
            },
        }

    def _calculate_statistics(self, results: List[Dict], total_time: float) -> Dict:
        """통계 계산"""

        # 기본 통계
        total_questions = len(results)
        successful = [r for r in results if r["error"] is None]
        failed = [r for r in results if r["error"] is not None]

        # 시간 통계
        times = [r["time"] for r in successful]
        avg_time = sum(times) / len(times) if times else 0

        # 문서 검색 성공률 (최소 1개 소스)
        retrieved = [r for r in successful if len(r["sources"]) > 0]
        retrieval_rate = len(retrieved) / total_questions if total_questions > 0 else 0

        # 평균 검색 문서 수
        avg_sources = (
            sum(len(r["sources"]) for r in successful) / len(successful)
            if successful
            else 0
        )

        return {
            "total_questions": total_questions,
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": (
                len(successful) / total_questions if total_questions > 0 else 0
            ),
            "retrieval_rate": retrieval_rate,
            "avg_sources": avg_sources,
            "avg_time": avg_time,
            "total_time": total_time,
        }

    def _print_statistics(self, stats: Dict, total: int):
        """통계 출력"""
        print(f"\n{'='*70}")
        print(f"[RESULTS] 평가 결과")
        print(f"{'='*70}")

        print(f"\n[기본 통계]")
        print(f"  총 질문 수: {stats['total_questions']}")
        print(f"  성공: {stats['successful']} ({stats['success_rate']*100:.1f}%)")
        print(f"  실패: {stats['failed']}")

        print(f"\n[검색 성능]")
        print(f"  검색 성공률: {stats['retrieval_rate']*100:.1f}%")
        print(f"  평균 검색 문서 수: {stats['avg_sources']:.1f}개")

        print(f"\n[응답 시간]")
        print(f"  평균 응답 시간: {stats['avg_time']:.2f}초")
        print(f"  전체 소요 시간: {stats['total_time']:.1f}초")

        print(f"\n{'='*70}\n")

    def save_results(self, results: Dict, output_file: str):
        """결과 저장"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"[SAVED] 결과 저장: {output_file}\n")


def main():
    parser = argparse.ArgumentParser(description="RAG 시스템 평가")
    parser.add_argument(
        "--test-file",
        type=str,
        default="evaluation/test_dataset_dedup.json",
        help="테스트 데이터셋 파일",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="결과 저장 파일 (기본: evaluation/results_TIMESTAMP.json)",
    )
    parser.add_argument(
        "--no-bm25", action="store_true", help="BM25 비활성화 (벡터 검색만)"
    )
    parser.add_argument("--no-rerank", action="store_true", help="Reranking 비활성화")

    args = parser.parse_args()

    # Chatbot 초기화
    print("\n[INIT] Chatbot 초기화 중...\n")

    # Config 수정 (BM25/Rerank 옵션)
    from chatbot import Config

    config = Config()

    if args.no_bm25:
        config.bm25_enabled = False
    if args.no_rerank:
        config.rerank_enabled = False

    chatbot = DocumentChatbot(config=config)

    # 평가 실행
    evaluator = RAGEvaluator(chatbot)
    results = evaluator.evaluate_dataset(test_file=args.test_file, verbose=True)

    # 결과 저장
    if args.output:
        output_file = args.output
    else:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        bm25_suffix = "hybrid" if config.bm25_enabled else "vector"
        rerank_suffix = "rerank" if config.rerank_enabled else "norerank"
        output_file = (
            f"evaluation/results_{bm25_suffix}_{rerank_suffix}_{timestamp}.json"
        )

    evaluator.save_results(results, output_file)

    print(f"{'='*70}")
    print(f"[COMPLETE] 평가 완료!")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
