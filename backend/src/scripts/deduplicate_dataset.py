# deduplicate_dataset.py
"""
평가 데이터셋 중복 제거
"""

from typing import List, Dict, Set
import json
from difflib import SequenceMatcher
from collections import defaultdict


class DatasetDeduplicator:
    """데이터셋 중복 제거기"""

    def __init__(self, similarity_threshold: float = 0.85):
        """
        Args:
            similarity_threshold: 유사도 임계값 (0.85 = 85% 이상 유사하면 중복)
        """
        self.threshold = similarity_threshold

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        두 텍스트의 유사도 계산

        Returns:
            0.0 ~ 1.0
        """
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

    def find_duplicates(self, questions: List[Dict]) -> Dict[int, List[int]]:
        """
        중복 질문 찾기

        Args:
            questions: 질문 리스트

        Returns:
            {대표_인덱스: [중복_인덱스들]}
        """
        duplicates = defaultdict(list)
        processed = set()

        for i, q1 in enumerate(questions):
            if i in processed:
                continue

            # 자기 자신은 대표로
            group = [i]

            for j, q2 in enumerate(questions[i + 1 :], start=i + 1):
                if j in processed:
                    continue

                similarity = self.calculate_similarity(q1["question"], q2["question"])

                if similarity >= self.threshold:
                    group.append(j)
                    processed.add(j)

            if len(group) > 1:
                duplicates[i] = group

        return duplicates

    def merge_duplicates(
        self, questions: List[Dict], duplicate_groups: Dict[int, List[int]]
    ) -> List[Dict]:
        """
        중복 질문 병합

        전략:
        1. 가장 자연스러운 질문 선택 (짧고 명확한 것)
        2. ground_truth 합치기 (중복 제거)
        3. keywords 합치기 (중복 제거)
        """
        merged = []
        processed = set()

        # 중복 그룹 처리
        for representative_idx, group_indices in duplicate_groups.items():
            # 대표 질문 선택 (가장 짧은 것)
            group_questions = [questions[i] for i in group_indices]
            best_question = min(group_questions, key=lambda q: len(q["question"]))

            # ground_truth 병합
            all_ground_truths = []
            for q in group_questions:
                all_ground_truths.extend(q.get("ground_truth", []))

            # keywords 병합
            all_keywords = []
            for q in group_questions:
                all_keywords.extend(q.get("keywords", []))

            # 중복 제거
            unique_ground_truths = list(set(all_ground_truths))
            unique_keywords = list(set(all_keywords))

            # 병합된 질문 생성
            merged_question = best_question.copy()
            merged_question["ground_truth"] = unique_ground_truths
            merged_question["keywords"] = unique_keywords
            merged_question["merged_from"] = len(group_indices)

            merged.append(merged_question)
            processed.update(group_indices)

        # 중복 아닌 질문 추가
        for i, q in enumerate(questions):
            if i not in processed:
                merged.append(q)

        return merged

    def deduplicate(
        self, input_path: str, output_path: str, verbose: bool = True
    ) -> Dict:
        """
        전체 중복 제거 프로세스

        Args:
            input_path: 원본 데이터셋 경로
            output_path: 중복 제거된 데이터셋 저장 경로
            verbose: 진행 상황 출력

        Returns:
            통계 정보
        """
        # 1. 로드
        with open(input_path, "r", encoding="utf-8") as f:
            questions = json.load(f)

        original_count = len(questions)

        if verbose:
            print(f"\n{'='*70}")
            print(f"[Deduplication] 중복 제거 시작")
            print(f"{'='*70}")
            print(f"  원본 질문 수: {original_count}")

        # 2. 중복 찾기
        duplicate_groups = self.find_duplicates(questions)

        if verbose:
            print(f"  중복 그룹 수: {len(duplicate_groups)}")

            # 중복 예시 출력
            if duplicate_groups:
                print(f"\n  중복 예시:")
                for i, (rep_idx, group_indices) in enumerate(
                    list(duplicate_groups.items())[:3], 1
                ):
                    print(f"\n  [{i}] 그룹 크기: {len(group_indices)}")
                    for idx in group_indices[:3]:
                        q = questions[idx]["question"]
                        print(f"      - {q}")

        # 3. 병합
        merged = self.merge_duplicates(questions, duplicate_groups)

        final_count = len(merged)
        removed = original_count - final_count

        if verbose:
            print(f"\n{'='*70}")
            print(f"[SUCCESS] 중복 제거 완료")
            print(f"{'='*70}")
            print(f"  최종 질문 수: {final_count}")
            print(f"  제거된 중복: {removed}개")
            print(f"  감소율: {removed/original_count*100:.1f}%")
            print(f"{'='*70}\n")

        # 4. 저장
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)

        if verbose:
            print(f"저장 완료: {output_path}\n")

        return {
            "original_count": original_count,
            "final_count": final_count,
            "removed_count": removed,
            "reduction_rate": removed / original_count,
        }


# 사용 예시
if __name__ == "__main__":
    deduplicator = DatasetDeduplicator(similarity_threshold=0.85)

    stats = deduplicator.deduplicate(
        input_path="./evaluation/test_dataset.json",
        output_path="./evaluation/test_dataset_dedup.json",
        verbose=True,
    )

    print(f"\n통계:")
    print(f"  원본: {stats['original_count']}개")
    print(f"  최종: {stats['final_count']}개")
    print(f"  감소: {stats['reduction_rate']*100:.1f}%")
