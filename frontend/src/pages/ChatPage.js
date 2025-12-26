import React, { useState, useRef, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ArrowLeft, Send, Loader } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import apiService from '../services/api';
import '../styles/ChatPage.css';

function ChatPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const docName = location.state?.docName || null;

  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSend = async () => {
    if (!inputValue.trim() || loading) return;

    const userMessage = inputValue.trim();
    setInputValue('');

    // 사용자 메시지 추가
    setMessages(prev => [...prev, {
      type: 'user',
      content: userMessage,
      timestamp: new Date()
    }]);

    setLoading(true);

    try {
      const response = await apiService.askQuestion(userMessage, docName);

      // AI 응답 추가
      setMessages(prev => [...prev, {
        type: 'assistant',
        content: response.answer,
        sources: response.sources,
        timestamp: new Date()
      }]);
    } catch (error) {
      setMessages(prev => [...prev, {
        type: 'error',
        content: '죄송합니다. 답변을 생성하는 중 오류가 발생했습니다: ' + error.message,
        timestamp: new Date()
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-page">
      <header className="chat-header">
        <button className="back-button" onClick={() => navigate('/')}>
          <ArrowLeft size={20} />
          뒤로
        </button>
        <div className="chat-title">
          <h2>{docName ? `📄 ${docName}` : '📚 전체 문서'}</h2>
          <p>{docName ? '특정 문서 검색' : '모든 문서에서 검색'}</p>
        </div>
      </header>

      <main className="chat-main">
        <div className="messages-container">
          {messages.length === 0 ? (
            <div className="welcome-message">
              <h3>👋 환영합니다!</h3>
              <p>문서에 대해 궁금한 점을 질문해보세요.</p>
              <div className="example-questions">
                <p>예시 질문:</p>
                <ul>
                  <li>"이 문서의 주요 내용은 무엇인가요?"</li>
                  <li>"제1조의 내용을 설명해주세요"</li>
                  <li>"핵심 개념을 요약해주세요"</li>
                </ul>
              </div>
            </div>
          ) : (
            <>
              {messages.map((message, index) => (
                <div key={index} className={`message ${message.type}`}>
                  <div className="message-content">
                    <ReactMarkdown>{message.content}</ReactMarkdown>

                    {message.sources && message.sources.length > 0 && (
                      <div className="sources">
                        <p className="sources-title">📎 출처:</p>
                        {message.sources.map((source, idx) => (
                          <div key={idx} className="source-item">
                            <span className="source-doc">{source.doc_name}</span>
                            <span className="source-page">p.{source.page}</span>
                            <span className="source-section">{source.toc_section}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="message-time">
                    {message.timestamp.toLocaleTimeString('ko-KR', {
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </div>
                </div>
              ))}
            </>
          )}

          {loading && (
            <div className="message assistant loading-message">
              <Loader size={20} className="spinner" />
              <span>답변 생성 중...</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className="input-container">
          <textarea
            className="chat-input"
            placeholder="질문을 입력하세요... (Shift+Enter: 줄바꿈)"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={loading}
            rows={1}
          />
          <button
            className="send-button"
            onClick={handleSend}
            disabled={loading || !inputValue.trim()}
          >
            <Send size={20} />
          </button>
        </div>
      </main>
    </div>
  );
}

export default ChatPage;
