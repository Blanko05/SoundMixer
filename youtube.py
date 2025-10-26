from googleapiclient.discovery import build
import yt_dlp
import os
from config import YOUTUBE_API_KEY

def search_youtube(query):
    """Search YouTube and return first video ID"""
    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    
    request = youtube.search().list(
        part='snippet',
        q=query,
        maxResults=1,
        type='video'
    )
    
    response = request.execute()
    
    if response['items']:
        video_id = response['items'][0]['id']['videoId']
        return video_id
    return None

def download_audio(video_id, output_path='downloads'):
    """Download audio from YouTube video"""
    os.makedirs(output_path, exist_ok=True)
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(output_path, '%(id)s.%(ext)s'),
        'quiet': False,  # Set to False to see more info
        'cookiefile': 'cookies.txt',  # Directly use the cookies file
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
        },
    }
    
    url = f'https://youtube.com/watch?v={video_id}'
    
    try:
        print("Downloading with cookies authentication...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        return os.path.join(output_path, f'{video_id}.mp3')
    
    except Exception as e:
        print(f"Download error: {e}")
        return None


def download_audio_fallback(video_id, output_path='downloads'):
    """Fallback download method without post-processing"""
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_path, f'{video_id}.%(ext)s'),
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        },
        'retries': 5,
    }
    
    url = f'https://youtube.com/watch?v={video_id}'
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    
    # Find the downloaded file
    for file in os.listdir(output_path):
        if file.startswith(video_id):
            return os.path.join(output_path, file)
    
    return None

if __name__ == "__main__":
    vid_id = search_youtube("snowman sia")
    print(f"Video ID: {vid_id}")
    if vid_id:
        file = download_audio(vid_id)
        print(f"Downloaded: {file}")
