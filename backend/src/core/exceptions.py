# exceptions.py (새 파일)
"""
RAG 시스템 커스텀 예외

사용자 친화적인 에러 메시지와 해결 방법 제공
"""


class RAGException(Exception):
    """RAG 시스템 기본 예외"""

    def __init__(self, message: str, solution: str = None):
        self.message = message
        self.solution = solution
        super().__init__(self.message)

    def to_dict(self):
        """API 응답용 딕셔너리"""
        result = {
            "error": self.__class__.__name__,
            "message": self.message,
        }
        if self.solution:
            result["solution"] = self.solution
        return result


class QdrantConnectionError(RAGException):
    """Qdrant 서버 연결 실패"""

    def __init__(self, host: str, port: int):
        super().__init__(
            message=f"Qdrant 서버에 연결할 수 없습니다 ({host}:{port})",
            solution="Docker가 실행 중인지 확인하거나 'docker-compose up -d' 실행",
        )


class OllamaConnectionError(RAGException):
    """Ollama 서버 연결 실패"""

    def __init__(self, model: str):
        super().__init__(
            message=f"Ollama 서버 또는 모델({model})에 연결할 수 없습니다",
            solution="터미널에서 'ollama serve' 실행 또는 'ollama pull {model}' 실행",
        )


class DocumentNotFoundError(RAGException):
    """문서를 찾을 수 없음"""

    def __init__(self, doc_name: str):
        super().__init__(
            message=f"문서 '{doc_name}'을 찾을 수 없습니다",
            solution="문서가 업로드되었는지 확인하거나 문서 목록을 조회하세요",
        )


class SearchError(RAGException):
    """검색 실패"""

    def __init__(self, reason: str):
        super().__init__(
            message=f"검색 중 오류 발생: {reason}",
            solution="검색 조건을 변경하거나 관리자에게 문의하세요",
        )


class RerankingError(RAGException):
    """Reranking 실패"""

    def __init__(self, reason: str):
        super().__init__(
            message=f"Reranking 실패: {reason}",
            solution="Vector Search 결과로 대체됩니다",
        )


class LLMGenerationError(RAGException):
    """LLM 답변 생성 실패"""

    def __init__(self, model: str, reason: str):
        super().__init__(
            message=f"답변 생성 실패 (모델: {model}): {reason}",
            solution="Ollama 서버 상태를 확인하거나 다시 시도하세요",
        )


class FileProcessingError(RAGException):
    """파일 처리 실패"""

    def __init__(self, file_path: str, reason: str):
        super().__init__(
            message=f"파일 처리 실패 ({file_path}): {reason}",
            solution="파일이 손상되지 않았는지 확인하거나 다른 파일로 시도하세요",
        )
