# compare_chunk_configs_test.py

from typing import List, Dict, Optional
import numpy as np
from langchain_core.documents import Document



class ChunkEvaluator:
    """개선된 청킹 품질 평가 (단순 휴리스틱)"""

    def evaluate_chunks_v2(
        self, chunks: List[Document], doc_type: Optional[str], original_docs: List[Document]
    ) -> Dict:
        """실용적인 평가 (doc_type은 Optional)"""

        chunk_sizes = [len(chunk.page_content) for chunk in chunks]
        original_size = sum(len(doc.page_content) for doc in original_docs)
        total_chunk_size = sum(chunk_sizes)

        # 1. 기본 통계
        redundancy_ratio = (total_chunk_size - original_size) / original_size

        stats = {
            "청크수": len(chunks),
            "평균크기": int(np.mean(chunk_sizes)),
            "원본크기": original_size,
            "중복비율": round(redundancy_ratio * 100, 1),
        }

        # 2. 크기 적합성 (30%)
        size_score = self._score_by_optimal(chunk_sizes, doc_type)

        # 3. 경계 품질 (30%)
        boundary_score = self._evaluate_boundaries(chunks)

        # 4. 청크 수 적정성 (20%)
        count_score = self._evaluate_chunk_count(len(chunks), doc_type)

        # 5. 중복 효율성 (20%)
        redundancy_score = max(0, 100 - (redundancy_ratio * 100))  # 중복 적을수록 좋음

        # 종합 점수
        final_score = (
            size_score * 0.3
            + boundary_score * 0.3
            + count_score * 0.2
            + redundancy_score * 0.2
        )

        return {
            "기본통계": stats,
            "크기적합성": round(size_score, 1),
            "경계품질": round(boundary_score, 1),
            "청크수적정성": round(count_score, 1),
            "중복효율": round(redundancy_score, 1),
            "종합점수": round(final_score, 1),
        }

    def _score_by_optimal(self, sizes: List[int], doc_type: Optional[str]) -> float:
        """크기 적합성 점수 (doc_type이 None이면 기본값 1000 사용)"""
        optimal = {
            "LEGAL": 1800,
            "ACADEMIC": 1200,
            "FINANCIAL": 1000,
            "TECHNICAL": 1000,
            "GENERAL": 1000,
        }

        # doc_type이 None이거나 없으면 기본값 1000
        if doc_type is None:
            optimal_size = 1000
        else:
            # doc_type이 문자열인지 객체인지 확인
            type_name = doc_type if isinstance(doc_type, str) else getattr(doc_type, 'name', 'GENERAL')
            optimal_size = optimal.get(type_name, 1000)

        deviations = [abs(size - optimal_size) / optimal_size for size in sizes]
        avg_deviation = np.mean(deviations)

        return max(0, 100 - (avg_deviation * 100))

    def _evaluate_boundaries(self, chunks: List[Document]) -> float:
        """
        경계 품질 평가
        - 청크가 자연스러운 구분점에서 나뉘었는가?
        """
        good_starts = 0
        good_ends = 0

        for chunk in chunks:
            text = chunk.page_content.strip()
            if not text:
                continue

            # 좋은 시작 패턴
            start_patterns = [
                text[0].isupper(),  # 대문자 시작
                text[0].isdigit(),  # 숫자 시작
                text[:2] in ["# ", "##", "- ", "* "],  # 마크다운 헤더/리스트
                text[:2] in ["▹ ", "○ ", "• "],  # 한글 리스트
                text[:3] in ["제", "조 ", "항 "],  # 법률 문서
                text.startswith("Ⅰ") or text.startswith("Ⅱ"),  # 로마 숫자
            ]
            if any(start_patterns):
                good_starts += 1

            # 좋은 끝 패턴
            end_patterns = [
                text[-1] in ".!?。",  # 문장 종결
                text[-1] == "\n",  # 줄바꿈
                text[-2:] == ". ",  # 문장 끝 + 공백
            ]
            if any(end_patterns):
                good_ends += 1

        # 시작과 끝 모두 중요
        start_ratio = good_starts / len(chunks)
        end_ratio = good_ends / len(chunks)

        boundary_score = (start_ratio * 0.5 + end_ratio * 0.5) * 100

        return boundary_score

    def _evaluate_chunk_count(self, num_chunks: int, doc_type: Optional[str]) -> float:
        """
        청크 수 적정성 평가
        - 너무 많으면: 검색 속도 느림, 관리 복잡
        - 너무 적으면: 검색 정밀도 낮음, 문맥 과다
        """
        # 문서 유형별 최적 범위
        optimal_ranges = {
            "LEGAL": (20, 50),  # 법률: 조항이 길어서 적은 청크
            "ACADEMIC": (30, 60),  # 논문: 섹션 기반
            "FINANCIAL": (40, 80),  # 재무: 표와 수치 많음
            "TECHNICAL": (25, 50),  # 기술: 중간
            "GENERAL": (30, 60),  # 일반: 표준
        }

        # doc_type이 None이면 기본값 사용
        if doc_type is None:
            min_optimal, max_optimal = (30, 60)
        else:
            type_name = doc_type if isinstance(doc_type, str) else getattr(doc_type, 'name', 'GENERAL')
            min_optimal, max_optimal = optimal_ranges.get(type_name, (30, 60))

        if min_optimal <= num_chunks <= max_optimal:
            return 100.0
        elif num_chunks < min_optimal:
            # 너무 적음
            ratio = num_chunks / min_optimal
            return ratio * 90  # 최대 90점
        else:
            # 너무 많음
            ratio = max_optimal / num_chunks
            return ratio * 85  # 최대 85점

    def _calculate_overlap_ratio(self, chunks: List[Document]) -> float:
        """청크 간 실제 중복 비율 추정 (참고용)"""
        if len(chunks) < 2:
            return 0.0

        overlaps = []
        for i in range(len(chunks) - 1):
            text1 = chunks[i].page_content
            text2 = chunks[i + 1].page_content

            # 끝 부분과 시작 부분 비교
            end_part = text1[-300:] if len(text1) > 300 else text1
            start_part = text2[:300] if len(text2) > 300 else text2

            # 공통 단어 수
            overlap = len(set(end_part.split()) & set(start_part.split()))
            overlaps.append(overlap)

        return np.mean(overlaps) if overlaps else 0.0
