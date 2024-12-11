.PHONY: install build run test lint clean setup dev rebuild docker-run


# Variables
DOCKER_IMAGE_NAME = raptors-analytics
DOCKER_CONTAINER_NAME = raptors-analytics-container
PYTHON_VERSION = 3.12
VENV_NAME = venv

setup: clean
	@echo "🔧 Creating virtual environment..."
	python3 -m venv $(VENV_NAME)
	@echo "📦 Installing dependencies..."
	. $(VENV_NAME)/bin/activate && \
		pip install --upgrade pip && \
		pip install -r requirements.txt && \
		pip install -e .
	@echo "📁 Creating necessary directories..."
	mkdir -p models

install:
	python -m pip install --upgrade pip
	python -m pip install -r requirements.txt
	python -m pip install -e .

dev:
	. $(VENV_NAME)/bin/activate && streamlit run src/dashboard/app.py
install:
	python -m pip install --upgrade pip
	python -m pip install -r requirements.txt

build:
	docker build -t $(DOCKER_IMAGE_NAME) .

docker-run:
	docker run -p 8501:8501 --name $(DOCKER_CONTAINER_NAME) \
		-v $(PWD):/app \
		-v $(PWD)/models:/app/models \
		$(DOCKER_IMAGE_NAME)

dev:
	. $(VENV_NAME)/bin/activate && streamlit run src/dashboard/app.py

run: setup dev

test:
	. $(VENV_NAME)/bin/activate && pytest tests/

lint:
	. $(VENV_NAME)/bin/activate && black src/
	. $(VENV_NAME)/bin/activate && flake8 src/

clean:
	@echo "🧹 Cleaning up..."
	docker stop $(DOCKER_CONTAINER_NAME) 2>/dev/null || true
	docker rm $(DOCKER_CONTAINER_NAME) 2>/dev/null || true
	rm -rf $(VENV_NAME)
	find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf models/*

rebuild: clean build

# Development shortcuts
update: clean setup

logs:
	docker logs -f $(DOCKER_CONTAINER_NAME)
