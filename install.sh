#!/usr/bin/env bash
# Install feynman-code-tutor as a personal Claude Code skill.
#   ./install.sh            -> ~/.claude/skills/
#   ./install.sh --project  -> ./.claude/skills/  (this repo's consumer project)
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/plugins/feynman-code-tutor/skills/feynman-code-tutor"
DEST="$HOME/.claude/skills"
[ "${1:-}" = "--project" ] && DEST=".claude/skills"

mkdir -p "$DEST"
rm -rf "$DEST/feynman-code-tutor"
cp -r "$SRC" "$DEST/feynman-code-tutor"
echo "Installed to $DEST/feynman-code-tutor"
echo "Restart Claude Code, then check it with /skills or just ask it to explain some code."
