# Document Assistant Frontend

Electron + React 기반 데스크톱 애플리케이션

## 🚀 빠른 시작

### 1. 의존성 설치

```bash
# Frontend 의존성 설치
cd frontend
npm install

# Electron 의존성 설치
cd ../electron
npm install
```

### 2. 개발 모드 실행

```bash
# Terminal 1: Backend 서버 실행
cd backend
python -m uvicorn src.api.main:app --reload

# Terminal 2: React 개발 서버 실행
cd frontend
npm start

# Terminal 3: Electron 실행
cd electron
npm start
```

또는 통합 실행:

```bash
cd frontend
npm run electron:dev
```

### 3. 프로덕션 빌드

```bash
cd frontend
npm run electron:build
```

결과물:
- `frontend/dist/Document-Assistant-Setup-1.0.0.exe` (Windows)
- `frontend/dist/Document-Assistant-1.0.0.dmg` (macOS)
- `frontend/dist/Document-Assistant-1.0.0.deb` (Linux)

## 📁 프로젝트 구조

```
frontend/
├── public/               # 정적 파일
│   └── index.html
├── src/
│   ├── components/       # 재사용 가능한 컴포넌트
│   ├── pages/           # 페이지 컴포넌트
│   │   ├── HomePage.js
│   │   └── ChatPage.js
│   ├── services/        # API 통신
│   │   └── api.js
│   ├── styles/          # CSS 스타일
│   │   ├── index.css
│   │   ├── App.css
│   │   ├── HomePage.css
│   │   └── ChatPage.css
│   ├── App.js
│   └── index.js
├── package.json
└── README.md

electron/
├── main.js              # Electron 메인 프로세스
├── preload.js          # 보안 브릿지
└── package.json

backend/                 # Python FastAPI 백엔드
└── src/
    └── api/
        └── main.py
```

## 🎨 주요 기능

### 홈페이지
- PDF 문서 업로드
- 업로드된 문서 목록 표시
- Backend 연결 상태 표시
- 문서별 채팅 시작

### 채팅페이지
- 실시간 질의응답
- 출처 정보 표시 (페이지, 섹션)
- 신뢰도 점수 표시
- Markdown 렌더링

## 🔧 기술 스택

### Frontend
- **React 18** - UI 프레임워크
- **React Router** - 라우팅
- **Axios** - HTTP 클라이언트
- **React Markdown** - 마크다운 렌더링
- **Lucide React** - 아이콘

### Desktop
- **Electron** - 데스크톱 앱 래퍼
- **Electron Builder** - 앱 패키징

### Backend (Python)
- **FastAPI** - REST API
- **Qdrant** - 벡터 DB
- **Ollama** - 로컬 LLM

## 📡 API 통신

Frontend는 `localhost:8000`에서 실행되는 Python Backend와 통신합니다.

### 주요 엔드포인트

```javascript
// Health Check
GET /health

// 질문하기
POST /ask
{
  "question": "질문 내용",
  "doc_name": "문서명" // 선택사항
}

// 문서 목록
GET /documents

// 문서 업로드
POST /upload
FormData { file: File }

// 문서 삭제
DELETE /documents/{doc_name}
```

## 🎯 개발 팁

### Hot Reload
- React: `npm start` 실행 시 자동 리로드
- Backend: `uvicorn --reload` 옵션으로 자동 재시작

### Debugging
- React DevTools: 브라우저 확장 설치
- Electron DevTools: `Ctrl+Shift+I` (개발 모드)
- Backend: FastAPI Swagger UI (`http://localhost:8000/docs`)

### 환경 변수
```javascript
// Frontend
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Electron
const isDev = require('electron-is-dev');
```

## 📦 배포

### Windows
```bash
npm run electron:build
# 결과: dist/Document-Assistant-Setup-1.0.0.exe
```

### macOS
```bash
npm run electron:build
# 결과: dist/Document-Assistant-1.0.0.dmg
```

### Linux
```bash
npm run electron:build
# 결과: dist/Document-Assistant-1.0.0.deb
```

## 🐛 트러블슈팅

### Backend 연결 실패
```
문제: "Backend 서버에 연결할 수 없습니다"
해결:
1. Backend가 실행 중인지 확인
2. http://localhost:8000/health 접속 테스트
3. 방화벽 설정 확인
```

### Electron 창이 안 열림
```
문제: Electron 실행 시 창이 나타나지 않음
해결:
1. React 개발 서버 먼저 실행 (npm start)
2. http://localhost:3000 접속 확인
3. Electron 실행
```

### 빌드 실패
```
문제: electron-builder 빌드 실패
해결:
1. node_modules 삭제 후 재설치
2. npm cache clean --force
3. npm install 다시 실행
```

## 🔐 보안

- **Context Isolation**: Electron과 React 분리
- **Node Integration**: 비활성화
- **Preload Script**: 안전한 API만 노출
- **로컬 실행**: 모든 데이터가 사용자 PC에만 저장

## 📄 라이선스

MIT License

## 🤝 기여

이슈와 PR을 환영합니다!
