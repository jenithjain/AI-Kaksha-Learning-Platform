import streamlit as st
import google.generativeai as genai
from moviepy.editor import *
from moviepy.config import change_settings
from pytube import YouTube
import requests
from PIL import Image
import io
import os
import tempfile
import json
import numpy as np
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure ImageMagick path
IMAGEMAGICK_BINARY = "C:\\Program Files\\ImageMagick-7.1.1-Q16-HDRI\\magick.exe"
change_settings({"IMAGEMAGICK_BINARY": IMAGEMAGICK_BINARY})

# Configure API key from environment variable
genai.configure(api_key=os.getenv('GEMINI_API_KEY', 'AIzaSyCjclFHDuq9431tqbtBTwG-COuR7HklbW0'))

def check_imagemagick():
    """Check if ImageMagick is properly configured"""
    try:
        # Try to create a simple TextClip
        clip = TextClip("Test", fontsize=30, color='white')
        clip.close()
        return True
    except Exception as e:
        st.error("""
        ImageMagick is not properly configured. Please:
        1. Download and install ImageMagick from https://imagemagick.org/script/download.php#windows
        2. During installation, ensure you check 'Add application directory to your system path'
        3. Update the IMAGEMAGICK_BINARY path in the code
        """)
        return False

def create_text_clip(text, duration, fontsize=45, position='center'):
    """Create text clip with better visibility"""
    # Create a semi-transparent black background for text
    bg_height = 100
    img = Image.new('RGBA', (1920, bg_height), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Add semi-transparent background
    overlay = Image.new('RGBA', (1920, bg_height), color=(0, 0, 0, 160))
    img.paste(overlay, (0, 0))
    
    try:
        font = ImageFont.truetype("arial.ttf", fontsize)
    except:
        font = ImageFont.load_default()
    
    # Draw text with better positioning
    text_width = draw.textlength(text, font=font)
    x = (1920 - text_width) / 2
    y = (bg_height - fontsize) / 2
    draw.text((x, y), text, font=font, fill='white')
    
    # Convert to MoviePy clip
    txt_clip = ImageClip(np.array(img))
    txt_clip = txt_clip.set_duration(duration)
    
    if position == 'center':
        txt_clip = txt_clip.set_position(('center', 'center'))
    elif position == 'bottom':
        txt_clip = txt_clip.set_position(('center', 0.8))
    
    return txt_clip

def create_audio_clip(text):
    """Create audio clip from text using gTTS with proper file handling"""
    try:
        # Create a unique temporary file
        temp_audio = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
        temp_audio_path = temp_audio.name
        temp_audio.close()

        # Generate and save audio
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(temp_audio_path)
        
        # Load the audio file
        audio_clip = AudioFileClip(temp_audio_path)
        
        # Explicitly close and remove the file
        try:
            os.unlink(temp_audio_path)
        except:
            # If file is still in use, schedule it for deletion on Windows
            try:
                import atexit
                atexit.register(lambda file: os.unlink(file) if os.path.exists(file) else None, temp_audio_path)
            except:
                pass
        
        return audio_clip
        
    except Exception as e:
        st.warning(f"Error creating audio: {str(e)}")
        return None

def search_images(query, num_images=2):
    """Search for images using Google Custom Search API"""
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        'key': "AIzaSyB3bz0Z6X2dXeaHwIpk5xlWBN8CB_-AcNM",
        'cx': "GOOGLE_CX",  # You need to create a Custom Search Engine and get the CX
        'q': query,
        'num': num_images,
        'searchType': 'image',
        'safe': 'high',
        'imgType': 'photo',
        'rights': 'cc_publicdomain|cc_attribute|cc_sharealike'
    }
    
    try:
        response = requests.get(url, params=params)
        results = response.json()
        
        if 'items' in results:
            images = []
            for item in results['items']:
                try:
                    img_response = requests.get(item['link'], timeout=5)
                    img = Image.open(io.BytesIO(img_response.content))
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    images.append(img)
                except Exception as e:
                    st.warning(f"Skipped an image due to error: {str(e)}")
                    continue
            return images
        return None
    except Exception as e:
        st.error(f"Error in image search: {str(e)}")
        return None

def get_ai_script(topic, duration="60 seconds"):
    """Generate AI script for the video"""
    model = genai.GenerativeModel("gemini-1.5-pro")
    prompt = f"""Create a clear, engaging {duration} educational video script about: {topic}

    Return ONLY a JSON object with this EXACT structure (no other text):
    {{
        "sections": [
            {{
                "time": "0-15s",
                "narration": "clear, conversational script text",
                "visuals": "specific description for image search",
                "keywords": ["key1", "key2"]
            }}
        ],
        "title": "catchy video title",
        "summary": "brief summary",
        "search_terms": ["specific terms for image search"]
    }}"""
    
    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Clean the response text
        response_text = response_text.replace('json', '').replace('', '').strip()
        if response_text.startswith('json'):
            response_text = response_text[4:].strip()  # Remove 'json' prefix
        
        # Remove any leading/trailing brackets or whitespace
        response_text = response_text.strip('{}').strip()
        response_text = '{' + response_text + '}'
        
        # Try to parse JSON
        try:
            script_data = json.loads(response_text)
            return script_data
        except json.JSONDecodeError as je:
            st.error(f"Invalid JSON format. Full response: {response_text}")
            return None
            
    except Exception as e:
        st.error(f"Error generating script: {str(e)}")
        st.error("Raw response: " + str(response.text))
        return None

def create_video_clip(section, duration):
    """Create video clip with improved visuals and audio"""
    try:
        # First create the audio to get its exact duration
        audio_clip = create_audio_clip(section['narration'])
        if audio_clip is None:
            return None
            
        # Use audio duration to ensure perfect sync
        actual_duration = audio_clip.duration
        
        # Get images from multiple sources
        images = search_images(section['visuals'], 3)
        if not images and 'keywords' in section:
            images = search_images(' '.join(section['keywords']), 3)
        
        if not images:
            # Fallback to text-only clip
            text_clip = create_text_clip(section['narration'], actual_duration)
            bg_clip = ColorClip((1920, 1080), color=(0, 0, 0))
            bg_clip = bg_clip.set_duration(actual_duration)
            video_clip = CompositeVideoClip([bg_clip, text_clip])
        else:
            clips = []
            segment_duration = actual_duration / len(images)
            
            for img in images:
                temp_img_path = tempfile.mktemp('.jpg')
                img.save(temp_img_path)
                
                # Create image clip with ken burns effect
                img_clip = ImageClip(temp_img_path)
                img_clip = img_clip.resize(width=1920)
                img_clip = img_clip.set_duration(segment_duration)
                
                # Enhanced zoom effect
                zoom = 1.3
                img_clip = img_clip.resize(lambda t: zoom - (zoom-1)*t/segment_duration)
                
                # Add text overlay with fade in/out
                text_clip = create_text_clip(section['narration'], segment_duration, position='bottom')
                text_clip = text_clip.fadein(0.5).fadeout(0.5)
                
                final_clip = CompositeVideoClip([img_clip, text_clip])
                clips.append(final_clip)
                
                os.remove(temp_img_path)
            
            video_clip = concatenate_videoclips(clips, method="compose")
        
        # Ensure video duration matches audio exactly
        video_clip = video_clip.set_duration(actual_duration)
        
        # Add crossfade between clips
        final_clip = video_clip.crossfadein(0.5).crossfadeout(0.5)
        
        # Set audio
        final_clip = final_clip.set_audio(audio_clip)
        
        return final_clip
        
    except Exception as e:
        st.warning(f"Error in clip creation: {str(e)}")
        return create_text_clip(section['narration'], duration)

def generate_video(script):
    """Generate full video from script with enhanced features"""
    clips = []
    
    # Add title clip with smaller font
    title_clip = create_text_clip(
        script['title'],
        duration=3,
        fontsize=60
    ).fadeout(1)
    clips.append(title_clip)
    
    # Process each section
    for section in script['sections']:
        start, end = map(lambda x: int(x.replace('s','')), 
                        section['time'].split('-'))
        duration = end - start
        
        clip = create_video_clip(section, duration)
        if clip is not None:
            # Add transition effects
            clip = clip.crossfadein(0.5)
            clips.append(clip)
    
    # Combine all clips with smooth transitions
    final_video = concatenate_videoclips(clips, method="compose")
    
    # Add background music (optional)
    # bg_music = AudioFileClip("path_to_background_music.mp3")
    # bg_music = bg_music.volumex(0.1).loop(duration=final_video.duration)
    # final_video = final_video.set_audio(CompositeAudioClip([final_video.audio, bg_music]))
    
    return final_video

# Streamlit UI
st.set_page_config(page_title="AI Video Generator", page_icon="🎥", layout="wide")

st.title("🎥 AI Educational Video Generator")
st.write("Create engaging educational videos with AI-generated content and visuals!")

# Input section
col1, col2 = st.columns([2, 1])

with col1:
    topic = st.text_input(
        "What would you like to explain?",
        placeholder="e.g., How does photosynthesis work?"
    )

with col2:
    duration = st.selectbox(
        "Video duration:",
        ["30 seconds", "60 seconds", "90 seconds", "120 seconds"]
    )

if st.button("🎬 Generate Video", use_container_width=True):
    if topic:
        if not check_imagemagick():
            st.error("Please configure ImageMagick before generating videos.")
        else:
            try:
                # Create tabs for process visualization
                script_tab, preview_tab = st.tabs(["📝 Script", "🎥 Video"])
                
                with script_tab:
                    with st.spinner("🤖 AI is writing your script..."):
                        script = get_ai_script(topic, duration)
                        if script:
                            st.success("Script generated successfully!")
                            st.json(script)
                
                with preview_tab:
                    if script:
                        with st.spinner("🎨 Creating your video..."):
                            video = generate_video(script)
                            
                            # Save video
                            temp_video_path = tempfile.mktemp('.mp4')
                            video.write_videofile(
                                temp_video_path,
                                fps=24,
                                codec='libx264',
                                audio_codec='aac'
                            )
                            
                            # Display video
                            st.success("✨ Video generated successfully!")
                            st.video(temp_video_path)
                            
                            # Download button
                            with open(temp_video_path, 'rb') as f:
                                st.download_button(
                                    "⬇ Download Video",
                                    f,
                                    file_name=f"{topic.replace(' ', '_')}.mp4",
                                    mime="video/mp4",
                                    use_container_width=True
                                )
                            
                            # Clean up
                            os.remove(temp_video_path)
                            
            except Exception as e:
                st.error(f"Error generating video: {str(e)}")
                st.error("Please try again with a different topic or duration.")
    else:
        st.warning("Please enter a topic!")

# Sidebar with tips and examples
with st.sidebar:
    st.header("💡 Tips for Great Videos")
    st.markdown("""
    Best Practices:
    1. Be specific with your topic
    2. Use clear, focused questions
    3. Choose appropriate duration
    4. Review the script before video generation
    5. Download videos for offline use
    """)
    
    st.markdown("### 📝 Example Topics")
    st.markdown("""
    - How do black holes work?
    - Explain DNA replication
    - What is machine learning?
    - How do vaccines work?
    - Explain climate change
    """)
    
    st.markdown("### ⚙ Features")
    st.markdown("""
    - AI-generated educational scripts
    - Dynamic visual content
    - Professional transitions
    - HD quality output
    - Downloadable videos
    """)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center'>
        <p>AI Video Generator | Educational Content Creator</p>
        <p style='font-size: 0.8em'>Powered by Gemini AI & Google Image Search</p>
    </div>
    """,
    unsafe_allow_html=True
)