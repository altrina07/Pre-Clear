#!/bin/bash
# Quick start script for Document Requirement AI service
# Handles setup, training, and service startup

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="$SCRIPT_DIR/venv"
DATA_DIR="$SCRIPT_DIR/data"
MODELS_DIR="$SCRIPT_DIR/models"

echo "================================================"
echo "Document Requirement AI - Quick Start"
echo "================================================"

# Check Python version
echo "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found. Please install Python 3.8+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo "✓ Found: $PYTHON_VERSION"

# Create virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"
echo "✓ Virtual environment activated"

# Install dependencies
echo ""
echo "Installing Python dependencies..."
pip install -q --upgrade pip
pip install -q -r "$SCRIPT_DIR/requirements.txt"
echo "✓ Dependencies installed"

# Create directories
mkdir -p "$DATA_DIR"
mkdir -p "$MODELS_DIR"
echo "✓ Directories created"

# Check for training data
echo ""
echo "Checking training data..."

SYNTHETIC_DATA="$DATA_DIR/synthetic_documents_data.csv"
CUSTOM_DATA="$DATA_DIR/documents_training_data.csv"

if [ -f "$CUSTOM_DATA" ]; then
    TRAINING_DATA="$CUSTOM_DATA"
    echo "✓ Using custom training data: $CUSTOM_DATA"
elif [ ! -f "$SYNTHETIC_DATA" ]; then
    echo "Generating synthetic training data..."
    python3 "$SCRIPT_DIR/generate_synthetic_data.py" \
        --rows 1000 \
        --seed 42 \
        --output "$SYNTHETIC_DATA"
    TRAINING_DATA="$SYNTHETIC_DATA"
    echo "✓ Synthetic data generated: $SYNTHETIC_DATA"
else
    TRAINING_DATA="$SYNTHETIC_DATA"
    echo "✓ Using existing synthetic data: $SYNTHETIC_DATA"
fi

# Check for trained model
echo ""
echo "Checking trained model..."

MODEL_FILE="$MODELS_DIR/required_docs_model.pkl"

if [ ! -f "$MODEL_FILE" ]; then
    echo "Training model..."
    python3 "$SCRIPT_DIR/train_model.py" \
        --data-file "$TRAINING_DATA" \
        --save-dir "$MODELS_DIR"
    echo "✓ Model trained and saved"
else
    echo "✓ Model already trained: $MODEL_FILE"
fi

# Copy .env if not exists
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo ""
    echo "Creating .env configuration file..."
    # Create default .env
    cat > "$SCRIPT_DIR/.env" << 'EOF'
DOCUMENT_RECOMMENDER_MODE=hybrid
DOCUMENT_MODEL_PATH=./models
CONFIDENCE_THRESHOLD=0.5
ML_WEIGHT=0.6
API_WEIGHT=0.4
COMPLIANCE_API_KEY=
COMPLIANCE_API_BASE_URL=https://api.descartes.com
DOCUMENT_PREDICTOR_HOST=0.0.0.0
DOCUMENT_PREDICTOR_PORT=8002
LOG_LEVEL=INFO
EOF
    echo "✓ .env created (edit with your settings)"
else
    echo "✓ .env already exists"
fi

# Start service
echo ""
echo "================================================"
echo "Starting FastAPI Service"
echo "================================================"
echo ""
echo "Service will be available at:"
echo "  API:    http://localhost:8002"
echo "  Health: http://localhost:8002/health"
echo "  Info:   http://localhost:8002/model-info"
echo ""
echo "Press Ctrl+C to stop the service"
echo ""

python3 "$SCRIPT_DIR/serve_app.py"
