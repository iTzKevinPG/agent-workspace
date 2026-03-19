#!/usr/bin/env bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}╭──────────────────────────────────────────╮${NC}"
echo -e "${GREEN}│  agent-workspace  ·  setup inicial       │${NC}"
echo -e "${GREEN}╰──────────────────────────────────────────╯${NC}"

# .env
if [ ! -f .env ]; then
  cp .env.example .env
  echo -e "${YELLOW}→ .env creado desde .env.example${NC}"
  echo -e "  Edita .env con tu ANTHROPIC_API_KEY antes de continuar."
else
  echo -e "✓ .env ya existe"
fi

# Directorios locales (no versionados)
mkdir -p namespaces logs memory
echo "✓ Carpetas locales creadas (namespaces/, logs/, memory/)"

# Entorno virtual
if [ ! -d .venv ]; then
  python3 -m venv .venv
  echo "✓ Entorno virtual creado en .venv/"
fi

source .venv/bin/activate
pip install -q -e .
echo "✓ Dependencias instaladas"

# Playwright (browser MCP)
python -m playwright install chromium --quiet 2>/dev/null || \
  echo "  (Playwright no pudo instalar Chromium — browser MCP desactivado)"

echo ""
echo -e "${GREEN}✓ Setup completo.${NC}"
echo ""
echo "Próximos pasos:"
echo "  1. Edita .env con tu ANTHROPIC_API_KEY"
echo "  2. Crea tu primer namespace:"
echo "     source .venv/bin/activate"
echo "     python run/init.py"
echo "  3. Arranca el orquestador:"
echo "     python run/start.py --namespace <nombre>"
