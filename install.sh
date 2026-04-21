#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
SENTINEL_SCRIPT="$SCRIPT_DIR/sentinel.py"

echo "🔧 Setting up Sentinel..."

# Create venv if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Install dependencies
echo "📥 Installing dependencies..."
"$VENV_DIR/bin/pip" install --upgrade pip -q
"$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/requirements.txt" -q

# Make sentinel executable
chmod +x "$SENTINEL_SCRIPT"

# Create shell wrapper script for global access
echo "🌍 Installing globally..."
WRAPPER_PATH="/usr/local/bin/sentinel"
cat > /tmp/sentinel_wrapper <<'EOF'
#!/bin/bash
source /home/mike/Development/sentinel/venv/bin/activate
exec /home/mike/Development/sentinel/sentinel.py "$@"
EOF
sudo install -m 755 /tmp/sentinel_wrapper "$WRAPPER_PATH"
rm /tmp/sentinel_wrapper

echo "✅ Sentinel is ready!"
echo ""
echo "Usage:"
echo "  sentinel <issue text>"
echo "  sentinel recent -n 10"
echo "  sentinel diagnose --command 'cmd' --error 'error'"

