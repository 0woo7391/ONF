# ONF

A Python-based webcam focus tracking program using OpenCV and MediaPipe.

This project uses a webcam feed to analyze facial landmarks and estimate user focus in real time.  
It is designed for educational, research, and personal productivity use.

---

## Features

- Real-time focus tracking via webcam
- Facial landmark detection using MediaPipe
- Focus state evaluation based on head pose and eye information
- Session logging for later analysis
- Lightweight and simple Python implementation

---

## Requirements

- Python 3.9 or higher
- A working webcam
- Supported OS: Windows, macOS, Linux

---
###Usage

Run the main script:

python main.py

---

###Project Structure
project/
 ├─ main.py          # Entry point of the program
 ├─ judge.py         # Focus evaluation logic
 ├─ logger.py        # Logging and session data handling
 ├─ config.py        # Configuration and constants
 ├─ logs/            # Session log files
 ├─ results/         # Output result files
 ├─ requirements.txt
 ├─ README.md
 └─ LICENSE


---

##Notes

This project was developed with the assistance of AI tools.

Focus estimation is heuristic-based and should not be considered a medical or psychological assessment.

Intended for educational and experimental purposes only.
---
## Installation

Clone the repository and set up a virtual environment:

```bash
git clone https://github.com/your-username/your-repository.git
cd your-repository

python -m venv venv
source venv/bin/activate   # macOS / Linux
venv\Scripts\activate      # Windows

pip install -r requirements.txt



