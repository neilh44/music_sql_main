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
}

const JourneyUI: React.FC = () => {
  const [userInput, setUserInput] = useState<string>("");
  const [responseData, setResponseData] = useState<BackendResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<string>("book");
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(false);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  
  const BACKEND_URL = "https://valet-server-rnz0tb7x1-neilh44s-projects.vercel.app/query";

  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [chatHistory, isLoading]);

  // Safe data transformation function
  const transformDataForVisualization = (results: number[][] | undefined): string[][] => {
    if (!results || !Array.isArray(results)) return [];
    
    return results.map(row => {
      // Ensure we have both elements
      if (!Array.isArray(row) || row.length < 2) return ['', '0'];
      
      // Convert both numbers to strings
      console.log("row[0]?.toString() || ''55555",row[0]?.toString() || '');
      console.log("row[1]?.toString() || '0'444444",row[1]?.toString() || '0');
      return [
        row[0]?.toString() || '',
        row[1]?.toString() || '0'
      ];
    });
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
    <div className="flex h-screen flex-col bg-white">
      <header className="flex flex-col sm:flex-row items-center justify-between border-b p-4 space-y-4 sm:space-y-0">
        <div className="flex flex-col sm:flex-row items-center gap-4 sm:gap-8 w-full sm:w-auto">
          <h1 className="text-xl font-semibold text-green-500">Summon Parking Valet</h1>
          <div className="flex border rounded-md w-full sm:w-auto">
            <button
              className={`flex-1 sm:flex-none px-4 py-2 ${activeTab === 'book' ? 'bg-gray-100' : ''}`}
              onClick={() => setActiveTab('book')}
            >
              AI Chat Assistant
            </button>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <button className="p-2 hover:bg-gray-100 rounded-full">
            <Share2 className="h-5 w-5" />
          </button>
          <button 
            className="sm:hidden p-2 hover:bg-gray-100 rounded-full"
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
          >
            <Image className="h-5 w-5" />
          </button>
        </div>
      </header>
      <main className="flex flex-1 overflow-hidden relative">
        <div className={`flex-1 flex flex-col ${activeTab === 'chat' ? 'block' : 'hidden sm:block'}`}>
          <div 
            ref={chatContainerRef}
            className="flex-1 overflow-y-auto p-4 space-y-4 max-h-[calc(100vh-250px)] min-h-[200px]"
          >
            {chatHistory.map((message) => (
              <React.Fragment key={message.id}>
                <div 
                  className={`max-w-2xl mx-auto ${
                    message.type === 'user' ? 'text-right' : 'text-left'
                  }`}
                >
                  <div 
                    className={`inline-block p-3 rounded-lg ${
                      message.type === 'user' 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {message.content}
                  </div>
                </div>
                {message.type === 'system' && message.responseData?.query_results && (
                  <div className="mt-4">
                    {message.responseData.query_results.length > 2 ? (
                      // Single data point display
                      <div className="flex items-center justify-center">
                        <div className="text-center">
                          <h3 className="text-lg font-semibold">
                            {message.responseData.query_results[0]?.[0]?.toString() || ''}
                          </h3>
                          <p className="text-3xl font-bold text-green-600">
                            {message.responseData.query_results[0]?.[1]?.toString() || ''}
                          </p>
                        </div>
                      </div>
                    ) : (
                      // Multiple data points visualization
                      <DataVisualization
                        data={transformDataForVisualization(message.responseData.query_results)}
                      />
                    )}
                  </div>
                )}
              </React.Fragment>
            ))}
            {isLoading && (
              <div className="text-center text-gray-500">
                Loading...
              </div>
            )}
          </div>

          <form onSubmit={handleSubmit} className="border-t p-4">
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
        </div>
      </main>
    </div>
  );
};

export default JourneyUI;