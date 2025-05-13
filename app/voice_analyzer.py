from .user_data import User
from dotenv import load_dotenv
import json
import time
import os
import threading
import queue
import speech_recognition as sr
from datetime import datetime
from pymongo import MongoClient
from huggingface_hub import InferenceClient
from openai import OpenAI
# import torch
# from transformers import AutoModelForCausalLM, AutoTokenizer

# Load environment variables from the .env file
load_dotenv()

class VoiceRecorder:
    def __init__(self, user_id="Guest"):
        self.transcript = {}
        self.questions = []
        self.question_count = 0
        self.answers = []
        self.answer_count = 0
        self.feedbacks = []
        self.grades = []
        
        self.transcript_lock = threading.Lock()
        
        self.pause_flag = threading.Event()
        self.stop_flag = threading.Event()
        self.answer_flag = threading.Event()
        self.recording_flag = threading.Event()
        self.analayzing_flag = threading.Event()
        
        self.producer_thread = None
        self.consumer_threads = []
        self.questions_thread = None
        
        self.audio_queue = queue.Queue()
        self.recognizer = sr.Recognizer()
        
        self.user_id = user_id
        self.user = User(user_id)
        self.mongodb_uri = os.getenv("MONGODB_URI")
        self.session_data = None

        # Load the LLM Model
        self.model_name = os.getenv("MODEL_NAME", "valhalla/t5-small-qg-hl")  # Default model
        self.huggingface_token = os.getenv("HUGGINGFACE_TOKEN")
        
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.model_name = "gpt-4.1"
        
        if not self.huggingface_token:
            raise Exception("Hugging Face token is missing. Please set it in the environment.")
            
        # self.model, self.tokenizer, self.device = self.load_language_model()
        self.model = self.load_language_model()
 
    def info(self):
        """
        Returns the model name, 
        """
        sessions_info = []
        sessions_id = []
        if self.user.user_data and self.user_id != "Guest":
            # Make a list of sessions topic for the user display - if there is not a session topic, append the session_id
            for session in self.user.user_data.get("sessions", []):
                sessions_id.append(session.get("session_id"))
                topic = session.get("session_topic")
                if topic:
                    sessions_info.append(topic)
                else:
                    sessions_info.append(sessions_id[-1])
        return {"model_name" : self.model_name,
                "mongodb_uri" : self.mongodb_uri,
                "user_id" : self.user_id,
                "sessions_id": sessions_id,
                "sessions_topic": sessions_info
                }
    def set_session_data(self, session_id):
        self.session_data = self.user.set_session_data(session_id)
    
    def run(self):
        """
        Starts the producer and consumer threads.
        """
        # Initialize the flags
        self.stop_flag.clear()
        self.pause_flag.clear()
        
        self.producer_thread = threading.Thread(target=self.producer, daemon=True)
        self.producer_thread.start()

        for _ in range(2):  # Two consumer threads
            t = threading.Thread(target=self.consumer, daemon=True)
            t.start()
            self.consumer_threads.append(t)

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
        
        print("Recording stopped.")
        
        # Save the transcript to MongoDB if have transcript
        if len(self.transcript) > 2:
            self.save_transcript_to_mongodb()
            
        print("Recording stopped.")
        self.reset()
    
    def pause(self):
        """
        Pauses the recording.
        """
        self.pause_flag.set()
        
        """# Wait for the recording thread to finish - can be removed, make sure that clearing pause flag before 
        while self.recording_flag.is_set() or not self.audio_queue.empty():
            time.sleep(0.1)"""
        print("Recording paused.")

    def resume(self):
        """
        Resumes the recording.
        """
        self.pause_flag.clear()
        print("Recording resumed.")

    def reset(self):
        """
        Resets the recorder by clearing the variables.
        """
        self.transcript = {}
        self.questions = []
        self.answers = []
        self.answer_count = 0
        self.question_count = 0
        self.feedbacks = []
        self.grades = []
        
        self.producer_thread = None
        self.consumer_threads = []
        self.questions_thread = None
        
        self.stop_flag.clear()
        self.pause_flag.clear()
        self.answer_flag.clear()
        self.recording_flag.clear()
                
        print("Recorder reset.")
        
    def record_audio(self, duration=10):
        """
        Record a 10-second audio clip from the microphone.
        """
        with sr.Microphone() as source:
            print("Please say something:")
            self.recording_flag.set()
            self.recognizer.adjust_for_ambient_noise(source)
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            audio_data = self.recognizer.record(source, duration=duration)
            self.audio_queue.put((current_time, audio_data))
            self.recording_flag.clear()

    def producer(self, duration=10):
        """
        Continuously records audio and puts the (timestamp, audio) tuple into a queue.
        Uses overlapping threads to avoid gaps between recordings.
        """
        while not self.stop_flag.is_set():
            while self.pause_flag.is_set():
                if recording_thread and recording_thread.is_alive():
                    # Wait for the recording thread to finish
                    recording_thread.join()
                if self.stop_flag.is_set():
                    break
                time.sleep(0.1)  # Sleep briefly to avoid hogging CPU

            if self.stop_flag.is_set():
                break
            
            recording_thread = threading.Thread(target=self.record_audio, args=(duration,))
            recording_thread.start()
            time.sleep(duration - 0.5)  # Wait for the recording to finish
        # Check if the recording thread is still alive
        if recording_thread.is_alive():
            recording_thread.join()
            
    def consumer(self):
        """
        Processes audio from the queue efficiently.
        """
        while not self.stop_flag.is_set() or not self.audio_queue.empty():
            while self.pause_flag.is_set() and self.audio_queue.empty() and not self.recording_flag.is_set():
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
        def get_last_word(transcript):
            last_value = list(transcript.values())[-1]
            last_word = last_value.split()[-1]
            return last_word.lower()
        
        def get_first_word(st):
            first_word = st.split()[0]
            return first_word
        
        print("Recognizing...")
        self.analayzing_flag.set()
        try:
            response = self.recognizer.recognize_google(audio, show_all=True, language="he-IL")
            if response and "alternative" in response:
                text = response["alternative"][0].get("transcript", "")
                confidence = response["alternative"][0].get("confidence", "N/A")
                
                # Check if the last word in the transcript is the same as the first word in the new text
                # If so, remove the first word from the new text
                if self.transcript:
                    first_word = get_first_word(text)
                    if get_last_word(self.transcript) == first_word.lower():
                        # erase the first word in text
                        text = text.replace(f"{first_word} ", "", 1)
                        
                # Update the transcript with the new text
                with self.transcript_lock:
                    self.transcript[timestamp] = text
                print(f"You said at {timestamp}: {text} (confidence: {confidence})")
                
                if self.answer_flag.is_set():
                    self.answers[self.answer_count] += f" {text}"
                if "stop the loop" in text.lower():
                    self.stop()
                self.analayzing_flag.clear()
            else:
                print("No speech recognized.")
        except sr.UnknownValueError:
            print("Could not understand the audio")
        except sr.RequestError as e:
            print(f"Could not request results from Google Web Speech API; {e}")

    def load_language_model(self):
        """
        Load the language model from Hugging Face or OpenAI.
        """
        try:
            # Good option when using GPU
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
            
            # API calls cost money but are faster, more accurate and easier to use
            client = OpenAI(api_key=self.openai_api_key)
            """
            
            # Using Hugging Face Inference API - good for lightweight models but has limitations
            client = InferenceClient(
                provider="hf-inference",
                api_key=self.huggingface_token
            )
            """
            print(f"LLM Model '{self.model_name}' loaded successfully.")
            return client
        except Exception as e:
            print(f"Error loading the model: {e}")
            return None

    def format_question(self):
        """
        Format a prompt to generate a student question based on the current lecture transcript.
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
            role = "You are a curious student attending a lecture."

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

            Transcript Snippet:"""

            prompt = f"[INST] {role} {instruction} {formatted_transcript}[/INST]"
            prompt = instruction
            return prompt, formatted_transcript
            
        except Exception as e:
            print(f"Error format a question: {e}")
            return None

    def format_feedback(self, index):
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
            question = self.questions[index]
            
            json_format = """
            {
            "Category": {
                "Accuracy": [score] # between 0-30,
                "Clarity and Explanation": [score] # between 0-20,
                "Coherence and Structure": [score] # between 0-15,
                "Relevance": [score] # between 0-15,
                "Audience Appropriateness": [score] # between 0-10,
                "Encouragement of Deeper Thinking: [score] # between 0-10
                },
            "Total Score": [score], # between 0-100,
            "Short Justification": [Short Justification]
            }
            """

            # Added constraint about being mid-lecture.
            prompt = f"""
            You will receive:
                1.	A lecture transcript (context for understanding the topic and audience).
                2.	A question asked during the lecture.
                3.	The lecturer’s answer to that question.

            Your task is to evaluate the lecturer’s answer based on the following six criteria.
            For each criterion, assign a score within the specified range.

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
                2.	Provide a short Justification for the total grade (maximum 20 words).

            ⸻

            Input: 
            Lecture Transcript: {formatted_transcript}
            
            Question: {question}
            
            ⸻
            
            json object output:
            {json_format}
            """

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
        
        while self.recording_flag.is_set() or not self.audio_queue.empty():
            # Wait for the recording thread to finish
            time.sleep(0.1)
        
        try:
            prompt, script = self.format_question()
            """
            # Using the InferenceClient to generate a question
            response = self.model.text_generation(
                prompt,
                model=self.model_name,
                max_new_tokens=150,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                repetition_penalty=1.2
            )
            """

            # using the openai API to generate a question
            response = self.model.responses.create(
                model=self.model_name,
                instructions="You are a smart educational assistant.",
                input=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": script}
                ],
                reasoning={},
                tools=[],
                temperature=0.7,
                max_output_tokens=100,
                top_p=0.9,
                store=True
            )
            response = response.output_text
            print("\n🔹 Generated Question: ", response)
            self.questions.append(response)
            self.question_count += 1
            return response
        
        except Exception as e:
            print(f"Error generating question: {e}")
            return None

    def generate_feedback(self, index):
        """
        Generates feedback based on the transcript using the loaded LLM model.
        """
        if not self.model:
            print("Model not loaded. Skipping feedback generation.")
            return "Model not loaded."
        
        try:
            prompt = self.format_feedback(index)
            """
            # Using the InferenceClient to generate feedback
            response = self.model.text_generation(
                prompt,
                model=self.model_name,
                max_new_tokens=200,
                temperature=0.5,
                top_p=0.9,
                repetition_penalty=1.2
            )
            print("\n🔹 Generated Feedback: ", response)
            """
            
            # using the openai API to generate a feedback
            response = self.model.responses.create(
                model=self.model_name,
                instructions="You are an AI evaluator assessing a lecturer’s performance.",
                input=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": self.answers[self.answer_count]}
                ],
                text={
                    "format": {
                        "type": "json_object"
                        }
                },
                reasoning={},
                tools=[],
                temperature=1.0,
                max_output_tokens=2048,
                top_p=1.0,
                store=True
            )
            response = response.output_text
            print("\n🔹 Generated Feedback: ", response)
                        
            # Assuming the response is a JSON string, parse it
            try:
                print(type(response))
                response = json.loads(response)
                total_grade = sum(response["Category"].values())
                total_grade = int(total_grade)
            except Exception as e:
                print(f"Error parsing feedback response: {e}")
                total_grade = 0
                
            self.feedbacks.append(response)
            self.grades.append(total_grade)
            return total_grade
        
        except Exception as e:
            print(f"Error generating feedback: {e}")
            return None
        
    def generate_topic(self):
        """
        Generates a question from the transcript using the loaded LLM model.
        """ 
        if not self.model:
            print("Model not loaded. Skipping question generation.")
            return None
        
        formatted_transcript=""
        with self.transcript_lock:
            if not self.transcript:
                print("No transcript available.")
                return "No transcript available."
            formatted_transcript += "\n".join([f"{k}: {v}" for k, v in self.transcript.items()])
            
        try:
            # using the openai API to generate a question
            response = self.model.responses.create(
                model=self.model_name,
                input=[
                    {"role": "system", "content": "You will recieve a transcript of a lecture. You will give back a topic for the transcript in 3-10 words"},
                    {"role": "user", "content": formatted_transcript}
                ],
                reasoning={},
                tools=[],
                temperature=0.9,
                max_output_tokens=16,
                top_p=0.9,
                store=True
            )
            response = response.output_text
            print("\n🔹 Generated topic: ", response)
            return response
        
        except Exception as e:
            print(f"Error generating topic: {e}")
            return None
        
    def answer_question(self, index):
        """
        Answer and Submit the question.
        """
        if self.answer_flag.is_set():
            print("answer_flag is set")
            self.pause_flag.set()
            
            # Wait for the audio queue to be empty before submitting the answer
            while self.recording_flag.is_set() or not self.audio_queue.empty() or self.analayzing_flag.is_set():
                time.sleep(0.5)
                
            feedback = self.generate_feedback(index) 
            
            self.pause_flag.clear()
            self.answer_flag.clear()
            self.answer_count += 1
            return feedback
            
        else:
            print("answer_flag is not set")
            self.answers.append("")
            self.answer_flag.set()
            return f"{self.questions[index]}"
        
    def save_transcript_to_mongodb(self):
        """
        Saves the transcript to MongoDB.
        """
        # Prepare the session data
        session_topic = None
        if self.session_data == None or "session_topic" not in self.session_data:
            session_topic = self.generate_topic()
        session_data = {
            "session_id": self.user.session_id,
            "session_topic": session_topic,
            "time": list(self.transcript.keys())[0],
            "questions": self.questions,
            "answers": self.answers,
            "feedbacks": self.feedbacks,
            "grades": self.grades,
            "transcript": self.transcript
        }
            
        self.user.save_session_to_mongodb(session_data)

if __name__ == "__main__":
    input("Press Enter to start voice recording...")
    recorder = VoiceRecorder()
    recorder.run()
