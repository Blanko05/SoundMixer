# parser.py
from openai import OpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

def parse_songs(user_message):
    """Extract two song names from user message using OpenAI"""
    
    response = client.chat.completions.create(
        model="gpt-5-nano",
        messages=[
            {
                "role": "system",
                "content": """Extract two song names from the user's message. 
                Return ONLY a JSON object with this format:
                {"song1": "song name 1", "song2": "song name 2"}
                
                Examples:
                "mix snowman by sia and 1998 by sleepy hallow" -> {"song1": "snowman sia", "song2": "1998 sleepy hallow"}
                "bad guy and french lessons" -> {"song1": "bad guy billie eilish", "song2": "french lessons"}"""
            },
            {"role": "user", "content": user_message}
        ],
        response_format={"type": "json_object"}
    )
    
    import json
    result = json.loads(response.choices[0].message.content)
    return result.get('song1'), result.get('song2')

if __name__ == "__main__":
    s1, s2 = parse_songs("mix snowman by sia with 1998 by sleepy hallow")
    print(f"Song 1: {s1}")
    print(f"Song 2: {s2}")