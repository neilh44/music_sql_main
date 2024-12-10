import React, { useState, useRef, useEffect } from "react";
import { Mountain, Image, MoreVertical, Share2, Camera, Video, Paperclip } from 'lucide-react';
import DataVisualization from "@/components/ui/DataVisualization";

interface ChatMessage {
  id: number;
  type: 'user' | 'system';
  content: string;
  responseData?: BackendResponse | null;
}

interface BackendResponse {
  query_results?: number[][];
  nl_explanation?: string;
  error?: string;
  entities?: Array<{text: string; label: string}>;
  columns?: string[];
  success?: boolean;
}

const JourneyUI: React.FC = () => {
  const [userInput, setUserInput] = useState<string>("");
  const [responseData, setResponseData] = useState<BackendResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  
  const BACKEND_URL = "https://valet-server-rnz0tb7x1-neilh44s-projects.vercel.app/query";

  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [chatHistory, isLoading]);

  const transformDataForVisualization = (
    results: number[][] | undefined,
    columns: string[] | undefined
  ): string[][] => {
    if (!results?.[0] || !columns) return [];
    return [
      results[0].map(val => val.toString()),
      columns
    ];
  };

  const callBackendAPI = async (userInput: string) => {
    setIsLoading(true);
    
    const userMessage: ChatMessage = {
      id: Date.now(),
      type: 'user',
      content: userInput
    };
    setChatHistory(prev => [...prev, userMessage]);

    try {
      const response = await fetch(BACKEND_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query: userInput }),
      });
  
      if (!response.ok) {
        throw new Error(`API request failed with status ${response.status}`);
      }
  
      const data: BackendResponse = await response.json();
      setResponseData(data);

      if (data.nl_explanation) {
        const systemMessage: ChatMessage = {
          id: Date.now() + 1,
          type: 'system',
          content: data.nl_explanation,
          responseData: data
        };
        setChatHistory(prev => [...prev, systemMessage]);
      }
    } catch (error) {
      console.error("Error calling backend:", error);
      const errorMessage: ChatMessage = {
        id: Date.now(),
        type: 'system',
        content: "An error occurred. Please try again."
      };
      setChatHistory(prev => [...prev, errorMessage]);
      setResponseData({ error: "An error occurred. Please try again." });
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

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      <header className="flex-none border-b p-4">
        <h1 className="text-xl font-semibold text-green-500">Summon Parking Valet</h1>
      </header>
      
      <main className="flex-1 overflow-hidden flex flex-col">
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
              
              {message.type === 'system' && message.responseData?.query_results && (
                <div className="mt-4">
                  <DataVisualization
                    data={transformDataForVisualization(
                      message.responseData.query_results,
                      message.responseData.columns
                    )}
                  />
                </div>
              )}
            </div>
          ))}
          {isLoading && <div className="text-center">Loading...</div>}
        </div>

        <form onSubmit={handleSubmit} className="flex-none border-t p-4">
          <div className="flex items-center space-x-2">
            <input 
              type="text"
              value={userInput}
              onChange={(e) => setUserInput(e.target.value)}
              placeholder="Ask anything..."
              className="flex-1 border rounded-full px-4 py-2"
            />
            <button 
              type="submit" 
              disabled={!userInput.trim()}
              className="bg-green-500 text-white px-4 py-2 rounded-full disabled:opacity-50"
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