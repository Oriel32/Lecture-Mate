from openai import OpenAI
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=openai_api_key)

# Example lecture transcript snippet
lecture_snippet = ""

response = client.responses.create(
  model="gpt-4.1",
  instructions="You are a curious student attending a lecture.",
  input=[
    {
      "role": "system", "content":
          """You are a curious student attending a lecture.
          Instruction: Formulate a concise question a student might ask based on the given lecture transcript snippet.
          Avoid questions on topics likely to be clarified later. 
          Focus on clarifying or elaborating on concepts already presented.
          Output only the question itself in Hebrew.
          """
    },
    {
      "role": "user",
      "content": lecture_snippet
    }
  ],
  reasoning={},
  tools=[],
  temperature=1,
  max_output_tokens=2048,
  top_p=1,
  store=True
)

print(response.output_text)