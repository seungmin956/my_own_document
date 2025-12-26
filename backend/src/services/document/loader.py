# pdf_loader.py

from typing import List, Tuple
from langchain_community.document_loaders import (
    PDFMinerLoader,
    PDFPlumberLoader,
    PyMuPDFLoader,
)
from langchain_core.documents import Document


class PDFLoaderOptimized:
    """
    여러 PDF 로더를 폴백 방식으로 시도하여 최적의 텍스트 추출

    우선순위:
    1. PDFMiner - 한글 문서에서 우수한 성능
    2. PDFPlumber - 테이블/레이아웃 처리 우수
    3. PyMuPDF - 빠른 처리 속도
    """

    def __init__(self, min_chars: int = 100):
        """
        Args:
            min_chars: 유효한 추출로 인정할 최소 글자 수
        """
        self.min_chars = min_chars
        self.loaders = [
            ("PyMuPDF", PyMuPDFLoader),
            ("PDFMiner", PDFMinerLoader),
            ("PDFPlumber", PDFPlumberLoader),
        ]

    def load(self, file_path: str) -> Tuple[List[Document], str]:
        """
        PDF 파일 로드 (폴백 전략 적용)

        Args:
            file_path: PDF 파일 경로

        Returns:
            (documents, loader_name): 추출된 문서 리스트와 사용된 로더 이름

        Raises:
            Exception: 모든 로더 실패 시
        """
        for name, LoaderClass in self.loaders:
            try:
                loader = LoaderClass(file_path)
                docs = loader.load()

                for idx, doc in enumerate(docs):
                    if "page" not in doc.metadata:
                        doc.metadata["page"] = idx + 1  # 1부터 시작

                # 텍스트 추출 성공 여부 확인
                total_text = "".join([doc.page_content for doc in docs])
                char_count = len(total_text.strip())

                if char_count >= self.min_chars:
                    print(
                        f"[OK] {name} 성공: {len(docs)}개 문서, {char_count:,}자 추출"
                    )
                    return docs, name
                else:
                    print(f"[SKIP] {name} 텍스트 부족: {char_count}자만 추출")

            except Exception as e:
                print(f"[ERROR] {name} 에러: {str(e)[:100]}")

        raise Exception(f"모든 PDF 로더 실패: {file_path}")

    # pdf_loader.py 수정

    def load_with_pdfplumber(self, pdf_path: str) -> List[Document]:
        """
        pdfplumber로 PDF 로드 (표 지원 강화)
        """
        import pdfplumber
        from langchain.schema import Document

        documents = []

        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # 1. 일반 텍스트 추출
                text = page.extract_text() or ""

                # 2. 표 추출 (✅ 추가)
                tables = page.extract_tables()

                # 3. 표를 마크다운으로 변환
                table_texts = []
                for i, table in enumerate(tables, 1):
                    if table:
                        table_md = self._table_to_markdown(table)
                        table_texts.append(f"\n[표 {i}]\n{table_md}\n")

                # 4. 텍스트 + 표 결합
                full_text = text
                if table_texts:
                    full_text += "\n\n" + "\n".join(table_texts)

                if full_text.strip():
                    documents.append(
                        Document(
                            page_content=full_text,
                            metadata={
                                "page": page_num,
                                "source": pdf_path,
                                "loader": "pdfplumber_with_tables",
                            },
                        )
                    )

        return documents

    def _table_to_markdown(self, table: List[List[str]]) -> str:
        """
        표를 마크다운 형식으로 변환

        Args:
            table: [
                ["구분", "2023", "2024"],
                ["매출", "100", "120"],
                ...
            ]

        Returns:
            | 구분 | 2023 | 2024 |
            |------|------|------|
            | 매출 | 100  | 120  |
        """
        if not table or not table[0]:
            return ""

        # 셀 정리 (None → 빈 문자열)
        cleaned = []
        for row in table:
            cleaned_row = [str(cell or "").strip() for cell in row]
            cleaned.append(cleaned_row)

        # 헤더
        header = "| " + " | ".join(cleaned[0]) + " |"
        separator = "|" + "|".join(["------"] * len(cleaned[0])) + "|"

        # 데이터 행
        rows = []
        for row in cleaned[1:]:
            rows.append("| " + " | ".join(row) + " |")

        return "\n".join([header, separator] + rows)

    def load_multiple(
        self, file_paths: List[str]
    ) -> List[Tuple[List[Document], str, str]]:
        """
        여러 PDF 파일 일괄 처리

        Args:
            file_paths: PDF 파일 경로 리스트

        Returns:
            [(documents, loader_name, file_path), ...] 리스트
        """
        results = []
        for file_path in file_paths:
            try:
                docs, loader_name = self.load(file_path)
                results.append((docs, loader_name, file_path))
            except Exception as e:
                print(f"파일 처리 실패 - {file_path}: {e}")
                results.append(([], None, file_path))

        return results


# 편의 함수
def load_pdf(file_path: str, min_chars: int = 100) -> Tuple[List[Document], str]:
    """PDF 파일을 로드하는 간단한 함수"""
    loader = PDFLoaderOptimized(min_chars=min_chars)
    return loader.load(file_path)


"""
사용 예시:

# 기본 사용
from pdf_loader import load_pdf

docs, loader_name = load_pdf("./data/document.pdf")
print(f"사용된 로더: {loader_name}")
print(f"추출된 페이지: {len(docs)}")

# 클래스 사용 (여러 파일 처리)
from pdf_loader import PDFLoaderOptimized

loader = PDFLoaderOptimized(min_chars=50)
results = loader.load_multiple([
    "./data/file1.pdf",
    "./data/file2.pdf"
])

for docs, loader_name, file_path in results:
    print(f"{file_path}: {loader_name} - {len(docs)}개 문서")
"""
