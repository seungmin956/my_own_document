import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, FileText, MessageSquare, Trash2 } from 'lucide-react';
import apiService from '../services/api';
import '../styles/HomePage.css';

function HomePage() {
  const navigate = useNavigate();
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [backendStatus, setBackendStatus] = useState('checking');
  const [uploadQueue, setUploadQueue] = useState([]);

  useEffect(() => {
    checkBackend();
    loadDocuments();
  }, []);

  const checkBackend = async () => {
    try {
      await apiService.checkHealth();
      setBackendStatus('connected');
    } catch (error) {
      setBackendStatus('disconnected');
      console.error('Backend connection failed:', error);
    }
  };

  // ✅ 삭제 핸들러 함수
  const handleDelete = async (e, docName) => {
    e.stopPropagation(); // 카드 클릭 이벤트 전파 방지
    if (!window.confirm(`정말 '${docName}' 문서를 삭제하시겠습니까?`)) {
      return;
    }

    try {
      await apiService.deleteDocument(docName);
      // 목록에서 즉시 제거 (새로고침 없이 UI 반영)
      setDocuments(prev => prev.filter(doc => doc.name !== docName));
      alert('삭제되었습니다.');
    } catch (error) {
      console.error('Failed to delete:', error);
      alert('삭제 실패: ' + error.message);
    }
  };

  const loadDocuments = async () => {
    try {
      const docs = await apiService.listDocuments();
      setDocuments(docs);
    } catch (error) {
      console.error('Failed to load documents:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (event) => {
    const files = Array.from(event.target.files);
    if (files.length === 0) return;

    // PDF 파일만 필터링
    const pdfFiles = files.filter(file => file.name.endsWith('.pdf'));
    if (pdfFiles.length === 0) {
      alert('PDF 파일만 업로드 가능합니다.');
      return;
    }

    if (pdfFiles.length !== files.length) {
      alert(`${files.length - pdfFiles.length}개의 PDF가 아닌 파일은 제외되었습니다.`);
    }

    // 업로드 큐 초기화
    const queue = pdfFiles.map(file => ({
      file,
      name: file.name,
      status: 'waiting', // waiting, uploading, completed, error
      progress: 0,
      error: null,
    }));
    setUploadQueue(queue);

    // 동시 업로드 제한 (최대 5개)
    await uploadWithConcurrency(queue, 5);

    // 입력 초기화
    event.target.value = '';
  };

  const uploadWithConcurrency = async (queue, maxConcurrent) => {
    const pending = [...queue];
    const active = new Set();

    const uploadFile = async (item) => {
      // 상태 업데이트: uploading
      setUploadQueue(prev =>
        prev.map(q => q.name === item.name ? { ...q, status: 'uploading' } : q)
      );

      try {
        await apiService.uploadDocument(item.file, (progress) => {
          setUploadQueue(prev =>
            prev.map(q => q.name === item.name ? { ...q, progress } : q)
          );
        });

        // 상태 업데이트: completed
        setUploadQueue(prev =>
          prev.map(q => q.name === item.name ? { ...q, status: 'completed', progress: 100 } : q)
        );
      } catch (error) {
        // 상태 업데이트: error
        setUploadQueue(prev =>
          prev.map(q => q.name === item.name ? { ...q, status: 'error', error: error.message } : q)
        );
      } finally {
        active.delete(item);
      }
    };

    // 병렬 업로드 처리
    while (pending.length > 0 || active.size > 0) {
      // 빈 슬롯만큼 새 업로드 시작
      while (active.size < maxConcurrent && pending.length > 0) {
        const item = pending.shift();
        active.add(item);
        uploadFile(item);
      }

      // 잠시 대기 (CPU 과부하 방지)
      await new Promise(resolve => setTimeout(resolve, 100));
    }

    // 모든 업로드 완료 후 문서 목록 새로고침
    await loadDocuments();

    // 성공/실패 요약
    const completed = queue.filter(q => q.status === 'completed').length;
    const failed = queue.filter(q => q.status === 'error').length;

    if (failed === 0) {
      alert(`${completed}개 파일이 성공적으로 업로드되었습니다!`);
    } else {
      alert(`완료: ${completed}개, 실패: ${failed}개`);
    }

    // 큐 초기화 (3초 후)
    setTimeout(() => setUploadQueue([]), 3000);
  };

  return (
    <div className="home-page">
      <header className="app-header">
        <h1>📚 Document Assistant</h1>
        <p>AI-powered Document QA System</p>
        <div className={`status-badge ${backendStatus}`}>
          <span className="status-dot"></span>
          {backendStatus === 'connected' ? 'Connected' :
           backendStatus === 'checking' ? 'Connecting...' : 'Disconnected'}
        </div>
      </header>

      <main className="home-content">
        <section className="upload-section">
          <div className="upload-card">
            <Upload size={48} className="upload-icon" />
            <h2>문서 업로드</h2>
            <p>PDF 파일을 업로드하여 AI 질의응답을 시작하세요</p>
            <input
              type="file"
              accept=".pdf"
              multiple
              onChange={handleFileUpload}
              style={{ display: 'none' }}
              id="file-upload"
              disabled={uploadQueue.length > 0}
            />
            <label htmlFor="file-upload" className="upload-button">
              {uploadQueue.length > 0 ? '업로드 중...' : 'PDF 선택 (여러 개 가능)'}
            </label>

            {/* 업로드 큐 표시 */}
            {uploadQueue.length > 0 && (
              <div className="upload-queue">
                <h3>업로드 진행 상황 ({uploadQueue.filter(q => q.status === 'completed').length}/{uploadQueue.length})</h3>
                {uploadQueue.map((item, idx) => (
                  <div key={idx} className={`upload-item ${item.status}`}>
                    <div className="upload-item-info">
                      <span className="upload-filename">{item.name}</span>
                      <span className="upload-status">
                        {item.status === 'waiting' && '⏳ 대기 중'}
                        {item.status === 'uploading' && `📤 업로드 중 (${item.progress}%)`}
                        {item.status === 'completed' && '✅ 완료'}
                        {item.status === 'error' && `❌ 실패: ${item.error}`}
                      </span>
                    </div>
                    {item.status === 'uploading' && (
                      <div className="progress-bar">
                        <div className="progress-fill" style={{ width: `${item.progress}%` }}></div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        <section className="documents-section">
          <h2>
            <FileText size={24} />
            업로드된 문서 ({documents.length})
          </h2>

          {loading ? (
            <div className="loading">문서 목록을 불러오는 중...</div>
          ) : documents.length === 0 ? (
            <div className="empty-state">
              <p>업로드된 문서가 없습니다.</p>
              <p>PDF 파일을 업로드하여 시작하세요.</p>
            </div>
          ) : (
            <div className="documents-grid">
              {documents.map((doc, index) => (
                <div key={index} className="document-card">
                  <FileText size={32} className="doc-icon" />
                  <h3>{doc.name}</h3>
                  <p>{doc.collections.length} collection(s)</p>
                  
                  {/* 버튼 그룹을 위한 div 추가 (선택사항이지만 스타일링에 좋음) */}
                  <div style={{ display: 'flex', gap: '8px', marginTop: '10px' }}>
                    <button
                      className="chat-button"
                      onClick={() => navigate('/chat', { state: { docName: doc.name } })}
                      style={{ flex: 1 }}
                    >
                      <MessageSquare size={16} />
                      질문하기
                    </button>
                    
                    {/* ✅ 삭제 버튼 */}
                    <button 
                      className="delete-button"
                      onClick={(e) => handleDelete(e, doc.name)}
                      style={{ 
                        padding: '10px', 
                        background: '#fee2e2', 
                        color: '#ef4444',
                        border: 'none',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center'
                      }}
                      title="문서 삭제"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <button
          className="global-chat-button"
          onClick={() => navigate('/chat')}
        >
          <MessageSquare size={20} />
          전체 문서 검색
        </button>
      </main>
    </div>
  );
}

export default HomePage;