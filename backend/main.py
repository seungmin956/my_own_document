"""
PDF 문서 처리 메인 파이프라인

전체 흐름:
1. PDF 로딩
2. 목차 추출
3. 최적 청크 설정 탐색 (3가지 설정 테스트)
4. 문서 청킹
5. 임베딩 생성
6. Qdrant 저장 (목차별 컬렉션 분리)
"""

import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv
from src.services.document.processor import process_pdf
from src.services.retrieval.embedding_generator import EmbeddingGenerator
from src.services.storage.qdrant_manager import QdrantManager

# .env 파일 로드
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)


class DocumentPipeline:
    """
    PDF → Qdrant 전체 파이프라인

    사용 예시:
    >>> pipeline = DocumentPipeline()
    >>> pipeline.process("./data/document.pdf")
    """

    def __init__(
        self,
        qdrant_host: str = None,
        qdrant_port: int = None,
        qdrant_api_key: str = None,
        embedding_model: str = None,
        auto_optimize: bool = True,
    ):
        """
        Args:
            qdrant_host: Qdrant 서버 주소 (기본값: .env의 QDRANT_HOST)
            qdrant_port: Qdrant 서버 포트 (기본값: .env의 QDRANT_PORT)
            qdrant_api_key: Qdrant API 키 (기본값: .env의 QDRANT_API_KEY)
            embedding_model: 임베딩 모델 (기본값: .env의 EMBEDDING_MODEL)
            auto_optimize: 최적 청크 설정 자동 탐색 여부
        """
        # 환경변수에서 기본값 로드
        qdrant_host = qdrant_host or os.getenv("QDRANT_HOST", "localhost")
        qdrant_port = qdrant_port or int(os.getenv("QDRANT_PORT", "6333"))
        qdrant_api_key = qdrant_api_key or os.getenv("QDRANT_API_KEY")
        if not qdrant_api_key:
            raise ValueError("QDRANT_API_KEY must be set in .env file")
        embedding_model = embedding_model or os.getenv("EMBEDDING_MODEL", "bge-m3")

        self.auto_optimize = auto_optimize

        # 임베딩 차원 결정
        embedding_dim = 1024 if embedding_model == "bge-m3" else 768

        # Qdrant 매니저 초기화
        self.qdrant = QdrantManager(
            host=qdrant_host,
            port=qdrant_port,
            api_key=qdrant_api_key,
            embedding_dimension=embedding_dim,
        )

        # 임베딩 생성기 초기화 (model은 .env에서 자동 로드)
        self.embedding_generator = EmbeddingGenerator(
            mode="local", verbose=False
        )

        # 설정 저장
        self.embedding_model = embedding_model

        print(f"\n{'='*70}")
        print("[INIT] Document Pipeline 초기화 완료")
        print(f"{'='*70}")
        print(f"  Qdrant: {qdrant_host}:{qdrant_port}")
        print(f"  Embedding: {embedding_model}")
        print(f"  Auto-optimize: {auto_optimize}")
        print(f"{'='*70}\n")

    def process(self, file_path: str, verbose: bool = True) -> dict:
        """
        단일 PDF 파일 처리

        Args:
            file_path: PDF 파일 경로
            verbose: 진행 상황 출력 여부

        Returns:
            처리 결과 딕셔너리
        """
        if not Path(file_path).exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")

        # 1. 문서 처리 (로딩 + 목차 추출 + 최적 청킹)
        if verbose:
            print(f"\n{'='*70}")
            print(f"[PIPELINE] 문서 처리 시작: {Path(file_path).name}")
            print(f"{'='*70}\n")

        chunks, config, metadata = process_pdf(
            file_path, auto_optimize=self.auto_optimize, verbose=verbose
        )

        # 2. 임베딩 생성
        if verbose:
            print("[5/6] 임베딩 생성 중...")

        texts = [chunk.page_content for chunk in chunks]
        embeddings = self.embedding_generator.embed_documents(texts)

        if verbose:
            print(f"   임베딩 생성 완료: {len(embeddings)}개")
            print(f"   임베딩 차원: {len(embeddings[0])}\n")

        # 3. Qdrant 저장
        if verbose:
            print("[6/6] Qdrant 저장 중...")

        result = self.qdrant.store_document(
            chunks=chunks, metadata=metadata, embeddings=embeddings
        )

        # 결과 요약
        summary = {
            "file_name": Path(file_path).name,
            "chunks": len(chunks),
            "optimal_config": {
                "name": config.config_name,
                "chunk_size": config.chunk_size,
                "chunk_overlap": config.chunk_overlap,
                "score": config.score,
            },
            "toc": {
                "has_toc": metadata["has_toc"],
                "items": metadata["toc_items_count"],
            },
            "qdrant": {
                "collections": len(result["collections"]),
                "total_points": result["total_points"],
                "collection_names": result["collections"],
            },
        }

        if verbose:
            self._print_summary(summary)

        return summary

    def process_multiple(
        self, file_paths: List[str], verbose: bool = True
    ) -> List[dict]:
        """
        여러 PDF 파일 일괄 처리

        Args:
            file_paths: PDF 파일 경로 리스트
            verbose: 진행 상황 출력 여부

        Returns:
            처리 결과 리스트
        """
        results = []

        for i, file_path in enumerate(file_paths, 1):
            print(f"\n{'='*70}")
            print(f"[{i}/{len(file_paths)}] 처리 중...")
            print(f"{'='*70}\n")

            try:
                result = self.process(file_path, verbose=verbose)
                results.append(result)
            except Exception as e:
                print(f"[ERROR] 처리 실패 - {Path(file_path).name}: {e}")
                results.append({"error": str(e), "file_name": Path(file_path).name})

        # 전체 요약
        if verbose:
            self._print_batch_summary(results)

        return results

    def _print_summary(self, summary: dict):
        """단일 문서 처리 결과 출력"""
        print(f"\n{'='*70}")
        print("[SUCCESS] 처리 완료!")
        print(f"{'='*70}")
        print(f"파일명: {summary['file_name']}")
        print(f"\n[청킹 결과]")
        print(f"  최적 설정: {summary['optimal_config']['name']}")
        print(
            f"  크기/오버랩: {summary['optimal_config']['chunk_size']}/{summary['optimal_config']['chunk_overlap']}"
        )
        print(f"  점수: {summary['optimal_config']['score']:.1f}")
        print(f"  청크 수: {summary['chunks']}")
        print(f"\n[목차 정보]")
        print(f"  목차 존재: {'있음' if summary['toc']['has_toc'] else '없음'}")
        print(f"  목차 항목: {summary['toc']['items']}개")
        print(f"\n[Qdrant 저장]")
        print(f"  컬렉션 수: {summary['qdrant']['collections']}")
        print(f"  저장 포인트: {summary['qdrant']['total_points']}")
        print(f"{'='*70}\n")

    def _print_batch_summary(self, results: List[dict]):
        """일괄 처리 결과 요약"""
        print(f"\n{'='*70}")
        print("[BATCH SUMMARY] 전체 처리 결과")
        print(f"{'='*70}")

        success = [r for r in results if "error" not in r]
        failed = [r for r in results if "error" in r]

        print(f"총 파일 수: {len(results)}")
        print(f"  성공: {len(success)}")
        print(f"  실패: {len(failed)}")

        if success:
            print(f"\n[성공한 파일]")
            for r in success:
                print(
                    f"  - {r['file_name']:<40} | {r['chunks']:3d}청크 | {r['qdrant']['collections']:2d}컬렉션"
                )

        if failed:
            print(f"\n[실패한 파일]")
            for r in failed:
                print(f"  - {r['file_name']:<40} | {r['error']}")

        print(f"{'='*70}\n")

    def list_documents(self):
        """Qdrant에 저장된 문서 목록"""
        collections = self.qdrant.list_collections()

        # 문서별로 그룹화
        doc_groups = {}
        for col in collections:
            # 컬렉션 이름에서 문서 이름 추출 (언더스코어 기준)
            parts = col.split("_")
            if len(parts) >= 2:
                # 마지막 부분이 "main" 또는 "sXX"로 시작하면 문서 그룹
                if parts[-1] == "main" or parts[-1].startswith("s"):
                    doc_name = "_".join(parts[:-1])
                else:
                    doc_name = col

                if doc_name not in doc_groups:
                    doc_groups[doc_name] = []
                doc_groups[doc_name].append(col)

        print(f"\n{'='*70}")
        print("[DOCUMENTS] Qdrant에 저장된 문서")
        print(f"{'='*70}")
        print(f"총 문서 수: {len(doc_groups)}")
        print(f"총 컬렉션 수: {len(collections)}\n")

        for doc_name, cols in doc_groups.items():
            print(f"  {doc_name}")
            print(f"    컬렉션: {len(cols)}개")
            if len(cols) <= 5:
                for col in cols:
                    print(f"      - {col}")
            else:
                for col in cols[:3]:
                    print(f"      - {col}")
                print(f"      ... 외 {len(cols) - 3}개")

        print(f"{'='*70}\n")

        return doc_groups

    def delete_document(self, doc_name: str):
        """문서 삭제"""
        deleted = self.qdrant.delete_document(doc_name)
        print(f"\n[OK] '{doc_name}' 문서 삭제 완료 ({deleted}개 컬렉션)\n")
        return deleted


# 편의 함수
def process_single_pdf(
    file_path: str,
    auto_optimize: bool = True,
    qdrant_api_key: str = None,
) -> dict:
    """
    단일 PDF 파일 처리 (간편 함수)

    Args:
        file_path: PDF 파일 경로
        auto_optimize: 최적 청크 설정 자동 탐색 여부
        qdrant_api_key: Qdrant API 키

    Returns:
        처리 결과
    """
    pipeline = DocumentPipeline(
        auto_optimize=auto_optimize, qdrant_api_key=qdrant_api_key
    )
    return pipeline.process(file_path)


def process_multiple_pdfs(
    file_paths: List[str],
    auto_optimize: bool = True,
    qdrant_api_key: str = None,
) -> List[dict]:
    """
    여러 PDF 파일 일괄 처리 (간편 함수)

    Args:
        file_paths: PDF 파일 경로 리스트
        auto_optimize: 최적 청크 설정 자동 탐색 여부
        qdrant_api_key: Qdrant API 키

    Returns:
        처리 결과 리스트
    """
    pipeline = DocumentPipeline(
        auto_optimize=auto_optimize, qdrant_api_key=qdrant_api_key
    )
    return pipeline.process_multiple(file_paths)


if __name__ == "__main__":
    import sys

    # CLI 사용법
    if len(sys.argv) < 2:
        print("\n사용법:")
        print("  python main.py <PDF파일경로> [옵션]")
        print("\n옵션:")
        print("  --no-optimize    최적화 없이 표준형 사용")
        print("\n예시:")
        print("  python main.py ./data/document.pdf")
        print("  python main.py ./data/document.pdf --no-optimize")
        print("  python main.py ./data/*.pdf")
        sys.exit(0)

    # 파일 경로 수집
    file_paths = []
    auto_optimize = True

    for arg in sys.argv[1:]:
        if arg == "--no-optimize":
            auto_optimize = False
        elif not arg.startswith("--"):
            # 와일드카드 지원
            from glob import glob

            matched = glob(arg)
            file_paths.extend([p for p in matched if p.endswith(".pdf")])

    if not file_paths:
        print("[ERROR] PDF 파일을 찾을 수 없습니다.")
        sys.exit(1)

    # 파이프라인 실행
    pipeline = DocumentPipeline(auto_optimize=auto_optimize)

    if len(file_paths) == 1:
        pipeline.process(file_paths[0])
    else:
        pipeline.process_multiple(file_paths)


"""
사용 예시:

# 1. 단일 파일 처리 (CLI)
python main.py ./data/document.pdf

# 2. 여러 파일 일괄 처리 (CLI)
python main.py ./data/*.pdf

# 3. 최적화 없이 표준형 사용 (CLI)
python main.py ./data/document.pdf --no-optimize

# 4. Python 코드에서 사용
from main import DocumentPipeline
import os

# 파이프라인 초기화 (.env에서 자동 로드)
pipeline = DocumentPipeline(auto_optimize=True)

# 또는 명시적으로 설정
pipeline = DocumentPipeline(
    qdrant_host="localhost",
    qdrant_port=6333,
    qdrant_api_key=os.getenv("QDRANT_API_KEY"),  # .env에서 로드
    embedding_model="bge-m3",
    auto_optimize=True
)

# 단일 파일 처리
result = pipeline.process("./data/document.pdf")

# 여러 파일 처리
results = pipeline.process_multiple([
    "./data/file1.pdf",
    "./data/file2.pdf",
])

# 저장된 문서 목록
pipeline.list_documents()

# 문서 삭제
pipeline.delete_document("document.pdf")

# 5. 간편 함수 사용
from main import process_single_pdf, process_multiple_pdfs

# 단일 파일
result = process_single_pdf("./data/document.pdf")

# 여러 파일
results = process_multiple_pdfs([
    "./data/file1.pdf",
    "./data/file2.pdf",
])
"""
