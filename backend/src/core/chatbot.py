# chatbot.py
"""
RAG 기반 문서 챗봇 (Reranking 통합)

검색 파이프라인:
1. Vector Search (빠르게 10개 후보)
2. Cross-Encoder Reranking (정확하게 5개 선택)
3. LLM 답변 생성
"""

import os
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langsmith import traceable
from src.core.exceptions import (
    QdrantConnectionError,
    OllamaConnectionError,
    DocumentNotFoundError,
    SearchError,
    LLMGenerationError,
)
from src.services.retrieval.bm25_retriever import BM25Retriever, hybrid_search

# .env 파일 명시적 로딩 (수정됨!) ⭐
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

# 환경 감지
APP_ENV = os.getenv("APP_ENV", "production")
IS_PRODUCTION = APP_ENV == "production"

# 디버그: 환경 변수 확인
if os.getenv("DEBUG", "false").lower() == "true":
    print(f"\n[DEBUG] 환경 변수:")
    print(f"  .env 경로: {env_path}")
    print(f"  .env 존재: {env_path.exists()}")
    print(f"  APP_ENV: {APP_ENV}")
    print(f"  IS_PRODUCTION: {IS_PRODUCTION}")
    print()

if IS_PRODUCTION:
    from src.core.user_config import UserConfig as Config
else:
    from src.core import config as dev_config

    class Config:
        """개발용 설정 래퍼"""

        def __init__(self):
            self.qdrant_host = dev_config.QDRANT_HOST
            self.qdrant_port = dev_config.QDRANT_PORT
            self.qdrant_api_key = dev_config.QDRANT_API_KEY
            # Model Configuration (from .env)
            self.embedding_model = dev_config.EMBEDDING_MODEL
            self.llm_model = dev_config.LLM_MODEL
            self.llm_temperature = dev_config.LLM_TEMPERATURE
            self.top_k = 5
            self.score_threshold = 0.4
            # Reranking 설정
            self.rerank_enabled = True
            self.rerank_model = dev_config.RERANK_MODEL
            self.rerank_max_candidates = 10
            self.rerank_top_k = 3
            # BM25 설정 추가 ⭐
            self.bm25_enabled = dev_config.BM25_ENABLED
            self.bm25_vector_weight = dev_config.BM25_VECTOR_WEIGHT
            self.bm25_weight = dev_config.BM25_BM25_WEIGHT


from src.services.storage.qdrant_manager import QdrantManager
from src.services.retrieval.embedding_generator import EmbeddingGenerator
from src.services.retrieval.reranker import OptimizedReranker as Reranker

# LangSmith 설정
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "document-assistant-rag")


class DocumentChatbot:
    """
    RAG 기반 문서 QA 챗봇 (Reranking 통합)

    검색 전략:
    - Reranking OFF: Vector Search만 (빠름)
    - Reranking ON: Vector + Cross-Encoder (정확)
    """

    def __init__(self, config: Optional[Config] = None):
        """
        Args:
            config: 설정 객체 (None이면 자동 생성)
        """
        # 설정 로드
        if config is None:
            config = Config()

        self.config = config

        # 1. Qdrant 매니저 (연결 확인 포함)
        try:
            self.qdrant = QdrantManager(
                host=config.qdrant_host,
                port=config.qdrant_port,
                api_key=config.qdrant_api_key,
                embedding_dimension=1024,
                verbose=False,
            )
        except ConnectionError as e:
            # QdrantManager 내부에서 이미 ConnectionError 발생
            raise QdrantConnectionError(
                host=config.qdrant_host, port=config.qdrant_port
            )

        # 2. 임베딩 생성기 (먼저 생성)
        self.embedding_generator = EmbeddingGenerator(
            mode="local", model=config.embedding_model, verbose=False
        )

        # 3. Ollama 연결 확인 (생성 후 확인)
        try:
            self.embedding_generator.embed_query("test")
        except Exception as e:
            raise OllamaConnectionError(model=config.embedding_model)

        # 4. LLM 초기화
        self.llm = ChatOllama(
            model=config.llm_model,
            temperature=config.llm_temperature,
            streaming=True,
        )

        # 5. Reranker (지연 로딩)
        self._reranker = None
        self.rerank_enabled = config.rerank_enabled

        if self.rerank_enabled:
            self._init_reranker(model_size=config.rerank_model, verbose=True)

        # 검색 설정
        self.score_threshold = config.score_threshold

        # Reranking 설정
        if self.rerank_enabled:
            self.vector_top_k = config.rerank_max_candidates
            self.final_top_k = config.rerank_top_k
        else:
            self.vector_top_k = config.top_k
            self.final_top_k = config.top_k

        # 6. BM25 Retriever (선택적)
        self.bm25_enabled = getattr(config, "bm25_enabled", False)
        if self.bm25_enabled:
            self.bm25_retriever = BM25Retriever(
                qdrant_manager=self.qdrant, verbose=False
            )
            self.bm25_vector_weight = getattr(config, "bm25_vector_weight", 0.7)
            self.bm25_weight = getattr(config, "bm25_weight", 0.3)
        else:
            self.bm25_retriever = None

        # 초기화 메시지
        env_type = "프로덕션" if IS_PRODUCTION else "개발"

        print(f"\n{'='*70}")
        print(f"[INIT] Document Chatbot 초기화 ({env_type})")
        print(f"{'='*70}")

        if IS_PRODUCTION:
            print(f"  설정: 사용자 설정 (~/.document-assistant)")
        else:
            print(f"  설정: 개발 설정 (.env)")

        print(f"  Qdrant: {config.qdrant_host}:{config.qdrant_port}")
        print(f"  Embedding: {config.embedding_model}")
        print(f"  LLM: {config.llm_model}")
        print(f"  검색 전략:")

        if self.bm25_enabled:
            print(f"    1. Hybrid Search (Vector + BM25)")
            print(
                f"       - Weights: Vector {self.bm25_vector_weight:.1f} / BM25 {self.bm25_weight:.1f}"
            )
            if self.rerank_enabled:
                print(f"    2. Reranking: {config.rerank_model} → {self.final_top_k}개")
            print(f"       - Candidates: {self.vector_top_k}")
        elif self.rerank_enabled:
            print(
                f"    1. Vector Search: top_k={self.vector_top_k}, threshold={self.score_threshold}"
            )
            print(f"    2. Reranking: {config.rerank_model} → top_k={self.final_top_k}")
        else:
            print(
                f"    Vector Search만: top_k={self.vector_top_k}, threshold={self.score_threshold}"
            )

        if LANGCHAIN_TRACING_V2:
            print(f"  LangSmith: Enabled")

        print(f"{'='*70}\n")

    def _init_reranker(self, model_size: str = "auto", verbose: bool = False):
        """Reranker 초기화 (지연 로딩)"""
        self._reranker = Reranker(
            model_size=model_size, max_length=256, verbose=verbose
        )

    @traceable(name="rag_ask", tags=["rag", "chatbot"])
    def ask(
        self,
        question: str,
        doc_name: Optional[str] = None,
        verbose: bool = True,
    ) -> Dict:
        try:
            if verbose:
                print(f"\n{'='*70}")
                print(f"[QUESTION] {question}")
                print(f"{'='*70}\n")

            # 1. 임베딩
            if verbose:
                print("[1/4] 질문 임베딩 생성 중...")
            query_embedding = self._embed_query(question)

            # 2. Vector Search (또는 Hybrid Search)
            if verbose:
                search_type = (
                    "Hybrid Search (Vector + BM25)"
                    if self.bm25_enabled
                    else "Vector Search"
                )
                print(f"[2/4] {search_type} 중 (top_k={self.vector_top_k})...")

            search_results = self._search(
                query_embedding, question, doc_name
            )  # query 인자 추가!

            if not search_results:
                if verbose:
                    print("\n[WARNING] 검색 결과가 없습니다.\n")
                return {
                    "question": question,
                    "answer": "관련된 정보를 찾을 수 없습니다.",
                    "sources": [],
                    "error": None,
                }

            if verbose:
                print(f"   검색 결과: {len(search_results)}개 청크")
                for i, result in enumerate(search_results[:3], 1):
                    toc_section = result["metadata"].get("toc_section", "Unknown")
                    print(
                        f"   [{i}] 점수: {result['score']:.3f} | "
                        f"{toc_section} (p.{result['metadata']['page']})"
                    )
                if len(search_results) > 3:
                    print(f"   ... 외 {len(search_results) - 3}개")

            # 3. Reranking
            if self.rerank_enabled and self._reranker:
                if verbose:
                    print(
                        f"\n[3/4] Reranking 중 ({len(search_results)}개 → {self.final_top_k}개)..."
                    )

                try:
                    reranked_results = self._reranker.rerank(
                        query=question,
                        candidates=search_results,
                        top_k=self.final_top_k,
                    )

                    if verbose:
                        print(f"   [OK] Reranking 완료: {len(reranked_results)}개 선택")
                        for i, result in enumerate(reranked_results[:3], 1):
                            toc_section = result["metadata"].get(
                                "toc_section", "Unknown"
                            )
                            print(
                                f"   [{i}] Rerank: {result['rerank_score']:.3f} | "
                                f"Vector: {result['score']:.3f} | "
                                f"{toc_section}"
                            )

                    final_results = reranked_results

                except Exception as e:
                    if verbose:
                        print(f"\n[WARNING] Reranking 실패: {e}")
                        print(f"   Vector Search 결과 사용\n")
                    final_results = search_results[: self.final_top_k]
            else:
                if verbose:
                    print(f"\n[3/4] Reranking 건너뜀")
                final_results = search_results[: self.final_top_k]

            # 4. 답변 생성
            if verbose:
                print(f"\n[4/4] 답변 생성 중 (LLM: {self.llm.model})...")

            answer = self._generate_answer(question, final_results, verbose=verbose)

            if verbose:
                print(f"\n{'='*70}")
                print("[ANSWER]")
                print(f"{'='*70}")
                print(answer)
                print(f"\n{'='*70}")
                print("[SOURCES]")
                print(f"{'='*70}")

                sources = self._extract_sources(final_results)
                for i, source in enumerate(sources, 1):
                    toc_section = source.get("toc_section", "Unknown")
                    score_info = (
                        f"Rerank: {source.get('rerank_score', 0):.3f}"
                        if "rerank_score" in source
                        else f"Vector: {source['score']:.3f}"
                    )
                    print(
                        f"[{i}] {toc_section} (p.{source['page']}) | "
                        f"문서: {source['doc_name']} | {score_info}"
                    )
                print(f"{'='*70}\n")

            return {
                "question": question,
                "answer": answer,
                "sources": self._extract_sources(final_results),
                "search_results": final_results,
                "error": None,
            }

        except (
            QdrantConnectionError,
            OllamaConnectionError,
            DocumentNotFoundError,
        ) as e:
            return {
                "question": question,
                "answer": None,
                "sources": [],
                "error": e.to_dict(),
            }

        except Exception as e:
            return {
                "question": question,
                "answer": None,
                "sources": [],
                "error": {
                    "error": "UnexpectedError",
                    "message": f"예상치 못한 오류: {str(e)}",
                    "solution": "관리자에게 문의하세요",
                },
            }

    @traceable(name="embed_query", tags=["embedding"])
    def _embed_query(self, question: str) -> List[float]:
        return self.embedding_generator.embed_query(question)

    @traceable(name="vector_search", tags=["retrieval"])
    def _search(
        self, query_vector: List[float], query: str, doc_name: Optional[str] = None
    ) -> List[Dict]:
        """벡터 검색 또는 하이브리드 검색"""
        try:
            if doc_name:
                collections = self.qdrant.list_collections(doc_name)
                if not collections:
                    return []
            else:
                collections = None

            # 벡터 검색
            vector_results = self.qdrant.search(
                query_vector=query_vector,
                collection_names=collections,
                limit=self.vector_top_k,
                score_threshold=self.score_threshold,
            )
            # BM25 하이브리드 검색
            if self.bm25_enabled and self.bm25_retriever:
                bm25_results = self.bm25_retriever.search(
                    query=query, top_k=self.vector_top_k, collection_names=collections
                )

                # 하이브리드 결합
                results = hybrid_search(
                    query=query,
                    vector_results=vector_results,
                    bm25_results=bm25_results,
                    vector_weight=self.bm25_vector_weight,
                    bm25_weight=self.bm25_weight,
                    top_k=self.vector_top_k,
                )
            else:
                results = vector_results

            return results

        except Exception as e:
            print(f"   [ERROR] 검색 중 에러: {e}")  # ⭐
            import traceback

            traceback.print_exc()  # ⭐
            raise SearchError(str(e))

    def _detect_language(self, text: str) -> str:
        """
        질문 언어 감지

        규칙:cc
        1. 한글 포함 → 한국어
        2. 한글 없고 영어 포함 → 영어
        3. 둘 다 없음 → 한국어 (기본값)
        """
        # 한글 범위: AC00-D7A3
        has_korean = any("\uac00" <= c <= "\ud7a3" for c in text)

        if has_korean:
            return "Korean"

        # 영어 알파벳 체크
        has_english = any(c.isascii() and c.isalpha() for c in text)

        return "English" if has_english else "Korean"

    @traceable(name="generate_answer", tags=["generation"])
    def _generate_answer(
        self, question: str, search_results: List[Dict], verbose: bool = True
    ) -> str:
        """LLM으로 답변 생성"""

        import time

        if verbose:
            print("\n[답변 생성 중...]")

        # 컨텍스트 구성 (3b 모델: 균형잡힌 컨텍스트)
        context_parts = []
        for i, result in enumerate(search_results[:3], 1):
            toc_section = result["metadata"].get("toc_section", "Unknown")
            text = result["text"][:300]  # 3b 모델은 300자로 충분

            context_parts.append(
                f"[문서 {i}] {toc_section} (p.{result['metadata']['page']})\n{text}"
            )

        context = "\n\n".join(context_parts)
        context = context[:1000]  # 3b 모델은 1000자로 충분 (속도 최적화)

        # 언어 감지
        question_lang = self._detect_language(question)

        # LangChain 스타일 범용 프롬프트 (1b 모델 최적화)
        if question_lang == "Korean":
            prompt = f"""당신은 문서 기반 질의응답 전문가입니다. 주어진 문서에서만 정보를 추출하여 정확하게 답변하세요.

# 참고 문서
{context}

# 질문
{question}

# 답변 규칙 (반드시 준수)
1. 위 참고 문서에 명시된 내용만 사용
2. 문서에 없는 내용은 절대 추측하지 말 것
3. 답을 찾을 수 없으면 "문서에서 해당 정보를 찾을 수 없습니다"라고만 답변
4. 출처 페이지 번호 반드시 포함 (예: "3페이지에 따르면...")
5. 각 문장은 20단어 이내로 짧고 명확하게 작성
6. **맞춤법과 문법을 정확하게 지켜서 한국어로만 답변** (영어/일본어/중국어 절대 사용 금지)

# 답변 작성
답변:"""
        else:
            prompt = f"""You are a document-based Q&A expert. Extract information only from the given document and answer accurately.

# Reference Document
{context}

# Question
{question}

# Answer Rules (Must Follow)
1. Use only information explicitly stated in the document above
2. Never guess or add information not in the document
3. If answer not found, say only "I cannot find this information in the document"
4. Always include source page number (e.g., "According to page 3...")
5. Write 2-3 sentences, be concise
6. **Answer in English only**

# Answer
Answer:"""

        # 시작 시간
        start_time = time.time()
        first_token_time = None
        full_response = ""
        chunk_count = 0
        max_time = 120  # 30초 → 120초로 증가 (CPU 환경 고려)

        # LLM 호출
        try:
            for chunk in self.llm.stream(prompt):
                # 타임아웃 체크
                if time.time() - start_time > max_time:
                    raise TimeoutError(f"답변 생성 시간 초과 ({max_time}초)")

                if chunk_count == 0 and first_token_time is None:
                    first_token_time = time.time() - start_time
                    print(f"   [INFO] 첫 응답: {first_token_time:.1f}초\n")

                if chunk.content:
                    print(chunk.content, end="", flush=True)
                    full_response += chunk.content

                chunk_count += 1

            print()

        except KeyboardInterrupt:
            print("\n\n[중단] 사용자가 생성을 중단했습니다.")
            full_response += "\n\n[답변 생성 중단됨]"

        except TimeoutError as e:
            raise LLMGenerationError(self.llm.model, "시간 초과")

        except Exception as e:
            raise LLMGenerationError(self.llm.model, str(e))

        # 후처리
        full_response = self._clean_response(full_response)

        # 출처 자동 추가
        if "참고:" not in full_response and search_results:
            page = search_results[0]["metadata"]["page"]
            full_response += f"\n\n참고: p.{page}"

        # 통계
        elapsed = time.time() - start_time
        generation_time = elapsed - (first_token_time or 0)

        print(f"   📊 첫 토큰: {first_token_time:.1f}초")
        print(f"   📊 생성: {generation_time:.1f}초")
        print(f"   📊 전체: {elapsed:.1f}초")

        return full_response

    def _clean_response(self, text: str) -> str:
        """응답 정제"""
        import re

        # 1. 한자 제거
        text = re.sub(r"[一-龯]", "", text)

        # 2. 연속된 줄바꿈 정리
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)

        # 3. 앞뒤 공백 제거
        text = text.strip()

        return text

    def _extract_sources(self, search_results: List[Dict]) -> List[Dict]:
        sources = []
        for result in search_results:
            source = {
                "doc_name": result["metadata"]["doc_name"],
                "toc_section": result["metadata"].get("toc_section", "Unknown"),
                "page": result["metadata"]["page"],
                "score": result["score"],
            }
            # Rerank 점수 추가 (있으면)
            if "rerank_score" in result:
                source["rerank_score"] = result["rerank_score"]

            sources.append(source)

        return sources

    def chat(self, doc_name: Optional[str] = None):
        """대화형 모드"""
        print(f"\n{'='*70}")
        print("[CHAT MODE] 대화형 챗봇 모드")
        print(f"{'='*70}")
        print(f"Reranking: {'Enabled' if self.rerank_enabled else 'Disabled'}")
        print("\n종료하려면 'quit', 'exit', 'q'를 입력하세요.")
        print(f"{'='*70}\n")

        while True:
            try:
                question = input("질문: ").strip()

                if question.lower() in ["quit", "exit", "q"]:
                    print("\n챗봇을 종료합니다.\n")
                    break

                if not question:
                    continue

                self.ask(question, doc_name=doc_name, verbose=True)

            except KeyboardInterrupt:
                print("\n\n챗봇을 종료합니다.\n")
                break
            except Exception as e:
                print(f"\n[ERROR] {e}\n")


def create_chatbot() -> DocumentChatbot:
    """챗봇 생성"""
    return DocumentChatbot()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "chat":
            chatbot = create_chatbot()
            chatbot.chat()
        else:
            question = " ".join(sys.argv[1:])
            chatbot = create_chatbot()
            chatbot.ask(question)
    else:
        print("\n사용법:")
        print("  python chatbot.py chat")
        print('  python chatbot.py "질문"')
