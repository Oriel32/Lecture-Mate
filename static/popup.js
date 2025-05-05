// static/popup.js

// Function to open the popup window and handle interactions
function openPopup() {
    // Get the session_id from the dropdown
    const sessionSelect = document.getElementById("sessionSelect");
    localStorage.setItem("session_id", sessionSelect ? sessionSelect.selectedIndex : 0);
    const session_id = localStorage.getItem("session_id");    

    // Open a new popup window
    const popup = window.open("", "Popup", "width=700,height=500");
    if (!popup) {
        alert("Popup blocked! Please allow popups for this site.");
        return;
    }

    // Write initial HTML content to the popup
    popup.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>LectureMate</title>
            <style>
                /* Base styles */
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    padding: 20px;
                    background-color: #f8f9fa;
                    color: #2c1810;
                    line-height: 1.6;
                    margin: 0;
                }

                /* Layout components */
                .container {
                    max-width: 800px;
                    margin: 0 auto;
                    background-color: #faf5ed;
                    border-radius: 12px;
                    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
                    padding: 20px;
                }

                .header {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 15px 0;
                    border-bottom: 2px solid #f0f0f0;
                    margin-bottom: 30px;
                }

                /* Logo and branding */
                #logoImg {
                    height: 70px;
                    object-fit: contain;
                }

                #sessionIdDisplay {
                    background-color: #f8f9fa;
                    padding: 8px 15px;
                    border-radius: 20px;
                    font-size: 0.9rem;
                    color: #565656;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
                }

                #welcomeMessage {
                    font-size: 1.2rem;
                    color: #2c1810;
                    margin: 0 20px;
                }

                /* Controls section */
                .controls {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 20px;
                }

                .button-group {
                    display: flex;
                    gap: 10px;
                    flex-wrap: wrap;
                    justify-content: center;
                }

                /* Buttons */
                button {
                    padding: 10px 20px;
                    border: none;
                    border-radius: 25px;
                    background-color: #40276a;
                    color: white;
                    font-weight: 500;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }

                button:hover {
                    background-color: #553285;
                    transform: translateY(-1px);
                }

                button:disabled {
                    background-color: #cccccc;
                    cursor: not-allowed;
                    transform: none;
                }

                /* Timer and output */
                #timerDisplay {
                    font-size: 1.2rem;
                    font-weight: 600;
                    color: #40276a;
                    padding: 10px 20px;
                    background-color: #f8f9fa;
                    border-radius: 20px;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
                }

                #output {
                    margin-top: 20px;
                    padding: 15px;
                    background-color: #f8f9fa;
                    border-radius: 8px;
                    max-height: 200px;
                    overflow-y: auto;
                }

                #output p {
                    margin: 8px 0;
                    padding: 8px;
                    border-radius: 4px;
                    background-color: white;
                }

                /* Question modal styles */
                .question-modal {
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    background-color: white;
                    border-radius: 12px;
                    padding: 20px;
                    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15);
                    max-width: 400px;
                    width: 90%;
                }

                .question-list {
                    list-style: none;
                    padding: 0;
                    margin: 15px 0;
                }

                .question-item {
                    padding: 10px;
                    margin: 5px 0;
                    border-radius: 8px;
                    background-color: #f8f9fa;
                    cursor: pointer;
                    transition: background-color 0.2s ease;
                }

                .question-item:hover {
                    background-color: #e9ecef;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <header class="header">
                    <img id="logoImg" src="/static/images/logo.png" alt="LectureMate Logo">
                    <p id="welcomeMessage">Welcome ${userId}</p>
                    <div id="sessionIdDisplay">${sessions_topic[session_id - 1]}</div>
                </header>

                <main class="controls">
                    <div class="button-group">
                        <button id="runScriptButton">
                            <span>Start Session</span>
                            <span>▶️</span>
                        </button>
                        <button id="pauseButton">
                            <span>Pause</span>
                            <span>⏯️</span>
                        </button>
                        <button id="stopButton">
                            <span>Stop Session</span>
                            <span>⏹️</span>
                        </button>
                    </div>

                    <div id="timerDisplay"></div>

                    <div class="button-group">
                        <button id="questionsButton">❓ 0 ❓</button>
                        <button id="answerButton">Submit Answer</button>
                    </div>

                    <div id="output">
                        <p>Click "Start Session" to begin recording</p>
                    </div>
                </main>
            </div>
        </body>
        </html>
    `);
    popup.document.close(); // Important after writing content

    // State variables for recording management
    let interval;
    let seconds = 0;
    let isRecording = false;
    let isPaused = false;
    // create constant random number between 50 and 70
    let randomNumber = Math.floor(Math.random() * (70 - 50 + 1)) + 50;
    let questionIndex = 0;

    // Get references to popup elements after the document is written
    const runButton = popup.document.getElementById("runScriptButton");
    const pauseButton = popup.document.getElementById("pauseButton");
    const stopButton = popup.document.getElementById("stopButton");
    const questionsButton = popup.document.getElementById("questionsButton");
    const answerButton = popup.document.getElementById("answerButton")
    const outputDiv = popup.document.getElementById("output");
    const timerElement = popup.document.getElementById("timerDisplay");


    
    const questionsList = [];
    const waitingQuestions = [];
    

    // Initial state for buttons
    pauseButton.disabled = true;
    stopButton.disabled = true;
    questionsButton.disabled = true;
    answerButton.disabled = true;

    // --- Helper function to update popup status ---
    function updateStatus(message, isError = false) {
        const statusElement = popup.document.createElement("p");
        
        // Add a timestamp to the message
        const timestamp = new Date().toLocaleTimeString(); // Format: HH:MM:SS
        statusElement.textContent = `[${timestamp}] ${message}`;
        
        if (isError) {
            statusElement.style.color = "red";
        }
        // Prepend new status messages to keep the latest on top
        outputDiv.insertBefore(statusElement, outputDiv.firstChild);
        console.log(`[${timestamp}] ${message}`); // Also log to console for debugging
    }

    // --- Helper function to handle API calls ---
    async function callApi(endpoint, options = { method: 'POST' }) {
        try {
            const response = await fetch(endpoint, options);
            if (!response.ok) {
                // Try to parse error response from server
                let errorData;
                try {
                    errorData = await response.json();
                } catch (parseError) {
                    // If parsing fails, use status text
                    throw new Error(`HTTP error ${response.status}: ${response.statusText}`);
                }
                throw new Error(errorData.message || `API request failed with status ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error(`API call to ${endpoint} failed:`, error);
            updateStatus(`Error: ${error.message}`, true);
            // Rethrow or handle as needed; here we let the caller know
            throw error;
        }
    }

    // --- Timer functions ---
    async function startTimer() {
        clearInterval(interval); // Clear any existing interval

        // 3-second timeout to enable buttons after starting the recording
        setTimeout(() => {
            pauseButton.disabled = false;
            stopButton.disabled = false;
        }, 3000);

        const startTime = Date.now() - seconds * 1000; // Adjust start time based on current seconds

        interval = setInterval(() => {
            const now = Date.now();
            const elapsed = Math.floor((now - startTime) / 1000);

            if (elapsed !== seconds) {
                seconds = elapsed;

                // Update the timerDisplay element directly
                timerElement.textContent = `Recording... ${seconds}s`;

                // Ask question every 60 seconds and answer button content is "Answer Question"
                if (seconds === randomNumber) {
                    try {
                        generateQuestion(); // Call the function to generate a question
                    } catch (error) {
                        pauseTimer(); // Pause the timer if an error occurs
                        console.error('Error generating question:', error);
                        updateStatus(`Error generating question ${error.message}`, true);
                    } finally {
                        randomNumber = seconds + Math.floor(Math.random() * (70 - 50 + 1)) + 50; // Update random number for next question
                    }
                }
            }
        }, 100); // Use a smaller interval for smoother updates
    }

    function stopTimer() {
        clearInterval(interval);
        const timerElement = popup.document.getElementById("timerDisplay");
            if(timerElement) {
                 timerElement.textContent = `Recording stopped. Total time: ${seconds}s`;
            }
        seconds = 0; // Reset timer
    }

    async function pauseTimer() {
        if (!isRecording) {
            popup.alert("No recording is in progress!");
            return;
        }

        try {
            if (isPaused) {
                // Resume
                updateStatus("Resuming recording...");
                const data = await callApi('/resume-recording');
                clearInterval(interval); // Clear existing interval
                startTimer(); // Resume timer
                isPaused = false;
                pauseButton.textContent = "Pause⏯️"; // Update button text
                updateStatus(`Resumed: ${data.message}`);
            } else {
                // Pause
                updateStatus("Pausing recording...");
                clearInterval(interval);
                const data = await callApi('/pause-recording'); // Ensure data is assigned here
                setTimeout(() => {
                    pauseButton.disabled = false;
                    stopButton.disabled = false;
                }, 2000);
                isPaused = true;
                pauseButton.textContent = "Resume⏯️"; // Update button text
                updateStatus(`Paused: ${data.message}`);
            }
        } catch (error) {
            // Error is logged by callApi, state might be inconsistent
            updateStatus(`Pause/Resume failed: ${error.message}`, true);
        } finally {
            timerElement.textContent = `Recording paused at ${seconds}s`;
        }
    }

    function generateQuestion() {
        updateStatus("Generating question...");
        callApi('/generate-question', { method: 'POST' })
            .then(data => {
                if (data && data.data.question) {
                    updateStatus(`Question generated: ${data.data.question}`);
                    questionsList.push(data.data.question); // Store the question in the list
                    waitingQuestions.push(data.data.question); // Store the question in the list
                    questionsButton.textContent = `❓ ${waitingQuestions.length} ❓`; // Update button text with the number of questions available
                    if (waitingQuestions.length === 1) {
                        questionsButton.disabled = false; // Enable answer button
                    }
                } else {
                        updateStatus("No question generated.", true);
                    }
            })
            .catch(error => {
                updateStatus(`Error generating question: ${error.message}`, true);
            });
    }

    // --- Event Listeners ---

    // Run/Start Recording
    runButton.onclick = async () => {
        if (isRecording) {
            popup.alert("Recording is already running!");
            return;
        }
        
        isRecording = true;
        isPaused = false;
        runButton.disabled = true; // Disable run button once started
        outputDiv.innerHTML = ""; // Clear previous output
        updateStatus("Starting recording...");


        try {
            startTimer();
            const data = await callApi('/run-voice-recorder', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id })
            });
            updateStatus(`Recorder started: ${data.message}`);
        } catch (error) {
            // Error is already logged by callApi
            stopTimer(); // Stop timer on error
            isRecording = false; // Reset state
            runButton.disabled = false;
            pauseButton.disabled = true;
            stopButton.disabled = true;
        }
    };

    // Pause/Resume Recording
    pauseButton.onclick = async () => {
        if (!isRecording) {
            popup.alert("No recording is in progress!");
            return;
        }

        // Disable buttons temporarily
        pauseButton.disabled = true;
        stopButton.disabled = true;

        pauseTimer();
    };

    // Stop Recording
    stopButton.onclick = async () => {
        if (!isRecording) {
            popup.alert("No recording is in progress!");
            return;
        }
        updateStatus("Stopping recording...");

        try {
            // Disable buttons to prevent multiple clicks
            runButton.disabled = true; 
            pauseButton.disabled = true;
            stopButton.disabled = true;
            questionsButton.disabled = true;
            answerButton.disabled = true;
            stopTimer(); // Stop the timer

            isRecording = false;
            isPaused = false;

            const data = await callApi('/stop-recording');
            // Re-enable run, disable pause/stop
            runButton.disabled = false;
            pauseButton.textContent = "Pause⏯️"; // Reset button text
            updateStatus(`Stopped: ${data.message}`);
            randomNumber = Math.floor(Math.random() * (70 - 50 + 1)) + 50; // Reset random number

        } catch (error) {
            // Error logged by callApi
            updateStatus(`Failed to stop: ${error.message}`, true);
            // Re-enable run, disable pause/stop
            runButton.disabled = false;
            pauseButton.textContent = "Pause⏯️"; // Reset button text
            updateStatus(`Stopped: ${data.message}`);
            randomNumber = Math.floor(Math.random() * (70 - 50 + 1)) + 50; // Reset random number
        } 
    };

    // Answer Question
    questionsButton.onclick = async () => {
        if (!isRecording) {
            popup.alert("No recording is in progress!");
            return;
        }

        // Create a modal-like div to display the questions
        const questionModal = popup.document.createElement("div");
        questionModal.style.position = "fixed";
        questionModal.style.top = "10px"; // Position at the top
        questionModal.style.right = "10px"; // Changed to top-right position
        questionModal.style.width = "auto"; // Ensure the modal doesn't span the entire width
        questionModal.style.backgroundColor = "#fff";
        questionModal.style.border = "1px solid #ccc";
        questionModal.style.padding = "20px";
        questionModal.style.boxShadow = "0 4px 8px rgba(0, 0, 0, 0.2)";
        questionModal.style.zIndex = "1000";

        // Add a close button
        const closeButton = popup.document.createElement("button");
        closeButton.textContent = "Close";
        closeButton.style.marginBottom = "10px";
        closeButton.onclick = () => {
            questionModal.remove();
        };
        questionModal.appendChild(closeButton);

        // Create a list of questions
        const questionList = popup.document.createElement("ul");
        questionList.style.direction = "rtl"; // Set direction to right-to-left
        waitingQuestions.forEach((question, index) => {
            const listItem = popup.document.createElement("li");
            listItem.textContent = question;
            listItem.style.cursor = "pointer";
            listItem.style.color = "#007BFF";
            listItem.style.textDecoration = "underline";
            listItem.style.borderBottom = "1px solid #ccc"; // Add a line between items
            listItem.style.padding = "5px 0"; // Add spacing between items


            // Add click event to call /answer-question with the index
            listItem.onclick = async () => {
                try {
                    // Find the index of the question in the questionsList
                    questionIndex = questionsList.findIndex(q => q === question);
            
                    // If the user want to answer the question when on pause state - resume the recording
                    if (isPaused){
                        pauseTimer();
                    }
                    // Call the API with the selected question index
                    const data = await callApi('/answer-question', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ index: questionIndex })
                    });
            
                    // Remove the question from the waitingQuestions list
                    waitingQuestions.splice(index, 1);
            
                    // Disable randomNumber
                    randomNumber = 0
                    
                    questionsButton.disabled = true;
                    answerButton.disabled = false;
                    
                    // Update the status with the data message
                    updateStatus(`Answering question ${questionIndex + 1}: ${data.message}`);
                } catch (error) {
                    // Handle errors and update the status
                    updateStatus(`Error answering question ${index + 1}: ${error.message}`, true);
                } finally {
                    questionsButton.textContent = `❓ ${waitingQuestions.length} ❓`;
                    // Close the modal after start answering
                    questionModal.remove();
                }
            };

            questionList.appendChild(listItem);
        });
        questionModal.appendChild(questionList);

        // Append the modal to the popup document
        popup.document.body.appendChild(questionModal);
    };

    answerButton.onclick = async () => {
        // Disable buttons temporarily
        answerButton.disabled = true;
        pauseButton.disabled = true;
        stopButton.disabled = true;
        try {
            const data = await callApi('/answer-question', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ index: questionIndex })
            });
            updateStatus(`${data.message}`);
            pauseButton.disabled = false;
            stopButton.disabled = false;
            if (waitingQuestions.length > 0) {
                questionsButton.disabled = false;
            }
            if (data && data.data.feedback) {
                updateStatus(`Total grade for the answer: ${data.data.feedback}/100`);
            }
        } catch (error) {
            // Error logged by callApi
            updateStatus(`Failed to answer: ${error.message}`, true);
        } finally {
            randomNumber = seconds + Math.floor(Math.random() * (70 - 50 + 1)) + 50; // Update random number for next question
        }
    };

        // Handle popup closing - attempt to stop recording if active
    popup.onbeforeunload = () => {
        if (isRecording) {
            // Try to stop synchronously if possible, but fetch is async.
            // This might not reliably complete before the window closes.
            navigator.sendBeacon('/stop-recording', new Blob()); // Best effort
                alert("Stopping recording as popup is closing.");
            // Cannot guarantee the server receives the stop command.
        }
    };
}

// Add event listener to the main page's button after the DOM is loaded
// This assumes the button in popup.html has id="openPopupButton"
document.addEventListener('DOMContentLoaded', () => {
    const openButton = document.getElementById('openPopupButton'); // Make sure your button in popup.html has this ID
    if (openButton) {
        openButton.onclick = openPopup;
    } else {
        console.error("Button with ID 'openPopupButton' not found in popup.html");
    }
});