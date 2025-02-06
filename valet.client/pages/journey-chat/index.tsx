import React, { useState, useRef, useEffect } from "react";
import DataVisualization from "@/components/ui/DataVisualization";
import FollowUpQuestions from "@/components/ui/FollowUpQuestions";

interface ChatMessage {
  id: number;
  type: 'user' | 'system';
  content: string;
  responseData?: BackendResponse | null;
}

interface BackendResponse {
  success?: boolean;
  session_id?: string;
  results?: (string | number)[][];
  explanation?: string;
  error?: string;
  columns?: string[];
  context_used?: boolean;
  context_analysis?: {
    patterns: string[];
    topic_focus: string[] | null;
    interaction_count: number;
    has_visualizations: boolean;
  };
  sql_query?: string;
  followup_questions?: string[];
}

const JourneyUI: React.FC = () => {
  const [userInput, setUserInput] = useState<string>("");
  const [responseData, setResponseData] = useState<BackendResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [followUpQuestions, setFollowUpQuestions] = useState<string[]>([]);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:5000';
  
  useEffect(() => {
    const storedSessionId = localStorage.getItem('querySessionId');
    if (storedSessionId) {
      setSessionId(storedSessionId);
    }

    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [chatHistory, isLoading]);

  const handleApiError = (error: any) => {
    const errorMessage = error?.response?.data?.error || error.message || "An error occurred";
    setError(errorMessage);
    return {
      success: false,
      error: errorMessage
    };
  };

  const fetchFollowUpQuestions = async (query: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/followup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          query: query
        }),
      });

      const data = await response.json();
      if (data.success && data.followup_questions) {
        setFollowUpQuestions(data.followup_questions);
      }
    } catch (error) {
      console.error('Error fetching follow-up questions:', error);
      setFollowUpQuestions([]);
    }
  };

  const callBackendAPI = async (userInput: string) => {
    setIsLoading(true);
    setError(null);
    setFollowUpQuestions([]); // Clear previous follow-up questions
    
    const userMessage: ChatMessage = {
      id: Date.now(),
      type: 'user',
      content: userInput
    };
    setChatHistory(prev => [...prev, userMessage]);

    try {
      const response = await fetch(`${API_BASE_URL}/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ 
          query: userInput,
          session_id: sessionId 
        }),
      });

      if (!response.ok) {
        throw new Error(`API request failed with status ${response.status}`);
      }

      const data: BackendResponse = await response.json();

      if (!data.success) {
        throw new Error(data.error || 'Failed to process query');
      }

      setResponseData(data);

      if (data.session_id && data.session_id !== sessionId) {
        localStorage.setItem('querySessionId', data.session_id);
        setSessionId(data.session_id);
      }

      const systemMessage: ChatMessage = {
        id: Date.now() + 1,
        type: 'system',
        content: data.explanation || 'Query processed successfully',
        responseData: data
      };
      setChatHistory(prev => [...prev, systemMessage]);

      // Fetch follow-up questions after successful response
      await fetchFollowUpQuestions(userInput);
      
    } catch (error: any) {
      const errorResponse = handleApiError(error);
      const errorMessage: ChatMessage = {
        id: Date.now(),
        type: 'system',
        content: errorResponse.error
      };
      setChatHistory(prev => [...prev, errorMessage]);
      setResponseData({ error: errorResponse.error });
    } finally {
      setIsLoading(false);
    }
  };

  const clearChat = async () => {
    if (!sessionId) return;

    try {
      setIsLoading(true);
      const response = await fetch(`${API_BASE_URL}/clear-context`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
        }),
      });

      const data = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(data.error || 'Failed to clear chat');
      }

      localStorage.removeItem('querySessionId');
      setSessionId('');
      setResponseData(null);
      setChatHistory([]);
      setError(null);
      setFollowUpQuestions([]);
    } catch (error: any) {
      handleApiError(error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (userInput.trim()) {
      await callBackendAPI(userInput);
      setUserInput("");
    }
  };

  const handleFollowUpClick = (question: string) => {
    setUserInput(question);
    callBackendAPI(question);
  };

  const transformDataForVisualization = (message: ChatMessage) => {
    if (!message.responseData?.results || !message.responseData?.columns) {
      return null;
    }

    return {
      results: message.responseData.results,
      columns: message.responseData.columns,
      explanation: message.responseData.explanation
    };
  };

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      <header className="flex-none border-b p-4">
        <div className="flex justify-between items-center">
          <h1 className="text-xl font-semibold text-green-500">Summon Parking Valet</h1>
          {sessionId && (
            <button
              onClick={clearChat}
              disabled={isLoading}
              className="px-4 py-2 text-sm bg-red-500 text-white rounded-md disabled:opacity-50 hover:bg-red-600"
            >
              Clear Chat
            </button>
          )}
        </div>
      </header>
      
      <main className="flex-1 overflow-hidden flex flex-col">
        {error && (
          <div className="m-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded-md">
            {error}
          </div>
        )}

        <div ref={chatContainerRef} className="flex-1 overflow-y-auto p-4 space-y-4">
          {chatHistory.map((message) => (
            <div key={message.id}>
              <div className={`max-w-2xl mx-auto ${
                message.type === 'user' ? 'text-right' : 'text-left'
              }`}>
                <div className={`inline-block p-3 rounded-lg ${
                  message.type === 'user' ? 'bg-green-100' : 'bg-gray-100'
                }`}>
                  {message.content}
                </div>
              </div>
              
              {message.type === 'system' && (
                <div className="mt-4">
                  {message.responseData && transformDataForVisualization(message) && (
                    <DataVisualization 
                      data={transformDataForVisualization(message)!}
                    />
                  )}
                  {followUpQuestions.length > 0 && (
                    <FollowUpQuestions
                      questions={followUpQuestions}
                      onQuestionClick={handleFollowUpClick}
                      className="max-w-2xl mx-auto"
                    />
                  )}
                </div>
              )}
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-center items-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-500"></div>
            </div>
          )}
        </div>

        <form onSubmit={handleSubmit} className="flex-none border-t p-4">
          <div className="flex items-center space-x-2">
            <input 
              type="text"
              value={userInput}
              onChange={(e) => setUserInput(e.target.value)}
              placeholder="Ask anything..."
              className="flex-1 border rounded-full px-4 py-2"
              disabled={isLoading}
            />
            <button 
              type="submit" 
              disabled={!userInput.trim() || isLoading}
              className="bg-green-500 text-white px-4 py-2 rounded-full disabled:opacity-50 hover:bg-green-600"
            >
              Send
            </button>
          </div>
        </form>
      </main>
    </div>
  );
};

export default JourneyUI;