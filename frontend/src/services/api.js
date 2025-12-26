/**
 * API Service - Backend 통신
 *
 * Python FastAPI Backend와 통신합니다.
 * 환경변수 REACT_APP_API_URL로 변경 가능 (기본값: http://localhost:8000)
 */

import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5분 (대용량 문서 처리 위해)
  headers: {
    'Content-Type': 'application/json',
  },
});

// 에러 처리 인터셉터
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === 'ECONNREFUSED') {
      console.error('[API] Backend 서버에 연결할 수 없습니다.');
      return Promise.reject(new Error('Backend 서버가 실행되지 않았습니다.'));
    }
    return Promise.reject(error);
  }
);

// API 함수들
export const apiService = {
  // Health Check
  async checkHealth() {
    try {
      const response = await api.get('/health');
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // 질문하기
  async askQuestion(question, docName = null) {
    try {
      const response = await api.post('/ask', {
        question,
        doc_name: docName,
      });
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // 문서 목록 조회
  async listDocuments() {
    try {
      const response = await api.get('/documents');
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // 문서 업로드
  async uploadDocument(file, onProgress) {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await api.post('/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 600000, // 업로드는 10분까지 허용
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          if (onProgress) {
            onProgress(percentCompleted);
          }
        },
      });
      return response.data;
    } catch (error) {
      throw error;
    }
  },

  // 문서 삭제
  async deleteDocument(docName) {
    try {
      const response = await api.delete(`/documents/${docName}`);
      return response.data;
    } catch (error) {
      throw error;
    }
  },
};

export default apiService;
