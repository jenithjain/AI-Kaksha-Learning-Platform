import streamlit as st
import google.generativeai as genai
import graphviz
import json
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import time
import gc
import os
import sys
from pytube import YouTube
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlencode, quote
from bs4 import BeautifulSoup
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

# Configure API keys
GOOGLE_API_KEY = "YOUR_GOOGLE_API_KEY"
YOUTUBE_API_KEY = "YOUR_YOUTUBE_API_KEY"
genai.configure(api_key=GOOGLE_API_KEY)

# Initialize Gemini model
model = genai.GenerativeModel(
    model_name="gemini-1.5-pro",
    generation_config={
        "temperature": 0.7,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
    }
)

# Page configuration
st.set_page_config(
    page_title="Academic & Learning Assistant",
    page_icon="🎓",
    layout="wide"
)

# Initialize session state
if "video_url" not in st.session_state:
    st.session_state.video_url = None
if "transcript" not in st.session_state:
    st.session_state.transcript = None
if "summary" not in st.session_state:
    st.session_state.summary = None
if "notes" not in st.session_state:
    st.session_state.notes = None
if "full_text" not in st.session_state:
    st.session_state.full_text = None
if "qa_history" not in st.session_state:
    st.session_state.qa_history = []
if "quiz_data" not in st.session_state:
    st.session_state.quiz_data = None
if "quiz_answers" not in st.session_state:
    st.session_state.quiz_answers = {}
if "quiz_results" not in st.session_state:
    st.session_state.quiz_results = {}
if "documents" not in st.session_state:
    st.session_state.documents = {}
if "data_analysis" not in st.session_state:
    st.session_state.data_analysis = {}
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Check Graphviz installation
def check_graphviz():
    """Check if Graphviz is installed and accessible"""
    if sys.platform == "win32":
        graphviz_paths = [
            "C:\\Program Files\\Graphviz\\bin",
            "C:\\Program Files (x86)\\Graphviz\\bin"
        ]
        for path in graphviz_paths:
            if os.path.exists(path):
                os.environ["PATH"] += os.pathsep + path
                return True
    return False

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
</style>
""", unsafe_allow_html=True)

# API Configuration
API_URL = "https://cheapest-gpt-4-turbo-gpt-4-vision-chatgpt-openai-ai-api"
API_KEY = "**************************************************"
API_HOST = "cheapest-gpt-4-turbo-gpt-4-vision-chatgpt-openai-ai-api."

# Function definitions from both files
def query_gpt4o(prompt, max_tokens=1000):
    """Query GPT-4o API"""
    try:
        headers = {
            "x-rapidapi-key": API_KEY,
            "x-rapidapi-host": API_HOST,
            "Content-Type": "application/json"
        }
        
        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "model": "gpt-4o",
            "max_tokens": max_tokens
        }
        
        response = requests.post(API_URL, json=payload, headers=headers)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            st.error(f"API Error: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error querying API: {str(e)}")
        return None

def get_flow_from_gemini(topic, objective):
    """Get flow structure from GPT-4o instead of Gemini"""
    prompt = f"""Create a comprehensive learning flow for:

Topic: {topic}
Objective: {objective}

Return the response in this JSON format:
{{
    "nodes": [
        {{
            "id": "1",
            "label": "Step Name",
            "description": "Detailed description",
            "duration": "X weeks/days",
            "resources": ["Resource 1", "Resource 2"]
        }}
    ],
    "edges": [
        {{"from": "1", "to": "2"}}
    ]
}}"""

    try:
        response = query_gpt4o(prompt)
        return json.loads(response)
    except Exception as e:
        st.error(f"Error generating flow: {str(e)}")
        return None

def create_visualization(flow_data, viz_type="digraph"):
    """Create visualization using Graphviz"""
    try:
        dot = graphviz.Digraph(
            comment='Flow Visualization',
            graph_attr={
                'rankdir': 'LR' if viz_type == "digraph" else 'TB',
                'splines': 'ortho',
                'nodesep': '0.8',
                'ranksep': '1.0',
                'fontname': 'Arial',
                'fontsize': '12'
            }
        )
        
        # Add nodes
        for node in flow_data["nodes"]:
            label = f"""<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">
                <TR><TD PORT="title" BGCOLOR="lightblue"><B>{node['label']}</B></TD></TR>
                <TR><TD BGCOLOR="white" ALIGN="LEFT">{node['description'][:100]}...</TD></TR>
                <TR><TD BGCOLOR="lightgrey" ALIGN="LEFT">Duration: {node.get('duration', 'N/A')}</TD></TR>
            </TABLE>>"""
            
            dot.node(node['id'], label, shape='none', margin='0')
        
        # Add edges
        for edge in flow_data["edges"]:
            dot.edge(edge['from'], edge['to'], penwidth='2.0', color='#666666')
        
        return dot
    except Exception as e:
        st.error(f"Error creating visualization: {str(e)}")
        return None

# Main application UI
st.title("🎓 Academic & Learning Assistant")

# Create tabs for different functionalities
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📚 Document Analysis",
    "🎯 Learning Path Generator",
    "📊 Data Analysis",
    "🤖 Chat Assistant",
    "⚙️ Settings"
])

with tab1:
    # Document analysis functionality from acd_assistant.py
    st.header("Document Analysis")
    # ... (Document analysis code)

with tab2:
    # Learning path generator from flow_visualizer.py
    st.header("Learning Path Generator")
    
    col1, col2 = st.columns(2)
    with col1:
        topic = st.text_input("Enter your topic:", placeholder="e.g., Machine Learning")
    with col2:
        objective = st.text_input("What's your objective?", placeholder="e.g., Build a ML model")

    viz_type = st.selectbox("Select visualization style:", ["digraph", "flowchart"])

    if st.button("Generate Learning Path"):
        if topic and objective:
            with st.spinner("Creating your learning path..."):
                flow_data = get_flow_from_gemini(topic, objective)
                if flow_data:
                    dot = create_visualization(flow_data, viz_type)
                    if dot:
                        st.graphviz_chart(dot)

with tab3:
    # Data analysis functionality from acd_assistant.py
    st.header("Data Analysis")
    # ... (Data analysis code)

with tab4:
    # Chat functionality
    st.header("Chat Assistant")
    # ... (Chat interface code)

with tab5:
    # Settings
    st.header("Settings")
    max_tokens = st.slider("Max Response Length", 100, 2000, 1000)
    temperature = st.slider("Temperature", 0.0, 1.0, 0.7)

# Sidebar
with st.sidebar:
    st.header("📚 Document Upload")
    uploaded_file = st.file_uploader(
        "Upload your study materials",
        type=["pdf", "csv", "xlsx", "xls", "txt"]
    )
    
    if uploaded_file:
        # ... (File processing code)
        pass

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <p>Academic & Learning Assistant | Your AI Study Companion</p>
</div>
""", unsafe_allow_html=True) 
