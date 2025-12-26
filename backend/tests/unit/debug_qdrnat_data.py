"""
Qdrant에 저장된 실제 데이터 확인

목적:
1. 컬렉션별 청크 크기 확인
2. 실제 텍스트 내용 샘플 확인
3. 페이지 분포 확인
"""

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue


def analyze_collections():
    """Qdrant 컬렉션 분석"""
    client = QdrantClient(
        host="localhost",
        port=6333,
        api_key="my-secure-portfolio-key-2025",
        prefer_grpc=False,
        https=False,
    )

    print("=" * 70)
    print("🔍 Qdrant 컬렉션 분석")
    print("=" * 70)

    # 전체 컬렉션 목록
    collections = client.get_collections()
    collection_names = [c.name for c in collections.collections]

    print(f"\n총 컬렉션 수: {len(collection_names)}")
    print()

    # 각 컬렉션 분석
    for col_name in collection_names[:10]:  # 처음 10개만
        print(f"\n{'─'*70}")
        print(f"📁 컬렉션: {col_name}")
        print(f"{'─'*70}")

        try:
            # 컬렉션 정보
            collection_info = client.get_collection(col_name)
            print(f"   포인트 수: {collection_info.points_count}")

            # 샘플 데이터 가져오기 (처음 3개)
            scroll_result = client.scroll(
                collection_name=col_name, limit=3, with_payload=True, with_vectors=False
            )

            points = scroll_result[0]

            if not points:
                print("   ⚠️  포인트 없음")
                continue

            print(f"\n   [샘플 데이터]")

            for i, point in enumerate(points, 1):
                payload = point.payload
                text = payload.get("text", "")
                page = payload.get("page", "N/A")
                chunk_idx = payload.get("chunk_index", "N/A")
                toc_title = payload.get("toc_title", "N/A")

                print(f"\n   [{i}] 청크 인덱스: {chunk_idx} | 페이지: {page}")
                print(f"       목차: {toc_title}")
                print(f"       텍스트 길이: {len(text)}자")
                print(f"       텍스트 샘플 (200자):")
                print(f"       {text[:200]}...")

        except Exception as e:
            print(f"   ❌ 오류: {e}")


def analyze_specific_collection(collection_name: str):
    """특정 컬렉션 상세 분석"""
    client = QdrantClient(
        host="localhost",
        port=6333,
        api_key="my-secure-portfolio-key-2025",
        prefer_grpc=False,
        https=False,
    )

    print(f"\n{'='*70}")
    print(f"📊 컬렉션 상세 분석: {collection_name}")
    print(f"{'='*70}")

    try:
        # 전체 데이터 가져오기
        scroll_result = client.scroll(
            collection_name=collection_name,
            limit=1000,  # 최대 1000개
            with_payload=True,
            with_vectors=False,
        )

        points = scroll_result[0]

        if not points:
            print("포인트 없음")
            return

        # 통계 수집
        text_lengths = []
        pages = []

        for point in points:
            payload = point.payload
            text = payload.get("text", "")
            page = payload.get("page", 0)

            text_lengths.append(len(text))
            pages.append(page)

        # 통계 출력
        print(f"\n총 청크 수: {len(points)}")
        print(f"\n[텍스트 길이 통계]")
        print(f"   평균: {sum(text_lengths) / len(text_lengths):.0f}자")
        print(f"   최소: {min(text_lengths)}자")
        print(f"   최대: {max(text_lengths)}자")

        print(f"\n[페이지 분포]")
        print(f"   최소 페이지: {min(pages)}")
        print(f"   최대 페이지: {max(pages)}")
        print(f"   범위: p.{min(pages)} ~ p.{max(pages)}")

        # 텍스트 샘플 (처음 5개)
        print(f"\n[처음 5개 청크 샘플]")
        for i, point in enumerate(points[:5], 1):
            payload = point.payload
            text = payload.get("text", "")
            page = payload.get("page", 0)

            print(f"\n   [{i}] p.{page} | {len(text)}자")
            print(f"       {text[:150]}...")

    except Exception as e:
        print(f"❌ 오류: {e}")


def check_company_background():
    """'Company Background' 컬렉션 확인"""
    client = QdrantClient(
        host="localhost",
        port=6333,
        api_key="my-secure-portfolio-key-2025",
        prefer_grpc=False,
        https=False,
    )

    print(f"\n{'='*70}")
    print("🔎 'Company Background' 컬렉션 검색")
    print(f"{'='*70}")

    # 컬렉션 목록에서 찾기
    collections = client.get_collections()
    collection_names = [c.name for c in collections.collections]

    background_collections = [
        c
        for c in collection_names
        if "background" in c.lower() or "company" in c.lower()
    ]

    print(f"\n발견된 컬렉션: {len(background_collections)}개")
    for col in background_collections:
        print(f"   - {col}")

    if background_collections:
        # 첫 번째 컬렉션 상세 분석
        analyze_specific_collection(background_collections[0])


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # 특정 컬렉션 분석
        collection_name = sys.argv[1]
        analyze_specific_collection(collection_name)
    else:
        # 전체 분석
        analyze_collections()

        # Company Background 상세 분석
        check_company_background()


"""
사용법:

# 전체 컬렉션 개요
python debug_qdrant_data.py

# 특정 컬렉션 상세 분석
python debug_qdrant_data.py "10-k-q4-2023-as-filed_s05_company_background"
"""
