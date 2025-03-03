import streamlit as st
import google.generativeai as genai
import graphviz
import json
import requests
import pandas as pd
import time
import gc
import os
import sys
from pytube import YouTube
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlencode, quote
from bs4 import BeautifulSoup

# Configure page
st.set_page_config(
    page_title="AI Learning Platform",
    page_icon="📚",
    layout="wide"
)

# Configure API keys
GOOGLE_API_KEY = "***************************************"
YOUTUBE_API_KEY = "**************************************"
genai.configure(api_key=GOOGLE_API_KEY)

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
if "http_session" not in st.session_state:
    st.session_state.http_session = requests.Session()

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

# ===== LEARNING ASSISTANT FUNCTIONS =====

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
        st.error(f"Error generating summary: {str(e)}")
        return "Could not generate summary."

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
        st.error(f"Error generating notes: {str(e)}")
        return "Could not generate study notes."

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
        st.error(f"Error answering question: {str(e)}")
        return "Could not answer the question."

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
            quiz_text = quiz_text.split("```json")[1].split("```")[0]
        elif "```" in quiz_text:
            quiz_text = quiz_text.split("```")[1]
            
        quiz_text = quiz_text.strip()
        
        # Parse JSON
        quiz_data = json.loads(quiz_text)
        
        # Validate quiz format
        if not isinstance(quiz_data, list) or len(quiz_data) == 0:
            raise ValueError("Invalid quiz format")
            
        return quiz_data
        
    except json.JSONDecodeError as e:
        st.error(f"Error parsing quiz response: {str(e)}")
        return None
    except Exception as e:
        st.error(f"Error generating quiz: {str(e)}")
        return None

def display_quiz(quiz):
    """Display quiz with enhanced features."""
    for i, q in enumerate(quiz):
        with st.expander(f"Question {i+1} ({q['difficulty'].upper()}) - {q['type'].replace('_', ' ').title()}", expanded=True):
            st.write(q['question'])
            st.caption(f"Source: {q['source']}")
            
            # Create unique keys for each question
            answer_key = f"answer_{i}"
            
            # Initialize answer in session state if not present
            if answer_key not in st.session_state.quiz_answers:
                st.session_state.quiz_answers[answer_key] = None
            
            # Radio button for answer selection
            selected_answer = st.radio(
                "Select your answer:",
                options=q['options'],
                key=answer_key,
                index=None if st.session_state.quiz_answers[answer_key] is None 
                      else q['options'].index(st.session_state.quiz_answers[answer_key])
            )
            
            # Update answer in session state
            if selected_answer is not None:
                st.session_state.quiz_answers[answer_key] = selected_answer
            
            # Check Answer button
            if st.button("Check Answer", key=f"check_{i}"):
                if selected_answer is not None:
                    is_correct = q['options'].index(selected_answer) == q['correct_answer']
                    if is_correct:
                        st.success("✅ Correct!")
                    else:
                        st.error(f"❌ Incorrect. The correct answer is: {q['options'][q['correct_answer']]}")
                    # Show explanation automatically when answer is checked
                    st.info(f"📝 Explanation: {q['explanation']}")
                else:
                    st.warning("Please select an answer first!")

def process_video(url):
    """Process YouTube video to extract transcript and generate content"""
    try:
        # Extract video ID
        if "youtube.com" in url or "youtu.be" in url:
            if "youtube.com" in url:
                video_id = url.split("v=")[1].split("&")[0]
            else:
                video_id = url.split("/")[-1].split("?")[0]
        else:
            st.error("Please enter a valid YouTube URL")
            return False
        
        # Get video transcript
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
        except Exception as e:
            st.error(f"Error getting transcript: {str(e)}")
            return False
        
        # Combine transcript text
        full_text = " ".join([entry["text"] for entry in transcript])
        
        # Generate summary and notes
        with st.spinner("Generating summary..."):
            final_summary = generate_summary(full_text)
        
        with st.spinner("Creating study notes..."):
            final_notes = generate_notes(full_text)
        
        # Store in session state
        st.session_state.video_url = url
        st.session_state.transcript = transcript
        st.session_state.summary = final_summary
        st.session_state.notes = final_notes
        st.session_state.full_text = full_text
        
        gc.collect()
        return True
            
    except Exception as e:
        st.error(f"Error processing video: {str(e)}")
        return False

# ===== LEARNING PATH GENERATOR FUNCTIONS =====

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
    return True  # Return True anyway to avoid blocking functionality

def get_flow_from_gemini(topic, objective):
    """Get flow structure from Gemini API with improved prompt"""
    
    prompt = f"""As an expert AI agent specializing in creating detailed learning paths and roadmaps, please create a comprehensive flow for:

Topic: {topic}
Objective: {objective}

Requirements:
1. Break down the process into clear, actionable steps
2. Include specific resources, tools, and estimated time for each step
3. Consider prerequisites and dependencies
4. Add practical milestones and checkpoints
5. Include best practices and common pitfalls to avoid
6. For each step, provide:
   - Specific online courses with links (Coursera, Udemy)
   - Book recommendations with authors
   - Video tutorials
   - Practice exercises

Return the response STRICTLY in this JSON format:
{{
    "nodes": [
        {{
            "id": "1",
            "label": "Step Name",
            "description": "Detailed description including key learning points",
            "duration": "X weeks/days",
            "resources": {{
                "courses": [
                    {{
                        "title": "Course Title",
                        "platform": "Coursera/Udemy",
                        "link": "https://www.coursera.org/..."
                    }}
                ],
                "books": [
                    {{
                        "title": "Book Title",
                        "author": "Author Name",
                        "link": "https://www.amazon.com/..."
                    }}
                ],
                "videos": [
                    {{
                        "title": "Video Title",
                        "platform": "YouTube",
                        "link": "https://www.youtube.com/..."
                    }}
                ],
                "practice": [
                    "Practice exercise 1",
                    "Practice exercise 2"
                ]
            }}
        }}
    ],
    "edges": [
        {{"from": "1", "to": "2"}}
    ]
}}

Make the flow practical, actionable, and comprehensive."""

    try:
        response = model.generate_content(prompt)
        json_str = response.text.strip()
        if '```json' in json_str:
            json_str = json_str.split('```json')[1].split('```')[0]
        elif '```' in json_str:
            json_str = json_str.split('```')[1].split('```')[0]
        return json.loads(json_str)
    except Exception as e:
        st.error(f"Error generating content: {str(e)}")
        return None

def create_visualization(flow_data, viz_type="digraph"):
    """Create enhanced visualization using Graphviz"""
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
        
        # Add nodes with enhanced styling
        for node in flow_data["nodes"]:
            label = f"{node['label']}\n({node.get('duration', 'N/A')})"
            
            dot.node(node['id'], label,
                    shape='box',
                    style='filled',
                    fillcolor='lightblue',
                    margin='0.2')
        
        # Add edges with styling
        for edge in flow_data["edges"]:
            dot.edge(edge['from'], edge['to'],
                    penwidth='1.5',
                    color='#666666')
        
        return dot
    except Exception as e:
        st.error(f"Error creating visualization: {str(e)}")
        return None

def display_step_resources(node):
    """Display resources with embedded links"""
    if 'resources' in node:
        resources = node['resources']
        
        # Courses Section
        if 'courses' in resources and resources['courses']:
            st.markdown("### 🎓 Online Courses")
            for course in resources['courses']:
                st.markdown(f"""
                - [{course['title']}]({course['link']})
                  - Platform: {course.get('platform', 'Online')}
                """)
        
        # Books Section
        if 'books' in resources and resources['books']:
            st.markdown("### 📚 Recommended Books")
            for book in resources['books']:
                st.markdown(f"""
                - [{book['title']}]({book['link']})
                  - Author: {book.get('author', 'Unknown')}
                """)
        
        # Videos Section
        if 'videos' in resources and resources['videos']:
            st.markdown("### 🎥 Video Tutorials")
            for video in resources['videos']:
                st.markdown(f"""
                - [{video['title']}]({video['link']})
                  - Platform: {video.get('platform', 'YouTube')}
                """)
        
        # Practice Exercises
        if 'practice' in resources and resources['practice']:
            st.markdown("### 💪 Practice Exercises")
            for exercise in resources['practice']:
                st.markdown(f"- {exercise}")

# ===== RESOURCE FINDER FUNCTIONS =====

def get_recommendations_from_gemini(topic):
    """Get course and book recommendations using Gemini API"""
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

    try:
        response = model.generate_content(prompt)
        json_str = response.text.strip()
        if '```json' in json_str:
            json_str = json_str.split('```json')[1].split('```')[0]
        elif '```' in json_str:
            json_str = json_str.split('```')[1].split('```')[0]
        return json.loads(json_str)
    except Exception as e:
        st.error(f"Error getting recommendations: {str(e)}")
        return None

def get_youtube_videos(query):
    """Fetches relevant YouTube videos using YouTube API"""
    try:
        search_url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": 3,
            "key": YOUTUBE_API_KEY
        }
        response = requests.get(search_url, params=params)
        results = response.json()

        videos = []
        if "items" in results:
            for item in results["items"]:
                video_id = item["id"]["videoId"]
                videos.append({
                    "title": item["snippet"]["title"],
                    "link": f"https://www.youtube.com/watch?v={video_id}",
                    "channel": item["snippet"]["channelTitle"]
                })
        return videos
    except Exception as e:
        st.warning(f"Could not fetch YouTube videos: {e}")
        return []

# ===== MAIN APP UI =====

# App navigation
st.sidebar.title("📚 AI Learning Platform")
app_mode = st.sidebar.selectbox(
    "Choose a Tool",
    ["Learning Assistant", "Learning Path Generator", "Resource Finder"]
)

# Learning Assistant
if app_mode == "Learning Assistant":
    st.title("📚 AI Learning Assistant")
    st.caption("Learn from educational videos with AI-powered summaries, notes, and quizzes")
    
    # Video input
    video_url = st.text_input("Enter YouTube URL")
    
    if st.button("Process Video"):
        if video_url:
            success = process_video(video_url)
            if success:
                st.success("Video processed successfully!")
    
    # Display content if video is processed
    if st.session_state.video_url:
        # Create tabs
        tab1, tab2, tab3, tab4 = st.tabs(["Summary & Notes", "Q&A", "Quiz", "Transcript"])
        
        # Summary & Notes tab
        with tab1:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Summary")
                st.write(st.session_state.summary)
                
            with col2:
                st.subheader("Study Notes")
                st.write(st.session_state.notes)
        
        # Q&A tab
        with tab2:
            st.subheader("Ask Questions")
            user_question = st.text_input("Ask a question about the video content")
            
            if user_question:
                with st.spinner("Thinking..."):
                    response = get_qa_response(user_question, st.session_state.full_text)
                    st.session_state.qa_history.append({"question": user_question, "answer": response})
            
            # Display Q&A history
            for qa in st.session_state.qa_history:
                with st.expander(f"Q: {qa['question']}", expanded=True):
                    st.write(qa['answer'])
        
        # Quiz tab
        with tab3:
            if st.button("Generate New Quiz"):
                with st.spinner("Creating quiz..."):
                    st.session_state.quiz_answers = {}  # Reset answers
                    st.session_state.quiz_results = {}  # Reset results
                    quiz = generate_quiz(st.session_state.full_text)
                    if quiz:
                        st.session_state.quiz_data = quiz
                        display_quiz(quiz)
            
            # Display existing quiz if available
            if st.session_state.quiz_data:
                display_quiz(st.session_state.quiz_data)
        
        # Transcript tab
        with tab4:
            st.subheader("Video Transcript")
            if st.session_state.transcript:
                df = pd.DataFrame(st.session_state.transcript)
                df['start'] = df['start'].apply(lambda x: time.strftime('%H:%M:%S', time.gmtime(x)))
                st.dataframe(df[['start', 'text']], use_container_width=True)
    
    else:
        st.info("Please enter a YouTube URL to get started!")

# Learning Path Generator
elif app_mode == "Learning Path Generator":
    st.title("🎯 Learning Path Generator")
    st.markdown("Create a personalized learning roadmap for any topic")
    
    # Check Graphviz installation
    if not check_graphviz():
        st.warning("""Graphviz is not installed or not found in PATH. Visualization may not work properly.
        Please install Graphviz:
        1. Download from https://graphviz.org/download/
        2. Run installer and check 'Add to PATH'
        3. Restart your application""")
    
    # Input section
    col1, col2 = st.columns(2)
    with col1:
        topic = st.text_input(
            "Enter your topic:",
            placeholder="e.g., Machine Learning, Web Development, Digital Marketing"
        )
        st.caption("Be specific about what you want to learn")
    
    with col2:
        objective = st.text_input(
            "What's your objective?",
            placeholder="e.g., Build a production-ready ML model in 3 months"
        )
        st.caption("Include timeframe and specific goals")
    
    viz_type = st.selectbox(
        "Select visualization style:",
        ["digraph", "flowchart"],
        help="Digraph shows horizontal flow, Flowchart shows vertical flow"
    )
    
    if st.button("Generate Learning Path", key="generate_path"):
        if topic and objective:
            with st.spinner("Creating your personalized learning path..."):
                flow_data = get_flow_from_gemini(topic, objective)
                
                if flow_data:
                    # Create tabs for different views
                    tab1, tab2 = st.tabs(["Visual Roadmap", "Detailed Steps"])
                    
                    with tab1:
                        dot = create_visualization(flow_data, viz_type)
                        if dot:
                            st.graphviz_chart(dot)
                            
                            # Save visualization
                            try:
                                dot.render("learning_path", format="png", cleanup=True)
                                with open("learning_path.png", "rb") as file:
                                    st.download_button(
                                        label="📥 Download Roadmap",
                                        data=file,
                                        file_name="learning_roadmap.png",
                                        mime="image/png"
                                    )
                            except Exception as e:
                                st.warning(f"Could not save visualization: {str(e)}")
                    
                    with tab2:
                        for node in flow_data["nodes"]:
                            with st.expander(f"📚 {node['label']} ({node.get('duration', 'N/A')})", expanded=True):
                                st.markdown("### Description")
                                st.write(node['description'])
                                
                                # Display resources
                                display_step_resources(node)
        else:
            st.warning("Please enter both topic and objective!")
    
    # Tips in sidebar
    with st.sidebar:
        st.subheader("💡 Tips for Best Results")
        st.markdown("""
        - Be specific about your learning goals
        - Include your current skill level
        - Specify time constraints
        - Mention any specific technologies
        - Include desired outcome
        """)
        
        st.subheader("📝 Example Topics")
        st.markdown("""
        1. "Learn Python for Data Science in 3 months"
        2. "Master React.js for Full-Stack Development"
        3. "Learn Digital Marketing for E-commerce"
        4. "DevOps Engineering Career Path"
        """)

# Resource Finder
elif app_mode == "Resource Finder":
    st.title("📚 Learning Resource Finder")
    st.write("Find the best courses, books, and tutorials for any topic!")
    
    # Input section
    topic = st.text_input("What do you want to learn?", 
                         placeholder="e.g., Python Programming, Machine Learning, Web Development")
    
    if st.button("Find Resources", key="search"):
        if topic:
            with st.spinner("Finding the best learning resources for you..."):
                # Get recommendations from Gemini
                resources = get_recommendations_from_gemini(topic)
                
                if resources:
                    st.success("Found learning resources!")
                    
                    # Create tabs for different resource types
                    tab1, tab2, tab3, tab4 = st.tabs([
                        "📚 Books", 
                        "🎓 Coursera", 
                        "💻 Udemy", 
                        "🎥 Videos"
                    ])
                    
                    with tab1:
                        if "books" in resources and resources["books"]:
                            for book in resources["books"]:
                                st.markdown(f"""
                                ### [{book['title']}]({book['link']})
                                **Author:** {book['author']}  
                                **Description:** _{book.get('description', '')}_
                                ---
                                """)
                        else:
                            st.info("No book recommendations found for this topic.")
                    
                    with tab2:
                        if "coursera_courses" in resources and resources["coursera_courses"]:
                            for course in resources["coursera_courses"]:
                                st.markdown(f"""
                                ### [{course['title']}]({course['link']})
                                _{course.get('description', '')}_
                                ---
                                """)
                        else:
                            st.info("No Coursera courses found for this topic.")
                    
                    with tab3:
                        if "udemy_courses" in resources and resources["udemy_courses"]:
                            for course in resources["udemy_courses"]:
                                st.markdown(f"""
                                ### [{course['title']}]({course['link']})
                                _{course.get('description', '')}_
                                ---
                                """)
                        else:
                            st.info("No Udemy courses found for this topic.")
                    
                    with tab4:
                        if "youtube_tutorials" in resources and resources["youtube_tutorials"]:
                            for video in resources["youtube_tutorials"]:
                                st.markdown(f"""
                                ### [{video['title']}]({video['link']})
                                **Channel:** {video['channel']}
                                ---
                                """)
                        else:
                            st.info("No YouTube tutorials found for this topic.")
        else:
            st.warning("Please enter a topic to search!")

    # Sidebar with tips
    with st.sidebar:
        st.markdown("### 💡 Tips for Better Results")
        st.markdown("""
        - Be specific with your topic
        - Include your skill level
        - Mention specific technologies
        - Add learning goals
        """)
        
        st.markdown("### 📝 Example Topics")
        st.markdown("""
        - Python for Data Science
        - React.js for Beginners
        - Advanced Machine Learning
        - Full Stack Web Development
        - DevOps Engineering
        """)

# Footer
st.markdown("---")
st.caption("AI Learning Platform | Powered by Gemini AI") 
