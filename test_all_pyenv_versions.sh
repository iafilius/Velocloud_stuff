#!/usr/bin/env bash
# Test all pyenv-installed Python versions for requirements and unittests
set -e

# Ensure pyenv is initialized for this shell
if [ -d "$HOME/.pyenv" ]; then
  export PATH="$HOME/.pyenv/bin:$PATH"
  eval "$(pyenv init --path)"
  eval "$(pyenv virtualenv-init -)"
fi

if ! command -v pyenv &>/dev/null; then
  echo "pyenv not found. Please install pyenv first."
  exit 1
fi

if [ ! -f requirements.txt ]; then
  echo "requirements.txt not found in current directory."
  exit 1
fi

PYTHON_VERSIONS=$(pyenv versions --bare)

for version in $PYTHON_VERSIONS; do
  echo "\n=== Testing with Python $version ==="
  pyenv local "$version"
  python -m venv .venv_$version
  source .venv_$version/bin/activate
  pip install --upgrade pip setuptools wheel
  pip install -r requirements.txt
  echo "Running unittests with Python $version..."
  python -m unittest discover -v || echo "Tests failed for Python $version"
  deactivate
  rm -rf .venv_$version
done

echo "All pyenv Python versions tested: $PYTHON_VERSIONS"
