import logging
from flask import Flask, render_template, jsonify, redirect, url_for, request
from .voice_analyzer import VoiceRecorder

# --- Basic Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__, template_folder='../templates', static_folder='../static')

# --- Global Instances ---
# Initialize these once when the application starts
recorder = None


# --- Helper Function for JSON Responses ---
def create_response(status, message, data=None, status_code=200):
    """Creates a consistent JSON response."""
    response = {"status": status, "message": message}
    if data is not None:
        response["data"] = data
    return jsonify(response), status_code

# --- Routes ---
@app.route('/')
def index():
    """Redirects root URL to the home page."""
    return redirect(url_for('home'))

@app.route('/home')
def home():
    global recorder
    username = request.args.get('username', 'Guest')
    try:
        recorder = VoiceRecorder(username)
        logging.info("VoiceRecorder initialized.")
    except Exception as e:
        logging.error(f"Failed to initialize VoiceRecorder: {e}", exc_info=True)
        # Depending on the severity, you might want to prevent the app from starting
        # For now, we'll log the error and let routes potentially fail later.
        recorder = None # Set to None to indicate failure
        
    voiceRecorder_info = recorder.info()
    """Renders the main page with the button to open the popup."""
    return render_template('home.html', title="Home", info=voiceRecorder_info)

@app.route('/run-voice-recorder', methods=['POST'])
def run_voice_recorder():
    """Starts the voice recorder background process."""
    global recorder
    if not recorder:
         return create_response("error", "VoiceRecorder is not initialized.", status_code=500)
    try:
        # Extract session_id from the request payload
        data = request.get_json()
        session_id = int(data.get('session_id', 0))  # Default to 0 if not provided

        logging.info(f"session_id: {session_id}")
        recorder.set_session_data(session_id)
        
        # Consider if recorder.run() should be started in a separate thread
        # if it's blocking and you want the endpoint to return immediately.
        # The current implementation in main_test.py seems to start threads internally,
        # but the run() method itself might block until completion. If so,
        # this endpoint will hang until the recording is stopped.
        # If run() launches threads and returns quickly:
        recorder.run() # Assume this starts threads and returns
        logging.info("Voice recorder run method called.")
        # Note: The original code returned the response from recorder.run().
        # If recorder.run() now blocks until stop(), you cannot return here immediately.
        # The response/generated question should likely be returned by the /stop-recording endpoint.
        return create_response("success", "VoiceRecorder process initiated.")
    except Exception as e:
        logging.error(f"Error starting VoiceRecorder: {e}", exc_info=True)
        return create_response("error", f"Failed to start recorder: {str(e)}", status_code=500)

@app.route('/stop-recording', methods=['POST'])
def stop_recording():
    """Stops the voice recording process."""
    global recorder
    if not recorder:
         return create_response("error", "VoiceRecorder is not initialized.", status_code=500)
    try:
        logging.info("Voice recorder stop method called.")
        # It might take a moment for threads in recorder to finish.
        # The recorder.stop() should ideally trigger saving and question generation.
        # If recorder.run() was blocking, this endpoint might not be reachable until it unblocks.
        # Consider having recorder.stop() return the final generated question if available.
        # For now, assume stop signals termination and the result might be fetched separately or logged.
        # Let's modify recorder.stop() or add a get_result method if needed.
        # Assuming stop itself doesn't return the result directly here:
        
        # return create_response("success", "Recording stop signal sent.")
        
        # If stop() could return the result (e.g., the generated question):
        recorder.stop()
        # final_result = recorder.stop() # Hypothetical modification
        # logging.info(f"Final result from recorder: {final_result}")
        return create_response("success", "Recording stopped successfully.")#, data={"final_result": final_result})

    except Exception as e:
        logging.error(f"Error stopping VoiceRecorder: {e}", exc_info=True)
        return create_response("error", f"Failed to stop recorder: {str(e)}", status_code=500)

@app.route('/pause-recording', methods=['POST'])
def pause_recording():
    """Pauses the voice recording."""
    global recorder
    if not recorder:
         return create_response("error", "VoiceRecorder is not initialized.", status_code=500)
    try:
        recorder.pause()
        logging.info("Voice recorder paused.")
        return create_response("success", "Recording paused successfully.")
    except Exception as e:
        logging.error(f"Error pausing VoiceRecorder: {e}", exc_info=True)
        return create_response("error", f"Failed to pause recording: {str(e)}", status_code=500)

@app.route('/resume-recording', methods=['POST'])
def resume_recording():
    """Resumes the voice recording."""
    global recorder
    if not recorder:
         return create_response("error", "VoiceRecorder is not initialized.", status_code=500)
    try:
        recorder.resume()
        logging.info("Voice recorder resumed.")
        return create_response("success", "Recording resumed successfully.")
        # Original code had "response": "Recording resumed!". Let's use the data field:
        # return create_response("success", "Recording resumed successfully.", data={"detail": "Recording resumed!"})
    except Exception as e:
        logging.error(f"Error resuming VoiceRecorder: {e}", exc_info=True)
        return create_response("error", f"Failed to resume recording: {str(e)}", status_code=500)

@app.route('/generate-question', methods=['POST'])
def generate_question():
    """Generates a question from the recorded voice."""
    global recorder
    if not recorder:
         return create_response("error", "VoiceRecorder is not initialized.", status_code=500)
    try:
        # Assuming this method generates a question based on the recording
        question = recorder.generate_question()
        if not question:
            return create_response("error", "No question generated.", status_code=500)
        logging.info(f"Generated question: {question}")
        return create_response("success", "Question generated successfully.", data={"question": question})
    except Exception as e:
        logging.error(f"Error generating question: {e}", exc_info=True)
        return create_response("error", f"Failed to generate question: {str(e)}", status_code=500)

@app.route('/answer-question', methods=['POST'])
def answer_question():
    """Answer and submit the generated question."""
    global recorder
    if not recorder:
         return create_response("error", "VoiceRecorder is not initialized.", status_code=500)
    try:
        # Extract the index from the request body
        data = request.get_json()
        index = data.get('index')

        if index is None:
            return create_response("error", "Index is required.", status_code=400)
        feedback = recorder.answer_question(index)
        logging.info(feedback)
        return create_response("success", "Answer question started/finished", data={"feedback": feedback})
    except Exception as e:
        logging.error(f"Error answering question: {e}", exc_info=True)
        return create_response("error", f"Failed to answer: {str(e)}", status_code=500)

# --- Run Application ---
if __name__ == '__main__':
    # Set debug=False for production
    app.run(debug=True) # Consider host='0.0.0.0' if running in a container or VM