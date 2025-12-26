# tokenizer.py
"""
한국어 토크나이저 (KiwiPiePy 기반)
"""

from typing import List
from kiwipiepy import Kiwi
import re


class KoreanTokenizer:
    """
    한국어/영어 혼합 토크나이저

    - 한국어: KiwiPiePy 형태소 분석
    - 영어: 소문자 변환 + 공백 분리
    - 특수문자: 제거
    """

    def __init__(self):
        self.kiwi = Kiwi()

        # 불용어 (선택)
        self.stopwords = {
            "은",
            "는",
            "이",
            "가",
            "을",
            "를",
            "의",
            "에",
            "에서",
            "와",
            "과",
            "도",
            "만",
            "라",
            "로",
            "으로",
        }

    def tokenize(self, text: str) -> List[str]:
        """한글 형태소 분석 토큰화 (법률 용어 보존)"""
        tokens = []

        # 정규식으로 법률 조항 패턴 먼저 추출
        legal_pattern = r"제\d+조|제\d+항|제\d+호"
        legal_terms = re.findall(legal_pattern, text)

        # Kiwi 형태소 분석
        result = self.kiwi.tokenize(text)

        for token in result:
            # 명사, 동사, 형용사, 영문, 숫자만 추출
            if token.tag in ["NNG", "NNP", "VV", "VA", "SL", "SN"]:
                word = token.form.lower()
                # 길이 1인 한글 제외 (조사 등)
                if len(word) > 1 or word.isascii():
                    tokens.append(word)

        # 법률 용어 추가 (중복 제거)
        tokens.extend([term for term in legal_terms if term not in tokens])

        return tokens

    def tokenize_for_indexing(self, text: str) -> List[str]:
        """
        인덱싱용 토큰화 (더 많이 추출)

        - 불용어 제거 안 함
        - 1글자도 포함
        """
        tokens = []
        result = self.kiwi.tokenize(text)

        for token in result:
            form = token.form
            tag = token.tag

            # 의미 있는 품사만
            if tag.startswith(("N", "V", "M", "SL", "SN")):
                tokens.append(form.lower() if tag == "SL" else form)

        return tokens


# 사용 예시
if __name__ == "__main__":
    tokenizer = KoreanTokenizer()

    # 테스트
    texts = [
        "삼성전자는 AI '삼성 가우스'를 공개했다",
        "제17조 제3항에 따르면",
        "What is Samsung Gauss?",
    ]

    for text in texts:
        tokens = tokenizer.tokenize(text)
        print(f"\n원본: {text}")
        print(f"토큰: {tokens}")
