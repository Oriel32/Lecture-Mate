import speech_recognition as sr
import pyaudio


recognizer = sr.Recognizer()

# Use the default microphone as the audio source
with sr.Microphone() as source:
    print("Please say something...")
    # Adjust for ambient noise and record audio
    recognizer.adjust_for_ambient_noise(source, duration=3)
    audio = recognizer.listen(source)

print("Recognizing...")
response = recognizer.recognize_google(audio, language="he-IL")

print("You said:", response)
