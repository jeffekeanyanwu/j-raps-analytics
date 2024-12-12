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

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/REPO_NAME.git
cd REPO_NAME
```
### 2. Create a virtual environment and install dependencies
```bash
make run-all
```
### 3. Run the dashboard
```bash
make dev
```

### Project Structure:
```bash
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
```

### Usage:
The dashboard provides:
- Real-time game statistics
- Player performance metrics
- Team analytics
- ML based predictions for upcoming games

### Development:
- Uses Docker for containerization
- Makefile for common operations
- Polars for efficient data processing
- Streamlit for interactive dashboard