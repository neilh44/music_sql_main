import tiktoken

class TokenManager:
    def __init__(self, model_name="llama3-8b-8192"):
        """
        Initialize TokenManager with specific model's tokenization.
        
        Args:
            model_name (str): Name of the model to use for tokenization. 
                             Defaults to "llama3-8b-8192".
        """
        try:
            self.encoding = tiktoken.encoding_for_model(model_name)
        except Exception:
            # Fallback to a default encoding if model-specific encoding fails
            self.encoding = tiktoken.get_encoding("cl100k_base")
        
        # Token limits can be adjusted based on your specific model
        self.max_input_tokens = 15000   # Maximum input tokens
        self.max_output_tokens = 4000   # Maximum output tokens
        self.max_context_tokens = 10000 # Maximum context window size

    def count_tokens(self, text):
        """
        Count the number of tokens in a text string.
        
        Args:
            text (str): Input text to tokenize.
        
        Returns:
            int: Number of tokens in the text.
        """
        if not text:
            return 0
        return len(self.encoding.encode(text))

    def truncate_text(self, text, max_tokens):
        """
        Truncate text to fit within a specified token limit.
        
        Args:
            text (str): Input text to truncate.
            max_tokens (int): Maximum number of tokens allowed.
        
        Returns:
            str: Truncated text.
        """
        if not text:
            return ""
        
        tokens = self.encoding.encode(text)
        if len(tokens) <= max_tokens:
            return text
        
        return self.encoding.decode(tokens[:max_tokens])

    def format_dataframe(self, df, max_tokens):
        """
        Convert DataFrame to a string representation within token limit.
        
        Args:
            df (pandas.DataFrame): Input DataFrame.
            max_tokens (int): Maximum number of tokens allowed.
        
        Returns:
            str: String representation of DataFrame truncated to token limit.
        """
        if df is None or df.empty:
            return ""
        
        df_str = df.to_string(index=False)
        return self.truncate_text(df_str, max_tokens)

    def get_context_window(self, messages, max_tokens):
        """
        Extract recent message history that fits within token limit.
        
        Args:
            messages (list): List of message dictionaries.
            max_tokens (int): Maximum number of tokens allowed.
        
        Returns:
            list: List of messages that fit within token limit.
        """
        total_tokens = 0
        context_messages = []
        
        for message in reversed(messages):
            message_tokens = self.count_tokens(str(message))
            if total_tokens + message_tokens > max_tokens:
                break
            context_messages.insert(0, message)
            total_tokens += message_tokens
            
        return context_messages