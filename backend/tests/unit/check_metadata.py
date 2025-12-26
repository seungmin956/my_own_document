"""
단일 컬렉션의 메타데이터 확인

목차 정보가 제대로 저장되었는지 확인
"""

from qdrant_client import QdrantClient


def check_metadata():
    """메타데이터 확인"""

    client = QdrantClient(
        host="localhost",
        port=6333,
        api_key="my-secure-portfolio-key-2025",
        prefer_grpc=False,
        https=False,
    )

    collection_name = "10-k-q4-2023-as-filed_main"

    print("=" * 70)
    print(f"📊 메타데이터 확인: {collection_name}")
    print("=" * 70)

    # 샘플 데이터 가져오기
    scroll_result = client.scroll(
        collection_name=collection_name, limit=20, with_payload=True, with_vectors=False
    )

    points = scroll_result[0]

    print(f"\n총 포인트: {len(points)}개 (샘플)")

    # 목차 섹션별 그룹화
    sections = {}
    for point in points:
        section = point.payload.get("toc_section", "Unknown")
        sections[section] = sections.get(section, 0) + 1

    print(f"\n발견된 섹션: {len(sections)}개")
    print(f"\n{'─'*70}")
    print(f"{'섹션 이름':<50} {'청크 수':>10}")
    print(f"{'─'*70}")

    for section, count in sorted(sections.items(), key=lambda x: x[1], reverse=True):
        section_display = section if section else "(섹션 정보 없음)"
        print(f"{section_display:<50} {count:>10}개")

    # 상세 샘플 (5개)
    print(f"\n{'─'*70}")
    print("상세 샘플 (5개):")
    print(f"{'─'*70}")

    for i, point in enumerate(points[:5], 1):
        payload = point.payload

        print(f"\n[{i}]")
        print(f"  페이지: {payload.get('page', 'N/A')}")
        print(f"  목차 섹션: {payload.get('toc_section', 'N/A')}")
        print(f"  목차 레벨: {payload.get('toc_level', 'N/A')}")
        print(f"  목차 페이지: {payload.get('toc_page', 'N/A')}")
        print(f"  텍스트 길이: {len(payload.get('text', ''))}자")
        print(f"  텍스트 샘플: {payload.get('text', '')[:100]}...")

    print(f"\n{'='*70}")
    print("✅ 메타데이터 확인 완료!")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    check_metadata()
