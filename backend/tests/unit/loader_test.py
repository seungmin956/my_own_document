# loader_test.py

import os
from backend.preprocessor.pdf_loader import PDFLoaderOptimized


def test_pdf_loader(data_dir: str = "./data"):
    """data 폴더의 모든 PDF 파일 테스트"""

    # PDF 파일 찾기
    pdf_files = [f for f in os.listdir(data_dir) if f.endswith(".pdf")]

    if not pdf_files:
        print(f"'{data_dir}' 폴더에 PDF 파일이 없습니다.")
        return

    print(f"총 {len(pdf_files)}개 PDF 파일 테스트 시작\n")
    print("=" * 70)

    loader = PDFLoaderOptimized(min_chars=100)
    results = []

    for pdf_file in pdf_files:
        file_path = os.path.join(data_dir, pdf_file)
        print(f"\n📄 파일: {pdf_file}")
        print("-" * 70)

        try:
            docs, loader_name = loader.load(file_path)

            # 통계 정보
            total_chars = sum(len(doc.page_content) for doc in docs)
            first_content = docs[0].page_content[:200].replace("\n", " ")

            print(f"✓ 성공")
            print(f"  - 사용 로더: {loader_name}")
            print(f"  - 문서 개수: {len(docs)}")
            print(f"  - 총 글자수: {total_chars:,}")
            print(f"  - 미리보기: {first_content}...")

            results.append(
                {
                    "파일": pdf_file,
                    "로더": loader_name,
                    "문서수": len(docs),
                    "글자수": total_chars,
                    "상태": "✓",
                }
            )

        except Exception as e:
            print(f"✗ 실패: {e}")
            results.append(
                {"파일": pdf_file, "로더": None, "문서수": 0, "글자수": 0, "상태": "✗"}
            )

        print("=" * 70)

    # 결과 요약
    print("\n\n📊 테스트 결과 요약")
    print("=" * 70)
    for r in results:
        status = r["상태"]
        print(f"{status} {r['파일']:<40} | {r['로더']:<12} | {r['글자수']:>10,}자")

    return results


# 실행
results = test_pdf_loader()
