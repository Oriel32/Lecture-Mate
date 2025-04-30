// static/popup.js

// Function to open the popup window and handle interactions
function openPopup() {
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
                body { font-family: sans-serif; padding: 15px; text-align: center; background-color: #faf5ed; color: #40276a;}
                button { margin: 5px; padding: 8px 12px; cursor: pointer; text-align: center;}
                #output { margin-top: 15px; border-top: 1px solid #ccc; padding-top: 10px; }
                p { margin: 5px 0; text-align: center; }
            </style>
        </head>
        <body>
            <div>
                <img id="logoImg" src="/static/logo.png" alt="LectureMate Logo" class="img-fluid" style="max-height: 100px;">
            </div>
            <button id="runScriptButton">Start Session▶️</button>
            <p id="timerDisplay"></p>
            <button id="questionsButton">❓ 0 ❓</button>
            <button id="answerButton">Submit Answer</button>
            <button id="pauseButton">Pause⏯️</button>
            <button id="stopButton">Stop Session⏹️</button> <div id="output"><p>Click "Run Voice Recorder" to start.</p></div>
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
                        randomNumber += Math.floor(Math.random() * (70 - 50 + 1)) + 50; // Update random number for next question
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
            const data = await callApi('/run-voice-recorder');
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
        }
    };

    // Answer Question
    questionsButton.onclick = async () => {
        if (!isRecording) {
            popup.alert("No recording is in progress!");
            return;
        }

        // Pause the timer only if not paused yet
        if (!isPaused) {
            pauseTimer();
        }
        // Create a modal-like div to display the questions
        const questionModal = popup.document.createElement("div");
        questionModal.style.position = "fixed";
        questionModal.style.top = "50%";
        questionModal.style.left = "50%";
        questionModal.style.transform = "translate(-50%, -50%)";
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
        waitingQuestions.forEach((question, index) => {
            const listItem = popup.document.createElement("li");
            listItem.textContent = question;
            listItem.style.cursor = "pointer";
            listItem.style.color = "#007BFF";
            listItem.style.textDecoration = "underline";

            // Add click event to call /answer-question with the index
            listItem.onclick = async () => {
                try {
                    // Find the index of the question in the questionsList
                    questionIndex = questionsList.findIndex(q => q === question);
            
                    // Call the API with the selected question index
                    const data = await callApi('/answer-question', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ index: questionIndex })
                    });
            
                    // Remove the question from the waitingQuestions list
                    waitingQuestions.splice(index, 1);
            
                    // Update the status with the data message
                    updateStatus(`Answering question ${questionIndex + 1}: ${data.message}`);
                } catch (error) {
                    // Handle errors and update the status
                    updateStatus(`Error answering question ${index + 1}: ${error.message}`, true);
                } finally {
                    pauseTimer();
                    questionsButton.textContent = `❓ ${waitingQuestions.length} ❓`;
                    questionsButton.disabled = true;
                    answerButton.disabled = false;
                    // Close the modal after answering
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