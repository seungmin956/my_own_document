"""
청크 메타데이터 확인

문제: Qdrant에 데이터가 저장 안 됨
원인: 청크의 page 정보가 제대로 전달되지 않음
"""

from backend.preprocessor.document_processor import process_pdf


def check_chunk_metadata():
    """청크 메타데이터 확인"""

    # PDF 처리
    file_path = "./data/_10-K-Q4-2023-As-Filed.pdf"

    print("=" * 70)
    print("🔍 청크 메타데이터 확인")
    print("=" * 70)

    chunks, config, metadata = process_pdf(
        file_path, auto_optimize=False, verbose=False  # 빠른 테스트
    )

    print(f"\n총 청크 수: {len(chunks)}")
    print(f"목차 항목 수: {metadata.get('toc_items_count', 0)}")

    # 처음 10개 청크 메타데이터 확인
    print(f"\n{'─'*70}")
    print("처음 10개 청크 메타데이터:")
    print(f"{'─'*70}")

    for i, chunk in enumerate(chunks[:10], 1):
        # Document 객체
        if hasattr(chunk, "page_content"):
            text = chunk.page_content
            meta = chunk.metadata if hasattr(chunk, "metadata") else {}
        else:
            # dict
            text = chunk.get("text", "")
            meta = chunk.get("metadata", {})

        print(f"\n[{i}] 텍스트 길이: {len(text)}자")
        print(f"    메타데이터 키: {list(meta.keys())}")
        print(f"    page: {meta.get('page', 'MISSING!')}")
        print(f"    source: {meta.get('source', 'N/A')}")
        print(f"    텍스트 샘플: {text[:100]}...")

    # 페이지 번호 분포 확인
    print(f"\n{'─'*70}")
    print("페이지 번호 분포:")
    print(f"{'─'*70}")

    pages = []
    missing_page = 0

    for chunk in chunks:
        if hasattr(chunk, "metadata"):
            page = chunk.metadata.get("page")
            if page is None:
                missing_page += 1
            else:
                pages.append(page)

    print(f"총 청크: {len(chunks)}개")
    print(f"page 있음: {len(pages)}개")
    print(f"page 없음: {missing_page}개")

    if pages:
        print(f"페이지 범위: {min(pages)} ~ {max(pages)}")
        print(f"평균 페이지: {sum(pages) / len(pages):.1f}")

    return chunks, metadata


if __name__ == "__main__":
    chunks, metadata = check_chunk_metadata()
