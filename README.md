# LectureMate

LectureMate is an AI-powered assistant for educators that records lectures, generates questions, and provides feedback on teaching responses. The application helps improve lecture quality and student engagement through real-time feedback.

## Features

- **Audio Recording**: Record lectures in real-time
- **Speech-to-Text**: Convert spoken words to text
- **AI Question Generation**: Generate relevant student questions
- **Answer Evaluation**: Receive feedback and scoring on your answers
- **Session Management**: Save and continue lecture sessions
- **Performance Insights**: Track teaching patterns and improvements

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/LectureMate.git
   cd LectureMate
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the root directory with the following variables:
   ```
   MONGODB_URI=your_mongodb_connection_string
   OPENAI_API_KEY=your_openai_api_key
   # or
   HUGGINGFACE_TOKEN=your_huggingface_token
   ```

## Usage

1. Start the application:
   ```
   python run.py
   ```

2. Open a web browser and navigate to: `http://localhost:5000`

3. Select "New Session" or continue an existing session

4. Use the interface controls:
   - Start Session: Begin recording your lecture
   - Pause: Temporarily pause recording
   - Stop Session: End the current recording session
   - Questions: View generated questions
   - Submit Answer: Submit your response for evaluation

## Technical Architecture

- **Frontend**: HTML, CSS, JavaScript, Bootstrap
- **Backend**: Flask (Python)
- **Voice Processing**: SpeechRecognition, PyAudio
- **AI Models**: OpenAI GPT-4, Hugging Face models
- **Database**: MongoDB

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributors

- [Oriel Sabcha](https://github.com/oriel32)
