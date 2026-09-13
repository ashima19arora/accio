# Accio 🪄
> **Digital Braille: An Autonomous Voice Accessibility Assistant for Users with Motor & Visual Impairments.**

Just as Braille revolutionized access to physical text, Accio provides a voice-first interface to navigate modern online-first operating systems and web applications. Essential daily services—education, appointments, form submissions, communication, and research—live on laptops and web platforms. For users with restricted motor control or visual impairments, Accio removes the keyboard/mouse barrier, acting as an always-present companion that autonomously executes native OS tasks, fills forms, browses the web, and retrieves spoken knowledge.

---

> 📖 **Comprehensive Guide & Feature Directory**: For full step-by-step instructions, voice command tables, floating orb controls, and architecture documentation, read the [USAGE_AND_FEATURES.md](USAGE_AND_FEATURES.md) guide!

---

## 🌟 Key Capabilities

### 1. Hands-Free Form Filling & Accessibility Navigation
Designed specifically for motor-impaired users to fill out online applications, surveys, and login pages without touching a keyboard or mouse:
- **Field Navigation:** *"Next field"* / *"Press tab"* / *"Previous field"* / *"Shift tab"*
- **Data Entry:** *"Fill field with John Doe"* / *"Enter email user@example.com"*
- **Form Submission:** *"Submit form"* / *"Press enter"*
- **Selection & Checkboxes:** *"Toggle checkbox"* / *"Press space"*
- **Clipboard & Text Editing:** *"Select all"*, *"Clear field"*, *"Copy text"*, *"Paste text"*, *"Undo"*

### 2. Full Browser Automation
- **Scrolling & Navigation:** *"Scroll down"*, *"Scroll up"*, *"Scroll to top"*, *"Scroll to bottom"*
- **Zoom Accessibility:** *"Zoom in"*, *"Zoom out"*, *"Reset zoom"*
- **In-Page Search:** *"Find on page quantum physics"* (triggers `Ctrl+F` and searches query)
- **Tabs & History:** *"New tab"*, *"Close tab"*, *"Next tab"*, *"Reopen tab"*, *"Show history"*, *"Open downloads"*, *"Bookmark page"*, *"Toggle fullscreen"*
- **Web Browsing:** *"Open YouTube"*, *"Go to github.com"*, *"Search the web for NASA Artemis"*

### 3. Messaging Automation
- **Direct Dictation & Sending:** *"Type I am running late and send"* (types text and executes `Enter` to dispatch message)
- **Send Cue:** *"Send message"* / *"Hit enter"*
- **Compound Navigation:** *"Open WhatsApp and type Hello Hashima"*

### 4. Hands-Free Instant Knowledge Q&A
For motor/visually impaired users who cannot read dense text on a screen:
- Direct spoken summaries retrieved via zero-key open APIs (Wikipedia & DuckDuckGo Instant Answers).
- Examples: *"What is photosynthesis?"*, *"Who is Albert Einstein?"*, *"Tell me about Mars"*, *"Quantum physics kya hai?"*
- Speaks concise 1-2 sentence factual answers aloud; automatically falls back to browser search if no instant summary is found.

### 5. Native OS, File Creation & Window Management
- **Safe File & Note Creation:** *"Create a txt file on desktop named Myank Important"* / *"Make a text file called Notes on documents"* / Hindi: *"Desktop par file banao Meeting Notes"* (creates file safely on Desktop/OneDrive, prevents overwriting, and opens in Notepad).
- **Snapping & Layouts:** *"Snap window left"*, *"Snap window right"*
- **Virtual Desktops:** *"Next desktop"*, *"Previous desktop"*, *"New desktop"*, *"Close desktop"*
- **Window Controls:** *"Minimize window"*, *"Maximize window"*, *"Show desktop"*, *"Switch window"* (Alt+Tab), *"Close window"*
- **Hardware & Status:** *"How much RAM is occupied?"*, *"Check battery status"*, *"What time is it?"*, *"Take a screenshot"*, *"Volume up/down/mute"*

### 6. Strict Multi-Tier Security Architecture
Accio is safe from accidental or malicious commands:
- **Lexical Threat Interception:** Prohibits destructive OS commands (`format`, `delete system32`, `rm -rf`, disk wipes).
- **Application Whitelist:** Only approved productivity applications (`notepad`, `calculator`, `paint`, `explorer`, `settings`, `whatsapp`, `chrome`, `edge`, `firefox`, `spotify`) can be launched; shell binaries (`cmd`, `powershell`, `rundll32`) are permanently blocked.
- **Security Audit Logger:** Every blocked threat and executed action is tracked in memory for real-time safety auditing without polluting the project folder.

### 7. Dual-Engine Bilingual Voice & Responsiveness
- **ASR:** Local offline high-accuracy speech transcription via NVIDIA NeMo Parakeet (`nemo-parakeet-tdt-0.6b-v2`).
- **Bilingual TTS:** Automatic language detection for **English** (Windows SAPI5 offline engine) and **Hindi / Hinglish** (`gTTS` via `pygame.mixer`).
- **Acoustic Feedback Elimination:** Synchronized speech locks (`actions.wait_until_speech_finishes()`) ensure the microphone never hears its own voice.
- **Natural Conversational Silence Detection:** Tuned pause threshold (`pause_threshold = 1.4s`, `non_speaking_duration = 0.5s`) allowing natural breathing and thinking pauses without premature cutoffs.
- **Turn-Taking Readiness Cue:** Accio signals readiness after completing each action (*"Hey, I am ready for the next query"* / *"मैं अगले सवाल के लिए तैयार हूँ"*).
- **45s Inactivity Sleep Mode & Intuitive Wake Words:** Goes to sleep when inactive to avoid false ambient triggers; wakes up instantly upon hearing everyday words like *"Hey"*, *"Wake up"*, *"Start"*, *"Wake up up"*, or *"Hello"*.

---

## 🚀 Getting Started

### Prerequisites
- Windows 10/11 (64-bit)
- Python 3.10+ (tested on Python 3.13)
- Working Microphone & Speakers / Headphones

### Installation
```bash
git clone https://github.com/Maayank18/accio.git
cd accio
pip install -r requirements.txt
```

### Running Accio

#### ⚡ Start Core System (Web, API & Desktop Orb)
Run the web application, backend API, and persistent Electron floating desktop orb together:
```bash
npm run dev
```

#### 🎙️ Voice Assistant Engine
Run the hands-free offline neural voice operating runtime in its dedicated terminal:
```bash
npm run voice
# or: python assistant.py
```

#### 🎯 Additional Commands
```bash
npm run dev:all      # Starts all 4 services concurrently (Web, API, Desktop Orb, Voice)
npm run dev:web      # Starts Express API & React Web Client only
npm run dev:desktop  # Launches Persistent Electron Floating Desktop Orb only
npm run test         # Runs full 28-case Unit & Security Test Suite
```

### Running Unit & Security Tests
```bash
python -m unittest discover -s tests -p "test_*.py" -v
```
*(All 28 unit and security tests pass with 100% success).*
