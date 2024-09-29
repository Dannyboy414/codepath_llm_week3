from dotenv import load_dotenv
import chainlit as cl

load_dotenv()

# Import the function from movie_functions.py
from movie_functions import get_now_playing_movies

# Note: If switching to LangSmith, uncomment the following, and replace @observe with @traceable
# from langsmith.wrappers import wrap_openai
# from langsmith import traceable
# client = wrap_openai(openai.AsyncClient())

from langfuse.decorators import observe
from langfuse.openai import AsyncOpenAI
 
client = AsyncOpenAI()

gen_kwargs = {
    "model": "gpt-4o",
    "temperature": 0.2,
    "max_tokens": 500
}

SYSTEM_PROMPT = """\
You are a movie critic and you keep track of what the latest movies are.
If a user asks for recent information, output a function call and the system add to the context.
If you need to call a function, only output the function call. 
Call functions using Python syntax in plain text, no code blocks.

You have access to the following functions:
- get_now_playing_movies()
- get_showtimes(title, location)
- buy_ticket(theater, movie, showtime)
- get_reviews(movie_id)
"""

@observe
@cl.on_chat_start
def on_chat_start():    
    message_history = [{"role": "system", "content": SYSTEM_PROMPT}]
    cl.user_session.set("message_history", message_history)

@observe
async def generate_response(client, message_history, gen_kwargs):
    response_message = cl.Message(content="")
    await response_message.send()

    stream = await client.chat.completions.create(messages=message_history, stream=True, **gen_kwargs)
    async for part in stream:
        if token := part.choices[0].delta.content or "":
            await response_message.stream_token(token)
    
    await response_message.update()
    if "get_now_playing_movies" in response_message.content:
        current_movies = get_now_playing_movies()
        response_message.content = current_movies
        await response_message.update()


    return response_message

@cl.on_message
@observe
async def on_message(message: cl.Message):
    message_history = cl.user_session.get("message_history", [])
    message_history.append({"role": "user", "content": message.content})
    
    response_message = await generate_response(client, message_history, gen_kwargs)

    message_history.append({"role": "assistant", "content": response_message.content})
    cl.user_session.set("message_history", message_history)

if __name__ == "__main__":
    cl.main()
