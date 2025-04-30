from huggingface_hub import InferenceClient
from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

'''mongo_uri = os.getenv("MONGODB_URI")
user_id = os.getenv("USER_ID", "user123")'''

model_name = "mistralai/Mistral-Nemo-Instruct-2407"
huggingface_token = os.getenv("HUGGINGFACE_TOKEN")

client = InferenceClient(
    provider="hf-inference",
    api_key=huggingface_token
)

'''# load transcript from MongoDB
db_client = MongoClient(mongo_uri)
db = db_client["mydb"]
collection = db["transcripts"]

# get the latest transcript for the user (order - sessions.transcript)
last_lecture = collection.find_one(
    {"user_id": user_id},
    sort=[("sessions.time", -1)]
)

last_session = last_lecture["sessions"][-1]  # Get the last session

transcript = ""
for key, value in last_session["transcript"].items():
    transcript += f"{value} "
    '''
    
transcript = """Hey everyone, today we're going to start tackling a fundamental concept that pops up in various forms on the math section: Algebraic Equations. Now, I know some of you might hear 'algebra' and feel a little intimidated, but trust me, we're going to break it down into manageable steps, and you'll see it's a powerful tool for solving problems.

Think of an algebraic equation like a puzzle where we're trying to find a missing piece. This missing piece is usually represented by a letter, most commonly 'x', but it could be any letter. The equation tells us that two expressions are equal to each other. Our goal is to figure out the value of that unknown letter that makes the equation true.

Let's look at a simple example:  x+5=12.

In this equation, 'x' is our unknown. The equation tells us that if we take some number (x) and add 5 to it, the result will be 12. Our job is to figure out what that 'some number' is.

How can we do that? Well, the basic principle in solving algebraic equations is to isolate the variable – in this case, 'x' – on one side of the equation. We want to get 'x = some number'.

To do that, we use inverse operations. An inverse operation is an operation that 'undoes' another operation. For example, the inverse of addition is subtraction, and the inverse of multiplication is division.

So, in our equation x+5=12, we have '+ 5' on the side with 'x'. To undo this addition, we perform the inverse operation, which is subtraction. But here's the crucial rule: whatever you do to one side of the equation, you must also do to the other side to keep it balanced.

So, we subtract 5 from both sides of the equation:

x+5−5=12−5

This simplifies to:

x=7

And just like that, we've solved for 'x'! We found that the missing piece of our puzzle is 7. If we substitute 7 back into the original equation, we get 7+5=12, which is true.
"""

# --- Define Role and Refined Prompt ---
role = "You are a curious student attending an AI lecture."

# Few-shot examples to guide the model's style and complexity
example_questions = """
Here are examples of the kind of questions a student might ask:
- What's the main difference between standard Machine Learning and Deep Learning again?
- You mentioned the 'black box' issue. Are people working on making these deep learning decisions more understandable?
- How much data does a typical deep learning model actually need to learn effectively?
- How realistic is the idea of achieving human-level AGI anytime soon?
- If the training data has bias, can we correct the bias in the AI model itself, or only by fixing the data?
"""

# Refined instruction including examples: Ask specifically for *only* the question.
# Added constraint about being mid-lecture.
instruction = f"""{example_questions}
Based on the following lecture transcript snippet, formulate one concise question that a student like you might ask the speaker, similar in style and complexity to the examples provided.
Since this is mid-lecture, avoid asking questions about topics or details that seem likely to be explained later in the lecture. Focus on clarifying concepts already presented or seeking brief elaborations on points made so far.
Only output a short and concise question itself, starting directly with the question text.

Transcript Snippet:
{transcript}

Student Question:"""

prompt = f"[INST] {role} {instruction} [/INST]"

response = client.text_generation(
    prompt,
    model=model_name,
    max_new_tokens=50,
    do_sample=True,
    temperature=0.7,
    top_p=0.9,
    repetition_penalty=1.2
)

# Limit the number of words in the generated text
word_limit = 20  # Set your desired word limit
limited_text = " ".join(response.split()[:word_limit])


print(response)

