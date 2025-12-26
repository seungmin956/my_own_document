"""
Qdrant Manager 테스트

qdrant_manager.py의 기능을 테스트합니다.
"""

from pathlib import Path
from backend.preprocessor.qdrant_manager import QdrantManager
from backend.preprocessor.document_processor import process_pdf
from backend.preprocessor.embedding_generator import EmbeddingGenerator


def test_connection():
    """Qdrant 연결 테스트"""
    print("\n" + "=" * 70)
    print("[TEST 1] Qdrant 연결 테스트")
    print("=" * 70 + "\n")

    try:
        # API 키 설정 (config/qdrant.yaml의 api_key 사용)
        manager = QdrantManager(host="localhost", port=6333, api_key="my-secure-portfolio-key-2025")
        collections = manager.list_collections()

        print(f"[OK] Qdrant 연결 성공")
        print(f"   기존 컬렉션 수: {len(collections)}")

        if collections:
            print("\n기존 컬렉션 목록:")
            for col in collections[:10]:
                print(f"   - {col}")
            if len(collections) > 10:
                print(f"   ... (외 {len(collections) - 10}개)")

        return manager

    except Exception as e:
        print(f"[ERROR] Qdrant 연결 실패: {e}")
        print("\nQdrant가 실행 중인지 확인하세요:")
        print("   docker ps | grep qdrant")
        return None


def test_collection_naming():
    """컬렉션 이름 정제 테스트"""
    print("\n" + "=" * 70)
    print("[TEST 2] 컬렉션 이름 정제 테스트")
    print("=" * 70 + "\n")

    manager = QdrantManager(api_key="my-secure-portfolio-key-2025", verbose=False)

    test_cases = [
        "SPRI_AI_Brief_2023년12월호_F.pdf",
        "_10-K-Q4-2023-As-Filed.pdf",
        "form10-k.pdf",
        "2004.04686v1.pdf",
        "Document with Spaces.pdf",
        "Special@#$%Characters!.pdf",
    ]

    print("파일명 -> 컬렉션 베이스 이름 변환:")
    for name in test_cases:
        sanitized = manager._sanitize_collection_name(name)
        print(f"   {name:<45} -> {sanitized}")


def test_single_document(file_path: str, manager: QdrantManager):
    """단일 문서 저장 테스트"""
    print("\n" + "=" * 70)
    print(f"[TEST 3] 문서 저장 테스트: {Path(file_path).name}")
    print("=" * 70 + "\n")

    if not Path(file_path).exists():
        print(f"[ERROR] 파일 없음: {file_path}")
        return None

    try:
        # 1. 문서 처리
        print("[1/3] 문서 처리 중...")
        chunks, config, metadata = process_pdf(file_path, auto_optimize=False, verbose=False)

        print(f"   청크 수: {len(chunks)}")
        print(f"   목차 존재: {metadata.get('has_toc', False)}")
        if metadata.get("toc"):
            print(f"   목차 항목 수: {len(metadata['toc'])}")

        # 2. 임베딩 생성
        print("\n[2/3] 임베딩 생성 중...")
        generator = EmbeddingGenerator(mode="local", model="bge-m3", verbose=False)

        # chunks는 Document 객체 리스트
        texts = [chunk.page_content for chunk in chunks]
        embeddings = generator.embed_documents(texts)

        print(f"   임베딩 생성 완료: {len(embeddings)}개")
        print(f"   임베딩 차원: {len(embeddings[0])}")

        # 3. Qdrant 저장
        print("\n[3/3] Qdrant 저장 중...")
        result = manager.store_document(
            chunks=chunks,
            metadata=metadata,
            embeddings=embeddings,
            doc_name=Path(file_path).name,
        )

        # 결과 출력
        print("\n" + "-" * 70)
        print("[결과 요약]")
        print("-" * 70)
        print(f"문서 이름: {result['doc_name']}")
        print(f"전체 청크: {result['total_points']}개")
        print(f"생성된 컬렉션: {len(result['collections'])}개")
        print(f"목차 기반 분리: {'O' if result['has_toc'] else 'X'}")

        if result["has_toc"]:
            print(f"\n컬렉션별 포인트 수:")
            for col_name, count in result["collection_points"].items():
                print(f"   {col_name}: {count}개")

        return result

    except Exception as e:
        print(f"\n[ERROR] 테스트 실패: {e}")
        import traceback

        traceback.print_exc()
        return None


def test_search(manager: QdrantManager, doc_name: str):
    """검색 테스트"""
    print("\n" + "=" * 70)
    print(f"[TEST 4] 검색 테스트: {doc_name}")
    print("=" * 70 + "\n")

    try:
        # 테스트 쿼리
        queries = [
            "인공지능 기술의 발전",
            "AI technology development",
            "financial statements and revenue",
        ]

        # 임베딩 생성기
        generator = EmbeddingGenerator(mode="local", model="bge-m3", verbose=False)

        # 문서의 컬렉션 찾기
        doc_collections = manager.list_collections(doc_name)

        if not doc_collections:
            print(f"[WARN] 문서의 컬렉션이 없습니다: {doc_name}")
            return

        print(f"검색 대상 컬렉션: {len(doc_collections)}개")
        for col in doc_collections[:5]:
            print(f"   - {col}")
        if len(doc_collections) > 5:
            print(f"   ... (외 {len(doc_collections) - 5}개)")

        # 각 쿼리로 검색
        for query in queries:
            print(f"\n{'='*70}")
            print(f"[QUERY] {query}")
            print(f"{'='*70}\n")

            # 쿼리 임베딩
            query_embedding = generator.embed_query(query)

            # 검색
            results = manager.search(
                query_vector=query_embedding,
                collection_names=doc_collections,
                limit=3,
                score_threshold=0.5,
            )

            if not results:
                print("   [결과 없음]\n")
                continue

            # 결과 출력
            for i, result in enumerate(results, 1):
                print(f"{i}. [점수: {result['score']:.3f}]")
                text = result["text"][:150]
                try:
                    print(f"   {text}...")
                except UnicodeEncodeError:
                    safe_text = text.encode('ascii', errors='replace').decode('ascii')
                    print(f"   {safe_text}...")

                print(f"   출처: {result['metadata']['toc_title']} (p.{result['metadata']['page']})")
                print(f"   컬렉션: {result['collection']}")
                print()

    except Exception as e:
        print(f"[ERROR] 검색 실패: {e}")
        import traceback

        traceback.print_exc()


def test_delete(manager: QdrantManager, doc_name: str):
    """문서 삭제 테스트"""
    print("\n" + "=" * 70)
    print(f"[TEST 5] 문서 삭제 테스트: {doc_name}")
    print("=" * 70 + "\n")

    try:
        # 삭제 전 컬렉션 확인
        before = manager.list_collections(doc_name)
        print(f"삭제 전 컬렉션 수: {len(before)}")

        # 삭제
        deleted = manager.delete_document(doc_name)

        # 삭제 후 확인
        after = manager.list_collections(doc_name)
        print(f"삭제 후 컬렉션 수: {len(after)}")

        print(f"\n[OK] {deleted}개 컬렉션 삭제 완료")

    except Exception as e:
        print(f"[ERROR] 삭제 실패: {e}")


def test_full_pipeline():
    """전체 파이프라인 통합 테스트"""
    print("\n" + "=" * 70)
    print("[FULL PIPELINE] 전체 통합 테스트")
    print("=" * 70)

    # 테스트 파일
    test_files = [
        "./data/SPRI_AI_Brief_2023년12월호_F.pdf",
        "./data/form10-k.pdf",
    ]

    # 1. 연결 테스트
    manager = test_connection()
    if manager is None:
        print("\n[ABORT] Qdrant 연결 실패로 테스트 중단")
        return

    # 2. 이름 정제 테스트
    test_collection_naming()

    # 3. 각 파일 처리
    results = []

    for file_path in test_files:
        if not Path(file_path).exists():
            print(f"\n[SKIP] 파일 없음: {file_path}")
            continue

        # 문서 저장
        result = test_single_document(file_path, manager)

        if result:
            results.append(result)

            # 검색 테스트
            test_search(manager, result["doc_name"])

            # 삭제는 마지막에만
            # test_delete(manager, result["doc_name"])

    # 전체 요약
    print("\n" + "=" * 70)
    print("[SUMMARY] 전체 테스트 요약")
    print("=" * 70)

    for result in results:
        status = "[O]" if result else "[X]"
        total = result["total_points"] if result else 0
        collections = len(result["collections"]) if result else 0

        print(
            f"{status} {result['doc_name']:<45} | {total:3d}개 청크, {collections:2d}개 컬렉션"
        )

    print("\n" + "=" * 70)
    print("[DONE] 테스트 완료!")
    print("=" * 70 + "\n")


def test_simple():
    """간단한 테스트 (빠른 확인용)"""
    print("\n" + "=" * 70)
    print("[SIMPLE TEST] 빠른 확인 테스트")
    print("=" * 70)

    # 연결만 확인
    manager = test_connection()

    if manager:
        # 컬렉션 이름 테스트
        test_collection_naming()

        # 하나의 파일만 테스트
        test_file = "./data/form10-k.pdf"

        if Path(test_file).exists():
            result = test_single_document(test_file, manager)

            if result:
                test_search(manager, result["doc_name"])

                # 삭제 테스트 (선택적)
                user_input = input("\n컬렉션을 삭제하시겠습니까? (y/N): ")
                if user_input.lower() == "y":
                    test_delete(manager, result["doc_name"])
        else:
            print(f"\n[ERROR] 테스트 파일 없음: {test_file}")
            print("다음 경로에 PDF 파일을 준비하세요:")
            print("   ./data/form10-k.pdf")
            print("   ./data/SPRI_AI_Brief_2023년12월호_F.pdf")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--full":
        # 전체 테스트
        test_full_pipeline()
    else:
        # 간단한 테스트 (기본)
        test_simple()


"""
사용법:

# 간단한 테스트 (기본)
python test_qdrant_manager.py

# 전체 테스트
python test_qdrant_manager.py --full

# 특정 파일만 테스트 (코드 수정 필요)
# test_simple() 함수의 test_file 변수 수정
"""
