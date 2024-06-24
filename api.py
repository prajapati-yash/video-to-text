import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pydub import AudioSegment
import tempfile
import google.generativeai as genai
import requests
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

temp_files = []

class VideoURL(BaseModel):
    url: str

def summarize_audio(audio_file_path):
    model = genai.GenerativeModel("models/gemini-1.5-pro-latest")
    audio_file = genai.upload_file(path=audio_file_path)
    
    description = "Please provide a summary of the audio content."
    
    response = model.generate_content([description, audio_file])
    return response.text

def make_title(audio_file_path):
    model = genai.GenerativeModel("models/gemini-1.5-pro-latest")
    audio_file = genai.upload_file(path=audio_file_path)
    
    description = "Please generate a title for this audio content."
    
    response = model.generate_content([description, audio_file])
    return response.text

def download_and_convert_to_mp3(url):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        temp_mp4_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        with open(temp_mp4_file.name, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        temp_files.append(temp_mp4_file.name)
        
        temp_mp3_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        audio = AudioSegment.from_file(temp_mp4_file.name, format="mp4")
        audio.export(temp_mp3_file.name, format="mp3")
        temp_files.append(temp_mp3_file.name)
        
        return temp_mp3_file.name
    except Exception as e:
        print(f"Error downloading or converting file: {e}")
        return None

def cleanup_temp_files():
    for file_path in temp_files:
        try:
            os.remove(file_path)
            print(f"Deleted temp file: {file_path}")
        except Exception as e:
            print(f"Error deleting temp file {file_path}: {e}")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Video Analysis API"}

@app.post("/analyze")
def analyze_video(video: VideoURL):
    try:
        audio_file_path = download_and_convert_to_mp3(video.url)
        if not audio_file_path:
            raise HTTPException(status_code=500, detail="Failed to download and convert file.")
        
        description = summarize_audio(audio_file_path)
        title = make_title(audio_file_path)
        
        cleanup_temp_files()
        
        return {"title": title, "description": description}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))