set positional-arguments
set dotenv-required
set shell := ["bash", "-cue"]

root_dir := `git rev-parse --show-toplevel`


# Default recipe to list all recipes.
[private]
default:
  just --list --no-aliases

# Setup project for development
install: 
  uv pip install -e '.[test,dev]'

# Lint python code
lint: install
	uv run ruff check src

# Run unit tests
test: install 
	uv run pytest

alias dev := nix-develop
# Enter a Nix development shell.
nix-develop *args:
  @echo "Starting nix developer shell in './tools/nix/flake.nix'."
  @cd "{{root_dir}}" && \
  cmd=("$@") && \
  { [ -n "${cmd:-}" ] || cmd=("zsh"); } && \
  nix develop ./tools/nix#default --accept-flake-config --command "${cmd[@]}"

# Manage container images.
mod image 'tools/just/image.just'