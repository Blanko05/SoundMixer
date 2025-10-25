# bot.py
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from config import TELEGRAM_BOT_TOKEN
from parser import parse_songs
from youtube import search_youtube, download_audio
from mixer import mix_stereo
import os
import re

# Store pending files per user
user_states = {}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    user_id = update.message.from_user.id
    user_text = update.message.text
    
    try:
        # Check if YouTube URLs
        urls = re.findall(r'(https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+))', user_text)
        
        if len(urls) >= 2:
            await handle_youtube_links(update, urls[0][1], urls[1][1])
            return
        
        # Check for left/right specification
        left_song, right_song = parse_left_right(user_text)
        
        if left_song and right_song:
            await handle_natural_language(update, left_song, right_song)
        else:
            # Fallback to AI parsing
            await update.message.reply_text("🔍 Finding songs...")
            song1, song2 = parse_songs(user_text)
            
            if not song1 or not song2:
                await update.message.reply_text("❌ Couldn't understand. Try:\n• 'mix X and Y'\n• 'left: X, right: Y'\n• Send 2 YouTube links\n• Upload 2 audio files")
                return
            
            await handle_natural_language(update, song1, song2)
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def handle_audio_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle uploaded audio files"""
    user_id = update.message.from_user.id
    
    try:
        # Download the file
        file = await update.message.effective_attachment.get_file()
        file_path = f"uploads/{user_id}_{file.file_id}.mp3"
        os.makedirs("uploads", exist_ok=True)
        await file.download_to_drive(file_path)
        
        # Check if waiting for 2nd file
        if user_id in user_states and user_states[user_id].get('waiting'):
            # Mix with first file
            first_file = user_states[user_id]['file1']
            
            await update.message.reply_text("🎛️ Mixing your files...")
            output = mix_stereo(first_file, file_path, "output.mp3")
            
            await update.message.reply_text("✅ Done! Sending...")
            await update.message.reply_document(document=open(output, 'rb'), filename="mix.mp3")
            
            # Cleanup
            os.remove(first_file)
            os.remove(file_path)
            os.remove(output)
            del user_states[user_id]
            
        else:
            # First file - wait for second
            user_states[user_id] = {'file1': file_path, 'waiting': True}
            await update.message.reply_text("✅ Got file 1! Now send the second audio file.")
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        if user_id in user_states:
            del user_states[user_id]

async def handle_youtube_links(update: Update, vid1: str, vid2: str):
    """Handle direct YouTube links"""
    try:
        await update.message.reply_text("⏬ Downloading from YouTube links...")
        
        file1 = download_audio(vid1)
        await update.message.reply_text("⏬ Downloaded 1/2...")
        
        file2 = download_audio(vid2)
        await update.message.reply_text("⏬ Downloaded 2/2...")
        
        await update.message.reply_text("🎛️ Mixing audio...")
        output = mix_stereo(file1, file2, "output.mp3")
        
        await update.message.reply_text("✅ Done! Sending...")
        await update.message.reply_document(document=open(output, 'rb'), filename="mix.mp3")
        
        # Cleanup
        os.remove(file1)
        os.remove(file2)
        os.remove(output)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def handle_natural_language(update: Update, left_song: str, right_song: str):
    """Handle natural language song requests"""
    try:
        await update.message.reply_text(f"📝 Left: {left_song}\n📝 Right: {right_song}\n\n🔎 Searching YouTube...")
        
        vid1 = search_youtube(left_song)
        if not vid1:
            await update.message.reply_text(f"❌ Couldn't find '{left_song}' on YouTube")
            return
        
        vid2 = search_youtube(right_song)
        if not vid2:
            await update.message.reply_text(f"❌ Couldn't find '{right_song}' on YouTube")
            return
        
        await update.message.reply_text("⏬ Downloading song 1/2...")
        file1 = download_audio(vid1)
        
        await update.message.reply_text("⏬ Downloading song 2/2...")
        file2 = download_audio(vid2)
        
        await update.message.reply_text("🎛️ Mixing audio...")
        output = mix_stereo(file1, file2, "output.mp3")
        
        await update.message.reply_text("✅ Done! Sending...")
        await update.message.reply_document(document=open(output, 'rb'), filename="mix.mp3")
        
        # Cleanup
        os.remove(file1)
        os.remove(file2)
        os.remove(output)
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

def parse_left_right(text: str):
    """Parse 'left: X, right: Y' or 'X on left, Y on right' formats"""
    
    # Pattern 1: "left: X, right: Y"
    pattern1 = r'left:\s*(.+?),\s*right:\s*(.+?)(?:$|\.)'
    match = re.search(pattern1, text, re.IGNORECASE)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    
    # Pattern 2: "X on left, Y on right"
    pattern2 = r'(.+?)\s+on\s+left,?\s*(.+?)\s+on\s+right'
    match = re.search(pattern2, text, re.IGNORECASE)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    
    return None, None

def run_bot():
    """Start the bot"""
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.AUDIO | filters.Document.AUDIO, handle_audio_file))
    
    print("🤖 Bot is running...")
    print("Features:")
    print("  • Natural language: 'mix X and Y'")
    print("  • Specify sides: 'left: X, right: Y'")
    print("  • YouTube links: Send 2 URLs")
    print("  • Upload files: Send 2 audio files")
    app.run_polling()