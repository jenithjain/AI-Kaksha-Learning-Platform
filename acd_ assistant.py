import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import requests
import json
import os
import tempfile
import base64
from io import BytesIO
from PIL import Image

# PDF processing
import PyPDF2
import pdfplumber

# Excel/CSV processing
import openpyxl
import csv

# Text processing
import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.stem import WordNetLemmatizer
from sklearn.feature_extraction.text import TfidfVectorizer

# Download NLTK resources
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')
    nltk.download('wordnet')

# Page configuration
st.set_page_config(
    page_title="Academic Assistant",
    page_icon="📚",
    layout="wide"
)

# Add custom CSS for dark mode
st.markdown("""
<style>
    /* Dark mode styles */
    .stApp {
        background-color: #1E1E1E;
        color: #FFFFFF;
    }
    
    /* Make text areas and inputs more visible */
    .stTextInput input, .stTextArea textarea {
        background-color: #2D2D2D !important;
        color: #FFFFFF !important;
    }
    
    /* Style dataframes */
    .dataframe {
        background-color: #2D2D2D !important;
        color: #FFFFFF !important;
    }
    
    /* Style expanders */
    .streamlit-expanderHeader {
        background-color: #2D2D2D !important;
        color: #FFFFFF !important;
    }
    
    /* Style buttons */
    .stButton>button {
        background-color: #4CAF50 !important;
        color: white !important;
    }
    
    /* Style success messages */
    .stSuccess {
        background-color: #2D2D2D !important;
        color: #4CAF50 !important;
    }
    
    /* Style error messages */
    .stError {
        background-color: #2D2D2D !important;
        color: #FF4B4B !important;
    }
    
    /* Chat messages */
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        background-color: #2D2D2D;
    }
    
    .user-message {
        background-color: #2D2D2D;
        border-left: 5px solid #4CAF50;
    }
    
    .assistant-message {
        background-color: #2D2D2D;
        border-left: 5px solid #2196F3;
    }
</style>
""", unsafe_allow_html=True)

# Update the import statement
import google.generativeai as genai

# Configure Gemini
genai.configure(api_key="*************************************")

# Initialize session state
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'documents' not in st.session_state:
    st.session_state.documents = {}
if 'current_summary' not in st.session_state:
    st.session_state.current_summary = ""
if 'current_notes' not in st.session_state:
    st.session_state.current_notes = ""
if 'current_qa' not in st.session_state:
    st.session_state.current_qa = ""
if 'data_analysis' not in st.session_state:
    st.session_state.data_analysis = {}

def query_ai(prompt, task_type="general", max_tokens=8192):
    """Query Gemini API with the given prompt"""
    
    system_prompts = {
        "summarize": "You are an expert summarizer. Create clear, concise summaries while retaining key information.",
        "study_notes": "You are an educational expert. Create comprehensive study notes with key concepts, examples, and learning points.",
        "analysis": "You are a data analysis expert. Provide detailed insights and patterns from the given data.",
        "qa": "You are a knowledgeable tutor. Provide clear, accurate answers with examples when helpful.",
        "practice_questions": "You are an expert educator specializing in creating effective assessment materials. Create challenging but fair practice questions.",
        "general": "You are a helpful AI assistant with expertise in academic topics."
    }

    # Combine system prompt and user prompt
    full_prompt = f"{system_prompts.get(task_type, system_prompts['general'])}\n\n{prompt}"
    
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(
            full_prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.7,
                top_p=0.95,
                top_k=40,
                max_output_tokens=max_tokens
            )
        )
        
        return response.text
        
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return "Error processing request."

def extract_text_from_pdf(file):
    """Extract text from PDF files using pdfplumber"""
    try:
        text = ""
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
        return text.strip()
    except Exception as e:
        st.error(f"Primary PDF extraction failed: {str(e)}")
        # Fallback to PyPDF2
        try:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text.strip()
        except Exception as e2:
            st.error(f"Backup PDF extraction failed: {str(e2)}")
            return None

def process_excel(excel_file):
    """Process Excel file and return dataframe and summary"""
    try:
        df = pd.read_excel(excel_file)
        return df
    except Exception as e:
        st.error(f"Error processing Excel file: {str(e)}")
        return None

def process_csv(csv_file):
    """Process CSV file and return dataframe and summary"""
    try:
        df = pd.read_csv(csv_file)
        return df
    except Exception as e:
        st.error(f"Error processing CSV file: {str(e)}")
        return None

def analyze_dataframe(df, file_name):
    """Analyze dataframe using Gemini API"""
    df_info = f"""
    File: {file_name}
    Shape: {df.shape}
    Columns: {list(df.columns)}
    Data Types: {df.dtypes.to_dict()}
    Summary Statistics: 
    {df.describe().to_string()}
    """
    return query_ai(df_info, task_type="analysis")

def generate_summary(text, max_length=1000):
    """Generate summary using Gemini API"""
    prompt = f"Please provide a clear and concise summary of the following text in about {max_length} characters:\n\n{text}"
    return query_ai(prompt, task_type="summarize")

def generate_study_notes(text, max_length=1500):
    """Generate study notes using Gemini API"""
    prompt = f"Create comprehensive study notes from this text, including key concepts, examples, and important points:\n\n{text}"
    return query_ai(prompt, task_type="study_notes")

def generate_practice_questions(text, num_questions=5):
    """Generate practice questions using Gemini API"""
    prompt = f"Based on this text, create {num_questions} practice questions with detailed answers:\n\n{text}"
    return query_ai(prompt, task_type="practice_questions")

def analyze_data_with_ai(df, file_name):
    """Detailed data analysis using Gemini API"""
    df_info = f"""
    File: {file_name}
    Shape: {df.shape}
    Columns: {list(df.columns)}
    Data Types: {df.dtypes.to_dict()}
    Missing Values: {df.isnull().sum().to_dict()}
    Summary Statistics: 
    {df.describe().to_string()}
    
    First 5 rows:
    {df.head().to_string()}
    """
    
    prompt = f"""Please analyze this dataset and provide:
    1. A summary of what this data represents
    2. Key insights and patterns
    3. Potential research questions
    4. Recommendations for further analysis
    5. Any limitations or issues

    Dataset Information:
    {df_info}
    """
    
    return query_ai(prompt, task_type="analysis")

# Main application UI
st.title("🧠 Academic Assistant")
st.markdown("""
<div class="card">
<p>Your AI-powered study companion for exam preparation, document analysis, and learning assistance.</p>
<p>Upload documents, generate summaries, create study notes, and get answers to your questions.</p>
</div>
""", unsafe_allow_html=True)

# Sidebar for file uploads and options
with st.sidebar:
    st.header("📚 Document Upload")
    
    uploaded_file = st.file_uploader("Upload your study materials", 
                                     type=["pdf", "csv", "xlsx", "xls", "txt"],
                                     help="Upload PDF, Excel, CSV, or text files")
    
    if uploaded_file is not None:
        file_name = uploaded_file.name
        file_type = file_name.split(".")[-1].lower()
        
        st.success(f"✅ Uploaded: {file_name}")
        
        # Process the file based on its type
        if file_type == "pdf":
            with st.spinner("Extracting text from PDF..."):
                text = extract_text_from_pdf(uploaded_file)
                if text:
                    st.session_state.documents[file_name] = {
                        "type": "pdf",
                        "content": text,
                        "processed": True
                    }
                    st.success(f"✅ Extracted {len(text)} characters from PDF")
                else:
                    st.error("Failed to extract text from PDF")
        
        elif file_type in ["xlsx", "xls"]:
            with st.spinner("Processing Excel file..."):
                df = process_excel(uploaded_file)
                if df is not None:
                    st.session_state.documents[file_name] = {
                        "type": "excel",
                        "content": df,
                        "processed": True
                    }
                    st.success(f"✅ Processed Excel file with {df.shape[0]} rows and {df.shape[1]} columns")
                    
                    # Analyze dataframe
                    with st.spinner("Analyzing data..."):
                        analysis = analyze_dataframe(df, file_name)
                        st.session_state.data_analysis[file_name] = analysis
        
        elif file_type == "csv":
            with st.spinner("Processing CSV file..."):
                df = process_csv(uploaded_file)
                if df is not None:
                    st.session_state.documents[file_name] = {
                        "type": "csv",
                        "content": df,
                        "processed": True
                    }
                    st.success(f"✅ Processed CSV file with {df.shape[0]} rows and {df.shape[1]} columns")
                    
                    # Analyze dataframe
                    with st.spinner("Analyzing data..."):
                        analysis = analyze_dataframe(df, file_name)
                        st.session_state.data_analysis[file_name] = analysis
        
        elif file_type == "txt":
            text = uploaded_file.getvalue().decode("utf-8")
            st.session_state.documents[file_name] = {
                "type": "txt",
                "content": text,
                "processed": True
            }
            st.success(f"✅ Processed text file with {len(text)} characters")
    
    st.header("📝 Available Documents")
    if st.session_state.documents:
        for doc_name in st.session_state.documents:
            doc_type = st.session_state.documents[doc_name]["type"]
            if doc_type in ["pdf", "txt"]:
                content_preview = st.session_state.documents[doc_name]["content"][:100] + "..."
                st.markdown(f"**{doc_name}** ({doc_type})")
                with st.expander("Preview"):
                    st.text(content_preview)
            else:
                st.markdown(f"**{doc_name}** ({doc_type})")
                with st.expander("Preview"):
                    st.dataframe(st.session_state.documents[doc_name]["content"].head(3))
    else:
        st.info("No documents uploaded yet")

# Main content area with tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Summarize", "📒 Study Notes", "❓ Q&A", "📊 Data Analysis", "🤖 AI Chat"])

with tab1:
    st.header("📋 Document Summarization")
    st.markdown("""
    <div class="card">
    <p>Generate concise summaries of your documents to quickly understand the main concepts and key points.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Document selection for summarization
    if st.session_state.documents:
        text_docs = {k: v for k, v in st.session_state.documents.items() 
                    if v["type"] in ["pdf", "txt"]}
        
        if text_docs:
            selected_doc = st.selectbox("Select document to summarize", 
                                        list(text_docs.keys()),
                                        key="summary_doc_select")
            
            summary_length = st.slider("Summary length", 
                                      min_value=300, 
                                      max_value=2000, 
                                      value=1000,
                                      step=100,
                                      help="Adjust the length of the generated summary")
            
            if st.button("Generate Summary", key="gen_summary_btn"):
                with st.spinner("Generating summary..."):
                    text = text_docs[selected_doc]["content"]
                    summary = generate_summary(text, max_length=summary_length)
                    st.session_state.current_summary = summary
            
            if st.session_state.current_summary:
                st.markdown("### Summary")
                st.markdown(st.session_state.current_summary)
                
                # Download button for summary
                summary_download = st.session_state.current_summary.encode()
                st.download_button(
                    label="Download Summary",
                    data=summary_download,
                    file_name=f"summary_{selected_doc.split('.')[0]}.md",
                    mime="text/markdown"
                )
        else:
            st.info("Upload a PDF or text document to generate a summary")
    else:
        st.info("Upload a document to get started")

with tab2:
    st.header("📒 Study Notes Generator")
    st.markdown("""
    <div class="card">
    <p>Transform your documents into comprehensive study notes optimized for exam preparation.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Document selection for study notes
    if st.session_state.documents:
        text_docs = {k: v for k, v in st.session_state.documents.items() 
                    if v["type"] in ["pdf", "txt"]}
        
        if text_docs:
            selected_doc = st.selectbox("Select document for study notes", 
                                        list(text_docs.keys()),
                                        key="notes_doc_select")
            
            notes_detail = st.select_slider(
                "Level of detail",
                options=["Concise", "Balanced", "Detailed"],
                value="Balanced",
                help="Adjust how detailed the study notes should be"
            )
            
            # Map detail level to token count
            detail_tokens = {
                "Concise": 1000,
                "Balanced": 1500,
                "Detailed": 2000
            }
            
            if st.button("Generate Study Notes", key="gen_notes_btn"):
                with st.spinner("Creating study notes..."):
                    text = text_docs[selected_doc]["content"]
                    notes = generate_study_notes(text, max_length=detail_tokens[notes_detail])
                    st.session_state.current_notes = notes
            
            if st.session_state.current_notes:
                st.markdown("### Study Notes")
                st.markdown(st.session_state.current_notes)
                
                # Generate practice questions based on the notes
                if st.button("Generate Practice Questions", key="gen_questions_btn"):
                    with st.spinner("Creating practice questions..."):
                        questions = generate_practice_questions(text_docs[selected_doc]["content"])
                        st.markdown("### Practice Questions")
                        st.markdown(questions)
                
                # Download button for notes
                notes_download = st.session_state.current_notes.encode()
                st.download_button(
                    label="Download Study Notes",
                    data=notes_download,
                    file_name=f"notes_{selected_doc.split('.')[0]}.md",
                    mime="text/markdown"
                )
        else:
            st.info("Upload a PDF or text document to generate study notes")
    else:
        st.info("Upload a document to get started")

with tab3:
    st.header("❓ Question & Answer")
    st.markdown("""
    <div class="card">
    <p>Ask questions about your documents and get detailed answers to help with your studies.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Document selection for Q&A
    if st.session_state.documents:
        selected_doc = st.selectbox("Select document for questions", 
                                   list(st.session_state.documents.keys()),
                                   key="qa_doc_select")
        
        # Get document content
        doc_content = ""
        if st.session_state.documents[selected_doc]["type"] in ["pdf", "txt"]:
            doc_content = st.session_state.documents[selected_doc]["content"]
        elif st.session_state.documents[selected_doc]["type"] in ["excel", "csv"]:
            df = st.session_state.documents[selected_doc]["content"]
            doc_content = f"""
            Dataset: {selected_doc}
            Shape: {df.shape}
            Columns: {list(df.columns)}
            
            First 5 rows:
            {df.head().to_string()}
            
            Summary statistics:
            {df.describe().to_string()}
            """
        
        # Question input
        user_question = st.text_input("Ask a question about the document:", 
                                     key="qa_question",
                                     placeholder="e.g., What are the main concepts discussed?")
        
        if st.button("Get Answer", key="get_answer_btn") and user_question:
            with st.spinner("Finding answer..."):
                system_message = """You are an expert academic tutor. Your task is to answer the student's
                question based on the provided document content. Be thorough, accurate, and educational in your response."""
                
                prompt = f"""Based on the following document content, please answer this question:
                
                Question: {user_question}
                
                Document content:
                {doc_content[:12000]}  # Truncate to avoid token limits
                
                Provide a comprehensive answer with examples and explanations where appropriate.
                If the question cannot be answered based on the document content, please say so clearly."""
                
                answer = query_ai(prompt, task_type="qa")
                st.session_state.current_qa = answer
        
        if st.session_state.current_qa:
            st.markdown("### Answer")
            st.markdown(st.session_state.current_qa)
    else:
        st.info("Upload a document to ask questions")

with tab4:
    st.header("📊 Data Analysis")
    st.markdown("""
    <div class="card">
    <p>Analyze your data files (CSV, Excel) to uncover insights, patterns, and visualizations.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check for data files
    data_docs = {k: v for k, v in st.session_state.documents.items() 
                if v["type"] in ["excel", "csv"]}
    
    if data_docs:
        selected_data = st.selectbox("Select data file to analyze", 
                                    list(data_docs.keys()),
                                    key="data_analysis_select")
        
        if selected_data in st.session_state.data_analysis:
            analysis = st.session_state.data_analysis[selected_data]
            df = data_docs[selected_data]["content"]
            
            st.markdown(f"### Dataset: {selected_data}")
            st.markdown(f"**Shape:** {analysis['shape'][0]} rows × {analysis['shape'][1]} columns")
            
            # Display dataframe
            st.subheader("Data Preview")
            st.dataframe(df.head(10))
            
            # Column information
            st.subheader("Column Information")
            col_info = pd.DataFrame({
                "Data Type": analysis["dtypes"],
                "Missing Values": analysis["missing_values"]
            })
            st.dataframe(col_info)
            
            # Visualizations
            st.subheader("Visualizations")
            if analysis["visualizations"]:
                viz_cols = st.columns(2)
                for i, (col_name, img_data) in enumerate(analysis["visualizations"].items()):
                    with viz_cols[i % 2]:
                        st.markdown(f"**{col_name}**")
                        st.image(f"data:image/png;base64,{img_data}")
            
            # AI Analysis
            st.subheader("AI Insights")
            if st.button("Generate AI Analysis", key="gen_ai_analysis"):
                with st.spinner("Analyzing data with AI..."):
                    ai_analysis = analyze_data_with_ai(df, selected_data)
                    st.markdown(ai_analysis)
            
            # Data operations
            st.subheader("Data Operations")
            operation = st.selectbox(
                "Select operation",
                ["Basic Statistics", "Correlation Analysis", "Group By", "Filter Data", "Custom Query"]
            )
            
            if operation == "Basic Statistics":
                st.write(df.describe())
                
            elif operation == "Correlation Analysis":
                numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
                if len(numeric_cols) > 1:
                    corr_matrix = df[numeric_cols].corr()
                    st.write(corr_matrix)
                    
                    fig, ax = plt.subplots(figsize=(10, 8))
                    sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', ax=ax)
                    st.pyplot(fig)
                else:
                    st.info("Not enough numeric columns for correlation analysis")
                    
            elif operation == "Group By":
                group_col = st.selectbox("Group by column", df.columns)
                agg_col = st.selectbox("Column to aggregate", 
                                      [c for c in df.columns if c != group_col])
                agg_func = st.selectbox("Aggregation function", 
                                       ["mean", "sum", "count", "min", "max"])
                
                if st.button("Apply Grouping"):
                    result = df.groupby(group_col)[agg_col].agg(agg_func).reset_index()
                    st.write(result)
                    
                    # Visualization
                    fig, ax = plt.subplots(figsize=(10, 6))
                    result.plot(x=group_col, y=agg_col, kind='bar', ax=ax)
                    plt.title(f"{agg_func.capitalize()} of {agg_col} by {group_col}")
                    plt.tight_layout()
                    st.pyplot(fig)
                    
            elif operation == "Filter Data":
                filter_col = st.selectbox("Column to filter", df.columns)
                
                # Adjust filter UI based on column type
                if df[filter_col].dtype in [np.int64, np.float64]:
                    min_val = float(df[filter_col].min())
                    max_val = float(df[filter_col].max())
                    filter_range = st.slider(f"Range for {filter_col}", 
                                           min_value=min_val,
                                           max_value=max_val,
                                           value=(min_val, max_val))
                    
                    if st.button("Apply Filter"):
                        filtered_df = df[(df[filter_col] >= filter_range[0]) & 
                                        (df[filter_col] <= filter_range[1])]
                        st.write(filtered_df)
                else:
                    unique_vals = df[filter_col].unique()
                    selected_vals = st.multiselect(f"Select values for {filter_col}", 
                                                 options=unique_vals,
                                                 default=list(unique_vals[:5]) if len(unique_vals) > 5 else list(unique_vals))
                    
                    if st.button("Apply Filter"):
                        filtered_df = df[df[filter_col].isin(selected_vals)]
                        st.write(filtered_df)
                    
            elif operation == "Custom Query":
                st.markdown("""
                Enter a custom query using Python syntax. 
                The dataframe is available as `df`.
                Example: `df[df['column'] > 50].groupby('category').mean()`
                """)
                
                query = st.text_area("Custom query:", height=100)
                
                if st.button("Execute Query"):
                    try:
                        # Execute the query (with safety limitations)
                        if "import" in query or "exec" in query or "eval" in query:
                            st.error("Import, exec, and eval statements are not allowed for security reasons.")
                        else:
                            result = eval(query)
                            st.write(result)
                    except Exception as e:
                        st.error(f"Error executing query: {str(e)}")

with tab5:
    st.header("🤖 AI Chat Assistant")
    st.markdown("""
    Chat with an AI tutor about your documents, ask follow-up questions, or get help with your studies.
    """)
    
    # Display chat history
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                st.markdown(f"**You:** {message['content']}")
            else:
                st.markdown(f"**AI Assistant:** {message['content']}")
    
    # Chat input
    user_input = st.text_input("Ask a question:", key="chat_input")
    
    if st.button("Send", key="send_button") and user_input:
        # Add user message to history
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        
        # Get context from current document if any is selected
        context = ""
        if st.session_state.documents:
            selected_doc = st.session_state.documents.get(st.session_state.get('current_doc', ''))
            if selected_doc:
                if selected_doc["type"] in ["pdf", "txt"]:
                    context = selected_doc["content"][:1000]  # First 1000 chars for context
                else:
                    context = f"Current dataset preview:\n{selected_doc['content'].head().to_string()}"
        
        # Prepare prompt with context
        prompt = f"""Context: {context}

Question: {user_input}

Please provide a helpful and educational response."""
        
        # Get AI response
        response = query_ai(prompt, task_type="qa")
        
        if response:
            # Add AI response to history
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            st.experimental_rerun()

# Sidebar for document management
with st.sidebar:
    st.header("📚 Document Management")
    
    if st.session_state.documents:
        st.write("Current Documents:")
        for doc_name in st.session_state.documents:
            st.write(f"- {doc_name}")
            
        if st.button("Clear All Documents"):
            st.session_state.documents = {}
            st.session_state.chat_history = []
            st.experimental_rerun()
    
    st.header("⚙️ Settings")
    st.write("Model: Grok")
    max_tokens = st.slider("Max Response Length", 100, 2000, 1000)
    temperature = st.slider("Temperature", 0.0, 1.0, 0.7)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <p>Academic Assistant | Your AI Study Companion</p>
</div>
""", unsafe_allow_html=True)
