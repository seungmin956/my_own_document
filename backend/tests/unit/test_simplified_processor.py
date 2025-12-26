"""
단순화된 document_processor.py 테스트
"""

from pathlib import Path
from backend.preprocessor.document_processor import process_pdf


def test_basic():
    """기본 처리 테스트"""
    print("\n" + "=" * 70)
    print("[TEST] 단순화된 document_processor 테스트")
    print("=" * 70 + "\n")

    test_file = "./data/form10-k.pdf"

    if not Path(test_file).exists():
        print(f"[ERROR] 테스트 파일 없음: {test_file}")
        print("다음 파일 중 하나를 준비하세요:")
        print("  - ./data/form10-k.pdf")
        print("  - ./data/SPRI_AI_Brief_2023년12월호_F.pdf")
        return

    try:
        # auto_optimize=True로 3가지 설정 테스트
        print("[MODE] auto_optimize=True (3가지 설정 테스트)\n")
        chunks, config, metadata = process_pdf(
            test_file, auto_optimize=True, verbose=True
        )

        print(f"\n[RESULT] 처리 완료!")
        print(f"  청크 수: {len(chunks)}")
        print(f"  최적 설정: {config.config_name}")
        print(f"  크기/오버랩: {config.chunk_size}/{config.chunk_overlap}")
        print(f"  점수: {config.score:.1f}")
        print(f"  목차: {metadata['toc_items_count']}개 항목")

        # 첫 번째 청크 미리보기
        if chunks:
            print(f"\n[PREVIEW] 첫 번째 청크:")
            preview = chunks[0].page_content[:200]
            try:
                print(f"  {preview}...")
            except UnicodeEncodeError:
                safe_preview = preview.encode("ascii", errors="replace").decode("ascii")
                print(f"  {safe_preview}...")

    except Exception as e:
        print(f"\n[ERROR] 테스트 실패: {e}")
        import traceback

        traceback.print_exc()


def test_no_optimize():
    """최적화 없이 표준형 사용"""
    print("\n" + "=" * 70)
    print("[TEST] auto_optimize=False (표준형 사용)")
    print("=" * 70 + "\n")

    test_file = "./data/form10-k.pdf"

    if not Path(test_file).exists():
        print(f"[SKIP] 테스트 파일 없음: {test_file}")
        return

    try:
        chunks, config, metadata = process_pdf(
            test_file, auto_optimize=False, verbose=True
        )

        print(f"\n[RESULT] 처리 완료!")
        print(f"  청크 수: {len(chunks)}")
        print(f"  설정: {config.config_name}")
        print(f"  크기/오버랩: {config.chunk_size}/{config.chunk_overlap}")

    except Exception as e:
        print(f"\n[ERROR] 테스트 실패: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # 기본 테스트
    test_basic()

    # 표준형 테스트
    # test_no_optimize()
