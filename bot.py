# bot.py
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler
from config import TELEGRAM_BOT_TOKEN
from parser import parse_songs
from youtube import search_youtube, download_audio
from mixer import mix_stereo
import os
import re

# Store user states
user_states = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message with command menu"""
    welcome = """
🎧 *Audio Mixer Bot*

Mix two songs into stereo (left/right channels)

*Commands:*
/mix - Quick mix with text
/url - Mix from YouTube links
/file - Mix uploaded files
/help - Detailed guide
/cancel - Stop current operation

*Quick Examples:*
`/mix sia snowman and drake hotline bling`
`left: sia, right: drake`
"""
    
    keyboard = [
        ["🎵 /mix", "🔗 /url"],
        ["📁 /file", "ℹ️ /help"]
    ]
    
    await update.message.reply_text(
        welcome,
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Detailed help"""
    help_text = """
📖 *How to Use*

*1. Quick Mix* `/mix`
Just type naturally:
- `/mix sia and drake`
- `left: sia, right: drake`
- `mix sia snowman and drake hotline bling`

*2. YouTube URLs* `/url`
Step-by-step URL submission

*3. Upload Files* `/file`
Step-by-step file upload

*Tips:*
- Include artist names for accuracy
- Files under 20MB
- MP3, M4A, WAV supported

Type /cancel anytime to stop
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel operation and cleanup"""
    user_id = update.message.from_user.id
    
    if user_id in user_states:
        state = user_states[user_id]
        
        # Cleanup files
        for key in ['file1', 'file2']:
            if key in state and os.path.exists(state[key]):
                os.remove(state[key])
        
        del user_states[user_id]
        await update.message.reply_text("❌ Cancelled", reply_markup=ReplyKeyboardRemove())
    else:
        await update.message.reply_text("Nothing to cancel")

async def mix_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick mix command"""
    if not context.args:
        await update.message.reply_text(
            "Usage: `/mix song1 and song2`\n"
            "Example: `/mix sia and drake`",
            parse_mode='Markdown'
        )
        return
    
    query = " ".join(context.args)
    await process_natural_language(update, query)

async def url_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start URL mode"""
    user_id = update.message.from_user.id
    user_states[user_id] = {'mode': 'url', 'step': 1}
    
    await update.message.reply_text(
        "🔗 Send first YouTube URL\n"
        "Example: https://youtu.be/VIDEO_ID\n\n"
        "Type /cancel to stop"
    )

async def file_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start file mode"""
    user_id = update.message.from_user.id
    user_states[user_id] = {'mode': 'file', 'step': 1}
    
    await update.message.reply_text(
        "📁 Upload first audio file\n"
        "Supported: MP3, M4A, WAV (max 20MB)\n\n"
        "Type /cancel to stop"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route messages based on user state"""
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    
    # Handle keyboard shortcuts
    shortcuts = {
        "🎵 /mix": mix_command,
        "🔗 /url": url_command,
        "📁 /file": file_command,
        "ℹ️ /help": help_command
    }
    
    if text in shortcuts:
        await shortcuts[text](update, context)
        return
    
    # Check user mode
    if user_id in user_states:
        mode = user_states[user_id].get('mode')
        
        if mode == 'url':
            await handle_url_step(update, text)
            return
    
    # Default: natural language mix
    await process_natural_language(update, text)

async def handle_url_step(update: Update, text: str):
    """Handle URL mode steps"""
    user_id = update.message.from_user.id
    state = user_states[user_id]
    
    video_id = extract_video_id(text)
    if not video_id:
        await update.message.reply_text(
            "❌ Invalid YouTube URL\n"
            "Send a valid link or /cancel"
        )
        return
    
    if state['step'] == 1:
        state['url1'] = video_id
        state['step'] = 2
        await update.message.reply_text("✅ Got it! Send second YouTube URL")
    else:
        await process_urls(update, state['url1'], video_id)
        del user_states[user_id]

async def handle_audio_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle file uploads"""
    user_id = update.message.from_user.id
    
    try:
        file = await update.message.effective_attachment.get_file()
        file_path = f"uploads/{user_id}_{file.file_id}.mp3"
        os.makedirs("uploads", exist_ok=True)
        await file.download_to_drive(file_path)
        
        if user_id in user_states and user_states[user_id].get('mode') == 'file':
            state = user_states[user_id]
            
            if state['step'] == 1:
                state['file1'] = file_path
                state['step'] = 2
                await update.message.reply_text("✅ Got it! Upload second audio file")
            else:
                await process_files(update, state['file1'], file_path)
                del user_states[user_id]
        else:
            # Quick mode
            if user_id in user_states and 'file1' in user_states[user_id]:
                await process_files(update, user_states[user_id]['file1'], file_path)
                del user_states[user_id]
            else:
                user_states[user_id] = {'file1': file_path}
                await update.message.reply_text("✅ Got it! Upload second file")
    
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        if user_id in user_states:
            del user_states[user_id]

async def process_urls(update: Update, vid1: str, vid2: str):
    """Download and mix from YouTube URLs"""
    try:
        msg = await update.message.reply_text("⏬ Downloading...")
        
        file1 = download_audio(vid1)
        await msg.edit_text("⏬ Downloading 2/2...")
        
        file2 = download_audio(vid2)
        await msg.edit_text("🎛️ Mixing...")
        
        output = mix_stereo(file1, file2, f"mix_{update.message.from_user.id}.mp3")
        
        await msg.edit_text("✅ Done!")
        await update.message.reply_document(document=open(output, 'rb'), filename="mix.mp3")
        
        os.remove(file1)
        os.remove(file2)
        os.remove(output)
    
    except Exception as e:
        await update.message.reply_text(f"❌ {str(e)}")

async def process_files(update: Update, file1: str, file2: str):
    """Mix uploaded files"""
    try:
        msg = await update.message.reply_text("🎛️ Mixing...")
        
        output = mix_stereo(file1, file2, f"mix_{update.message.from_user.id}.mp3")
        
        await msg.edit_text("✅ Done!")
        await update.message.reply_document(document=open(output, 'rb'), filename="mix.mp3")
        
        os.remove(file1)
        os.remove(file2)
        os.remove(output)
    
    except Exception as e:
        await update.message.reply_text(f"❌ {str(e)}")

async def process_natural_language(update: Update, text: str):
    """Parse and mix from natural language"""
    try:
        # Try manual parsing first
        left, right = parse_left_right(text)
        
        if not left or not right:
            msg = await update.message.reply_text("🔍 Parsing...")
            left, right = parse_songs(text)
            
            if not left or not right:
                await msg.edit_text(
                    "❌ Couldn't find two songs\n\n"
                    "Try:\n"
                    "• `/mix song1 and song2`\n"
                    "• `left: song1, right: song2`\n"
                    "• Use /url or /file"
                )
                return
        else:
            msg = await update.message.reply_text(f"🎵 Left: {left}\n🎵 Right: {right}")
        
        await msg.edit_text(f"🎵 {left}\n🎵 {right}\n\n🔍 Searching...")
        
        vid1 = search_youtube(left)
        if not vid1:
            await msg.edit_text(f"❌ Couldn't find: {left}")
            return
        
        vid2 = search_youtube(right)
        if not vid2:
            await msg.edit_text(f"❌ Couldn't find: {right}")
            return
        
        await msg.edit_text("⏬ Downloading...")
        file1 = download_audio(vid1)
        
        await msg.edit_text("⏬ Downloading 2/2...")
        file2 = download_audio(vid2)
        
        await msg.edit_text("🎛️ Mixing...")
        output = mix_stereo(file1, file2, f"mix_{update.message.from_user.id}.mp3")
        
        await msg.edit_text("✅ Done!")
        await update.message.reply_document(document=open(output, 'rb'), filename="mix.mp3")
        
        os.remove(file1)
        os.remove(file2)
        os.remove(output)
    
    except Exception as e:
        await update.message.reply_text(f"❌ {str(e)}")

def extract_video_id(text: str):
    """Extract YouTube video ID"""
    patterns = [
        r'(?:youtu\.be/|youtube\.com/watch\?v=)([a-zA-Z0-9_-]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None

def parse_left_right(text: str):
    """Parse left/right specification"""
    text = re.sub(r'^(mix|combine)\s+', '', text, flags=re.IGNORECASE)
    
    patterns = [
        r'left:\s*(.+?),\s*right:\s*(.+)',
        r'(.+?)\s+on\s+left,?\s*(.+?)\s+on\s+right',
        r'(.+?)\s+and\s+(.+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip(), match.group(2).strip()
    
    return None, None

def run_bot():
    """Start bot"""
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("mix", mix_command))
    app.add_handler(CommandHandler("url", url_command))
    app.add_handler(CommandHandler("file", file_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.AUDIO | filters.Document.AUDIO, handle_audio_file))
    
    print("🤖 Bot running - Command-based interface")
    app.run_polling()
