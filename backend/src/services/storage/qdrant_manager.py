# qdrant_manager.py

from typing import List, Dict, Optional, Tuple
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)
import re
from pathlib import Path
import uuid
import time


def safe_print(message: str):
    """Windows cp949 인코딩 오류 방지 출력"""
    try:
        print(message)
    except UnicodeEncodeError:
        safe_message = message.encode("ascii", errors="replace").decode("ascii")
        print(safe_message)


class QdrantManager:
    """
    Qdrant 벡터 DB 관리자 (온프레미스)

    목차별 컬렉션 분리 전략:
    - 목차 있음: {doc_name}_section_{idx} 컬렉션 생성
    - 목차 없음: {doc_name}_main 단일 컬렉션 생성

    사용 예시:
    >>> manager = QdrantManager(host="localhost", port=6333)
    >>> manager.store_document(chunks, metadata, embeddings)
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        api_key: Optional[str] = None,
        embedding_dimension: int = 1024,
        distance_metric: str = "Cosine",
        verbose: bool = True,
    ):
        """
        Args:
            host: Qdrant 서버 주소
            port: Qdrant 서버 포트
            api_key: Qdrant API 키
            embedding_dimension: 임베딩 벡터 차원
            distance_metric: 거리 측정 방식
            verbose: 진행 상황 출력
        """
        self.host = host
        self.port = port
        self.embedding_dimension = embedding_dimension  # ← 추가!
        self.distance_metric = self._get_distance_metric(distance_metric)  # ← 추가!
        self.verbose = verbose  # ← 추가!

        # 재시도 설정
        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                self.client = QdrantClient(
                    host=host,
                    port=port,
                    api_key=api_key,
                    https=False,
                    prefer_grpc=False,
                    timeout=300,  # 5분으로 증가 (대용량 문서 처리 위해)
                )

                # 연결 테스트
                self.client.get_collections()

                if verbose:
                    print(f"[OK] Qdrant 연결: {host}:{port}")

                break  # 성공하면 루프 종료

            except Exception as e:
                if attempt < max_retries - 1:
                    if verbose:
                        print(f"⚠️  Qdrant 연결 실패 (시도 {attempt+1}/{max_retries})")
                        print(f"   {retry_delay}초 후 재시도...")
                    time.sleep(retry_delay)
                else:
                    # 최종 실패
                    raise ConnectionError(
                        f"Qdrant 서버에 연결할 수 없습니다 ({host}:{port}).\n"
                        f"해결 방법: docker-compose up -d"
                    )

    def _get_distance_metric(self, metric: str) -> Distance:
        """거리 측정 방식 변환"""
        metrics = {
            "Cosine": Distance.COSINE,
            "Euclid": Distance.EUCLID,
            "Dot": Distance.DOT,
        }
        return metrics.get(metric, Distance.COSINE)

    def _check_connection(self):
        """Qdrant 서버 연결 확인"""
        try:
            collections = self.client.get_collections()
            print(f"   기존 컬렉션 수: {len(collections.collections)}")
        except Exception as e:
            print(f"[WARN] Qdrant 연결 확인 실패: {e}")

    def _sanitize_collection_name(self, name: str) -> str:
        """
        컬렉션 이름 정제 (Qdrant 규칙 준수)

        규칙:
        - 영문, 숫자, 언더스코어, 하이픈만 허용
        - 63자 이하
        - 소문자 권장
        """
        # 파일명에서 확장자 제거
        name = Path(name).stem

        # 특수문자를 언더스코어로 변환
        name = re.sub(r"[^\w\-]", "_", name)

        # 연속된 언더스코어 제거
        name = re.sub(r"_+", "_", name)

        # 소문자 변환 및 길이 제한
        name = name.lower()[:63]

        # 시작/끝 언더스코어 제거
        name = name.strip("_")

        return name

    def _determine_collections(
        self, doc_name: str, toc: Optional[List[Dict]]
    ) -> List[Dict]:
        """
        문서의 컬렉션 구조 결정 - 단일 컬렉션 전략

        변경: 목차와 상관없이 항상 단일 컬렉션 생성
        목차 정보는 메타데이터로 저장
        """
        base_name = self._sanitize_collection_name(doc_name)

        return [
            {
                "name": f"{base_name}_main",
                "title": "Full Document",
                "page_start": 0,
                "page_end": 999999,
            }
        ]

    def _find_toc_section(self, page: int, toc: Optional[List[Dict]]) -> Optional[Dict]:
        """
        특정 페이지가 속한 목차 섹션 찾기

        Args:
            page: 청크의 페이지 번호
            toc: 목차 리스트

        Returns:
            해당 페이지가 속한 목차 섹션 (없으면 None)
        """
        if not toc:
            return None

        # 페이지 순서로 정렬
        sorted_toc = sorted(toc, key=lambda x: x.get("page", 0))

        # 해당 페이지가 속한 섹션 찾기
        for i, item in enumerate(sorted_toc):
            current_page = item.get("page", 0)

            # 다음 섹션의 시작 페이지
            if i + 1 < len(sorted_toc):
                next_page = sorted_toc[i + 1].get("page", 999999)
            else:
                next_page = 999999

            # 범위 체크
            if current_page <= page < next_page:
                return item

        return None

    def _create_collection(self, collection_name: str):
        """컬렉션 생성"""
        try:
            # 이미 존재하는지 확인
            collections = self.client.get_collections()
            existing = [c.name for c in collections.collections]

            if collection_name in existing:
                if self.verbose:
                    safe_print(f"   [SKIP] 컬렉션 이미 존재: {collection_name}")
                return

            # 새 컬렉션 생성
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_dimension, distance=self.distance_metric
                ),
            )

            if self.verbose:
                safe_print(f"   [CREATE] 컬렉션 생성: {collection_name}")

        except Exception as e:
            safe_print(f"[ERROR] 컬렉션 생성 실패 ({collection_name}): {e}")
            raise

    def _assign_chunk_to_collection(
        self, chunk: Dict, collections: List[Dict]
    ) -> Optional[str]:
        """청크가 속할 컬렉션 결정"""
        # 청크의 페이지 번호 확인
        page = chunk.get("metadata", {}).get("page", 1)

        # 페이지 범위에 맞는 컬렉션 찾기
        for collection in collections:
            if collection["page_start"] <= page <= collection["page_end"]:
                return collection["name"]

        # 매칭 실패시 첫 번째 컬렉션 사용
        return collections[0]["name"] if collections else None

    def store_document(
        self,
        chunks: List[Dict],
        metadata: Dict,
        embeddings: List[List[float]],
        doc_name: Optional[str] = None,
    ) -> Dict:
        """
        문서를 Qdrant에 저장 (단일 컬렉션 + 메타데이터)

        변경:
        - 단일 컬렉션만 생성
        - 목차 정보를 메타데이터로 저장
        """
        # 문서 이름 확인
        if doc_name is None:
            doc_name = metadata.get("file_name", "unknown_document")

        # 목차 추출
        toc = metadata.get("toc", None)
        has_toc = metadata.get("has_toc", False)

        if self.verbose:
            print(f"\n{'='*70}")
            print(f"[STORE] 문서 저장: {doc_name}")
            print(f"{'='*70}")
            print(f"청크 수: {len(chunks)}")
            print(f"목차 존재: {has_toc} ({len(toc) if toc else 0}개 항목)")

        # 컬렉션 구조 결정 (단일 컬렉션)
        collections = self._determine_collections(doc_name, toc)
        collection_name = collections[0]["name"]

        if self.verbose:
            print(f"컬렉션: {collection_name} (단일 컬렉션 전략)")

        # 컬렉션 생성
        print(f"\n[1/2] 컬렉션 생성 중...")
        self._create_collection(collection_name)

        # 포인트 생성
        print(f"\n[2/2] 데이터 저장 중...")
        points = []

        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            # Document 객체 처리
            if hasattr(chunk, "page_content"):
                chunk_text = chunk.page_content
                chunk_page = chunk.metadata.get("page", 0)
            else:
                chunk_text = chunk.get("text", "")
                chunk_page = chunk.get("metadata", {}).get("page", 0)

            # ✅ 목차 섹션 찾기
            toc_section = self._find_toc_section(chunk_page, toc) if toc else None

            # 포인트 생성
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    "text": chunk_text,
                    "page": chunk_page,
                    "chunk_index": idx,
                    "doc_name": doc_name,
                    "doc_type": metadata.get("doc_type", "unknown"),
                    "has_toc": has_toc,
                    # ✅ 목차 정보 메타데이터로 저장
                    "toc_section": toc_section.get("title") if toc_section else None,
                    "toc_level": toc_section.get("level") if toc_section else None,
                    "toc_page": toc_section.get("page") if toc_section else None,
                },
            )
            points.append(point)

        # Qdrant 업로드 (배치)
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            self.client.upsert(collection_name=collection_name, points=batch)

            if self.verbose and (i + batch_size) % 200 == 0:
                print(f"   진행: {min(i+batch_size, len(points))}/{len(points)}")

        # 결과 반환
        result = {
            "doc_name": doc_name,
            "collections": [collection_name],
            "total_points": len(points),
            "collection_points": {collection_name: len(points)},
            "has_toc": has_toc,
            "toc_items": len(toc) if toc else 0,
        }

        if self.verbose:
            print(f"\n{'='*70}")
            print(f"[SUCCESS] 저장 완료!")
            print(f"   컬렉션: {collection_name}")
            print(f"   포인트: {len(points)}개")
            if has_toc:
                print(f"   목차 항목: {len(toc)}개 (메타데이터로 저장)")
            print(f"{'='*70}\n")

        return result

    def search(
        self,
        query_vector: List[float],
        collection_names: Optional[List[str]] = None,
        limit: int = 5,
        score_threshold: float = 0.7,
    ) -> List[Dict]:
        """벡터 검색"""
        from qdrant_client.models import SearchRequest

        # 검색할 컬렉션 결정
        if collection_names is None:
            collections_info = self.client.get_collections()
            collection_names = [c.name for c in collections_info.collections]

        all_results = []

        for collection_name in collection_names:
            try:
                results = self.client.query_points(
                    collection_name=collection_name,
                    query=query_vector,
                    limit=limit,
                    score_threshold=score_threshold,
                ).points

                for result in results:
                    all_results.append(
                        {
                            "text": result.payload.get("text", ""),
                            "score": result.score,
                            "collection": collection_name,
                            "metadata": {
                                "page": result.payload.get("page"),
                                "doc_name": result.payload.get("doc_name"),
                                "doc_type": result.payload.get("doc_type"),
                                # ✅ 수정: toc_title → toc_section
                                "toc_section": result.payload.get("toc_section"),
                                "toc_level": result.payload.get("toc_level"),
                            },
                        }
                    )

            except Exception as e:
                safe_print(f"[WARN] 검색 실패 ({collection_name}): {e}")

        # 점수 순 정렬
        all_results.sort(key=lambda x: x["score"], reverse=True)

        return all_results[:limit]

    def delete_document(self, doc_name: str) -> int:
        """
        문서의 모든 컬렉션 삭제

        Args:
            doc_name: 문서 이름

        Returns:
            삭제된 컬렉션 수
        """
        sanitized_name = self._sanitize_collection_name(doc_name)

        collections_info = self.client.get_collections()
        all_collections = [c.name for c in collections_info.collections]

        # 해당 문서의 컬렉션 찾기
        target_collections = [
            c for c in all_collections if c.startswith(sanitized_name)
        ]

        deleted = 0
        for collection_name in target_collections:
            try:
                self.client.delete_collection(collection_name)
                deleted += 1
                if self.verbose:
                    safe_print(f"[DELETE] {collection_name}")
            except Exception as e:
                safe_print(f"[ERROR] 삭제 실패 ({collection_name}): {e}")

        if self.verbose:
            print(f"\n[OK] {deleted}개 컬렉션 삭제 완료")

        return deleted

    def list_collections(self, doc_name: Optional[str] = None) -> List[str]:
        """
        컬렉션 목록 조회

        Args:
            doc_name: 특정 문서의 컬렉션만 조회 (None이면 전체)

        Returns:
            컬렉션 이름 리스트
        """
        collections_info = self.client.get_collections()
        all_collections = [c.name for c in collections_info.collections]

        if doc_name:
            sanitized_name = self._sanitize_collection_name(doc_name)
            return [c for c in all_collections if c.startswith(sanitized_name)]

        return all_collections


# 편의 함수
def create_qdrant_manager(
    host: str = "localhost",
    port: int = 6333,
    api_key: Optional[str] = None,
    embedding_dimension: int = 1024,
) -> QdrantManager:
    """Qdrant 매니저 생성 간단 함수"""
    return QdrantManager(
        host=host, port=port, api_key=api_key, embedding_dimension=embedding_dimension
    )


"""
사용 예시:

# 1. 기본 사용 (document_processor.py와 통합)
from qdrant_manager import QdrantManager
from document_processor import process_pdf
from embedding_generator import EmbeddingGenerator

# 문서 처리
chunks, config, metadata = process_pdf("./data/document.pdf", auto_optimize=True)

# 임베딩 생성
generator = EmbeddingGenerator(mode="local", model="bge-m3")
texts = [chunk["text"] for chunk in chunks]
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


# 2. 검색
query = "AI 기술의 발전"
query_embedding = generator.embed_query(query)

results = manager.search(
    query_vector=query_embedding,
    limit=5,
    score_threshold=0.7
)

for result in results:
    print(f"[{result['score']:.3f}] {result['text'][:100]}...")
    print(f"   출처: {result['metadata']['toc_title']} (p.{result['metadata']['page']})")


# 3. 문서 삭제
manager.delete_document("document.pdf")


# 4. 컬렉션 목록
collections = manager.list_collections()
print(f"전체 컬렉션: {collections}")

doc_collections = manager.list_collections("document.pdf")
print(f"document.pdf 컬렉션: {doc_collections}")
"""
