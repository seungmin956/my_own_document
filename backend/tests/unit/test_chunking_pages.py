"""
청킹 전후 페이지 정보 추적

문제: 청킹 후 모든 청크가 page=1
원인: 확인 필요
"""

from backend.preprocessor.pdf_loader import load_pdf
from langchain_text_splitters import RecursiveCharacterTextSplitter


def test_chunking_page_preservation():
    """청킹 시 페이지 정보 보존 확인"""

    file_path = "./data/_10-K-Q4-2023-As-Filed.pdf"

    print("=" * 70)
    print("🔍 청킹 전후 페이지 정보 추적")
    print("=" * 70)

    # 1. PDF 로드
    print("\n[1] PDF 로딩...")
    docs, loader_name = load_pdf(file_path)

    print(f"   로더: {loader_name}")
    print(f"   문서 수: {len(docs)}개")

    # 처음 10개 문서의 페이지 확인
    print(f"\n처음 10개 문서의 페이지 정보:")
    print(f"{'─'*70}")

    for i, doc in enumerate(docs[:10], 1):
        page = doc.metadata.get("page", "NONE")
        text_len = len(doc.page_content)
        text_sample = doc.page_content[:50].replace("\n", " ")

        print(f"[{i}] page={page} | {text_len}자 | {text_sample}...")

    # 2. 청킹 테스트 (현재 방식)
    print(f"\n{'─'*70}")
    print("[2] 청킹 테스트 - 전체 문서 한번에")
    print(f"{'─'*70}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )

    chunks_bad = splitter.split_documents(docs)

    print(f"   청크 수: {len(chunks_bad)}개")
    print(f"\n처음 10개 청크의 페이지 정보:")

    for i, chunk in enumerate(chunks_bad[:10], 1):
        page = chunk.metadata.get("page", "NONE")
        text_len = len(chunk.page_content)
        text_sample = chunk.page_content[:50].replace("\n", " ")

        print(f"[{i}] page={page} | {text_len}자 | {text_sample}...")

    # 페이지 분포
    page_counts_bad = {}
    for chunk in chunks_bad:
        page = chunk.metadata.get("page", -1)
        page_counts_bad[page] = page_counts_bad.get(page, 0) + 1

    print(f"\n페이지 분포:")
    for page in sorted(page_counts_bad.keys())[:10]:
        print(f"   page {page}: {page_counts_bad[page]}개")

    # 3. 청킹 테스트 (개별 문서)
    print(f"\n{'─'*70}")
    print("[3] 청킹 테스트 - 각 문서 개별 청킹")
    print(f"{'─'*70}")

    chunks_good = []

    for doc in docs:
        doc_chunks = splitter.split_documents([doc])

        # 페이지 정보 보존
        original_page = doc.metadata.get("page", 0)
        for chunk in doc_chunks:
            chunk.metadata["page"] = original_page

        chunks_good.extend(doc_chunks)

    print(f"   청크 수: {len(chunks_good)}개")
    print(f"\n처음 10개 청크의 페이지 정보:")

    for i, chunk in enumerate(chunks_good[:10], 1):
        page = chunk.metadata.get("page", "NONE")
        text_len = len(chunk.page_content)
        text_sample = chunk.page_content[:50].replace("\n", " ")

        print(f"[{i}] page={page} | {text_len}자 | {text_sample}...")

    # 페이지 분포
    page_counts_good = {}
    for chunk in chunks_good:
        page = chunk.metadata.get("page", -1)
        page_counts_good[page] = page_counts_good.get(page, 0) + 1

    print(f"\n페이지 분포 (처음 20페이지):")
    for page in sorted(page_counts_good.keys())[:20]:
        print(f"   page {page}: {page_counts_good[page]}개")

    # 4. 비교
    print(f"\n{'='*70}")
    print("결과 비교")
    print(f"{'='*70}")

    print(f"\n[전체 청킹] 페이지 종류: {len(page_counts_bad)}개")
    print(f"   {list(sorted(page_counts_bad.keys())[:10])}")

    print(f"\n[개별 청킹] 페이지 종류: {len(page_counts_good)}개")
    print(f"   {list(sorted(page_counts_good.keys())[:10])}")

    if len(page_counts_good) > len(page_counts_bad):
        print(f"\n✅ 개별 청킹이 페이지 정보를 더 잘 보존합니다!")
    else:
        print(f"\n⚠️  여전히 문제가 있습니다.")


if __name__ == "__main__":
    test_chunking_page_preservation()
