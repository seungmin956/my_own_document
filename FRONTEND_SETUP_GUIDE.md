# 🎨 프론트엔드 설정 가이드

Electron + React 데스크톱 앱 개발 가이드입니다.

## ✅ 완료된 작업

### 1. 프로젝트 구조 생성 ✅
```
document-assistant/
├── frontend/            # React 애플리케이션
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   │   ├── HomePage.js      # 메인 페이지
│   │   │   └── ChatPage.js      # 채팅 페이지
│   │   ├── services/
│   │   │   └── api.js           # Backend API 통신
│   │   ├── styles/
│   │   │   ├── index.css
│   │   │   ├── App.css
│   │   │   ├── HomePage.css
│   │   │   └── ChatPage.css
│   │   ├── App.js
│   │   └── index.js
│   ├── package.json
│   └── README.md
│
├── electron/           # Electron 래퍼
│   ├── main.js        # 메인 프로세스
│   ├── preload.js     # 보안 브릿지
│   └── package.json
│
└── backend/           # Python FastAPI (기존)
    └── src/
        └── api/
            └── main.py
```

### 2. 핵심 파일 작성 ✅
- ✅ Electron 메인 프로세스 (Python Backend 자동 실행)
- ✅ React 라우팅 (HomePage, ChatPage)
- ✅ API 서비스 (Backend 통신)
- ✅ UI 컴포넌트 (문서 업로드, 채팅)
- ✅ 스타일링 (모던한 UI/UX)

---

## 🚀 다음 단계

### Step 1: 의존성 설치

```bash
# 1. Frontend 패키지 설치
cd frontend
npm install

# 2. Electron 패키지 설치
cd ../electron
npm install
```

**설치되는 주요 패키지:**
- react, react-dom, react-router-dom
- axios (HTTP 클라이언트)
- react-markdown (마크다운 렌더링)
- lucide-react (아이콘)
- electron, electron-builder

---

### Step 2: 개발 모드 실행

#### 방법 A: 개별 실행 (권장 - 디버깅 쉬움)

**Terminal 1 - Backend**
```bash
cd backend
python -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

**Terminal 2 - React**
```bash
cd frontend
npm start
```

**Terminal 3 - Electron**
```bash
cd electron
npm start
```

#### 방법 B: 통합 실행

```bash
cd frontend
npm run electron:dev
```

---

### Step 3: 동작 확인

#### ✅ 체크리스트

1. **Backend 실행 확인**
   ```bash
   # 브라우저에서 접속
   http://localhost:8000/docs

   # 또는 curl
   curl http://localhost:8000/health
   ```

2. **React 앱 확인**
   ```bash
   # 브라우저 자동 열림
   http://localhost:3000

   # 홈페이지 표시되는지 확인
   ```

3. **Electron 창 확인**
   - 3초 후 Electron 창이 열림
   - 상단에 "Connected" 배지 표시
   - 문서 업로드 카드 표시

---

## 🎯 기능 테스트

### 1. PDF 업로드 테스트

```
1. "PDF 선택" 버튼 클릭
2. backend/data/ 폴더의 PDF 선택
3. "업로드 중..." 메시지 확인
4. "문서가 성공적으로 업로드되었습니다!" 알림
5. 문서 카드에 추가되는지 확인
```

### 2. 채팅 테스트

```
1. 문서 카드의 "질문하기" 버튼 클릭
2. 질문 입력: "이 문서의 주요 내용은?"
3. "답변 생성 중..." 스피너 표시
4. AI 응답 + 출처 정보 표시
5. 출처에 페이지, 섹션, 신뢰도 점수 확인
```

### 3. 전체 문서 검색 테스트

```
1. 우측 하단 "전체 문서 검색" 버튼 클릭
2. 모든 문서를 대상으로 질문
3. 여러 문서에서 검색된 출처 확인
```

---

## 📦 프로덕션 빌드

### Windows용 실행 파일 생성

```bash
cd frontend
npm run electron:build
```

**결과물:**
```
frontend/dist/
└── Document-Assistant-Setup-1.0.0.exe
```

**사용자 배포:**
1. `.exe` 파일을 사용자에게 전달
2. 사용자가 설치 실행
3. `C:\Program Files\Document Assistant\` 설치
4. 바탕화면 아이콘 생성
5. 클릭하면 앱 실행

### macOS / Linux 빌드

```bash
# macOS
npm run electron:build -- --mac
# 결과: dist/Document-Assistant-1.0.0.dmg

# Linux
npm run electron:build -- --linux
# 결과: dist/Document-Assistant-1.0.0.deb
```

---

## 🎨 UI/UX 특징

### 디자인 콘셉트
- **그라데이션 헤더**: 보라색 계열 (전문적이고 모던)
- **카드 기반 레이아웃**: 정보 구조화
- **부드러운 애니메이션**: 호버, 클릭 시 변화
- **반응형 그리드**: 창 크기에 따라 자동 조정

### 색상 팔레트
```css
Primary: #667eea (보라)
Secondary: #764ba2 (짙은 보라)
Background: #f5f7fa (연한 회색)
Text: #1f2937 (검정)
Success: #10b981 (녹색)
Error: #ef4444 (빨강)
```

### 주요 컴포넌트
- **Upload Card**: 드래그 앤 드롭 느낌의 업로드 UI
- **Document Card**: 호버 시 살짝 떠오르는 효과
- **Chat Bubble**: 메신저 스타일 말풍선
- **Floating Button**: 우측 하단 고정 버튼

---

## 🔧 커스터마이징

### 1. 색상 변경

`frontend/src/styles/HomePage.css`:
```css
/* 그라데이션 색상 변경 */
background: linear-gradient(135deg, #YOUR_COLOR1 0%, #YOUR_COLOR2 100%);
```

### 2. 로고 추가

```bash
# 아이콘 파일 준비
frontend/assets/
├── icon.ico    # Windows (256x256)
├── icon.icns   # macOS
└── icon.png    # Linux

# package.json에 자동 적용됨
```

### 3. 앱 이름 변경

`frontend/package.json`:
```json
{
  "build": {
    "productName": "Your App Name",
    "appId": "com.yourcompany.yourapp"
  }
}
```

---

## 🐛 문제 해결

### 1. Backend 연결 안됨

**증상:** "Disconnected" 배지 표시

**해결:**
```bash
# Backend 실행 확인
cd backend
python -m uvicorn src.api.main:app --reload

# 포트 확인
netstat -an | grep 8000

# 방화벽 확인
# Windows Defender에서 Python 허용
```

### 2. Electron 창 안 열림

**증상:** `npm start` 후 창 없음

**해결:**
```bash
# React 개발 서버 먼저 실행
cd frontend
npm start

# 브라우저에서 확인
http://localhost:3000

# Electron 실행
cd ../electron
npm start
```

### 3. 빌드 실패

**증상:** `electron-builder` 에러

**해결:**
```bash
# 캐시 정리
cd frontend
rm -rf node_modules
npm cache clean --force

# 재설치
npm install

# 빌드 재시도
npm run electron:build
```

### 4. PDF 업로드 실패

**증상:** "업로드 실패" 메시지

**해결:**
```bash
# Backend 로그 확인
# Terminal에서 에러 메시지 확인

# Python 의존성 확인
cd backend
pip install -r requirements.txt

# Qdrant 실행 확인
docker ps | grep qdrant
```

---

## 📚 추가 개발

### 컴포넌트 추가

```bash
# 새 컴포넌트 생성
frontend/src/components/YourComponent.js
frontend/src/styles/YourComponent.css
```

```javascript
// YourComponent.js
import React from 'react';
import './YourComponent.css';

function YourComponent() {
  return (
    <div className="your-component">
      {/* Your content */}
    </div>
  );
}

export default YourComponent;
```

### API 엔드포인트 추가

```javascript
// frontend/src/services/api.js
export const apiService = {
  // 기존 함수들...

  // 새 엔드포인트 추가
  async yourNewEndpoint(params) {
    try {
      const response = await api.post('/your-endpoint', params);
      return response.data;
    } catch (error) {
      throw error;
    }
  },
};
```

---

## 🎉 완료!

이제 다음을 실행하면 됩니다:

```bash
# 1. 의존성 설치
cd frontend && npm install
cd ../electron && npm install

# 2. 개발 모드 실행
# Terminal 1
cd backend && python -m uvicorn src.api.main:app --reload

# Terminal 2
cd frontend && npm start

# Terminal 3
cd electron && npm start
```

데스크톱 앱이 열리고 문서를 업로드하여 AI에게 질문할 수 있습니다! 🚀
