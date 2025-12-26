# api/main.py
"""
Document Assistant REST API

RAG 시스템 백엔드 API 서버
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from pathlib import Path
import uuid
import shutil
import sys
import io

from src.core.chatbot import DocumentChatbot
from src.core.exceptions import RAGException

app = FastAPI(
    title="Document Assistant API",
    description="RAG 기반 문서 QA 시스템 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 설정 (프론트엔드 연결용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 인스턴스 (싱글톤 패턴 - 성능 최적화)
chatbot = None
embedding_generator = None
document_processor = None


# ============================================
# 요청/응답 스키마
# ============================================


class QuestionRequest(BaseModel):
    """질문 요청"""

    question: str = Field(..., min_length=1, max_length=1000, description="사용자 질문")
    doc_name: Optional[str] = Field(None, description="특정 문서명 (없으면 전체 검색)")
    # ✅ [추가] 대화 내역 필드 (기본값 [] 설정 필수!)
    history: List[Dict[str, str]] = Field(default=[], description="이전 대화 내역")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"question": "삼성에서 개발한 AI는 무엇인가요?", "doc_name": None}
            ]
        }
    }


class Source(BaseModel):
    """출처 정보"""

    doc_name: str
    toc_section: Optional[str]
    page: int
    score: float
    rerank_score: Optional[float] = None


class ErrorDetail(BaseModel):
    """에러 상세 정보"""

    error: str
    message: str
    solution: Optional[str] = None


class AnswerResponse(BaseModel):
    """답변 응답"""

    question: str
    answer: Optional[str]
    sources: List[Source]
    error: Optional[ErrorDetail] = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "question": "삼성에서 개발한 AI는?",
                    "answer": "삼성 가우스는 삼성전자의 자체 개발 생성 AI 모델입니다...",
                    "sources": [
                        {
                            "doc_name": "SPRI_AI_Brief.pdf",
                            "toc_section": "2. 기업/산업",
                            "page": 12,
                            "score": 0.95,
                            "rerank_score": 1.76,
                        }
                    ],
                    "error": None,
                }
            ]
        }
    }


class DocumentInfo(BaseModel):
    """문서 정보"""

    name: str
    collections: List[str]
    chunk_count: Optional[int] = None


class UploadResponse(BaseModel):
    """업로드 응답"""

    doc_name: str
    collections: List[str]
    total_points: int
    message: str


class HealthResponse(BaseModel):
    """헬스 체크 응답"""

    status: str
    qdrant: str
    ollama: str
    embedding_model: str
    llm_model: str


# ============================================
# 시작/종료 이벤트
# ============================================


@app.on_event("startup")
async def startup_event():
    """서버 시작 시 챗봇 및 공유 인스턴스 초기화"""
    global chatbot, embedding_generator, document_processor
    try:
        print("\n" + "=" * 70)
        print("[API] 서버 시작 중...")
        print("=" * 70)

        # 챗봇 초기화
        chatbot = DocumentChatbot()

        # 공유 인스턴스 초기화 (성능 최적화)
        from src.services.retrieval.embedding_generator import EmbeddingGenerator
        from src.services.document.processor import DocumentProcessor

        print("\n[INIT] 공유 인스턴스 초기화 중...")
        embedding_generator = EmbeddingGenerator(
            mode="local", verbose=True
        )  # model은 .env에서 로드
        document_processor = DocumentProcessor()
        print("[OK] 공유 인스턴스 초기화 완료\n")

        # ⭐ [추가] LLM 워밍업 (서버 켤 때 미리 로딩하기)
        print("[INIT] LLM 모델 워밍업 시작 (첫 로딩)...")
        try:
            # 빈 질문을 던져서 모델을 메모리에 올림
            chatbot.ask("test", verbose=False)
            print("[OK] LLM 워밍업 완료 (이제 사용자 답변은 빠릅니다!)")
        except Exception as e:
            print(f"[WARN] LLM 워밍업 실패 (첫 질문이 느릴 수 있음): {e}")

        print("[OK] 서버 준비 완료!")
        print("   API 문서: http://localhost:8000/docs")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\n[ERROR] 서버 시작 실패: {e}\n")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 정리"""
    print("\n[API] 서버 종료 중...")


# ============================================
# API 엔드포인트
# ============================================


@app.get("/", tags=["Root"])
def root():
    """
    API 루트

    서비스 기본 정보 반환
    """
    return {
        "service": "Document Assistant API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "health": "/health",
            "ask": "/ask",
            "documents": "/documents",
            "upload": "/upload",
        },
    }


@app.get("/health", response_model=HealthResponse, tags=["System"])
def health_check():
    """
    헬스 체크

    시스템 구성 요소의 연결 상태 확인
    """
    if chatbot is None:
        raise HTTPException(status_code=503, detail="Chatbot not initialized")

    try:
        # Qdrant 연결 확인
        chatbot.qdrant.client.get_collections()
        qdrant_status = "connected"
    except:
        qdrant_status = "disconnected"

    try:
        # Ollama 연결 확인
        chatbot.embedding_generator.embed_query("test")
        ollama_status = "connected"
    except:
        ollama_status = "disconnected"

    return {
        "status": (
            "healthy"
            if (qdrant_status == "connected" and ollama_status == "connected")
            else "degraded"
        ),
        "qdrant": qdrant_status,
        "ollama": ollama_status,
        "embedding_model": chatbot.config.embedding_model,
        "llm_model": chatbot.config.llm_model,
    }


@app.post("/ask", response_model=AnswerResponse, tags=["Chat"])
def ask_question(request: QuestionRequest):
    """
    질문하기

    RAG 파이프라인을 통해 질문에 답변

    - **question**: 사용자 질문 (필수, 1-1000자)
    - **doc_name**: 특정 문서로 제한 (선택)
    """
    if chatbot is None:
        raise HTTPException(status_code=503, detail="Chatbot not initialized")

    try:
        result = chatbot.ask(
            question=request.question,
            doc_name=request.doc_name,
            chat_history=request.history,
            verbose=False,  # API는 로그 최소화
        )

        # 에러가 있으면 HTTP 예외 발생
        if result["error"]:
            error = result["error"]
            status_code = 400

            # 에러 타입별 상태 코드
            if error.get("error") == "QdrantConnectionError":
                status_code = 503
            elif error.get("error") == "OllamaConnectionError":
                status_code = 503
            elif error.get("error") == "DocumentNotFoundError":
                status_code = 404

            raise HTTPException(status_code=status_code, detail=error)

        return result

    except HTTPException:
        raise
    except RAGException as e:
        raise HTTPException(status_code=400, detail=e.to_dict())
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalServerError",
                "message": str(e),
                "solution": "관리자에게 문의하세요",
            },
        )


@app.get("/documents", response_model=List[DocumentInfo], tags=["Documents"])
def list_documents():
    """
    문서 목록 조회

    업로드된 모든 문서 정보 반환
    """
    if chatbot is None:
        raise HTTPException(status_code=503, detail="Chatbot not initialized")

    try:
        collections = chatbot.qdrant.list_collections()

        # 컬렉션을 문서별로 그룹화
        doc_dict: Dict[str, List[str]] = {}

        for collection in collections:
            # "spri_ai_brief_2023년12월호_f_main" → 문서명 추출
            # 실제로는 Qdrant에서 메타데이터 조회 필요
            if collection.endswith("_main"):
                doc_name = collection.replace("_main", "")

                if doc_name not in doc_dict:
                    doc_dict[doc_name] = []

                doc_dict[doc_name].append(collection)

        # 결과 구성
        result = []
        for doc_name, colls in doc_dict.items():
            result.append(
                {
                    "name": doc_name,
                    "collections": colls,
                    "chunk_count": None,  # TODO: 실제 청크 수 조회
                }
            )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload", response_model=UploadResponse, tags=["Documents"])
def upload_document(
    file: UploadFile = File(..., description="PDF 파일"),
    background_tasks: BackgroundTasks = None,
):
    """
    문서 업로드 및 처리

    - PDF 파일만 지원
    - 자동으로 청킹, 임베딩, Qdrant 저장
    - 백그라운드에서 처리 (대용량 파일 대응)
    """
    if chatbot is None:
        raise HTTPException(status_code=503, detail="Chatbot not initialized")

    try:
        # 파일 검증
        if not file.filename.endswith(".pdf"):
            raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다")

        # 파일 크기 제한 (100MB)
        content = file.file.read()
        if len(content) > 100 * 1024 * 1024:
            raise HTTPException(
                status_code=400, detail="파일 크기는 100MB 이하여야 합니다"
            )

        # 임시 저장
        upload_dir = Path("./data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)

        # 파일명 안전하게 처리
        safe_filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = upload_dir / safe_filename

        with open(file_path, "wb") as f:
            f.write(content)

        file.file.close()

        # 문서 처리 (전역 인스턴스 재사용)
        chunks, config, metadata = document_processor.process(
            file_path=str(file_path), auto_optimize=True, verbose=False
        )

        # 임베딩 생성 (전역 인스턴스 재사용 - 모델 로딩 오버헤드 제거)
        texts = [chunk.page_content for chunk in chunks]
        embeddings = embedding_generator.embed_documents(texts)

        # Qdrant 저장
        result = chatbot.qdrant.store_document(
            chunks=chunks,
            metadata=metadata,
            embeddings=embeddings,
            doc_name=file.filename,  # 원본 파일명 사용
        )

        # 임시 파일 삭제 (백그라운드)
        if background_tasks:
            background_tasks.add_task(file_path.unlink, missing_ok=True)

        return {
            "doc_name": file.filename,
            "collections": result["collections"],
            "total_points": result["total_points"],
            "message": "문서 업로드 및 처리 완료",
        }

    except HTTPException:
        raise
    except Exception as e:
        # 에러 로깅 추가
        import traceback

        print(f"\n[ERROR] Upload failed:")
        print(f"Error: {str(e)}")
        print(f"Traceback:")
        traceback.print_exc()

        # 실패 시 임시 파일 삭제
        if "file_path" in locals() and file_path.exists():
            file_path.unlink()

        raise HTTPException(status_code=500, detail=f"업로드 실패: {str(e)}")


@app.delete("/documents/{doc_name}", tags=["Documents"])
def delete_document(doc_name: str):
    """
    문서 삭제

    Qdrant에서 해당 문서의 모든 컬렉션 삭제
    """
    if chatbot is None:
        raise HTTPException(status_code=503, detail="Chatbot not initialized")

    try:
        deleted = chatbot.qdrant.delete_document(doc_name)

        if deleted == 0:
            raise HTTPException(
                status_code=404, detail=f"문서 '{doc_name}'을 찾을 수 없습니다"
            )

        return {
            "doc_name": doc_name,
            "deleted_collections": deleted,
            "message": "문서 삭제 완료",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 실행
# ============================================

if __name__ == "__main__":
    import uvicorn

    print("\n" + "=" * 70)
    print("Document Assistant API 서버 시작")
    print("=" * 70)
    print("\n포트: 8000")
    print("문서: http://localhost:8000/docs")
    print("\n종료: Ctrl+C\n")

    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 개발 시에만
        log_level="info",
    )
