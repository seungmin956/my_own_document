"""
PyMuPDF vs PDFMiner 상세 비교

실제 텍스트 품질과 구조를 비교
"""

from langchain_community.document_loaders import PDFMinerLoader, PyMuPDFLoader
from pathlib import Path


def compare_loaders(file_path: str):
    """두 로더 비교"""

    print("=" * 70)
    print(f"📊 로더 비교: {Path(file_path).name}")
    print("=" * 70)

    # 1. PDFMiner
    print("\n[1] PDFMiner")
    print("─" * 70)

    try:
        loader = PDFMinerLoader(file_path)
        docs_miner = loader.load()

        print(f"문서 수: {len(docs_miner)}개")
        print(f"총 길이: {sum(len(d.page_content) for d in docs_miner):,}자")

        if docs_miner:
            print(f"\n[첫 번째 Document]")
            print(f"  페이지: {docs_miner[0].metadata.get('page', 'NONE')}")
            print(f"  길이: {len(docs_miner[0].page_content):,}자")
            print(f"  샘플 (200자):")
            print(f"  {docs_miner[0].page_content[:200]}")
    except Exception as e:
        print(f"❌ 오류: {e}")
        docs_miner = []

    # 2. PyMuPDF
    print("\n[2] PyMuPDF")
    print("─" * 70)

    try:
        loader = PyMuPDFLoader(file_path)
        docs_pymupdf = loader.load()

        print(f"문서 수: {len(docs_pymupdf)}개")
        print(f"총 길이: {sum(len(d.page_content) for d in docs_pymupdf):,}자")

        if docs_pymupdf:
            print(f"\n[첫 3개 Documents]")
            for i, doc in enumerate(docs_pymupdf[:3], 1):
                page = doc.metadata.get("page", "NONE")
                length = len(doc.page_content)
                sample = doc.page_content[:100].replace("\n", " ")

                print(f"  [{i}] 페이지: {page} | {length:,}자")
                print(f"      {sample}...")
    except Exception as e:
        print(f"❌ 오류: {e}")
        docs_pymupdf = []

    # 3. 비교
    print(f"\n{'='*70}")
    print("비교 결과")
    print(f"{'='*70}")

    if docs_miner and docs_pymupdf:
        miner_total = sum(len(d.page_content) for d in docs_miner)
        pymupdf_total = sum(len(d.page_content) for d in docs_pymupdf)

        print(f"\n문서 수:")
        print(f"  PDFMiner:  {len(docs_miner):3d}개")
        print(f"  PyMuPDF:   {len(docs_pymupdf):3d}개")

        print(f"\n총 텍스트 길이:")
        print(f"  PDFMiner:  {miner_total:,}자")
        print(f"  PyMuPDF:   {pymupdf_total:,}자")
        print(
            f"  차이:      {abs(miner_total - pymupdf_total):,}자 ({abs(miner_total - pymupdf_total)/miner_total*100:.1f}%)"
        )

        print(f"\n페이지 정보:")
        miner_pages = [d.metadata.get("page") for d in docs_miner]
        pymupdf_pages = [d.metadata.get("page") for d in docs_pymupdf]

        print(f"  PDFMiner:  {set(miner_pages)}")
        print(f"  PyMuPDF:   {list(pymupdf_pages[:5])}... (처음 5개)")

        # 텍스트 품질 샘플 비교
        print(f"\n{'─'*70}")
        print("텍스트 품질 샘플 비교 (첫 500자):")
        print(f"{'─'*70}")

        print("\n[PDFMiner]")
        if docs_miner:
            print(docs_miner[0].page_content[:500])

        print("\n[PyMuPDF]")
        if docs_pymupdf:
            # 여러 페이지 합치기
            combined = "\n".join([d.page_content for d in docs_pymupdf[:3]])
            print(combined[:500])

        print(f"\n{'─'*70}")
        print("결론:")
        print(f"{'─'*70}")

        if len(docs_pymupdf) > 1:
            print("✅ PyMuPDF: 페이지별 분리 성공 → 목차 매칭 가능")
        else:
            print("⚠️  PyMuPDF: 페이지 분리 실패")

        if len(docs_miner) == 1:
            print("❌ PDFMiner: 전체를 1개 문서로 → 목차 매칭 불가능")

        # 텍스트 품질
        diff_percent = abs(miner_total - pymupdf_total) / miner_total * 100
        if diff_percent < 5:
            print(f"✅ 텍스트 품질: 거의 동일 (차이 {diff_percent:.1f}%)")
        elif diff_percent < 15:
            print(f"⚠️  텍스트 품질: 약간 차이 (차이 {diff_percent:.1f}%)")
        else:
            print(f"❌ 텍스트 품질: 큰 차이 (차이 {diff_percent:.1f}%)")


if __name__ == "__main__":
    file_path = "./data/_10-K-Q4-2023-As-Filed.pdf"

    if Path(file_path).exists():
        compare_loaders(file_path)
    else:
        print(f"❌ 파일 없음: {file_path}")
