// types/index.ts
export interface ChatMessage {
    id: number;
    type: 'user' | 'system';
    content: string;
    responseData?: BackendResponse | null;
    timestamp?: number;
  }
  
  export interface BackendResponse {
    query_results?: number[][];
    nl_explanation?: string;
    error?: string;
    entities?: Array<{text: string; label: string}>;
  }