# Raptors Analytics Dashboard

A real-time analytics dashboard for Toronto Raptors using NBA API, featuring live game stats, player statistics, and ML-based predictions.

## Features
- Live game tracking
- Player statistics visualization
- Team performance analytics
- ML-based point predictions
- Real-time data updates

## Tech Stack
- Python 3.12
- Streamlit
- Polars
- NBA API
- scikit-learn
- Plotly

## Setup and Installation
1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/REPO_NAME.git
cd REPO_NAME
	2.	Create a virtual environment and install dependencies:

make setup
	3.	Run the dashboard:

make dev
Project Structure

raptors-analytics/
├── src/
│   ├── config/
│   │   └── config.yaml
│   ├── dashboard/
│   │   └── app.py
│   ├── data/
│   │   └── nba_data.py
│   ├── models/
│   │   └── predictor.py
│   └── utils/
│       └── config.py
├── Dockerfile
├── Makefile
└── requirements.txt
Usage
The dashboard provides:
	•	Real-time game statistics
	•	Player performance metrics
	•	Team analytics
	•	ML-based predictions for upcoming games
Development
	•	Uses Docker for containerization
	•	Makefile for common operations
	•	Polars for efficient data processing
	•	Streamlit for interactive dashboard


6. Add and commit the README:
```bash
git add README.md
git commit -m "Add README documentation"
git push
Optional but recommended:
	7.	Add a license file (e.g., MIT License):

# Create LICENSE file (MIT License example)
echo "MIT License

Copyright (c) 2023 YOUR_NAME

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE." > LICENSE

git add LICENSE
git commit -m "Add MIT License"
git push
