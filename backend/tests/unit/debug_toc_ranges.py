"""
목차와 컬렉션 범위 디버깅

문제: 모든 청크가 Cover Page에 저장됨
원인: 컬렉션 페이지 범위 설정 오류 추정
"""

from backend.preprocessor.document_processor import process_pdf
from backend.preprocessor.qdrant_manager import QdrantManager


def debug_toc_and_collections():
    """목차와 컬렉션 범위 확인"""

    file_path = "./data/_10-K-Q4-2023-As-Filed.pdf"

    print("=" * 70)
    print("🔍 목차 및 컬렉션 범위 디버깅")
    print("=" * 70)

    # 1. 문서 처리 (목차 추출 포함)
    print("\n[1/3] 문서 처리 중...")
    chunks, config, metadata = process_pdf(
        file_path, auto_optimize=False, verbose=False
    )

    toc = metadata.get("toc", [])

    print(f"\n총 청크: {len(chunks)}개")
    print(f"목차 항목: {len(toc)}개")

    # 2. 목차 확인 (처음 20개)
    print(f"\n{'─'*70}")
    print("목차 (처음 20개):")
    print(f"{'─'*70}")
    print(f"{'번호':<5} {'제목':<40} {'페이지':>8}")
    print(f"{'─'*70}")

    for i, item in enumerate(toc[:20], 1):
        title = item["title"][:40]
        page = item["page"]
        print(f"{i:<5} {title:<40} {page:>8}")

    if len(toc) > 20:
        print(f"... (외 {len(toc) - 20}개)")

    # 3. 컬렉션 범위 계산 (QdrantManager 로직 재현)
    print(f"\n{'─'*70}")
    print("컬렉션 범위 (처음 20개):")
    print(f"{'─'*70}")
    print(f"{'번호':<5} {'제목':<35} {'시작':>6} {'끝':>8}")
    print(f"{'─'*70}")

    manager = QdrantManager()
    doc_name = "10-k-q4-2023-as-filed"

    # _determine_collections 로직 재현
    collections = manager._determine_collections(doc_name, toc)

    for i, col in enumerate(collections[:20], 1):
        title = col["title"][:35]
        page_start = col["page_start"]
        page_end = col["page_end"]

        # 999999 대신 "끝"으로 표시
        if page_end == 999999:
            page_end_str = "끝"
        else:
            page_end_str = str(page_end)

        print(f"{i:<5} {title:<35} {page_start:>6} {page_end_str:>8}")

    if len(collections) > 20:
        print(f"... (외 {len(collections) - 20}개)")

    # 4. 청크 페이지 분포 확인
    print(f"\n{'─'*70}")
    print("청크 페이지 분포:")
    print(f"{'─'*70}")

    page_counts = {}
    for chunk in chunks:
        page = chunk.metadata.get("page", -1)
        page_counts[page] = page_counts.get(page, 0) + 1

    # 정렬
    sorted_pages = sorted(page_counts.items())

    print(f"{'페이지':<10} {'청크 수':>10}")
    print(f"{'─'*25}")

    for page, count in sorted_pages[:30]:  # 처음 30페이지만
        print(f"{page:<10} {count:>10}개")

    if len(sorted_pages) > 30:
        print(f"... (외 {len(sorted_pages) - 30}개)")

    print(f"\n총 페이지 범위: {min(page_counts.keys())} ~ {max(page_counts.keys())}")

    # 5. 할당 시뮬레이션
    print(f"\n{'─'*70}")
    print("청크 할당 시뮬레이션 (처음 10개 청크):")
    print(f"{'─'*70}")

    for i, chunk in enumerate(chunks[:10], 1):
        page = chunk.metadata.get("page", -1)
        text = chunk.page_content[:50]

        # 어느 컬렉션에 할당되는지 확인
        assigned_col = None
        for col in collections:
            if col["page_start"] <= page <= col["page_end"]:
                assigned_col = col["title"]
                break

        print(f"\n[{i}] 페이지: {page}")
        print(f"    텍스트: {text}...")
        print(f"    할당: {assigned_col if assigned_col else '❌ 할당 안 됨'}")

    # 6. 문제 진단
    print(f"\n{'='*70}")
    print("🔎 문제 진단")
    print(f"{'='*70}")

    # Cover Page 범위 확인
    cover_page_col = collections[0] if collections else None
    if cover_page_col:
        print(f"\nCover Page 컬렉션:")
        print(f"  - 제목: {cover_page_col['title']}")
        print(
            f"  - 페이지 범위: {cover_page_col['page_start']} ~ {cover_page_col['page_end']}"
        )

        # 범위 내 청크 수 계산
        in_range = sum(
            1
            for chunk in chunks
            if cover_page_col["page_start"]
            <= chunk.metadata.get("page", -1)
            <= cover_page_col["page_end"]
        )

        print(f"  - 범위 내 청크: {in_range}개 / {len(chunks)}개")

        if in_range == len(chunks):
            print(f"\n❌ 문제 발견: Cover Page 범위가 너무 넓습니다!")
            print(f"   모든 청크가 이 범위 안에 들어갑니다.")

            if cover_page_col["page_end"] == 999999:
                print(f"\n원인: page_end가 999999로 설정됨 (마지막 섹션으로 인식)")
                print(f"해결: 목차 항목이 1개뿐일 가능성 → 목차 추출 재확인 필요")


if __name__ == "__main__":
    debug_toc_and_collections()
