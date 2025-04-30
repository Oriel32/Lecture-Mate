from dotenv import load_dotenv
import time
import os
import json
import threading
import queue
import speech_recognition as sr
from datetime import datetime
from pymongo import MongoClient
from huggingface_hub import InferenceClient
# import torch
# from transformers import AutoModelForCausalLM, AutoTokenizer

# Load environment variables from the .env file
load_dotenv()

class VoiceRecorder:
    def __init__(self):
        self.transcript = {}
        self.questions = []
        self.answers = [""]
        self.feedbacks = []
        self.grades = []
        self.transcript_lock = threading.Lock()
        self.pause_flag = threading.Event()
        self.stop_flag = threading.Event()
        self.answer_flag = threading.Event()
        self.answer_count = 0
        self.producer_thread = None
        self.consumer_threads = []
        self.questions_thread = None
        self.audio_queue = queue.Queue()
        self.recognizer = sr.Recognizer()
        self.mongodb_uri = os.getenv("MONGODB_URI")
        self.user_id = os.getenv("USER_ID", "user123")
        self.session_id = os.getenv("SESSION_ID", "0")

        # Load the LLM Model
        self.model_name = os.getenv("MODEL_NAME", "mistralai/Mistral-Nemo-Instruct-2407")  # Default model
        self.huggingface_token = os.getenv("HUGGINGFACE_TOKEN")

        if not self.huggingface_token:
            raise Exception("Hugging Face token is missing. Please set it in the environment.")
            
        # self.model, self.tokenizer, self.device = self.load_language_model()
        self.model = self.load_language_model()
 
    def info(self):
        """
        Returns the model name and the Hugging Face token.
        """
        return {"model_name" : self.model_name, "huggingface_token" : self.huggingface_token, "mongodb_uri" : self.mongodb_uri, "user_id" : self.user_id, "session_id" : self.session_id}
        
    def record_audio(self):
        """
        Record a 10-second audio clip from the microphone.
        """
        with sr.Microphone() as source:
            print("Please say something:")
            self.recognizer.adjust_for_ambient_noise(source)
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            audio_data = self.recognizer.record(source, duration=10)
            return current_time, audio_data

    def producer(self):
        """
        Continuously records audio and puts the (timestamp, audio) tuple into a queue.
        """
        while not self.stop_flag.is_set():
            while self.pause_flag.is_set():
                # Check if stopped while paused
                if self.stop_flag.is_set():
                    break
                time.sleep(0.1) # Sleep briefly to avoid hogging CPU
            # Add this check immediately after the while loop in both functions
            if self.stop_flag.is_set():
                break # Exit the main loop if stopped
            timestamp, audio = self.record_audio()
            self.audio_queue.put((timestamp, audio))
    
    def consumer(self):
        """
        Processes audio from the queue efficiently.
        """
        while not self.stop_flag.is_set() or not self.audio_queue.empty():
            while self.pause_flag.is_set():
                # Check if stopped while paused
                if self.stop_flag.is_set():
                    break
                time.sleep(0.1) # Sleep briefly to avoid hogging CPU
                # Add this check immediately after the while loop in both functions
                if self.stop_flag.is_set():
                    break # Exit the main loop if stopped
            try:
                timestamp, audio = self.audio_queue.get(timeout=5)  # Blocks for 5 seconds
            except queue.Empty:
                continue
            
            if timestamp and audio:
                self.analyze_audio(timestamp, audio)
                self.audio_queue.task_done()

    def analyze_audio(self, timestamp, audio):
        """
        Uses Google's Speech Recognition API to analyze audio and updates the transcript.
        """
        print("Recognizing...")
        try:
            response = self.recognizer.recognize_google(audio, show_all=True, language="he-IL")
            if response and "alternative" in response and len(response["alternative"]) > 0:
                text = response["alternative"][0].get("transcript", "")
                confidence = response["alternative"][0].get("confidence", "N/A")
                with self.transcript_lock:
                    self.transcript[timestamp] = text
                print(f"You said at {timestamp}: {text} (confidence: {confidence})")
                
                if "שאלות" in text.lower():
                    self.answer_flag.set()
                    self.generate_question()
                    
                if self.answer_flag.is_set():
                    self.answers[self.answer_count] += text
                    
                if "בואו נמשיך" in text.lower():
                    self.generate_feedback()
                    self.answer_flag.clear()
                    self.answers.append("")
                    self.answer_count += 1
                    
                if "תעצור שיעור" in text.lower():
                    self.stop()
            else:
                print("No speech recognized.")
        except sr.UnknownValueError:
            print("Could not understand the audio")
        except sr.RequestError as e:
            print(f"Could not request results from Google Web Speech API; {e}")

    def save_transcript_to_mongodb(self):
        """
        Saves the transcript to MongoDB. If the user exists, it adds the new session to their sessions array.
        """
        if not self.mongodb_uri:
            print("MongoDB URI is not provided in environment variables.")
            return

        try:
            # Update or insert new session
            client = MongoClient(self.mongodb_uri)
            db = client["mydb"]
            collection = db["transcripts"]

            # Prepare the session data
            if self.transcript:
                session_data = {
                    "session_id": self.session_id,
                    "time": list(self.transcript.keys())[-1],
                    "questions": self.questions,
                    "answers": self.answers,
                    "transcript": self.transcript
                }
            
            update_result = collection.update_one(
            {"user_id": self.user_id},
            {
                "$push": {
                    "sessions": session_data
                }
            },
            upsert=True  # If the user doesn't exist, insert a new document
        )

            if update_result.upserted_id:
                print(f"New user created with user_id: {self.user_id}")
            else:
                print(f"Session added for user_id: {self.user_id}")
        except Exception as e:
            print("Error saving transcript to MongoDB:", e)

    def load_language_model(self):
        try:
            """
            tokenizer = AutoTokenizer.from_pretrained(model_name, token=huggingface_token)
            device = "cuda" if torch.cuda.is_available() else "cpu"
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None,
                token=huggingface_token
            )
            """
            client = InferenceClient(
                provider="hf-inference",
                api_key=self.huggingface_token
            )
            print(f"LLM Model '{self.model_name}' loaded successfully.")
            return client
        except Exception as e:
            print(f"Error loading the model: {e}")
            return None

    def format_question(self):
        """
        format a question for the transcript.
        """
        if not self.model: # if not self.model or not self.tokenizer:
            print("Model not loaded. Skipping question formatting.")
            return None

        with self.transcript_lock:
            if not self.transcript:
                print("No transcript available.")
                return "No transcript available."
            formatted_transcript = "\n".join([f"{k}: {v}" for k, v in self.transcript.items()])
        
        # Create a structured prompt
        try:
            # --- Define Role and Refined Prompt ---
            role = "You are a smart educational assistant."

            # Few-shot examples to guide the model's style and complexity
            example_questions = """Please answer the following questions thoughtfully and in a way that someone without specialized knowledge can understand:
                What's the core idea behind the concept of supply and demand in economics? Can you give a simple example of how changes in one affect the other?
                In history, what are some common factors that have led to the rise and fall of major civilizations or empires?
                When scientists talk about climate change, what are the main pieces of evidence they point to, and what are some of the projected consequences?
                What are the fundamental principles of democracy as a form of government, and what are some of the different ways it can be structured?
                In psychology, what's the difference between intrinsic and extrinsic motivation, and how can understanding this help in everyday life?
            """

            # Refined instruction including examples: Ask specifically for *only* the question.
            # Added constraint about being mid-lecture.
            instruction = f"""
            Your task is to read a lecture transcript and generate one question that could reasonably be asked by a student who is listening to the lecture.

            The question should meet the following criteria:

                1. Relevant – Directly relates to the content of the lecture.

                2. Insightful – Encourages clarification, deeper understanding, or elaboration.

                3. Clear – Formulated in a way that is easy to understand.

                4. Appropriate – Suitable for the audience and level of the lecture.
                
            * DO NOT ASK QUESTIONS THAT BEEN ASKED ALREADY: {self.questions}

            Lecture transcript:
            {formatted_transcript}"""

            prompt = f"[INST] {role} {instruction} [/INST]"
            return prompt
            
        except Exception as e:
            print(f"Error format a question: {e}")
            return None

    def format_feedback(self):
        """
        format a feedback for the transcript.
        """
        if not self.model:
            print("Model not loaded. Skipping feedback formatting.")
            return None
        with self.transcript_lock:
            if not self.transcript:
                print("No transcript available.")
                return "No transcript available."
            formatted_transcript = "\n".join([f"{k}: {v}" for k, v in self.transcript.items()])
        # Create a structured prompt
        try:
            # --- Define Role and Refined Prompt ---
            role = "You are an AI evaluator assessing a lecturer’s performance."
            
            question = self.questions[self.answer_count]

            answer = self.answers[self.answer_count]
            
            json_format = """
            {
            "Evaluation": [
                {
                "category": "Accuracy",
                "score": [score],
                "max_score": 30
                },
                {
                "category": "Clarity and Explanation",
                "score": [score],
                "max_score": 20
                },
                {
                "category": "Coherence and Structure",
                "score": [score],
                "max_score": 15
                },
                {
                "category": "Relevance",
                "score": [score],
                "max_score": 15
                },
                {
                "category": "Audience Appropriateness",
                "score": [score],
                "max_score": 10
                },
                {
                "category": "Encouragement of Deeper Thinking",
                "score": [score],
                "max_score": 10
                }
            ],
            "Short Justification": [Short Justification]
            }
            """

            # Added constraint about being mid-lecture.
            instruction = f"""
            You will receive:
                1.	A lecture transcript (context for understanding the topic and audience).
                2.	A question asked during the lecture.
                3.	The lecturer’s answer to that question.

            Your task is to evaluate the lecturer’s answer based on the following six criteria.
            For each criterion, assign a score within the specified range, then calculate the final score from 0 to 100.

            ⸻

            Evaluation Criteria:
                1.	Accuracy (0–30 points)
                •	Is the answer factually correct and based on professional knowledge?
                2.	Clarity and Explanation (0–20 points)
                •	Is the answer explained clearly and understandably, possibly with helpful examples or analogies?
                3.	Coherence and Structure (0–15 points)
                •	Is the answer logically structured with smooth flow and progression of ideas?
                4.	Relevance (0–15 points)
                •	Does the answer directly address the question without going off-topic?
                5.	Audience Appropriateness (0–10 points)
                •	Is the answer appropriate to the level of the students (not too complex or too simplistic)?
                6.	Encouragement of Deeper Thinking (0–10 points)
                •	Does the answer spark interest, promote critical thinking, or offer new perspectives?

            ⸻

            Instructions:
                1.	Assign a score for each of the six criteria.
                2.	Provide a summary Justification for the total grade (maximum 20 words).

            ⸻

            Input Format: 
            Lecture Transcript: {formatted_transcript}
            Question: {question}
            Lecturer’s Answer: {answer}

            ⸻

            json Format = {json_format}
            
            """

            prompt = f"[INST] {role} {instruction} [/INST]"
            return prompt
        except Exception as e:
            print(f"Error format a feedback: {e}")
            return None

    def generate_question(self):
        """
        Generates a question from the transcript using the loaded LLM model.
        """
        if not self.model:
            print("Model not loaded. Skipping question generation.")
            return None
        
        if len(self.transcript) < 2:
            print("No transcript available.")
            return None
        
        try:
            prompt = self.format_question()
            # Using the InferenceClient to generate a question
            response = self.model.text_generation(
                prompt,
                model=self.model_name,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                repetition_penalty=1.2
            )
            print("\n🔹 Generated Question: ", response)
            self.questions.append(response)
            return response
        
        except Exception as e:
            print(f"Error generating question: {e}")
            return None

    def generate_feedback(self):
        """
        Generates feedback based on the transcript using the loaded LLM model.
        """
        if not self.model:
            print("Model not loaded. Skipping feedback generation.")
            return "Model not loaded."
        
        try:
            prompt = self.format_feedback()
            # Using the InferenceClient to generate feedback
            response = self.model.text_generation(
                prompt,
                model=self.model_name,
                do_sample=True,
                temperature=0.8,
                top_p=0.9,
                frequency_penalty=-0.5,
                repetition_penalty=1.2,
                max_new_tokens=300
                )
            
            json_response = json.loads(response)
            # Extracting the scores and calculating the total grade
            total_grade = sum([item["score"] for item in json_response["Evaluation"]])
            
            print(f"\n🔹 Generated Feedback: {response}\nGrade: {total_grade}")
            self.feedbacks.append(response)
            self.grades.append(total_grade)
            return json_response
        
        except Exception as e:
            print(f"Error generating feedback: {e}")
            return None
        
    def answer_question(self):
        """
        Answer and Submit the question.
        """
        if self.answer_flag.is_set():
            # Wait for the audio queue to be empty before submitting the answer
            #while not self.audio_queue.empty():
            #   time.sleep(0.1)
            feedback = self.generate_feedback()
            
            print(f"question: {self.questions[self.answer_count]}")
            print(f"answer: {self.answers[self.answer_count]}")
            print(f"feedback: {feedback}")  
            
            self.answers.append("")
            self.answer_flag.clear()
            self.answer_count += 1
            self.pause_flag.set()
            return feedback
            
        else:
            self.answer_flag.set()
            self.pause_flag.clear()
            return "Answering question..."
        
    def stop(self):
        """
        Stops the recording and processing.
        """
        self.stop_flag.set()
        
        # --- Wait for threads to finish ---
        # Wait for the producer thread
        if self.producer_thread and self.producer_thread.is_alive():
            print("Waiting for producer thread...")
            self.producer_thread.join()
            print("Producer thread finished.")

        # Wait for all consumer threads
        print(f"Waiting for {len(self.consumer_threads)} consumer thread(s)...")
        for i, t in enumerate(self.consumer_threads):
            if t and t.is_alive():
                print(f"Waiting for consumer thread {i}...")
                t.join()
                print(f"Consumer thread {i} finished.")
        print("All threads have finished.")
        # --- End waiting section ---
        
        if len(self.transcript) < 1:
            print("Recording stopped.")
            self.reset()
            # return "Not enough data to generate a question."
        
        # Generate a question from the transcript
        # response = self.generate_question()
        
        print("Recording stopped.")
        self.reset()
        # return response
    
    def pause(self):
        """
        Pauses the recording.
        """
        self.pause_flag.set()
        print("Recording paused.")

    def resume(self):
        """
        Resumes the recording.
        """
        self.pause_flag.clear()
        print("Recording resumed.")

    def reset(self):
        """
        Resets the recorder by clearing the transcript and stopping any ongoing processes.
        """
        # Ensure threads are stopped if reset is called externally
        if not self.stop_flag.is_set():
             self.stop_flag.set() # Signal threads to stop if not already signalled
        print("Resetting recorder state...")
        self.transcript = {}
        self.stop_flag.clear() # Clear flag for next run
        self.pause_flag.clear() # Clear flag for next run

        # Clear the queue
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
            self.audio_queue.task_done() # Mark tasks as done if clearing

        # Clear thread references
        self.producer_thread = None
        self.consumer_threads = []

        print("Recorder reset.")
        
    def run(self):
        """
        Starts the producer and consumer threads.
        """
        # Initialize the flags
        self.stop_flag.clear()
        self.pause_flag.clear()
        
        self.producer_thread = threading.Thread(target=self.producer, daemon=True)
        self.producer_thread.start()

        consumer_threads = []
        for _ in range(2):  # Two consumer threads
            t = threading.Thread(target=self.consumer, daemon=True)
            t.start()
            consumer_threads.append(t)
            
        self.producer_thread.join() 
        for t in consumer_threads:
            t.join()

if __name__ == "__main__":
    input("Press Enter to start voice recording...")
    recorder = VoiceRecorder()
    recorder.run()

    