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
        'quiet': True,
    }
    
    url = f'https://youtube.com/watch?v={video_id}'
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    
    return os.path.join(output_path, f'{video_id}.mp3')

if __name__ == "__main__":
    vid_id = search_youtube("snowman sia")
    print(f"Video ID: {vid_id}")
    file = download_audio(vid_id)
    print(f"Downloaded: {file}")