# document_processor.py

from typing import List, Dict, Tuple, Optional
from pathlib import Path
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.services.document.loader import PDFLoaderOptimized
from src.services.document.cache import DocumentCache
from src.services.document.toc_extractor import TOCExtractor


class OptimalChunkConfig:
    """최적 청킹 설정을 찾기 위한 평가 결과"""

    def __init__(
        self,
        chunk_size: int,
        chunk_overlap: int,
        score: float,
        num_chunks: int,
        config_name: str = "",
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.score = score
        self.num_chunks = num_chunks
        self.config_name = config_name

    def __repr__(self):
        return (
            f"OptimalChunkConfig(size={self.chunk_size}, "
            f"overlap={self.chunk_overlap}, score={self.score:.1f}, "
            f"chunks={self.num_chunks})"
        )


class DocumentProcessor:
    """
    PDF 문서 처리 파이프라인 (단순화 버전)

    주요 기능:
    1. PDF 로딩 (pdf_loader.py)
    2. 목차 추출 (toc_extractor.py)
    3. 최적 청크 설정 탐색 (3가지 설정 테스트)
    4. 최적 설정으로 문서 청킹 (RecursiveCharacterTextSplitter 직접 사용)
    """

    # 기본 테스트 설정들
    DEFAULT_TEST_CONFIGS = [
        {
            "chunk_size": 1000,
            "chunk_overlap": 100,
            "name": "효율형",
            "description": "저장공간 효율, 빠른 검색",
        },
        {
            "chunk_size": 1000,
            "chunk_overlap": 200,
            "name": "표준형",
            "description": "균형잡힌 범용 설정",
        },
        {
            "chunk_size": 1500,
            "chunk_overlap": 300,
            "name": "문맥형",
            "description": "긴 문맥 보존, 품질 우선",
        },
    ]

    def __init__(
        self,
        use_cache: bool = True,
        cache_dir: str = "./cache",
    ):
        """
        Args:
            use_cache: PDF 로딩 캐싱 사용 여부
            cache_dir: 캐시 디렉토리 경로
        """
        self.pdf_loader = PDFLoaderOptimized()
        self.toc_extractor = TOCExtractor()
        self.cache = DocumentCache(cache_dir) if use_cache else None

    def process(
        self,
        file_path: str,
        auto_optimize: bool = True,
        test_configs: Optional[List[Dict]] = None,
        verbose: bool = True,
    ) -> Tuple[List[Document], OptimalChunkConfig, Dict]:
        """
        PDF 문서를 처리하는 메인 파이프라인

        Args:
            file_path: PDF 파일 경로
            auto_optimize: True면 최적 청크 설정 자동 탐색, False면 표준형 사용
            test_configs: 테스트할 청크 설정 리스트 (None이면 DEFAULT_TEST_CONFIGS 사용)
            verbose: 진행 상황 출력 여부

        Returns:
            (chunks, optimal_config, metadata)
            - chunks: 청킹된 Document 리스트
            - optimal_config: 최적 청크 설정 정보
            - metadata: 처리 과정 메타데이터
        """
        metadata = {
            "file_path": file_path,
            "file_name": Path(file_path).name,
        }

        if verbose:
            print(f"\n{'='*70}")
            print(f"[START] PDF 문서 처리: {Path(file_path).name}")
            print(f"{'='*70}\n")

        # 1단계: PDF 로딩
        if verbose:
            print("[1/4] PDF 로딩 중...")

        docs, loader_name = self._load_pdf(file_path)
        metadata["loader_name"] = loader_name
        metadata["num_pages"] = len(docs)
        metadata["total_chars"] = sum(len(doc.page_content) for doc in docs)

        if verbose:
            print(f"   로더: {loader_name}")
            print(f"   페이지 수: {len(docs)}")
            print(f"   전체 글자 수: {metadata['total_chars']:,}\n")

        # 2단계: 목차 추출
        if verbose:
            print("[2/4] 목차 추출 중...")

        toc = self.toc_extractor.extract(file_path)
        metadata["toc"] = toc
        metadata["has_toc"] = toc is not None
        metadata["toc_items_count"] = len(toc) if toc else 0

        if verbose:
            if toc:
                print(f"   목차 추출 성공: {len(toc)}개 항목")
                # 처음 3개만 미리보기
                for i, item in enumerate(toc[:3], 1):
                    indent = "  " * (item.get("level", 1) - 1)
                    try:
                        print(f"      {indent}[{i}] {item['title']} (p.{item['page']})")
                    except UnicodeEncodeError:
                        safe_title = (
                            item["title"]
                            .encode("ascii", errors="replace")
                            .decode("ascii")
                        )
                        print(f"      {indent}[{i}] {safe_title} (p.{item['page']})")
                if len(toc) > 3:
                    print(f"      ... 외 {len(toc)-3}개 항목")
            else:
                print(f"   목차 없음 (단일 컬렉션 사용 예정)")
            print()

        # 3단계: 최적 청크 설정 탐색
        if auto_optimize:
            if verbose:
                print("[3/4] 최적 청크 설정 탐색 중...")

            optimal_config = self._find_optimal_config(docs, test_configs, verbose)

            if verbose:
                print(
                    f"\n   [BEST] {optimal_config.config_name} "
                    f"(크기={optimal_config.chunk_size}, "
                    f"오버랩={optimal_config.chunk_overlap})"
                )
                print(f"   점수: {optimal_config.score:.1f}")
                print(f"   예상 청크 수: {optimal_config.num_chunks}\n")
        else:
            # 표준형 기본 설정 사용
            standard_config = self.DEFAULT_TEST_CONFIGS[1]  # "표준형"
            optimal_config = OptimalChunkConfig(
                chunk_size=standard_config["chunk_size"],
                chunk_overlap=standard_config["chunk_overlap"],
                score=0.0,
                num_chunks=0,
                config_name=standard_config["name"],
            )
            if verbose:
                print(
                    f"[3/4] 기본 청크 설정 사용: "
                    f"{optimal_config.config_name} "
                    f"(크기={optimal_config.chunk_size}, "
                    f"오버랩={optimal_config.chunk_overlap})\n"
                )

        # 4단계: 최적 설정으로 청킹
        if verbose:
            print("[4/4] 문서 청킹 중...")

        chunks = self._split_documents(
            docs,
            chunk_size=optimal_config.chunk_size,
            chunk_overlap=optimal_config.chunk_overlap,
        )

        metadata["final_chunk_count"] = len(chunks)
        metadata["optimal_config"] = {
            "chunk_size": optimal_config.chunk_size,
            "chunk_overlap": optimal_config.chunk_overlap,
            "score": optimal_config.score,
        }

        if verbose:
            print(f"   최종 청크 수: {len(chunks)}")
            print(f"\n{'='*70}")
            print("[SUCCESS] 문서 처리 완료!")
            print(f"{'='*70}\n")

        return chunks, optimal_config, metadata

    def process_multiple(
        self,
        file_paths: List[str],
        auto_optimize: bool = True,
        verbose: bool = True,
    ) -> List[Tuple[List[Document], OptimalChunkConfig, Dict]]:
        """
        여러 PDF 문서를 일괄 처리

        Args:
            file_paths: PDF 파일 경로 리스트
            auto_optimize: 최적 청크 설정 자동 탐색 여부
            verbose: 진행 상황 출력 여부

        Returns:
            [(chunks, optimal_config, metadata), ...] 리스트
        """
        results = []

        for i, file_path in enumerate(file_paths):
            if verbose:
                print(f"\n[{i+1}/{len(file_paths)}] 처리 중...")

            try:
                result = self.process(
                    file_path=file_path,
                    auto_optimize=auto_optimize,
                    verbose=verbose,
                )
                results.append(result)
            except Exception as e:
                print(f"[ERROR] 처리 실패 - {Path(file_path).name}: {e}")
                results.append(([], None, {"error": str(e)}))

        return results

    def _load_pdf(self, file_path: str) -> Tuple[List[Document], str]:
        """PDF 로딩 (캐시 사용 가능)"""
        if self.cache:
            return self.cache.load_with_cache(file_path)
        else:
            return self.pdf_loader.load(file_path)

    def _split_documents(self, docs, chunk_size, chunk_overlap):
        """문서를 청크로 분할 (페이지 정보 보존)"""

        all_chunks = []

        # ✅ 각 문서(=페이지)를 개별적으로 청킹
        for doc in docs:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=len,
                separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""],
            )

            # 단일 문서 청킹
            doc_chunks = splitter.split_documents([doc])

            # 모든 청크에 원본 페이지 번호 보존
            for chunk in doc_chunks:
                if "page" not in chunk.metadata:
                    chunk.metadata["page"] = doc.metadata.get("page", 0)

            all_chunks.extend(doc_chunks)

        return all_chunks

    def _find_optimal_config(
        self,
        docs: List[Document],
        test_configs: Optional[List[Dict]] = None,
        verbose: bool = True,
    ) -> OptimalChunkConfig:
        """
        여러 청크 설정을 테스트하여 최적 설정 찾기

        ChunkEvaluator를 사용하여 각 설정의 점수 평가
        """
        from src.services.document.compare_chunk_configs_test import ChunkEvaluator

        evaluator = ChunkEvaluator()
        configs_to_test = test_configs or self.DEFAULT_TEST_CONFIGS

        best_config = None
        best_score = -1
        results = []

        for config in configs_to_test:
            # 청킹 테스트
            chunks = self._split_documents(
                docs,
                chunk_size=config["chunk_size"],
                chunk_overlap=config["chunk_overlap"],
            )

            # 평가 (doc_type 없이)
            eval_result = evaluator.evaluate_chunks_v2(chunks, None, docs)

            score = eval_result["종합점수"]
            results.append(
                {
                    "config": config,
                    "score": score,
                    "num_chunks": eval_result["기본통계"]["청크수"],
                    "eval_result": eval_result,
                }
            )

            if score > best_score:
                best_score = score
                best_config = OptimalChunkConfig(
                    chunk_size=config["chunk_size"],
                    chunk_overlap=config["chunk_overlap"],
                    score=score,
                    num_chunks=eval_result["기본통계"]["청크수"],
                    config_name=config["name"],
                )

            if verbose:
                print(
                    f"   - {config['name']:<12} | "
                    f"{score:>5.1f}점 | "
                    f"{config['chunk_size']}/{config['chunk_overlap']}"
                )

        return best_config

    def get_summary(self, metadata: Dict) -> str:
        """처리 결과 요약 문자열 생성"""
        lines = [
            "=" * 70,
            "[SUMMARY] 문서 처리 요약",
            "=" * 70,
            f"파일명: {metadata['file_name']}",
            f"페이지 수: {metadata['num_pages']}",
            f"전체 글자 수: {metadata['total_chars']:,}",
            "",
            "목차 정보:",
            f"  - 목차 존재: {'있음' if metadata['has_toc'] else '없음'}",
            f"  - 목차 항목 수: {metadata['toc_items_count']}",
            "",
            "최적 청크 설정:",
            f"  - 크기: {metadata['optimal_config']['chunk_size']}",
            f"  - 오버랩: {metadata['optimal_config']['chunk_overlap']}",
            f"  - 점수: {metadata['optimal_config']['score']:.1f}",
            f"  - 최종 청크 수: {metadata['final_chunk_count']}",
            "=" * 70,
        ]
        return "\n".join(lines)


# 편의 함수
def process_pdf(
    file_path: str,
    auto_optimize: bool = True,
    verbose: bool = True,
) -> Tuple[List[Document], OptimalChunkConfig, Dict]:
    """
    PDF 문서를 처리하는 간단한 함수

    Args:
        file_path: PDF 파일 경로
        auto_optimize: 최적 청크 설정 자동 탐색 여부 (False면 표준형 사용)
        verbose: 진행 상황 출력 여부

    Returns:
        (chunks, optimal_config, metadata)
    """
    processor = DocumentProcessor()
    return processor.process(
        file_path=file_path,
        auto_optimize=auto_optimize,
        verbose=verbose,
    )


"""
사용 예시:

# 1. 기본 사용 - 자동 최적화 (3가지 설정 테스트)
from document_processor import process_pdf

chunks, config, metadata = process_pdf("./data/document.pdf")
print(f"생성된 청크: {len(chunks)}")
print(f"최적 설정: {config}")

# 2. 최적화 없이 표준형 사용
chunks, config, metadata = process_pdf(
    "./data/document.pdf",
    auto_optimize=False  # 표준형(1000/200) 사용
)

# 3. 클래스 직접 사용 (여러 파일 처리)
from document_processor import DocumentProcessor

processor = DocumentProcessor(use_cache=True)
results = processor.process_multiple([
    "./data/file1.pdf",
    "./data/file2.pdf",
])

for chunks, config, metadata in results:
    print(processor.get_summary(metadata))

# 4. 커스텀 테스트 설정
custom_configs = [
    {"chunk_size": 800, "chunk_overlap": 100, "name": "테스트1"},
    {"chunk_size": 1200, "chunk_overlap": 200, "name": "테스트2"},
]

processor = DocumentProcessor()
chunks, config, metadata = processor.process(
    "./data/document.pdf",
    auto_optimize=True,
    test_configs=custom_configs
)

# 5. Qdrant 저장까지 전체 파이프라인
from qdrant_manager import QdrantManager
from embedding_generator import EmbeddingGenerator

# 문서 처리
chunks, config, metadata = process_pdf("./data/document.pdf", auto_optimize=True)

# 임베딩 생성
generator = EmbeddingGenerator(mode="local", model="bge-m3")
texts = [chunk.page_content for chunk in chunks]
embeddings = generator.embed_documents(texts)

# Qdrant 저장
import os
manager = QdrantManager(
    host=os.getenv("QDRANT_HOST", "localhost"),
    port=int(os.getenv("QDRANT_PORT", "6333")),
    api_key=os.getenv("QDRANT_API_KEY")
)
result = manager.store_document(chunks, metadata, embeddings)

print(f"저장 완료: {result['total_points']}개 포인트, {len(result['collections'])}개 컬렉션")
"""
