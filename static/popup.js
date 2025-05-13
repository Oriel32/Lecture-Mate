// static/popup.js

// Function to open the popup window and handle interactions
function openPopup() {
    // Get the session_id from the dropdown
    const sessionSelect = document.getElementById("sessionSelect");
    localStorage.setItem("session_id", sessionSelect ? sessionSelect.selectedIndex : 0);
    const session_id = localStorage.getItem("session_id");

    // Check if the session ID is a new session
    let session;
    if (session_id === "0") {
        session = "New Session";
    } else {
        session = sessions_topic[session_id - 1];
    }

    // Open a new popup window
    const popup = window.open("", "Popup", "width=850,height=650");
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
            <link rel="stylesheet" href="/static/styles.css">
        </head>
        <body>
            <div class="popup-container">
                <header class="popup-header">
                    <div class="logo-welcome-container">
                        <img id="logoImg" src="/static/images/logo.png" alt="LectureMate Logo" class="popup-logo">
                        <p class="welcome-message">Welcome ${userId}</p>
                    </div>
                    <div id="timerDisplay" class="timer-display">00:00:00</div>
                    <div class="session-display" title="${session}">${session}</div>
                </header>

                <main class="controls">
                    <div id="output" class="output-container">
                        <p class="output-message">Click "Start Session" to begin recording</p>
                    </div>

                    <div class="button-group">
                        <button id="userGradesButton" class="recorder-button">
                            <span>User Grades</span>
                            <span>📊</span>
                        </button>
                        <button id="runScriptButton" class="recorder-button">
                            <span>Start Session</span>
                            <span>▶️</span>
                        </button>
                        <button id="pauseButton" class="recorder-button">
                            <span>Pause</span>
                            <span>⏯️</span>
                        </button>
                        <button id="stopButton" class="recorder-button">
                            <span>End Session</span>
                            <span>⏹️</span>
                        </button>
                    </div>

                    <div class="button-group">
                        <button id="questionsButton" class="recorder-button">❓ 0 ❓</button>
                        <button id="answerButton" class="recorder-button">Submit Answer</button>
                    </div>
                </main>
            </div>
        </body>
        </html>
    `);
    popup.document.close(); // Important after writing content

    // State variables for recording management
    let interval;
    let startTime = 0;
    let elapsedTime = 0;
    let pausedTime = 0;
    let isRecording = false;
    let isPaused = false;
    // create constant random number between 50 and 70
    let randomNumber = Math.floor(Math.random() * (70 - 50 + 1)) + 50;
    let questionIndex = 0;

    // Get references to popup elements after the document is written
    const userGradesButton = popup.document.getElementById("userGradesButton");
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
        statusElement.className = "output-message";
        
        if (isError) {
            statusElement.classList.add("error-message");
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
    function formatTime(totalSeconds) {
        const hours = Math.floor(totalSeconds / 3600);
        const minutes = Math.floor((totalSeconds % 3600) / 60);
        const seconds = totalSeconds % 60;
        
        return [
            hours.toString().padStart(2, '0'),
            minutes.toString().padStart(2, '0'),
            seconds.toString().padStart(2, '0')
        ].join(':');
    }
    
    function updateTimerDisplay(status = 'running') {
        if (!timerElement) return;
        
        // Calculate current seconds
        let currentSeconds = Math.floor(elapsedTime / 1000);
        
        // Update timer text
        timerElement.textContent = formatTime(currentSeconds);
        
        // Update timer appearance based on status
        timerElement.className = 'timer-display';
        if (status === 'running') {
            timerElement.classList.add('timer-running');
        } else if (status === 'paused') {
            timerElement.classList.add('timer-paused');
        } else if (status === 'stopped') {
            timerElement.classList.add('timer-stopped');
        }
    }

    async function startTimer() {
        clearInterval(interval); // Clear any existing interval
        
        // Initialize times
        if (!isPaused) {
            startTime = Date.now();
            elapsedTime = 0;
            pausedTime = 0;
        } else {
            // If resuming from pause, adjust the start time
            startTime = Date.now() - pausedTime;
        }

        // 3-second timeout to enable buttons after starting the recording
        setTimeout(() => {
            pauseButton.disabled = false;
            stopButton.disabled = false;
        }, 3000);

        interval = setInterval(() => {
            // Calculate elapsed time including any previous paused time
            const now = Date.now();
            elapsedTime = now - startTime;
            
            // Update the timer display
            updateTimerDisplay('running');
            
            // Get seconds for question timing
            const currentSeconds = Math.floor(elapsedTime / 1000);
            
            // Ask question every randomNumber seconds
            if (currentSeconds === randomNumber) {
                try {
                    generateQuestion(); // Call the function to generate a question
                } catch (error) {
                    pauseTimer(); // Pause the timer if an error occurs
                    console.error('Error generating question:', error);
                    updateStatus(`Error generating question ${error.message}`, true);
                } finally {
                    randomNumber = currentSeconds + Math.floor(Math.random() * (70 - 50 + 1)) + 50; // Update random number for next question
                }
            }
        }, 100); // Use a smaller interval for smoother updates
    }

    function stopTimer() {
        clearInterval(interval);
        
        // Calculate final elapsed time
        const totalSeconds = Math.floor(elapsedTime / 1000);
        
        // Update display with stopped status
        updateTimerDisplay('stopped');
        
        // Reset timer variables
        elapsedTime = 0;
        pausedTime = 0;
        
        // Add stopped message to output
        updateStatus(`Ending Session - Total time: ${formatTime(totalSeconds)}`);
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
                
                // Resume timer - calculate new start time based on total elapsed time
                startTime = Date.now() - pausedTime;
                startTimer();
                
                isPaused = false;
                pauseButton.textContent = "Pause⏯️"; // Update button text
                updateStatus(`Resumed: ${data.message}`);
            } else {
                // Pause
                updateStatus("Pausing recording...");
                clearInterval(interval);
                
                // Store when we paused
                pausedTime = Date.now() - startTime;
                
                // Update timer display to show paused state
                updateTimerDisplay('paused');
                
                const data = await callApi('/pause-recording');
                
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
        questionModal.className = "question-modal";
        
        // Add a close button
        const closeButton = popup.document.createElement("button");
        closeButton.textContent = "Close";
        closeButton.className = "recorder-button";
        closeButton.style.marginBottom = "10px";
        closeButton.onclick = () => {
            questionModal.remove();
        };
        questionModal.appendChild(closeButton);

        // Create a list of questions
        const questionList = popup.document.createElement("ul");
        questionList.className = "question-list";
        
        waitingQuestions.forEach((question, index) => {
            const listItem = popup.document.createElement("li");
            listItem.textContent = question;
            listItem.className = "question-item";

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
            
                    
            
                    // Disable randomNumber
                    randomNumber = 0
                    
                    questionsButton.disabled = true;
                    answerButton.disabled = false;
                    
                    // Update the status with the data message
                    updateStatus(`Answering question ${questionIndex}: ${data.data.feedback}`);

                    // Remove the question from the waitingQuestions list
                    waitingQuestions.splice(index, 1);
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
            randomNumber = Math.floor(elapsedTime / 1000) + Math.floor(Math.random() * (70 - 50 + 1)) + 50; // Update random number for next question
        }
    };

    userGradesButton.onclick = async () => {
        // Open the user-grades.html page in a new tab
        console.log("Opening user-grades.html page");
        popup.location.href = '/user-grades';
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