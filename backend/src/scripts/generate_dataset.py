# generate_dataset.py
"""
LLM으로 평가 데이터셋 자동 생성
"""

from typing import List, Dict
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
import json
import re


def clean_text(text: str) -> str:
    """
    깨진 문자 제거

    Args:
        text: 원본 텍스트

    Returns:
        정제된 텍스트
    """
    # 1. 깨진 문자 제거
    text = text.replace("�", "")

    # 2. 비정상 유니코드 제거
    text = re.sub(r"[\x00-\x1F\x7F-\x9F]", "", text)

    # 3. 연속된 공백 제거
    text = re.sub(r"\s+", " ", text)

    # 4. 앞뒤 공백 제거
    text = text.strip()

    return text


class DatasetGenerator:
    """LLM 기반 데이터셋 생성기"""

    def __init__(self, llm_model: str = "llama3.2:3b"):
        self.llm = ChatOllama(model=llm_model, temperature=0.7)

        self.prompt = ChatPromptTemplate.from_template(
            """
당신은 RAG 시스템 평가용 질문을 생성하는 전문가입니다.

문서 내용:
{document}

메타데이터:
- 페이지: {page}
- 섹션: {section}

다음 조건을 만족하는 질문 3개를 생성하세요:

1. 직접적 질문 (Factual):
   - 문서에 명시된 구체적 사실 묻기
   - 예: "삼성 가우스는 무엇인가?"

2. 개념적 질문 (Conceptual):
   - 문서 내용의 이해/해석 필요
   - 예: "온디바이스 AI의 장점은?"

3. 비교/종합 질문 (Analytical):
   - 다른 정보와 비교하거나 종합 필요
   - 예: "삼성과 구글의 AI 전략 차이는?"

CRITICAL: 반드시 JSON 형식으로만 출력하세요:
{{
  "questions": [
    {{
      "type": "factual",
      "question": "...",
      "difficulty": "easy",
      "keywords": ["키워드1", "키워드2"]
    }},
    {{
      "type": "conceptual",
      "question": "...",
      "difficulty": "medium",
      "keywords": ["키워드1", "키워드2"]
    }},
    {{
      "type": "analytical",
      "question": "...",
      "difficulty": "hard",
      "keywords": ["키워드1", "키워드2"]
    }}
  ]
}}

JSON만 출력하고 다른 텍스트는 포함하지 마세요.
"""
        )

    def generate_from_chunk(self, chunk: Dict, verbose: bool = True) -> List[Dict]:
        """
        문서 청크로부터 질문 생성

        Args:
            chunk: LangChain Document 객체 또는 딕셔너리

        Returns:
            질문 리스트
        """
        # Document 객체 처리
        if hasattr(chunk, "page_content"):
            text = chunk.page_content
            metadata = chunk.metadata
        else:
            text = chunk.get("page_content", chunk.get("text", ""))
            metadata = chunk.get("metadata", {})

        if verbose:
            print(f"\n청크 처리 중 (p.{metadata.get('page', '?')})...")

        # LLM 호출
        response = self.llm.invoke(
            self.prompt.format(
                document=text[:500],
                page=metadata.get("page", "Unknown"),
                section=metadata.get("toc_section", "Unknown"),
            )
        )

        # JSON 파싱
        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            data = json.loads(content.strip())
            questions = data.get("questions", [])

            # ground_truth 생성
            doc_name = metadata.get("source", "unknown")
            page = metadata.get("page", 0)

            # 파일명 정제
            if doc_name != "unknown":
                doc_name = doc_name.replace(".pdf", "").lower()

            ground_truth_id = f"{doc_name}_page_{page}"

            # 메타데이터 추가 + 텍스트 정제
            for q in questions:
                # 텍스트 정제
                q["question"] = clean_text(q["question"])
                q["keywords"] = [clean_text(k) for k in q.get("keywords", [])]

                # 메타데이터 추가
                q["ground_truth"] = [ground_truth_id]
                q["source_page"] = page
                q["source_section"] = metadata.get("toc_section")
                q["doc_name"] = doc_name

            if verbose:
                print(f"  ✅ {len(questions)}개 질문 생성")

            return questions

        except Exception as e:
            if verbose:
                print(f"  ❌ 파싱 실패: {e}")
            return []

    def _fix_common_json_errors(self, content: str) -> str:
        """JSON 오류 자동 수정"""
        import re

        # 마지막 쉼표 제거
        content = re.sub(r",(\s*[}\]])", r"\1", content)

        # 제어 문자 제거
        content = re.sub(r"[\x00-\x1F\x7F]", "", content)

        return content

    def generate_dataset(
        self, chunks: List[Dict], num_chunks: int = 10, output_path: str = None
    ) -> List[Dict]:
        """
        여러 청크로부터 데이터셋 생성

        Args:
            chunks: 문서 청크 리스트
            num_chunks: 사용할 청크 수
            output_path: 저장 경로

        Returns:
            전체 질문 리스트
        """
        print(f"\n{'='*70}")
        print(f"[Dataset Generator] 데이터셋 생성 시작")
        print(f"{'='*70}")
        print(f"  청크 수: {num_chunks}")

        # 청크 샘플링
        import random

        sampled_chunks = random.sample(chunks, min(num_chunks, len(chunks)))

        # 질문 생성
        all_questions = []
        for i, chunk in enumerate(sampled_chunks, 1):
            print(f"\n[{i}/{num_chunks}]")
            questions = self.generate_from_chunk(chunk)
            all_questions.extend(questions)

        print(f"\n{'='*70}")
        print(f"[SUCCESS] 총 {len(all_questions)}개 질문 생성")
        print(f"{'='*70}\n")

        # 저장
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(all_questions, f, ensure_ascii=False, indent=2)
            print(f"저장 완료: {output_path}\n")

        return all_questions


# 사용 예시
if __name__ == "__main__":
    from src.services.document.processor import process_pdf
    from pathlib import Path

    # 1. PDF 파일 찾기
    data_dir = Path("./data")
    pdf_files = list(data_dir.glob("*.pdf"))

    print(f"\n{'='*70}")
    print(f"[PDF Files] {len(pdf_files)}개 PDF 파일 발견")
    print(f"{'='*70}")
    for pdf in pdf_files:
        print(f"  - {pdf.name}")
    print()

    # 2. 청크 수집
    all_chunks = []
    for pdf_path in pdf_files:
        print(f"\n처리 중: {pdf_path.name}")
        chunks, _, _ = process_pdf(str(pdf_path), verbose=False)
        all_chunks.extend(chunks)
        print(f"  ✅ {len(chunks)}개 청크 추출")

    print(f"\n{'='*70}")
    print(f"[Total] 총 {len(all_chunks)}개 청크 수집 완료")
    print(f"{'='*70}\n")

    # 3. 데이터셋 생성
    generator = DatasetGenerator()
    chunks_per_pdf = 10
    total_chunks = chunks_per_pdf * len(pdf_files)

    dataset = generator.generate_dataset(
        chunks=all_chunks,
        num_chunks=total_chunks,
        output_path="./evaluation/test_dataset.json",
    )

    # 4. 샘플 출력
    print("\n샘플 질문:")
    for q in dataset[:3]:
        print(f"\n질문: {q['question']}")
        print(f"유형: {q['type']}")
        print(f"난이도: {q['difficulty']}")
        print(f"Ground Truth: {q['ground_truth']}")
