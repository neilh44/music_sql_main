import React from 'react';

interface FollowUpQuestionsProps {
  questions: string[];
  onQuestionClick: (question: string) => void;
  className?: string;
}

const FollowUpQuestions: React.FC<FollowUpQuestionsProps> = ({ 
  questions, 
  onQuestionClick,
  className = ''
}) => {
  if (!questions || questions.length === 0) return null;

  return (
    <div className={`mt-4 space-y-2 ${className}`}>
      <p className="text-sm font-medium text-gray-500">Suggested questions:</p>
      <div className="flex flex-wrap gap-2">
        {questions.map((question, index) => (
          <button
            key={index}
            onClick={() => onQuestionClick(question)}
            className="px-3 py-1 text-sm bg-green-50 text-green-700 rounded-full 
                     hover:bg-green-100 transition-colors border border-green-200"
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  );
};

export default FollowUpQuestions;