import streamlit as st
import google.generativeai as genai
import graphviz
import json
from PIL import Image
import os
import sys

# Configure Gemini
genai.configure(api_key="********************************")

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

    model = genai.GenerativeModel(
        model_name="gemini-1.5-pro",
        generation_config={
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
        }
    )

    try:
        response = model.generate_content(prompt)
        json_str = response.text.strip()
        if 'json' in json_str:
            json_str = json_str.split('json')[1].split('```')[0]
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
        
        # Add nodes with enhanced styling but without HTML tags
        for node in flow_data["nodes"]:
            # Clean the label text by removing HTML tags
            label = f"""[{node['label']}]
Duration: {node.get('duration', 'N/A')}
{node['description'][:100]}..."""
            
            dot.node(node['id'], 
                    label,
                    shape='box',
                    style='rounded,filled',
                    fillcolor='lightblue',
                    margin='0.2')
        
        # Add edges with styling
        for edge in flow_data["edges"]:
            dot.edge(edge['from'], edge['to'],
                    penwidth='2.0',
                    color='#666666')
        
        return dot
    except Exception as e:
        st.error(f"Error creating visualization: {str(e)}")
        return None

# Check Graphviz installation
if not check_graphviz():
    st.error("""Graphviz is not installed or not found in PATH. Please install Graphviz:
    1. Download from https://graphviz.org/download/
    2. Run installer and check 'Add to PATH'
    3. Restart your application""")
    st.stop()

# Streamlit UI with enhanced styling
st.set_page_config(layout="wide")
st.title("🎯 Advanced Learning Path Generator")
st.markdown("""
<style>
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        padding: 10px 20px;
    }
    .stSelectbox {
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Input section with examples
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

if st.button("Generate Learning Path", key="generate"):
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
                            dot.render("flow_chart", format="png", cleanup=True)
                            with open("flow_chart.png", "rb") as file:
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
                        with st.expander(f"📚 {node['label']} ({node.get('duration', 'N/A')})"):
                            st.markdown("### Description")
                            st.write(node['description'])
                            
                            st.markdown("### Learning Resources")
                            
                            # Display Courses
                            if "courses" in node.get("resources", {}):
                                st.markdown("#### 🎓 Online Courses")
                                for course in node["resources"]["courses"]:
                                    st.markdown(f"""
                                    - [{course['title']}]({course['link']})
                                      - Platform: {course['platform']}
                                      - {course.get('description', '')}
                                    """)
                            
                            # Display Videos
                            if "videos" in node.get("resources", {}):
                                st.markdown("#### 🎥 Video Tutorials")
                                for video in node["resources"]["videos"]:
                                    st.markdown(f"""
                                    - [{video['title']}]({video['link']})
                                      - Channel: {video['channel']}
                                    """)
                            
                            # Display Documentation
                            if "documentation" in node.get("resources", {}):
                                st.markdown("#### 📄 Documentation")
                                for doc in node["resources"]["documentation"]:
                                    st.markdown(f"- [{doc['name']}]({doc['link']})")
                            
                            # Display GitHub Repositories
                            if "github" in node.get("resources", {}):
                                st.markdown("#### 💻 GitHub Repositories")
                                for repo in node["resources"]["github"]:
                                    st.markdown(f"- [{repo['name']}]({repo['link']})")
                            
                            # Display Books
                            if "books" in node.get("resources", {}):
                                st.markdown("#### 📚 Books")
                                for book in node["resources"]["books"]:
                                    st.markdown(f"""
                                    - [{book['title']}]({book['link']})
                                      - Author: {book['author']}
                                    """)
    else:
        st.warning("Please enter both topic and objective!")

# Sidebar with tips and examples
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
