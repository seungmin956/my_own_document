# toc_extractor.py

import fitz  # PyMuPDF
import re
import json
from typing import List, Dict, Optional
from pathlib import Path


class TOCExtractor:
    """
    목차 추출 - 3단계 하이브리드 전략

    1순위: PyMuPDF 메타데이터 (100% 정확, 빠름)
    2순위: 텍스트 패턴 매칭 (빠르지만 제한적)
    3순위: LLM 폴백 (느리지만 범용적, llama3.2:3b)

    NOTE: PDFMiner는 텍스트 추출에 사용
          PyMuPDF는 목차 추출 전용으로 사용
    """

    def __init__(
        self,
        min_toc_items: int = 3,
        use_llm_fallback: bool = True,
        llm_model: str = "llama3.2:3b",
    ):
        """
        Args:
            min_toc_items: 유효한 목차로 인정할 최소 항목 수
            use_llm_fallback: LLM 폴백 사용 여부
            llm_model: 사용할 LLM 모델
        """
        self.min_toc_items = min_toc_items
        self.use_llm_fallback = use_llm_fallback
        self.llm_model = llm_model
        self._llm = None  # 지연 초기화

    def extract(self, file_path: str) -> Optional[List[Dict]]:
        """
        목차 추출 메인 메서드

        Returns:
            목차 항목 리스트 또는 None
            [
                {"level": 1, "title": "제1장 서론", "page": 5},
                {"level": 2, "title": "1.1 배경", "page": 6},
                ...
            ]
        """
        # 1순위: PyMuPDF 메타데이터 목차
        toc = self._extract_metadata_toc(file_path)
        if self._is_valid_toc(toc):
            print(f"[OK] 메타데이터 목차 추출 성공: {len(toc)}개 항목")
            return toc

        # 2순위: 텍스트 패턴 분석 (여러 패턴 자동 시도)
        print("[WARN] 메타데이터 목차 없음, 텍스트 패턴 분석 시도...")
        toc = self._extract_text_toc(file_path)
        if self._is_valid_toc(toc):
            print(f"[OK] 텍스트 패턴 목차 추출 성공: {len(toc)}개 항목")
            return toc

        # 3순위: LLM 폴백 (선택적)
        if self.use_llm_fallback:
            print("[WARN] 텍스트 패턴 실패, LLM 폴백 시도...")
            toc = self._extract_toc_with_llm(file_path)
            if self._is_valid_toc(toc):
                print(f"[OK] LLM 목차 추출 성공: {len(toc)}개 항목")
                return toc

        # 4순위: 포기
        print("[FAIL] 목차 추출 실패 -> 단일 컬렉션 사용 예정")
        return None

    def _extract_metadata_toc(self, file_path: str) -> Optional[List[Dict]]:
        """PyMuPDF 메타데이터 목차 추출"""
        try:
            doc = fitz.open(file_path)
            toc = doc.get_toc()  # [(level, title, page), ...]
            doc.close()

            if not toc:
                return None

            return [
                {
                    "level": level,
                    "title": title.strip(),
                    "page": max(0, page - 1),
                    "source": "metadata",
                }
                for level, title, page in toc
            ]

        except Exception as e:
            print(f"[ERROR] PyMuPDF 메타데이터 추출 실패: {e}")
            return None

    def _extract_text_toc(self, file_path: str) -> Optional[List[Dict]]:
        """텍스트 패턴 기반 목차 추출 (자동 패턴 감지)"""
        # 앞부분 10페이지 텍스트 추출
        text = self._get_first_pages_text(file_path, max_pages=10)

        if not text:
            return None

        # 여러 패턴을 시도하고 점수화
        best_toc = None
        best_score = 0

        patterns = [
            self._try_pattern_numbered,  # "1. 제목 ... 5"
            self._try_pattern_bullet,  # "■ 제목 ... 5"
            self._try_pattern_chapter,  # "제1장 제목 ... 5"
            self._try_pattern_roman,  # "I. Title ... 5"
        ]

        for pattern_func in patterns:
            toc = pattern_func(text)
            if toc:
                score = self._score_toc(toc)
                if score > best_score:
                    best_toc = toc
                    best_score = score

        return best_toc if best_score >= 50 else None  # 임계값

    def _get_first_pages_text(self, file_path: str, max_pages: int = 10) -> str:
        """PyMuPDF로 앞부분 페이지 텍스트 추출"""
        try:
            doc = fitz.open(file_path)
            text = ""

            for page_num in range(min(max_pages, len(doc))):
                page = doc[page_num]
                text += page.get_text() + "\n"

            doc.close()
            return text

        except Exception as e:
            print(f"[ERROR] 텍스트 추출 실패: {e}")
            return ""

    def _try_pattern_numbered(self, text: str) -> Optional[List[Dict]]:
        """패턴: "1. 제목 ... 5" """
        toc_items = []
        pattern = r"^(\d+)\.\s+(.+?)\s+[\.·\s]+\s*(\d+)\s*$"

        for line in text.split("\n"):
            line = line.strip()
            match = re.match(pattern, line, re.UNICODE)
            if match:
                toc_items.append(
                    {
                        "level": 1,
                        "title": f"{match.group(1)}. {match.group(2).strip()}",
                        "page": int(match.group(3)),
                        "source": "text_pattern_numbered",
                    }
                )

        return toc_items if toc_items else None

    def _try_pattern_bullet(self, text: str) -> Optional[List[Dict]]:
        """패턴: "■ 제목 ... 5" (SPRI 스타일)"""
        toc_items = []
        pattern = r"^[■□▪▫●○]\s+(.+?)\s+[\.·\s]+\s*(\d+)\s*$"

        for line in text.split("\n"):
            line = line.strip()
            match = re.match(pattern, line, re.UNICODE)
            if match:
                toc_items.append(
                    {
                        "level": 1,
                        "title": match.group(1).strip(),
                        "page": int(match.group(2)),
                        "source": "text_pattern_bullet",
                    }
                )

        return toc_items if toc_items else None

    def _try_pattern_chapter(self, text: str) -> Optional[List[Dict]]:
        """패턴: "제1장 제목 ... 5" """
        toc_items = []
        pattern = r"^제(\d+)장\s+(.+?)\s+[\.·\s]+\s*(\d+)\s*$"

        for line in text.split("\n"):
            line = line.strip()
            match = re.match(pattern, line, re.UNICODE)
            if match:
                toc_items.append(
                    {
                        "level": 1,
                        "title": f"제{match.group(1)}장 {match.group(2).strip()}",
                        "page": int(match.group(3)),
                        "source": "text_pattern_chapter",
                    }
                )

        return toc_items if toc_items else None

    def _try_pattern_roman(self, text: str) -> Optional[List[Dict]]:
        """패턴: "I. Title ... 5" """
        toc_items = []
        pattern = r"^([IVX]+)\.\s+(.+?)\s+[\.·\s]+\s*(\d+)\s*$"

        for line in text.split("\n"):
            line = line.strip()
            match = re.match(pattern, line, re.UNICODE)
            if match:
                toc_items.append(
                    {
                        "level": 1,
                        "title": f"{match.group(1)}. {match.group(2).strip()}",
                        "page": int(match.group(3)),
                        "source": "text_pattern_roman",
                    }
                )

        return toc_items if toc_items else None

    def _score_toc(self, toc: List[Dict]) -> float:
        """목차 품질 점수 (0~100)"""
        if not toc:
            return 0

        score = 0

        # 항목 수 (5~30개가 이상적)
        if 5 <= len(toc) <= 30:
            score += 40
        elif 3 <= len(toc) <= 50:
            score += 20

        # 페이지 번호 순서 체크
        pages = [item["page"] for item in toc]
        if pages == sorted(pages):
            score += 30

        # 제목 길이 체크
        avg_len = sum(len(item["title"]) for item in toc) / len(toc)
        if 5 <= avg_len <= 50:
            score += 30

        return score

    def _is_valid_toc(self, toc: Optional[List]) -> bool:
        """유효한 목차인지 확인"""
        return toc is not None and len(toc) >= self.min_toc_items

    def _extract_toc_with_llm(self, file_path: str) -> Optional[List[Dict]]:
        """
        LLM을 사용하여 목차 추출(llama3.2:3b)

        앞부분 5페이지 텍스트를 LLM에게 주고 목차를 JSON 형식으로 추출 요청
        """
        try:
            # LLM 지연 초기화
            if self._llm is None:
                from langchain_ollama import ChatOllama

                self._llm = ChatOllama(model=self.llm_model, temperature=0)
                print(f"[INFO] LLM 초기화: {self.llm_model}")

            # 앞부분 텍스트 추출 (목차가 보통 앞에 있음)
            text = self._get_first_pages_text(file_path, max_pages=5)

            if not text or len(text) < 100:
                return None

            # 프롬프트 구성
            prompt = f"""You are a helpful assistant that extracts table of contents from PDF documents.

Given the following text from the beginning of a PDF document, extract the table of contents (TOC) if it exists.

Text:
{text[:4000]}

Instructions:
1. Find the table of contents section (it might be labeled as "Contents", "목차", "Table of Contents", "KEY Contents", etc.)
2. Extract each TOC entry with its title and page number
3. Determine the hierarchy level (1 for main chapters, 2 for subsections, 3 for sub-subsections)
4. Return ONLY a valid JSON array in this exact format, with no additional text:

[
  {{"level": 1, "title": "Chapter Title", "page": 5}},
  {{"level": 2, "title": "Section Title", "page": 7}},
  ...
]

Important:
- If NO table of contents is found, return: []
- Return ONLY the JSON array, nothing else
- Page numbers must be integers
- Titles should be clean (no extra dots or page numbers in the title)
"""

            # LLM 호출
            response = self._llm.invoke(prompt)
            response_text = (
                response.content if hasattr(response, "content") else str(response)
            )

            # JSON 파싱
            toc = self._parse_llm_response(response_text)

            if toc:
                # source 추가
                for item in toc:
                    item["source"] = f"llm_{self.llm_model}"

            return toc

        except Exception as e:
            print(f"[ERROR] LLM 목차 추출 실패: {e}")
            return None

    def _parse_llm_response(self, response_text: str) -> Optional[List[Dict]]:
        """LLM 응답에서 JSON 파싱"""
        try:
            # JSON 블록 찾기 (```json ... ``` 형태일 수 있음)
            response_text = response_text.strip()

            # 코드 블록 제거
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()

            # [ 로 시작하는 부분 찾기
            if "[" in response_text:
                start = response_text.find("[")
                end = response_text.rfind("]") + 1
                response_text = response_text[start:end]

            # JSON 파싱
            toc = json.loads(response_text)

            # 검증
            if not isinstance(toc, list):
                return None

            # 각 항목 검증 및 정제
            valid_toc = []
            for item in toc:
                if isinstance(item, dict) and "title" in item and "page" in item:
                    # level 기본값 설정
                    if "level" not in item:
                        item["level"] = 1

                    # page를 int로 변환
                    try:
                        item["page"] = int(item["page"])
                        valid_toc.append(item)
                    except (ValueError, TypeError):
                        continue

            return valid_toc if valid_toc else None

        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON 파싱 실패: {e}")
            print(f"[DEBUG] 응답 텍스트: {response_text[:200]}...")
            return None
        except Exception as e:
            print(f"[ERROR] LLM 응답 처리 실패: {e}")
            return None


# 편의 함수
def extract_toc(file_path: str, use_llm_fallback: bool = True) -> Optional[List[Dict]]:
    """목차 추출 간단 함수"""
    extractor = TOCExtractor(use_llm_fallback=use_llm_fallback)
    return extractor.extract(file_path)
