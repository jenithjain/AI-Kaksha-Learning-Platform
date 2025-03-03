from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import google.generativeai as genai
import json
import requests
import time
from pytube import YouTube
from youtube_transcript_api import YouTubeTranscriptApi
import graphviz
import os
import sys
import re

# Configure API keys
GOOGLE_API_KEY = "***************************************"
YOUTUBE_API_KEY = "*************************************"
genai.configure(api_key=GOOGLE_API_KEY)

# Initialize FastAPI app
app = FastAPI(
    title="AI Learning Platform API",
    description="API for AI-powered learning tools including video processing, learning paths, and resource finding",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

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

# ===== PYDANTIC MODELS =====

class VideoRequest(BaseModel):
    url: str = Field(..., description="YouTube video URL")

class QuestionRequest(BaseModel):
    video_id: str = Field(..., description="YouTube video ID")
    question: str = Field(..., description="Question about the video content")

class LearningPathRequest(BaseModel):
    topic: str = Field(..., description="Learning topic")
    objective: str = Field(..., description="Learning objective")
    viz_type: str = Field("digraph", description="Visualization type (digraph or flowchart)")

class ResourceRequest(BaseModel):
    topic: str = Field(..., description="Topic to find resources for")

# ===== HELPER FUNCTIONS =====

def extract_video_id(url):
    """Extract YouTube video ID from URL"""
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
        r'(?:watch\?v=)([0-9A-Za-z_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def get_transcript(video_id):
    """Get transcript for a YouTube video"""
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        return transcript_list
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Could not get transcript: {str(e)}")

def get_video_info(video_id):
    """Get video information using pytube"""
    try:
        yt = YouTube(f"https://www.youtube.com/watch?v={video_id}")
        return {
            "title": yt.title,
            "author": yt.author,
            "length": yt.length,
            "thumbnail_url": yt.thumbnail_url
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Could not get video info: {str(e)}")

def generate_summary(text):
    """Generate summary using Gemini"""
    try:
        summary_prompt = f"""Summarize the following content in a concise way:
        {text}
        
        Provide a clear, structured summary that captures the main points and key insights.
        """
        
        response = model.generate_content(summary_prompt)
        return response.text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating summary: {str(e)}")

def generate_notes(text):
    """Generate study notes using Gemini"""
    try:
        notes_prompt = f"""Create detailed study notes from the following content:
        {text}
        
        Format the notes with:
        - Main topics and subtopics
        - Key concepts explained
        - Important definitions
        - Bullet points for clarity
        """
        
        response = model.generate_content(notes_prompt)
        return response.text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating notes: {str(e)}")

def get_qa_response(question, context):
    """Get answer to user question using Gemini"""
    try:
        qa_prompt = f"""Answer the following question based on this content:
        
        Content: {context}
        
        Question: {question}
        
        Provide a detailed, accurate answer using only information from the content.
        """
        
        response = model.generate_content(qa_prompt)
        return response.text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error answering question: {str(e)}")

def generate_quiz(text):
    """Generate quiz questions using Gemini"""
    try:
        quiz_prompt = f"""Create a quiz based on this content. Format your response as a valid JSON array of questions.
        Content: {text}

        Requirements:
        1. Generate exactly 5 questions
        2. Mix of multiple choice and true/false questions
        3. Each question must follow this exact JSON format:
        {{
            "type": "multiple_choice",
            "difficulty": "easy",
            "question": "What is...",
            "options": ["option1", "option2", "option3", "option4"],
            "correct_answer": 0,
            "explanation": "Explanation here",
            "source": "Content"
        }}
        
        Ensure the response is ONLY the JSON array with no additional text.
        """
        
        response = model.generate_content(quiz_prompt)
        quiz_text = response.text.strip()
        
        # Clean the response to ensure valid JSON
        if "```json" in quiz_text:
            quiz_text = quiz_text.split("```json")[1].split("```")[0].strip()
        elif "```" in quiz_text:
            quiz_text = quiz_text.split("```")[1].strip()
        
        return json.loads(quiz_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating quiz: {str(e)}")

def check_graphviz():
    """Check if Graphviz is installed and accessible"""
    if sys.platform == "win32":
        graphviz_paths = [
            r"C:\Program Files\Graphviz\bin",
            r"C:\Program Files (x86)\Graphviz\bin"
        ]
        for path in graphviz_paths:
            if os.path.exists(path):
                os.environ["PATH"] += os.pathsep + path
                return True
    return False

def get_flow_from_gemini(topic, objective):
    """Get flow structure from Gemini API"""
    try:
        prompt = f"""As an expert AI agent specializing in creating detailed learning paths and roadmaps, please create a comprehensive flow for:

        Topic: {topic}
        Objective: {objective}

        Requirements:
        1. Break down the process into clear, actionable steps
        2. Include specific resources, tools, and estimated time for each step
        3. Consider prerequisites and dependencies
        4. Add practical milestones and checkpoints
        5. Include best practices and common pitfalls to avoid

        Return the response STRICTLY in this JSON format:
        {{
            "nodes": [
                {{
                    "id": "1",
                    "label": "Step Name",
                    "description": "Detailed description including:
                                - Specific actions to take
                                - Required resources
                                - Estimated time
                                - Key learning points
                                - Practical exercises
                                - Success criteria",
                    "duration": "X weeks/days",
                    "resources": ["Resource 1", "Resource 2"]
                }},
                // more nodes...
            ],
            "edges": [
                {{"from": "1", "to": "2"}},
                // more connections...
            ]
        }}

        Make the flow practical, actionable, and comprehensive."""

        response = model.generate_content(prompt)
        json_str = response.text.strip()
        
        # Clean the response to ensure valid JSON
        if '```json' in json_str:
            json_str = json_str.split('```json')[1].split('```')[0].strip()
        elif '```' in json_str:
            json_str = json_str.split('```')[1].strip()
            
        return json.loads(json_str)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating learning path: {str(e)}")

def get_recommendations_from_gemini(topic):
    """Get course and book recommendations using Gemini API"""
    try:
        prompt = f"""As an expert in {topic}, provide a curated list of the best learning resources.
        
        Please provide:
        1. Top 3 Coursera courses with direct links
        2. Top 3 Udemy courses with direct links
        3. Top 3 books with authors and Amazon links
        4. Top 3 YouTube tutorial channels or playlists
        
        Format your response EXACTLY as this JSON:
        {{
            "coursera_courses": [
                {{
                    "title": "exact course title",
                    "link": "https://www.coursera.org/...",
                    "description": "brief description"
                }}
            ],
            "udemy_courses": [
                {{
                    "title": "exact course title",
                    "link": "https://www.udemy.com/course/...",
                    "description": "brief description"
                }}
            ],
            "books": [
                {{
                    "title": "exact book title",
                    "author": "author name",
                    "link": "https://www.amazon.com/...",
                    "description": "brief description"
                }}
            ],
            "youtube_tutorials": [
                {{
                    "title": "tutorial title",
                    "link": "https://www.youtube.com/...",
                    "channel": "channel name"
                }}
            ]
        }}
        
        Ensure all links are real and active. Include only highly-rated and current resources."""

        response = model.generate_content(prompt)
        json_str = response.text.strip()
        
        # Clean the response to ensure valid JSON
        if '```json' in json_str:
            json_str = json_str.split('```json')[1].split('```')[0].strip()
        elif '```' in json_str:
            json_str = json_str.split('```')[1].strip()
            
        return json.loads(json_str)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting recommendations: {str(e)}")

# ===== API ENDPOINTS =====

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "AI Learning Platform API",
        "version": "1.0.0",
        "endpoints": {
            "video": "/video",
            "question": "/question",
            "quiz": "/quiz",
            "learning-path": "/learning-path",
            "resources": "/resources"
        }
    }

# ----- VIDEO PROCESSING ENDPOINTS -----

@app.post("/video")
async def process_video(request: VideoRequest):
    """Process a YouTube video and return summary, notes, and transcript"""
    video_id = extract_video_id(request.url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")
    
    # Get video info
    video_info = get_video_info(video_id)
    
    # Get transcript
    transcript = get_transcript(video_id)
    
    # Combine transcript text
    full_text = " ".join([item["text"] for item in transcript])
    
    # Generate summary and notes
    summary = generate_summary(full_text)
    notes = generate_notes(full_text)
    
    return {
        "video_id": video_id,
        "video_info": video_info,
        "summary": summary,
        "notes": notes,
        "transcript": transcript,
        "full_text": full_text
    }

@app.post("/question")
async def answer_question(request: QuestionRequest):
    """Answer a question about a video's content"""
    # Get transcript
    transcript = get_transcript(request.video_id)
    
    # Combine transcript text
    full_text = " ".join([item["text"] for item in transcript])
    
    # Get answer
    answer = get_qa_response(request.question, full_text)
    
    return {
        "question": request.question,
        "answer": answer
    }

@app.get("/quiz/{video_id}")
async def get_quiz(video_id: str):
    """Generate a quiz for a video"""
    # Get transcript
    transcript = get_transcript(video_id)
    
    # Combine transcript text
    full_text = " ".join([item["text"] for item in transcript])
    
    # Generate quiz
    quiz = generate_quiz(full_text)
    
    return {
        "video_id": video_id,
        "quiz": quiz
    }

# ----- LEARNING PATH ENDPOINTS -----

@app.post("/learning-path")
async def create_learning_path(request: LearningPathRequest):
    """Create a learning path for a topic and objective"""
    # Check if Graphviz is installed
    graphviz_installed = check_graphviz()
    
    # Get learning path data
    flow_data = get_flow_from_gemini(request.topic, request.objective)
    
    # Create visualization if Graphviz is installed
    visualization_url = None
    if graphviz_installed:
        try:
            dot = graphviz.Digraph(
                comment='Flow Visualization',
                graph_attr={
                    'rankdir': 'LR' if request.viz_type == "digraph" else 'TB',
                    'splines': 'ortho',
                    'nodesep': '0.8',
                    'ranksep': '1.0',
                    'fontname': 'Arial',
                    'fontsize': '12'
                }
            )
            
            # Add nodes
            for node in flow_data["nodes"]:
                dot.node(node['id'], node['label'])
            
            # Add edges
            for edge in flow_data["edges"]:
                dot.edge(edge['from'], edge['to'])
            
            # Render visualization
            dot.render("learning_path", format="png", cleanup=True)
            visualization_url = "learning_path.png"
        except Exception as e:
            visualization_url = None
    
    return {
        "topic": request.topic,
        "objective": request.objective,
        "flow_data": flow_data,
        "visualization_available": graphviz_installed,
        "visualization_url": visualization_url
    }

# ----- RESOURCE FINDER ENDPOINTS -----

@app.post("/resources")
async def find_resources(request: ResourceRequest):
    """Find learning resources for a topic"""
    # Get recommendations
    resources = get_recommendations_from_gemini(request.topic)
    
    return {
        "topic": request.topic,
        "resources": resources
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 
