.PHONY: install build run test lint clean setup dev rebuild docker-run docker-compose

# Variables
DOCKER_IMAGE_NAME = raptors-analytics
DOCKER_CONTAINER_NAME = raptors-analytics-container
PYTHON_VERSION = 3.12
VENV_NAME = venv

# Colors for terminal output
COLOR_RESET = \033[0m
COLOR_BLUE = \033[34m
COLOR_GREEN = \033[32m
COLOR_YELLOW = \033[33m

# Setup commands
setup: clean
	@echo "$(COLOR_BLUE)🔧 Creating virtual environment...$(COLOR_RESET)"
	python3 -m venv $(VENV_NAME)
	@echo "$(COLOR_BLUE)📦 Installing dependencies...$(COLOR_RESET)"
	. $(VENV_NAME)/bin/activate && \
		pip install --upgrade pip && \
		pip install -r requirements.txt && \
		pip install -e .
	@echo "$(COLOR_BLUE)📁 Creating necessary directories...$(COLOR_RESET)"
	mkdir -p models

install:
	python -m pip install --upgrade pip
	python -m pip install -r requirements.txt
	python -m pip install -e .

# Development commands
dev:
	. $(VENV_NAME)/bin/activate && PYTHONPATH=$(PWD) streamlit run src/dashboard/app.py

# Docker commands
build:
	@echo "$(COLOR_BLUE)🐳 Building Docker image...$(COLOR_RESET)"
	docker build -t $(DOCKER_IMAGE_NAME) .

docker-run:
	@echo "$(COLOR_BLUE)🚀 Running Docker container...$(COLOR_RESET)"
	docker run -p 8501:8501 --name $(DOCKER_CONTAINER_NAME) \
		-v $(PWD):/app \
		-v $(PWD)/models:/app/models \
		$(DOCKER_IMAGE_NAME)

# Docker Compose commands
dc-up:
	@echo "$(COLOR_BLUE)🚀 Starting all services...$(COLOR_RESET)"
	docker-compose up

dc-build:
	@echo "$(COLOR_BLUE)🏗️  Building and starting all services...$(COLOR_RESET)"
	docker-compose up --build

dc-down:
	@echo "$(COLOR_YELLOW)🔽 Stopping all services...$(COLOR_RESET)"
	docker-compose down

dc-logs:
	@echo "$(COLOR_BLUE)📋 Viewing logs...$(COLOR_RESET)"
	docker-compose logs -f

# Redis specific commands
redis-cli:
	@echo "$(COLOR_BLUE)🔧 Connecting to Redis CLI...$(COLOR_RESET)"
	docker-compose exec redis redis-cli

redis-monitor:
	@echo "$(COLOR_BLUE)👀 Monitoring Redis...$(COLOR_RESET)"
	docker-compose exec redis redis-cli monitor

redis-stats:
	@echo "$(COLOR_BLUE)📊 Redis Statistics...$(COLOR_RESET)"
	docker-compose exec redis redis-cli info stats

redis-clear:
	@echo "$(COLOR_YELLOW)🧹 Clearing Redis cache...$(COLOR_RESET)"
	docker-compose exec redis redis-cli FLUSHALL

redis-test:
	@echo "$(COLOR_BLUE)🧪 Testing Redis connection...$(COLOR_RESET)"
	docker-compose exec redis redis-cli ping

# Testing and linting
test:
	@echo "$(COLOR_BLUE)🧪 Running tests...$(COLOR_RESET)"
	. $(VENV_NAME)/bin/activate && pytest tests/

test-cache:
	@echo "$(COLOR_BLUE)🧪 Testing cache functionality...$(COLOR_RESET)"
	. $(VENV_NAME)/bin/activate && pytest tests/test_cache.py -v

lint:
	@echo "$(COLOR_BLUE)🧹 Running linters...$(COLOR_RESET)"
	. $(VENV_NAME)/bin/activate && black src/
	. $(VENV_NAME)/bin/activate && flake8 src/

# Cleanup commands
clean:
	@echo "$(COLOR_YELLOW)🧹 Cleaning up...$(COLOR_RESET)"
	docker-compose down -v || true
	docker stop $(DOCKER_CONTAINER_NAME) 2>/dev/null || true
	docker rm $(DOCKER_CONTAINER_NAME) 2>/dev/null || true
	rm -rf $(VENV_NAME)
	find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf models/*

rebuild: clean dc-build

# Development workflow shortcuts
dev-setup: clean setup dev

# Quick start development
quick-start:
	@echo "$(COLOR_GREEN)🚀 Starting development environment...$(COLOR_RESET)"
	make clean
	make setup
	make dc-build
	make dc-up

# Status check
status:
	@echo "$(COLOR_BLUE)📊 Checking services status...$(COLOR_RESET)"
	docker-compose ps
	@echo "\n$(COLOR_BLUE)Redis Status:$(COLOR_RESET)"
	docker-compose exec redis redis-cli ping || echo "Redis not running"

setup-monitoring:
	@echo "$(COLOR_BLUE)🔧 Setting up monitoring...$(COLOR_RESET)"
	mkdir -p monitoring/prometheus
	mkdir -p monitoring/grafana/provisioning/dashboards
	@echo "$(COLOR_BLUE)📊 Copying dashboard configurations...$(COLOR_RESET)"
	cp monitoring/grafana/provisioning/dashboards/redis.json monitoring/grafana/provisioning/dashboards/

monitoring-reset:
	@echo "$(COLOR_YELLOW)🔄 Resetting monitoring...$(COLOR_RESET)"
	docker-compose down
	docker volume rm raptors-analytics_prometheus_data
	docker volume rm raptors-analytics_grafana_data
	make setup-monitoring
	make dc-up

run-all: clean setup-monitoring start-all check-services

setup-monitoring:
	@echo "$(COLOR_BLUE)🔧 Setting up monitoring...$(COLOR_RESET)"
	mkdir -p monitoring/prometheus
	mkdir -p monitoring/grafana/provisioning/dashboards
	@echo "$(COLOR_BLUE)📝 Creating Prometheus config...$(COLOR_RESET)"
	echo "global:\n  scrape_interval: 15s\n\nscrape_configs:\n  - job_name: 'redis'\n    static_configs:\n      - targets: ['redis-exporter:9121']" > monitoring/prometheus/prometheus.yml
	@echo "$(COLOR_BLUE)✨ Setup complete$(COLOR_RESET)"

start-all:
	@echo "$(COLOR_BLUE)🚀 Building and starting all services...$(COLOR_RESET)"
	docker-compose up --build -d
	@echo "$(COLOR_BLUE)⏳ Waiting for services to start...$(COLOR_RESET)"
	sleep 10

check-services:
	@echo "$(COLOR_GREEN)🌟 Checking services:$(COLOR_RESET)"
	@docker-compose ps --quiet redis && echo "✅ Redis is running" || echo "❌ Redis failed to start"
	@docker-compose ps --quiet redis-exporter && echo "✅ Redis Exporter is running" || echo "❌ Redis Exporter failed to start"
	@docker-compose ps --quiet prometheus && echo "✅ Prometheus is running" || echo "❌ Prometheus failed to start"
	@docker-compose ps --quiet grafana && echo "✅ Grafana is running" || echo "❌ Grafana failed to start"
	@docker-compose ps --quiet app && echo "✅ App is running" || echo "❌ App failed to start"
	@echo "\n$(COLOR_GREEN)🌟 Service URLs:$(COLOR_RESET)"
	@echo "📊 Streamlit: http://localhost:8501"
	@echo "📈 Prometheus: http://localhost:9090"
	@echo "📉 Grafana: http://localhost:3000 (admin/admin)"
	@echo "🔍 Redis Exporter: http://localhost:9121/metrics"
	@echo "\n$(COLOR_BLUE)📋 Full Service Status:$(COLOR_RESET)"
	@docker-compose ps
	@echo "\n$(COLOR_YELLOW)💡 Tip: Use 'make dc-logs' to view logs$(COLOR_RESET)"

.PHONY: run-all setup-monitoring start-all check-services

# Help
help:
	@echo "$(COLOR_BLUE)Available commands:$(COLOR_RESET)"
	@echo "$(COLOR_GREEN)Development:$(COLOR_RESET)"
	@echo "  make dev-setup    - Clean, setup, and run development environment"
	@echo "  make quick-start  - Quick start all services"
	@echo "  make dev         - Run Streamlit development server"
	@echo "\n$(COLOR_GREEN)Docker:$(COLOR_RESET)"
	@echo "  make dc-up       - Start all services"
	@echo "  make dc-down     - Stop all services"
	@echo "  make dc-logs     - View logs"
	@echo "\n$(COLOR_GREEN)Redis:$(COLOR_RESET)"
	@echo "  make redis-cli    - Open Redis CLI"
	@echo "  make redis-clear  - Clear Redis cache"
	@echo "  make redis-stats  - View Redis statistics"
	@echo "\n$(COLOR_GREEN)Testing:$(COLOR_RESET)"
	@echo "  make test        - Run all tests"
	@echo "  make test-cache  - Test cache functionality"
	@echo "  make lint        - Run linters"
