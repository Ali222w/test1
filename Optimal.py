import streamlit as st
import os
from langchain_groq import ChatGroq
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import create_retrieval_chain
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.memory import ConversationBufferMemory
from streamlit_mic_recorder import speech_to_text
import fitz
import pdfplumber

# Initialize API key variables
groq_api_key = "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"
google_api_key = "AIzaSyDdAiOdIa2I28sphYw36Genb4D--2IN1tU"

# Change the page title and icon
st.set_page_config(
    page_title="BGC ChatBot",
    page_icon="BGC Logo Colored.svg",
    layout="wide"
)

# Function to apply CSS based on language direction
def apply_css_direction(direction):
    st.markdown(
        f"""
        <style>
            .stApp {{
                direction: {direction};
                text-align: {direction};
            }}
            .stChatInput {{
                direction: {direction};
            }}
            .stChatMessage {{
                direction: {direction};
                text-align: {direction};
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )

# PDF Search and Screenshot Class
class PDFSearchAndDisplay:
    def __init__(self):
        pass

    def search_and_highlight(self, pdf_path, search_term):
        highlighted_pages = []
        with pdfplumber.open(pdf_path) as pdf:
            for page_number, page in enumerate(pdf.pages):
                text = page.extract_text()
                if search_term in text:
                    highlighted_pages.append((page_number, text))
        return highlighted_pages

    def capture_screenshots(self, pdf_path, pages):
        doc = fitz.open(pdf_path)
        screenshots = []
        for page_number, _ in pages:
            page = doc.load_page(page_number)
            pix = page.get_pixmap()
            screenshot_path = f"screenshot_page_{page_number}.png"
            pix.save(screenshot_path)
            screenshots.append(screenshot_path)
        return screenshots

# Sidebar configuration
with st.sidebar:
    # Language selection dropdown
    interface_language = st.selectbox("Interface Language", ["English", "العربية"])

    # Apply CSS direction based on selected language
    apply_css_direction("rtl" if interface_language == "العربية" else "ltr")
    st.title("Settings" if interface_language == "English" else "الإعدادات")

    # Validate API key inputs and initialize components if valid
    if groq_api_key and google_api_key:
        # Set Google API key as environment variable
        os.environ["GOOGLE_API_KEY"] = google_api_key

        # Initialize ChatGroq with the provided Groq API key
        llm = ChatGroq(groq_api_key=groq_api_key, model_name="gemma2-9b-it")

        # Define the chat prompt template with memory
        prompt = ChatPromptTemplate.from_messages([
            ("system", """
            You are a helpful assistant for Basrah Gas Company (BGC). Your task is to answer questions based on the provided context about BGC. Follow these rules strictly:

            1. **Language Handling:**
               - If the question is in English, answer in English.
               - If the question is in Arabic, answer in Arabic.
               - If the user explicitly asks for a response in a specific language, respond in that language.

            2. **Contextual Answers:**
               - Provide accurate and concise answers based on the context provided.
               - Do not explicitly mention the source of information unless asked.

            3. **Handling Unclear or Unanswerable Questions:**
               - If the question is unclear or lacks sufficient context, respond with:
                 - In English: "I'm sorry, I couldn't understand your question. Could you please provide more details?"
                 - In Arabic: "عذرًا، لم أتمكن من فهم سؤالك. هل يمكنك تقديم المزيد من التفاصيل؟"
               - If the question cannot be answered based on the provided context, respond with:
                 - In English: "I'm sorry, I don't have enough information to answer that question."
                 - In Arabic: "عذرًا، لا أملك معلومات كافية للإجابة على هذا السؤال."

            4. **User Interface Language:**
               - If the user has selected Arabic as the interface language, prioritize Arabic in your responses unless the question is explicitly in English.
               - If the user has selected English as the interface language, prioritize English in your responses unless the question is explicitly in Arabic.

            5. **Professional Tone:**
               - Maintain a professional and respectful tone in all responses.
               - Avoid making assumptions or providing speculative answers.
            """),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}"),
            ("system", "Context: {context}"),
        ])

        # Load existing embeddings from multiple sources
        if "vectors" not in st.session_state:
            with st.spinner("جارٍ تحميل التضميدات... الرجاء الانتظار." if interface_language == "العربية" else "Loading embeddings... Please wait."):
                embeddings = GoogleGenerativeAIEmbeddings(
                    model="models/embedding-001"
                )
                
                # Load existing FAISS indexes from both embeddings folders
                embeddings_paths = ["embeddings", "embeddings(OCR)"]
                st.session_state.vectors = None

                try:
                    for path in embeddings_paths:
                        # Load the FAISS index for each folder
                        new_vectors = FAISS.load_local(
                            path,
                            embeddings,
                            allow_dangerous_deserialization=True
                        )
                        # Merge vectors from multiple sources
                        if st.session_state.vectors is None:
                            st.session_state.vectors = new_vectors
                        else:
                            st.session_state.vectors.merge_from(new_vectors)
                except Exception as e:
                    st.error(f"حدث خطأ أثناء تحميل التضميدات: {str(e)}" if interface_language == "العربية" else f"Error loading embeddings: {str(e)}")
                    st.session_state.vectors = None

        # Microphone button in the sidebar
        st.markdown("### الإدخال الصوتي" if interface_language == "العربية" else "### Voice Input")
        input_lang_code = "ar" if interface_language == "العربية" else "en"
        voice_input = speech_to_text(
            start_prompt="🎤",
            stop_prompt="⏹️ إيقاف" if interface_language == "العربية" else "⏹️ Stop",
            language=input_lang_code,
            use_container_width=True,
            just_once=True,
            key="mic_button",
        )

        # Reset button in the sidebar
        if st.button("إعادة تعيين الدردشة" if interface_language == "العربية" else "Reset Chat"):
            st.session_state.messages = []
            st.session_state.memory.clear()
            st.success("تمت إعادة تعيين الدردشة بنجاح." if interface_language == "العربية" else "Chat has been reset successfully.")
            st.rerun()
    else:
        st.error("الرجاء إدخال مفاتيح API للمتابعة." if interface_language == "العربية" else "Please enter both API keys to proceed.")

# Initialize the PDFSearchAndDisplay class with the default PDF file
pdf_path = "BGC.pdf"
pdf_searcher = PDFSearchAndDisplay()

# Main area for chat interface
col1, col2 = st.columns([1, 4])

with col1:
    st.image("BGC Logo Colored.svg", width=100)

with col2:
    if interface_language == "العربية":
        st.title("بوت دردشة BGC")
        st.write("""
        **مرحبًا!**  
        هذا بوت الدردشة الخاص بشركة غاز البصرة (BGC). يمكنك استخدام هذا البوت للحصول على معلومات حول الشركة وأنشطتها.  
        **كيفية الاستخدام:**  
        - اكتب سؤالك في مربع النص أدناه.  
        - أو استخدم زر المايكروفون للتحدث مباشرة.  
        - سيتم الرد عليك بناءً على المعلومات المتاحة.  
        """)
    else:
        st.title(" BGC ChatBot")
        st.write("""
        **Welcome!**  
        This is the Basrah Gas Company (BGC) ChatBot. You can use this bot to get information about the company and its activities.  
        **How to use:**  
        - Type your question in the text box below.  
        - Or use the microphone button to speak directly.  
        - You will receive a response based on the available information.  
        """)

# Initialize session state for chat messages
if "messages" not in st.session_state:
    st.session_state.messages = []

# Initialize memory
if "memory" not in st.session_state:
    st.session_state.memory = ConversationBufferMemory(
        memory_key="history",
        return_messages=True
    )

# List of negative phrases
negative_phrases = [
    "I'm sorry",
    "عذرًا",
    "لا أملك معلومات كافية",
    "I don't have enough information",
    "لم أتمكن من فهم سؤالك",
    "I couldn't understand your question",
    "لا يمكنني الإجابة على هذا السؤال",
    "I cannot answer this question",
    "يرجى تقديم المزيد من التفاصيل",
    "Please provide more details",
    "غير واضح",
    "Unclear",
    "غير متأكد",
    "Not sure",
    "لا أعرف",
    "I don't know",
    "غير متاح",
    "Not available",
    "غير موجود",
    "Not found",
    "غير معروف",
    "Unknown",
    "غير محدد",
    "Unspecified",
    "غير مؤكد",
    "Uncertain",
    "غير كافي",
    "Insufficient",
    "غير دقيق",
    "Inaccurate",
    "غير مفهوم",
    "Not clear",
    "غير مكتمل",
    "Incomplete",
    "غير صحيح",
    "Incorrect",
    "غير مناسب",
    "Inappropriate",
    "Please provide me",
    "يرجى تزويدي",
    "Can you provide more",
    "هل يمكنك تقديم المزيد"
]

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Process voice input
if voice_input:
    st.session_state.messages.append({"role": "user", "content": voice_input})
    with st.chat_message("user"):
        st.markdown(voice_input)

    if "vectors" in st.session_state and st.session_state.vectors is not None:
        document_chain = create_stuff_documents_chain(llm, prompt)
        retriever = st.session_state.vectors.as_retriever()
        retrieval_chain = create_retrieval_chain(retriever, document_chain)

        response = retrieval_chain.invoke({
            "input": voice_input,
            "context": retriever.get_relevant_documents(voice_input),
            "history": st.session_state.memory.chat_memory.messages
        })
        assistant_response = response["answer"]

        st.session_state.messages.append({"role": "assistant", "content": assistant_response})
        with st.chat_message("assistant"):
            st.markdown(assistant_response)

        st.session_state.memory.chat_memory.add_user_message(voice_input)
        st.session_state.memory.chat_memory.add_ai_message(assistant_response)

        if not any(phrase in assistant_response for phrase in negative_phrases):
            with st.expander("مراجع الصفحات" if interface_language == "العربية" else "Page References"):
                if "context" in response:
                    page_numbers = set()
                    for doc in response["context"]:
                        page_number = doc.metadata.get("page", "unknown")
                        if page_number != "unknown" and str(page_number).isdigit():
                            page_numbers.add(int(page_number))

                    if page_numbers:
                        page_numbers_str = ", ".join(map(str, sorted(page_numbers)))
                        st.write(f"هذه الإجابة وفقًا للصفحات: {page_numbers_str}" if interface_language == "العربية" else f"This answer is according to pages: {page_numbers_str}")

                        highlighted_pages = [(page_number, "") for page_number in page_numbers]
                        screenshots = pdf_searcher.capture_screenshots(pdf_path, highlighted_pages)
                        for screenshot in screenshots:
                            st.image(screenshot)
                    else:
                        st.write("لا توجد أرقام صفحات صالحة في السياق." if interface_language == "العربية" else "No valid page numbers available in the context.")
                else:
                    st.write("لا يوجد سياق متاح." if interface_language == "العربية" else "No context available.")
    else:
        assistant_response = (
            "لم يتم تحميل التضميدات. يرجى التحقق مما إذا كان مسار التضميدات صحيحًا." if interface_language == "العربية" 
            else "Embeddings not loaded. Please check if the embeddings path is correct."
        )
        st.session_state.messages.append({"role": "assistant", "content": assistant_response})
        with st.chat_message("assistant"):
            st.markdown(assistant_response)

# Text input processing
if interface_language == "العربية":
    human_input = st.chat_input("اكتب سؤالك هنا...")
else:
    human_input = st.chat_input("Type your question here...")

if human_input:
    st.session_state.messages.append({"role": "user", "content": human_input})
    with st.chat_message("user"):
        st.markdown(human_input)

    if "vectors" in st.session_state and st.session_state.vectors is not None:
        document_chain = create_stuff_documents_chain(llm, prompt)
        retriever = st.session_state.vectors.as_retriever()
        retrieval_chain = create_retrieval_chain(retriever, document_chain)

        response = retrieval_chain.invoke({
            "input": human_input,
            "context": retriever.get_relevant_documents(human_input),
            "history": st.session_state.memory.chat_memory.messages
        })
        assistant_response = response["answer"]

        st.session_state.messages.append({"role": "assistant", "content": assistant_response})
        with st.chat_message("assistant"):
            st.markdown(assistant_response)

        st.session_state.memory.chat_memory.add_user_message(human_input)
        st.session_state.memory.chat_memory.add_ai_message(assistant_response)

        if not any(phrase in assistant_response for phrase in negative_phrases):
            with st.expander("مراجع الصفحات" if interface_language == "العربية" else "Page References"):
                if "context" in response:
                    page_numbers = set()
                    for doc in response["context"]:
                        page_number = doc.metadata.get("page", "unknown")
                        if page_number != "unknown" and str(page_number).isdigit():
                            page_numbers.add(int(page_number))

                    if page_numbers:
                        page_numbers_str = ", ".join(map(str, sorted(page_numbers)))
                        st.write(f"هذه الإجابة وفقًا للصفحات: {page_numbers_str}" if interface_language == "العربية" else f"This Answer is According to Pages: {page_numbers_str}")

                        highlighted_pages = [(page_number, "") for page_number in page_numbers]
                        screenshots = pdf_searcher.capture_screenshots(pdf_path, highlighted_pages)
                        for screenshot in screenshots:
                            st.image(screenshot)
                    else:
                        st.write("لا توجد أرقام صفحات صالحة في السياق." if interface_language == "العربية" else "No valid page numbers available in the context.")
                else:
                    st.write("لا يوجد سياق متاح." if interface_language == "العربية" else "No context available.")
    else:
        assistant_response = (
            "لم يتم تحميل التضميدات. يرجى التحقق مما إذا كان مسار التضميدات صحيحًا." if interface_language == "العربية" 
            else "Embeddings not loaded. Please check if the embeddings path is correct."
        )
        st.session_state.messages.append({"role": "assistant", "content": assistant_response})
        with st.chat_message("assistant"):
            st.markdown(assistant_response)
