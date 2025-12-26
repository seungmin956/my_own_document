"""
목차 추출 통합 테스트

toc_extractor.py의 기능을 테스트합니다.
"""

from pathlib import Path
from toc_extractor import TOCExtractor, extract_toc


def test_single_file(file_path: str):
    """단일 파일 목차 추출 테스트"""
    print(f"\n{'='*70}")
    print(f"[FILE] {Path(file_path).name}")
    print(f"{'='*70}\n")

    if not Path(file_path).exists():
        print(f"[ERROR] 파일 없음: {file_path}\n")
        return None

    # 목차 추출
    extractor = TOCExtractor()
    toc = extractor.extract(file_path)

    # 결과 출력
    if toc:
        print(f"\n[SUCCESS] 추출 성공: {len(toc)}개 항목")
        print(f"   출처: {toc[0]['source']}")
        print(f"\n{'-'*70}")
        print("목차 내용:")
        print(f"{'-'*70}")

        for i, item in enumerate(toc, 1):
            level = item.get("level", 1)
            indent = "  " * (level - 1)
            marker = "[*]" if level == 1 else " > "

            title = item['title'][:50] if len(item['title']) > 50 else item['title']
            try:
                print(
                    f"{i:3d}. {indent}{marker} {title:<50} -> Page {item['page']:3d}"
                )
            except UnicodeEncodeError:
                # 특수 문자 안전하게 처리
                safe_title = title.encode('ascii', errors='replace').decode('ascii')
                print(
                    f"{i:3d}. {indent}{marker} {safe_title:<50} -> Page {item['page']:3d}"
                )

            # 처음 20개만 출력
            if i >= 20 and len(toc) > 20:
                print(f"     ... (외 {len(toc) - 20}개 항목)")
                break
    else:
        print("\n[FAIL] 목차 추출 실패")

    print()
    return toc


def test_all_files():
    """전체 테스트 파일 목차 추출"""
    test_files = [
        "./data/SPRI_AI_Brief_2023년12월호_F.pdf",
        "./data/2004.04686v1.pdf",
        "./data/form10-k.pdf",
        "./data/_10-K-Q4-2023-As-Filed.pdf",
    ]

    print("\n" + "=" * 70)
    print("[TEST] 목차 추출 전체 테스트")
    print("=" * 70)

    results = []

    for file_path in test_files:
        toc = test_single_file(file_path)
        results.append(
            {
                "file": Path(file_path).name,
                "toc": toc,
                "count": len(toc) if toc else 0,
                "has_toc": toc is not None,
            }
        )

    # 요약
    print("\n" + "=" * 70)
    print("[SUMMARY] 전체 결과 요약")
    print("=" * 70)

    for result in results:
        status = "[O]" if result["has_toc"] else "[X]"
        count_str = f"{result['count']:3d}개" if result["has_toc"] else "없음   "

        print(f"{status} {result['file']:<45} | {count_str}")

    # 통계
    success = sum(1 for r in results if r["has_toc"])
    total = len(results)

    print(f"\n성공률: {success}/{total} ({success/total*100:.0f}%)")
    print("=" * 70 + "\n")

    return results


def test_with_processor():
    """DocumentProcessor와 통합 테스트"""
    print("\n" + "=" * 70)
    print("[INTEGRATION] DocumentProcessor 통합 테스트")
    print("=" * 70 + "\n")

    try:
        from backend.preprocessor.document_processor import process_pdf

        test_file = "./data/_10-K-Q4-2023-As-Filed.pdf"

        if not Path(test_file).exists():
            print(f"[ERROR] 테스트 파일 없음: {test_file}")
            return

        print(f"테스트 파일: {Path(test_file).name}\n")

        # 문서 처리 (목차 추출 포함)
        chunks, config, metadata = process_pdf(
            test_file, auto_optimize=True, verbose=True
        )

        # 목차 정보 확인
        print("\n" + "=" * 70)
        print("[METADATA] 메타데이터 확인")
        print("=" * 70)
        print(f"목차 존재: {metadata.get('has_toc', False)}")
        print(f"목차 항목 수: {metadata.get('toc_items_count', 0)}")

        if metadata.get("toc"):
            print("\n처음 5개 항목:")
            for i, item in enumerate(metadata["toc"][:5], 1):
                print(f"  {i}. {item['title']} (p.{item['page']})")

        print("\n[SUCCESS] 통합 테스트 완료!")

    except ImportError as e:
        print(f"[ERROR] document_processor.py 수정이 필요합니다.")
        print(f"   에러: {e}")
    except Exception as e:
        print(f"[ERROR] 테스트 실패: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # 특정 파일 테스트
        file_path = sys.argv[1]
        test_single_file(file_path)
    else:
        # 전체 테스트
        print("[START] 목차 추출 테스트 시작\n")

        # 1. 개별 파일 테스트
        results = test_all_files()

        # 2. DocumentProcessor 통합 테스트
        test_with_processor()

        print("\n[DONE] 모든 테스트 완료!")


"""
사용법:

# 전체 테스트
python test_toc_extraction_full.py

# 특정 파일만 테스트
python test_toc_extraction_full.py ./data/form10-k.pdf
"""
