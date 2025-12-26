"""
컬렉션별 데이터 분포 확인

어느 컬렉션에 몇 개의 청크가 저장되었는지 확인
"""

from qdrant_client import QdrantClient


def check_collection_distribution():
    """컬렉션별 포인트 수 확인"""

    client = QdrantClient(
        host="localhost",
        port=6333,
        api_key="my-secure-portfolio-key-2025",
        prefer_grpc=False,
        https=False,
    )

    print("=" * 70)
    print("📊 컬렉션별 데이터 분포")
    print("=" * 70)

    # 전체 컬렉션
    collections = client.get_collections()
    collection_names = [c.name for c in collections.collections]

    # 10-K 관련 컬렉션만 필터
    apple_collections = [c for c in collection_names if "10-k" in c.lower()]

    print(f"\n10-K 관련 컬렉션: {len(apple_collections)}개\n")

    # 포인트 수 확인
    distribution = []

    for col_name in apple_collections:
        try:
            info = client.get_collection(col_name)
            points_count = info.points_count

            if points_count > 0:
                distribution.append({"name": col_name, "points": points_count})
        except:
            pass

    # 정렬 (포인트 많은 순)
    distribution.sort(key=lambda x: x["points"], reverse=True)

    # 출력
    total_points = sum(d["points"] for d in distribution)

    print(f"총 포인트 수: {total_points}개")
    print(f"데이터 있는 컬렉션: {len(distribution)}개")
    print(f"빈 컬렉션: {len(apple_collections) - len(distribution)}개\n")

    print(f"{'─'*70}")
    print(f"{'컬렉션 이름':<50} {'포인트 수':>10}")
    print(f"{'─'*70}")

    for d in distribution[:20]:  # 상위 20개만
        name_short = d["name"][-47:] if len(d["name"]) > 47 else d["name"]
        print(f"{name_short:<50} {d['points']:>10}개")

    if len(distribution) > 20:
        print(f"... (외 {len(distribution) - 20}개)")

    print(f"{'─'*70}\n")

    # Company Background 찾기
    print("🔎 'Company Background' 컬렉션 검색:")
    background_cols = [
        d
        for d in distribution
        if "background" in d["name"].lower() or "company" in d["name"].lower()
    ]

    if background_cols:
        for col in background_cols:
            print(f"   ✅ {col['name']}: {col['points']}개 포인트")

            # 샘플 데이터 확인
            scroll_result = client.scroll(
                collection_name=col["name"],
                limit=2,
                with_payload=True,
                with_vectors=False,
            )

            points = scroll_result[0]
            if points:
                print(f"\n   [샘플 데이터]")
                for i, point in enumerate(points, 1):
                    text = point.payload.get("text", "")[:150]
                    page = point.payload.get("page", "N/A")
                    print(f"   [{i}] p.{page}: {text}...")
    else:
        print(f"   ❌ 'Company Background' 컬렉션을 찾을 수 없음")

    return distribution


def check_cover_page_content():
    """Cover Page에 뭐가 저장되었는지 확인"""

    client = QdrantClient(
        host="localhost",
        port=6333,
        api_key="my-secure-portfolio-key-2025",
        prefer_grpc=False,
        https=False,
    )

    print(f"\n{'='*70}")
    print("📄 Cover Page 컬렉션 내용 확인")
    print(f"{'='*70}\n")

    # Cover Page 컬렉션 찾기
    collections = client.get_collections()
    collection_names = [c.name for c in collections.collections]

    cover_cols = [c for c in collection_names if "cover" in c.lower()]

    if not cover_cols:
        print("Cover Page 컬렉션 없음")
        return

    for col_name in cover_cols[:2]:  # 처음 2개만
        print(f"컬렉션: {col_name}")

        info = client.get_collection(col_name)
        print(f"포인트 수: {info.points_count}개\n")

        # 전체 데이터 확인
        scroll_result = client.scroll(
            collection_name=col_name, limit=100, with_payload=True, with_vectors=False
        )

        points = scroll_result[0]

        if points:
            print(f"[처음 5개 청크]")
            for i, point in enumerate(points[:5], 1):
                text = point.payload.get("text", "")
                page = point.payload.get("page", "N/A")

                print(f"\n[{i}] 페이지: {page} | 길이: {len(text)}자")
                print(f"    {text[:200]}...")


if __name__ == "__main__":
    # 1. 전체 분포
    distribution = check_collection_distribution()

    # 2. Cover Page 상세
    check_cover_page_content()
