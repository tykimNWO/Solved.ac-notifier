import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Sparkles, Brain, Code2, MessageSquare, FileCode2, Search, Code, Notebook, CheckCircle2 } from 'lucide-react';
import CodeMirror from '@uiw/react-codemirror';
import { python } from '@codemirror/lang-python';
import { markdown } from '@codemirror/lang-markdown';
import { vscodeDark } from '@uiw/codemirror-theme-vscode';

const API_BASE_URL = 'http://localhost:8000/api';

const getTierInfo = (tier: number) => {
  if (!tier || tier === 0) return { name: "Unrated", color: "text-gray-400", bg: "bg-gray-400/10", border: "border-gray-400/30" };
  if (tier <= 5) return { name: `Bronze ${6 - tier}`, color: "text-[#ad5600]", bg: "bg-[#ad5600]/10", border: "border-[#ad5600]/30" };
  if (tier <= 10) return { name: `Silver ${11 - tier}`, color: "text-[#435f7a]", bg: "bg-[#435f7a]/10", border: "border-[#435f7a]/30" };
  if (tier <= 15) return { name: `Gold ${16 - tier}`, color: "text-[#ec9a00]", bg: "bg-[#ec9a00]/10", border: "border-[#ec9a00]/30" };
  if (tier <= 20) return { name: `Platinum ${21 - tier}`, color: "text-[#27e2a4]", bg: "bg-[#27e2a4]/10", border: "border-[#27e2a4]/30" };
  if (tier <= 25) return { name: `Diamond ${26 - tier}`, color: "text-[#00b4fc]", bg: "bg-[#00b4fc]/10", border: "border-[#00b4fc]/30" };
  return { name: `Ruby ${31 - tier}`, color: "text-[#ff0062]", bg: "bg-[#ff0062]/10", border: "border-[#ff0062]/30" };
};

function App() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<{role: 'user' | 'ai', text: string, elapsed?: number}[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [thinkingText, setThinkingText] = useState('');
  const sendTimeRef = useRef<number>(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const [activeTab, setActiveTab] = useState<'chat' | 'problem' | 'editor' | 'memo'>('chat');
  const [searchProblemId, setSearchProblemId] = useState('');
  const [problemData, setProblemData] = useState<any>(null);
  const [userCode, setUserCode] = useState('# 여기에 파이썬 코드를 작성하세요\n\nimport sys\n\ndef solution():\n    # input = sys.stdin.readline\n    pass\n\nif __name__ == "__main__":\n    solution()');
  const [judgeResults, setJudgeResults] = useState<any[] | null>(null);
  
  // 메모 전용 상태
  const [memo, setMemo] = useState('');
  const [isSavingMemo, setIsSavingMemo] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // 1. 초기 로딩 시 DB에서 히스토리 가져오기
  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/chat/history`);
        const data = await res.json();
        if (data.status === 'success') {
          setMessages(data.history);
        }
      } catch (err) {
        console.error("히스토리 로드 실패:", err);
      }
    };
    fetchHistory();
  }, []);

  // 메시지 추가 시 또는 탭 전환 시 자동 스크롤
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, activeTab]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [input]);

  const suggestions = [
    { icon: <Sparkles className="w-5 h-5 text-yellow-400" />, title: "오늘의 추천", text: "나의 현재 실력에 딱 맞는 플래티넘 도약용 문제 추천해줘." },
    { icon: <Brain className="w-5 h-5 text-purple-400" />, title: "약점 집중 보완", text: "최근에 많이 틀린 태그 위주로 어려운 문제 찾아줘." },
    { icon: <Code2 className="w-5 h-5 text-blue-400" />, title: "가벼운 두뇌 회전", text: "오늘은 머리 식히게 골드 하위 구현 문제 줘." },
  ];

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;
    const userText = input;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', text: userText }, { role: 'ai', text: '' }]);
    setIsLoading(true);
    setThinkingText('');
    sendTimeRef.current = Date.now();

    try {
      const res = await fetch(`${API_BASE_URL}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message: userText, 
          history: messages.map(msg => ({role: msg.role, text: msg.text})),
          current_problem_id: parseInt(searchProblemId) || null
        }),
      });
      if (!res.body) throw new Error("스트리밍 오류");
      const reader = res.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let done = false;
      setIsLoading(true);
      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;
        if (value) {
          const chunk = decoder.decode(value, { stream: true });
          setMessages(prev => {
            const newMessages = [...prev];
            const lastIdx = newMessages.length - 1;
            const updatedText = newMessages[lastIdx].text + chunk;
            newMessages[lastIdx] = { ...newMessages[lastIdx], text: updatedText };

            // 사고 과정 실시간 추출 → 로딩 상태에 표시
            const tStart = updatedText.indexOf('[THOUGHT]');
            const tEnd = updatedText.indexOf('[/THOUGHT]');
            if (tStart !== -1) {
              if (tEnd !== -1) {
                setThinkingText(updatedText.substring(tStart + 9, tEnd).trim());
              } else {
                setThinkingText(updatedText.substring(tStart + 9).trim());
              }
            }

            return newMessages;
          });
        }
      }
      setMessages(prev => {
        const newMessages = [...prev];
        const lastIdx = newMessages.length - 1;
        const finalMessage = newMessages[lastIdx].text;

        // 정규식으로 [LOAD_PROBLEM:숫자] 형태를 찾습니다.
        const match = finalMessage.match(/\[LOAD_PROBLEM:(\d+)\]/);
        
        if (match) {
          const problemId = match[1]; // 숫자(예: 1005)만 추출
          
          // 사용자 화면에서는 이 태그가 보이지 않도록 깔끔하게 지워줍니다.
          newMessages[lastIdx].text = finalMessage.replace(match[0], '').trim() + '\n\n⏳ 추천된 문제(워크스페이스)로 잠시 후 이동합니다...';
          // 1. 메시지 업데이트 (안내 문구 추가)
          setMessages(prev => {
            const updated = [...prev];
            updated[updated.length - 1].text += "\n\n🎯 태영님께 최적화된 문제를 찾았습니다. 3초 후 워크스페이스로 이동합니다...";
            return updated;
          });
          
          // 2초 뒤에 탭을 전환하고 문제를 로드합니다. (자연스러운 UX를 위해 약간의 딜레이)
          setTimeout(() => {
            setActiveTab('problem'); // 워크스페이스 탭으로 자동 이동!
            loadProblem(problemId);  // 수정한 함수를 통해 즉시 데이터 로드!
          }, 3000);
        }
        return newMessages;
      });
      // 응답 시간 계산 후 마지막 AI 메시지에 기록
      const elapsed = Math.round((Date.now() - sendTimeRef.current) / 1000);
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = { ...updated[updated.length - 1], elapsed };
        return updated;
      });
      setIsLoading(false);
      setThinkingText('');
    } catch (error) {
      console.error("통신 오류:", error);
      setIsLoading(false);
      setThinkingText('');
    }
  };

  const handleClearHistory = async () => {
    if (!confirm("모든 대화 내역을 삭제하시겠습니까?")) return;
    try {
      const res = await fetch(`${API_BASE_URL}/chat/history`, { method: 'DELETE' });
      if (res.ok) {
        setMessages([]);
      }
    } catch (err) {
      console.error("히스토리 삭제 실패:", err);
    }
  };

  const fetchMemo = async (pid: number) => {
    try {
      const res = await fetch(`${API_BASE_URL}/memo/${pid}`);
      const data = await res.json();
      setMemo(data.content || '');
    } catch (error) { console.error("메모 로드 실패:", error); }
  };

  const loadProblem = async (specificId?: string) => {
    const targetId = specificId || searchProblemId;
    if (!targetId || !targetId.trim()) return;
    try {
      const res = await fetch(`${API_BASE_URL}/problem/${targetId}`);
      if (!res.ok) throw new Error("문제를 찾을 수 없습니다.");
      const response = await res.json();
      if (response.status === 'success') {
        setProblemData(response.data);
        fetchMemo(parseInt(targetId));
        if (specificId) setSearchProblemId(targetId);
      }
    } catch (error: any) { alert("문제 로드 실패: " + error.message); }
  };

  const handleJudge = async () => {
    if (!searchProblemId || isLoading) return;
    setIsLoading(true);
    setJudgeResults(null);
    try {
      const res = await fetch(`${API_BASE_URL}/judge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ problem_id: parseInt(searchProblemId), code: userCode }),
      });
      const response = await res.json();
      if (response.status === 'success') setJudgeResults(response.results);
      else alert(response.detail || "채점 중 오류 발생");
    } catch (error) { alert("서버 연결 실패"); } finally { setIsLoading(false); }
  };

  const handleSaveMemo = async () => {
    if (!searchProblemId) return;
    setIsSavingMemo(true);
    try {
      await fetch(`${API_BASE_URL}/memo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ problem_id: parseInt(searchProblemId), content: memo }),
      });
      alert("학습 내용이 저장되었습니다.");
    } catch (error) { alert("메모 저장 실패"); } finally { setIsSavingMemo(false); }
  };

  return (
    <div className="h-[100dvh] flex flex-col bg-[#131314] text-gray-100 font-sans overflow-hidden">
      <div className="flex-1 overflow-y-auto custom-scrollbar pb-24">
        
        {/* Tab 1: AI 채팅 */}
        {activeTab === 'chat' && (
          <div className="max-w-4xl mx-auto p-6 flex flex-col items-center">
            {messages.length === 0 ? (
              <div className="mt-10 md:mt-20 w-full animate-fade-in-up">
                <div className="flex flex-col items-center text-center mb-10">
                  <div>
                    <h1 className="text-3xl font-semibold mb-4 text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-purple-400 to-purple-600">안녕하세요, 태영님</h1>
                    <p className="text-transparent bg-clip-text bg-gradient-to-r from-gray-400 to-gray-500 text-sm">최상의 알고리즘 퍼포먼스를 위해 무엇을 도와드릴까요?</p>
                  </div>
                  {messages.length > 0 && (
                    <button onClick={handleClearHistory} className="px-4 py-2 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 rounded-xl text-red-400 text-xs transition-all">
                      대화 초기화
                    </button>
                  )}
                </div>
                <div className="grid grid-cols-1 gap-3 w-full max-w-2xl mx-auto">
                  {suggestions.map((item, idx) => (
                    <button key={idx} onClick={() => setInput(item.text)} className="flex items-center p-4 bg-[#1E1F20] rounded-2xl border border-gray-800/50 hover:bg-[#2A2B2F] transition-all text-left">
                      <div className="mr-4 p-2 bg-[#131314] rounded-xl">{item.icon}</div>
                      <div>
                        <div className="font-semibold text-sm text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-400">{item.title}</div>
                        <div className="text-xs text-gray-500">{item.text}</div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="w-full max-w-4xl">
                <div className="flex justify-end mb-4">
                  <button onClick={handleClearHistory} className="px-3 py-1 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 rounded-lg text-red-400 text-xs transition-all">
                    대화 초기화
                  </button>
                </div>
                <div ref={scrollRef} className="w-full space-y-6 py-4 overflow-y-auto max-h-[70vh] scroll-smooth custom-scrollbar">
                  {messages.map((msg, i) => {
                    // [THOUGHT] 태그에서 사고 과정과 본문을 분리
                    let thoughtText = '';
                    let contentText = msg.text;
                    if (msg.role === 'ai') {
                      const tStart = msg.text.indexOf('[THOUGHT]');
                      const tEnd = msg.text.indexOf('[/THOUGHT]');
                      if (tStart !== -1 && tEnd !== -1) {
                        thoughtText = msg.text.substring(tStart + 9, tEnd).trim();
                        contentText = msg.text.substring(tEnd + 10).trim();
                      } else if (tStart !== -1) {
                        thoughtText = msg.text.substring(tStart + 9).trim();
                        contentText = '';
                      }
                    }

                    const isStreaming = isLoading && i === messages.length - 1;

                    return (
                      <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div className={`max-w-[85%] rounded-2xl ${msg.role === 'user' ? 'bg-gradient-to-br from-blue-500 via-purple-500 to-purple-600 text-white shadow-lg p-4' : ''}`}>
                          {msg.role === 'ai' && isStreaming && !contentText ? (
                            // 로딩 상태: 사고 과정을 독립 카드로 표시
                            <div className="p-4 bg-[#1A1B1E] border border-blue-500/20 rounded-2xl animate-pulse-subtle">
                              <div className="flex items-center gap-2 mb-2 text-blue-400 font-semibold text-sm">
                                <Brain className="w-4 h-4 animate-spin" style={{ animationDuration: '3s' }} /> 분석 중...
                              </div>
                              <p className="text-xs text-gray-400 leading-relaxed">{thinkingText || '질문을 분석하고 최적의 문제를 탐색하고 있습니다...'}</p>
                              <div className="flex gap-1 items-center mt-3">
                                <div className="w-1.5 h-1.5 bg-blue-400/50 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                                <div className="w-1.5 h-1.5 bg-blue-400/50 rounded-full animate-bounce" style={{ animationDelay: '200ms' }}></div>
                                <div className="w-1.5 h-1.5 bg-blue-400/50 rounded-full animate-bounce" style={{ animationDelay: '400ms' }}></div>
                              </div>
                            </div>
                          ) : msg.role === 'ai' ? (
                            // 답변 완료 상태: 사고 과정 + 본문
                            <div className="p-4 bg-[#1E1F20] text-gray-200 border border-gray-800 rounded-2xl">
                              {thoughtText && (
                                <details className="mb-3 group">
                                  <summary className="flex items-center gap-2 cursor-pointer text-xs text-blue-400/70 hover:text-blue-400 transition-colors select-none">
                                    <Brain className="w-3 h-3" />
                                    <span className="font-semibold">사고 과정 보기</span>
                                    <span className="text-gray-600 group-open:hidden">▶</span>
                                    <span className="text-gray-600 hidden group-open:inline">▼</span>
                                  </summary>
                                  <div className="mt-2 p-3 bg-black/20 border border-white/5 rounded-xl text-xs text-gray-400 italic leading-relaxed">
                                    {thoughtText}
                                  </div>
                                </details>
                              )}
                              {contentText && <p className="text-sm leading-relaxed whitespace-pre-wrap">{contentText}</p>}
                              {msg.elapsed !== undefined && (
                                <p className="text-[10px] text-gray-600 mt-3 text-right">⏱ 응답 시간: {msg.elapsed}초</p>
                              )}
                            </div>
                          ) : (
                            // 사용자 메시지
                            <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.text}</p>
                          )}
                        </div>
                      </div>
                    );
                  })}
              </div>
          </div>
            )}
          </div>
        )}

        {/* Tab 2: 워크스페이스 */}
        {activeTab === 'problem' && (
          <div className="p-6">
            <div className="flex gap-2 mb-8 bg-[#1E1F20] p-1.5 rounded-2xl border border-gray-800 focus-within:border-purple-500/50 transition-all">
              <input type="number" value={searchProblemId} onChange={(e) => setSearchProblemId(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && loadProblem()} placeholder="문제 번호 입력" className="flex-1 bg-transparent p-2 outline-none text-white text-sm" />
              <button onClick={() => loadProblem()} className="bg-gradient-to-r from-blue-500 via-purple-500 to-purple-600 hover:opacity-90 p-2.5 rounded-xl transition-all shadow-lg shadow-purple-500/20"><Search className="w-4 h-4 text-white" /></button>
            </div>
            {problemData && (
              <div className="space-y-8 text-sm">
                
                {/* 문제 상단 정보 (제목, 티어, 태그) */}
                <div className="mb-6 space-y-4">
                  <div className="flex flex-wrap items-center gap-3">
                    <span className={`px-2.5 py-1 text-xs font-bold rounded-lg border shadow-sm ${getTierInfo(problemData.tier).bg} ${getTierInfo(problemData.tier).color} ${getTierInfo(problemData.tier).border}`}>
                      {getTierInfo(problemData.tier).name}
                    </span>
                    <h2 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-white to-gray-300">
                      {searchProblemId}. {problemData.title || '문제'}
                    </h2>
                    {problemData.is_solved && (
                      <span className="flex items-center gap-1.5 px-3 py-1 text-xs font-bold text-green-400 bg-green-500/10 border border-green-500/30 rounded-full shadow-sm">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Solved!
                      </span>
                    )}
                  </div>
                  
                  {problemData.tags && problemData.tags.length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-2">
                      {problemData.tags.map((tag: string, idx: number) => (
                        <span key={idx} className="px-3 py-1 text-xs text-purple-300 bg-purple-500/10 border border-purple-500/30 rounded-full shadow-sm shadow-purple-500/10 backdrop-blur-sm">
                          #{tag}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                <div className="space-y-4">
                  <h3 className="text-lg font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-400 inline-block border-b border-purple-500/30 pb-1">문제 설명</h3>
                  <div className="prose prose-invert prose-sm max-w-none text-gray-300 leading-relaxed" dangerouslySetInnerHTML={{ __html: problemData.description }} />
                </div>
                <div className="grid grid-cols-1 gap-4">
                  <div className="bg-[#1E1F20] p-5 rounded-2xl border border-gray-800">
                    <h3 className="text-lg font-bold mb-2 text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-400">입력</h3>
                    <div className="prose prose-invert" dangerouslySetInnerHTML={{ __html: problemData.input_desc }} />
                  </div>
                  <div className="bg-[#1E1F20] p-5 rounded-2xl border border-gray-800">
                    <h3 className="text-lg font-bold mb-2 text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-400">출력</h3>
                    <div className="prose prose-invert" dangerouslySetInnerHTML={{ __html: problemData.output_desc }} />
                  </div>
                </div>
                {/* 제한 입출력 */}
                {/* App.tsx 내의 문제 설명 렌더링 부분 상단에 추가 */}
                {problemData.problem_limit && (
                  <div className="mb-6 p-4 bg-purple-500/5 border border-purple-500/20 rounded-2xl">
                    <h3 className="text-sm font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-400 mb-2 flex items-center gap-2">
                      <Brain className="w-4 h-4" /> 제약 조건
                    </h3>
                    <div 
                      className="prose prose-invert prose-xs text-gray-400" 
                      dangerouslySetInnerHTML={{ __html: problemData.problem_limit }} 
                    />
                  </div>
                )}
                {/* 예제 입출력 */}
                <div className="space-y-4">
                  <h3 className="text-lg font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-400 ml-1">예제 입출력</h3>
                  {problemData.sample_inputs && problemData.sample_inputs.map((sampleIn: string, idx: number) => (
                    <div key={idx} className="flex flex-col gap-2">
                      <div className="flex gap-2">
                        <div className="flex-1 bg-black/30 p-3 rounded-lg border border-gray-800 font-mono text-xs whitespace-pre-wrap">
                          <div className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400/80 to-purple-400/80 mb-2 font-sans">예제 입력 {idx + 1}</div>
                          {sampleIn}
                        </div>
                        <div className="flex-1 bg-black/30 p-3 rounded-lg border border-gray-800 font-mono text-xs whitespace-pre-wrap">
                          <div className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400/80 to-purple-400/80 mb-2 font-sans">예제 출력 {idx + 1}</div>
                          {problemData.sample_outputs[idx]}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 3: 코드 에디터 */}
        {activeTab === 'editor' && (
          <div className="p-6 space-y-4 h-full flex flex-col">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-400 inline-block">코드 에디터</h3>
              <button onClick={handleJudge} disabled={isLoading} className="px-4 py-2 bg-gradient-to-r from-blue-500 via-purple-500 to-purple-600 rounded-xl text-xs font-bold hover:opacity-90 transition-all shadow-lg shadow-purple-500/20 disabled:opacity-50 text-white">
                {isLoading ? '채점 중...' : '코드 채점하기'}
              </button>
            </div>
            <div className="flex-1 bg-[#1E1F20] rounded-2xl border border-gray-800 overflow-hidden font-mono shadow-inner min-h-[400px]">
              <CodeMirror
                value={userCode}
                height="100%"
                theme={vscodeDark}
                extensions={[python()]}
                onChange={(value) => setUserCode(value)}
                className="text-sm h-full"
                basicSetup={{
                  lineNumbers: true,
                  foldGutter: true,
                  dropCursor: true,
                  allowMultipleSelections: true,
                  indentOnInput: true,
                  syntaxHighlighting: true,
                  bracketMatching: true,
                  closeBrackets: true,
                  autocompletion: true,
                  rectangularSelection: true,
                  crosshairCursor: true,
                  highlightActiveLine: true,
                  highlightSelectionMatches: true,
                  closeBracketsKeymap: true,
                  defaultKeymap: true,
                  searchKeymap: true,
                  historyKeymap: true,
                  foldKeymap: true,
                  completionKeymap: true,
                  lintKeymap: true,
                }}
              />
            </div>
            {judgeResults && (
              <div className="mt-4 space-y-2">
                {judgeResults.map((res, idx) => (
                  <div key={idx} className={`p-4 rounded-xl border ${res.result === 'Success' ? 'border-green-500/30 bg-green-500/5' : 'border-red-500/30 bg-red-500/5'}`}>
                    <div className="flex justify-between items-center text-xs font-bold">
                      <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-400">케이스 #{res.case}</span>
                      <span className={res.result === 'Success' ? 'text-green-400' : 'text-red-400'}>{res.result === 'Success' ? '✅ 맞았습니다' : '❌ ' + res.result}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab 4: 학습 노트 (디자인 업데이트된 버튼) */}
        {activeTab === 'memo' && (
          <div className="p-6 h-full flex flex-col space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-400 inline-block">학습 노트</h3>
              <button 
                onClick={handleSaveMemo} 
                disabled={isSavingMemo || !searchProblemId} 
                className="px-4 py-2 bg-gradient-to-r from-blue-500 via-purple-500 to-purple-600 rounded-xl text-xs font-bold hover:opacity-90 transition-all shadow-lg shadow-purple-500/20 disabled:opacity-50 text-white"
              >
                {isSavingMemo ? '저장 중...' : '메모 저장'}
              </button>
            </div>
            <div className="flex-1 bg-[#1E1F20] rounded-2xl border border-gray-800 overflow-hidden shadow-inner">
              <CodeMirror
                value={memo}
                height="100%"
                theme={vscodeDark}
                extensions={[markdown()]}
                onChange={(value) => setMemo(value)}
                className="text-sm h-full"
                placeholder="이 문제의 핵심 아이디어를 기록하세요..."
              />
            </div>
          </div>
        )}
      </div>

      {/* 플로팅 하단 바 */}
      <div className="fixed bottom-6 left-0 right-0 px-6 pointer-events-none flex justify-center">
        <div className={`bg-[#1E1F20]/80 backdrop-blur-xl border border-white/10 rounded-3xl p-2 shadow-2xl flex pointer-events-auto transition-all duration-300 ${activeTab === 'chat' ? 'w-full max-w-md' : 'w-fit'}`}>
          {activeTab === 'chat' && (
            <div className="flex-1 flex items-end bg-[#131314]/50 rounded-2xl border border-white/5 px-3 py-1 mr-2">
              <textarea ref={textareaRef} value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleSend())} placeholder="메시지 입력..." className="w-full bg-transparent resize-none outline-none py-2 text-xs text-gray-300 max-h-24" rows={1} />
              <button onClick={handleSend} disabled={!input.trim() || isLoading} className="p-2 hover:scale-110 transition-all"><div className="bg-gradient-to-r from-blue-400 via-purple-400 to-purple-600 rounded-full p-1.5 shadow-lg"><Send className="w-3.5 h-3.5 text-white" /></div></button>
            </div>
          )}
          <div className="flex gap-1">
            <button onClick={() => setActiveTab('chat')} className={`p-3 rounded-2xl relative transition-all ${activeTab === 'chat' ? 'text-white' : 'text-gray-500 hover:text-gray-300'}`}>{activeTab === 'chat' && <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 via-purple-500/20 to-purple-600/20 rounded-2xl animate-pulse" />}<MessageSquare className="w-5 h-5 relative z-10" /></button>
            <button onClick={() => setActiveTab('problem')} className={`p-3 rounded-2xl relative transition-all ${activeTab === 'problem' ? 'text-white' : 'text-gray-500 hover:text-gray-300'}`}>{activeTab === 'problem' && <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 via-purple-500/20 to-purple-600/20 rounded-2xl animate-pulse" />}<FileCode2 className="w-5 h-5 relative z-10" /></button>
            <button onClick={() => setActiveTab('editor')} className={`p-3 rounded-2xl relative transition-all ${activeTab === 'editor' ? 'text-white' : 'text-gray-500 hover:text-gray-300'}`}>{activeTab === 'editor' && <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 via-purple-500/20 to-purple-600/20 rounded-2xl animate-pulse" />}<Code className="w-5 h-5 relative z-10" /></button>
            <button onClick={() => setActiveTab('memo')} className={`p-3 rounded-2xl relative transition-all ${activeTab === 'memo' ? 'text-white' : 'text-gray-500 hover:text-gray-300'}`}>{activeTab === 'memo' && <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 via-purple-500/20 to-purple-600/20 rounded-2xl animate-pulse" />}<Notebook className="w-5 h-5 relative z-10" /></button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;