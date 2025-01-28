import openai
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

def summarize_entry(entry, max_tokens=1024, temperature=1.0):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Summarize the following journal entry" + "\n\n" + entry}],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content

# Example usage
prompt = "Today was a productive day. I managed to finish my work early and spent the evening relaxing with a good book."
output = summarize_entry(prompt)
print(output) 