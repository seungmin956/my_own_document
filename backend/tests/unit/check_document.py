from backend.preprocessor.qdrant_manager import QdrantManager

qdrant = QdrantManager(
    host="localhost",
    port=6333,
    api_key="my-secure-portfolio-key-2025",
    embedding_dimension=1024,
)

# SPRI 컬렉션 찾기
collection_name = "spri_ai_brief_2023년12월호_f_main"

print(f"검색 컬렉션: {collection_name}\n")

# 모든 포인트 가져오기
points = qdrant.client.scroll(
    collection_name=collection_name,
    limit=1000,  # 충분히 큰 값
    with_payload=True,
    with_vectors=False,
)[0]

print(f"총 포인트 수: {len(points)}\n")

# p.12, p.13 내용 확인
for page_num in [12, 13]:
    print(f"\n{'='*70}")
    print(f"[p.{page_num} 내용]")
    print("=" * 70)

    page_points = [p for p in points if p.payload.get("page") == page_num]

    if page_points:
        for i, point in enumerate(page_points, 1):
            print(f"\n--- 청크 {i} ---")
            print(f"섹션: {point.payload.get('toc_section', 'N/A')}")
            print(f"\n텍스트:")
            print(point.payload.get("text", "N/A")[:500])
            print("...")
    else:
        print(f"p.{page_num}에 해당하는 내용이 없습니다.")
