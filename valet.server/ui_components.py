import streamlit as st
from datetime import datetime
import streamlit as st
from typing import List, Optional, Any, Union
import pandas as pd

class ResponseCard:
    """
    A component for displaying query responses and error messages in a consistent format.
    """
    
    @staticmethod
    def display(
        response: Union[pd.DataFrame, str],
        title: str = "Response",
        response_type: str = "success",
        explanation: Optional[str] = None,
        followup_questions: Optional[List[str]] = None
    ):
        """
        Display a success response with optional explanation and follow-up questions.
        
        Args:
            response: The main response content (DataFrame or string)
            title: Title for the response card
            response_type: Type of response ('success' or 'error')
            explanation: Optional explanation text
            followup_questions: Optional list of follow-up questions
        """
        with st.container():
            # Header
            st.markdown(f"### {title}")
            
            # Explanation if provided
            if explanation:
                st.markdown(explanation)
            
            # Main response content
            if isinstance(response, pd.DataFrame):
                st.dataframe(response)
            else:
                st.markdown(response)
            
            # Follow-up questions
            if followup_questions:
                st.markdown("#### Suggested Follow-up Questions")
                for question in followup_questions:
                    if st.button(question):
                        # Store the selected question in session state
                        st.session_state.user_input = question
    
    @staticmethod
    def error_card(
        error_message: str,
        suggestions: Optional[List[str]] = None,
        title: str = "Error"
    ):
        """
        Display an error message with optional suggestions.
        
        Args:
            error_message: The error message to display
            suggestions: Optional list of suggestions for resolving the error
            title: Title for the error card
        """
        with st.container():
            st.error(f"### {title}")
            st.markdown(error_message)
            
            if suggestions:
                st.markdown("#### Suggestions")
                for suggestion in suggestions:
                    st.markdown(f"- {suggestion}")

    @staticmethod
    def loading_card(message: str = "Processing your request..."):
        """
        Display a loading message while processing.
        
        Args:
            message: The loading message to display
        """
        with st.container():
            with st.spinner(message):
                st.empty()
                
class LLMService:
    def __init__(self):
        # Initialize any required LLM configurations here
        pass
        
    def process_query(self, query, conversation_history=None):
        """
        Process a query using the LLM service
        
        Args:
            query (str): The user's input query
            conversation_history (list): List of previous messages for context
            
        Returns:
            str: The LLM's response
        """
        try:
            # Here you would typically:
            # 1. Format the conversation history and query
            # 2. Make an API call to your LLM service
            # 3. Process and return the response
            
            # For now, returning a mock response
            return f"I understand you're asking about: {query}. How can I help further?"
        except Exception as e:
            st.error(f"Error processing query: {str(e)}")
            return "I apologize, but I encountered an error processing your request. Please try again."

class ChatHistory:
    def __init__(self):
        self.messages = []
        self.conversations = {}
        self.current_conversation_id = None

    def add_message(self, role, content, conversation_id=None):
        timestamp = datetime.now().strftime("%I:%M %p")
        message = {
            'role': role,
            'content': content,
            'timestamp': timestamp,
        }

        if conversation_id is None:
            conversation_id = self.current_conversation_id

        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []

        self.conversations[conversation_id].append(message)
        self.messages = self.conversations[conversation_id]

    def get_conversation_pair(self, conversation_id):
        return self.conversations.get(conversation_id, [])

    def create_new_conversation(self):
        conversation_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_conversation_id = conversation_id
        self.conversations[conversation_id] = []
        return conversation_id

    def get_conversation_history(self, conversation_id):
        """
        Get the conversation history in a format suitable for the LLM
        """
        messages = self.conversations.get(conversation_id, [])
        return [{"role": msg["role"], "content": msg["content"]} for msg in messages]


class ClaudeUI:
    def __init__(self):
        self.initialize_session_state()
        self.setup_layout()
        self.llm_service = LLMService()

    @staticmethod
    def initialize_session_state():
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = ChatHistory()
        if 'selected_conversation_id' not in st.session_state:
            st.session_state.selected_conversation_id = None
        if 'user_input' not in st.session_state:
            st.session_state.user_input = ""

    def setup_layout(self):
        st.set_page_config(
            layout="wide",
            page_title="Mr Parker by Summon",
            initial_sidebar_state="expanded"
        )
    
    def render_title(self):
        st.markdown("<h1>Welcome to Summon Valet Parking </h1>", unsafe_allow_html=True)    
    
    def render_sidebar(self):
        with st.sidebar:
            st.markdown('<div class="sidebar-title">Chat History</div>', unsafe_allow_html=True)

            if st.button("New Chat"):
                new_conversation_id = st.session_state.chat_history.create_new_conversation()
                st.query_params["conversation"] = new_conversation_id
                st.session_state.selected_conversation_id = new_conversation_id

            for conv_id, messages in st.session_state.chat_history.conversations.items():
                if messages:
                    first_message = messages[0]['content']
                    preview = first_message[:40] + "..." if len(first_message) > 40 else first_message
                    link = f"?conversation={conv_id}"
                    st.markdown(f"- [{preview}]({link})")

    def render_chat_messages(self, chat_history, selected_conversation_id=None):
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)

        if not selected_conversation_id:
            st.markdown('<div>No conversation selected. Start a new chat!</div>', unsafe_allow_html=True)
            return

        messages_to_display = chat_history.get_conversation_pair(selected_conversation_id)
        for msg in messages_to_display:
            self.render_message(msg)

        st.markdown('</div>', unsafe_allow_html=True)

    def render_message(self, msg):
        role_class = "user-message" if msg['role'] == 'user' else 'assistant-message'
        sender_name = 'You' if msg['role'] == 'user' else 'Mr Parker'

        st.markdown(f"""
            <div class="chat-message {role_class}">
                <div class="timestamp">{msg['timestamp']}</div>
                <div class="sender-name">{sender_name}</div>
                <div class="message-content">{msg['content']}</div>
            </div>
        """, unsafe_allow_html=True)

    def render_input_form(self):
        st.markdown('<div class="input-container">', unsafe_allow_html=True)
        with st.form(key='chat_form', clear_on_submit=True):
            user_input = st.text_area("Type your message...", key='user_input', height=100)
            col1, col2 = st.columns([5, 1])
            with col2:
                submit_button = st.form_submit_button("Send")
        st.markdown('</div>', unsafe_allow_html=True)
        return user_input, submit_button

    def process_user_input(self, user_input, conversation_id):
        """
        Process user input and get LLM response
        """
        # Get conversation history
        conversation_history = st.session_state.chat_history.get_conversation_history(conversation_id)
        
        # Process query through LLM service
        response = self.llm_service.process_query(user_input, conversation_history)
        
        return response

    def run(self):
        selected_conversation = st.query_params.get("conversation")
        if selected_conversation:
            st.session_state.selected_conversation_id = selected_conversation
        elif not st.session_state.selected_conversation_id:
            st.session_state.selected_conversation_id = st.session_state.chat_history.create_new_conversation()

        self.render_sidebar()

        user_input, submit_button = self.render_input_form()

        if submit_button and user_input:
            # Add user message
            st.session_state.chat_history.add_message(
                'user',
                user_input,
                st.session_state.selected_conversation_id
            )

            # Process user input and get response
            assistant_response = self.process_user_input(
                user_input,
                st.session_state.selected_conversation_id
            )

            # Add assistant response
            st.session_state.chat_history.add_message(
                'assistant',
                assistant_response,
                st.session_state.selected_conversation_id
            )

        self.render_chat_messages(
            st.session_state.chat_history,
            st.session_state.selected_conversation_id
        )


if __name__ == "__main__":
    app = ClaudeUI()
    app.run()