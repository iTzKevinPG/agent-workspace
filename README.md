# agent-workspace

Orquestador de agentes multi-rol basado en CrewAI + Claude.
Disenado para trabajar sobre proyectos locales sin versionar contexto sensible.

## Como funciona

- Defines **namespaces** (un dominio de trabajo, ej: ecommerce-web)
- Cada namespace apunta a una carpeta local con tus repos
- El orquestador carga el namespace, arma el equipo de agentes, y se queda **esperando tareas**
- Tu das instrucciones en lenguaje natural; los agentes planifican y ejecutan sobre tus archivos
- Tu revisas, haces commit y abres el MR — los agentes no tocan git

## Setup inicial (una vez por PC)

```bash
git clone <este-repo>
cd agent-workspace
bash setup.sh
```

Edita `.env` con tu `ANTHROPIC_API_KEY`.

## Crear un namespace

```bash
source .venv/Scripts/activate
python run/init.py
```

El wizard te pregunta: stack, metodologia, path a tus proyectos, agentes a activar.
Genera `namespaces/<nombre>/` localmente (no se versiona).

Luego agrega symlinks a tus repos:
```bash
ln -s /ruta/a/mi-tienda namespaces/ecommerce-web/projects/mi-tienda
```

## Arrancar el orquestador

```bash
# Sesion interactiva (se mantiene encendida)
python run/start.py --namespace ecommerce-web

# Con proyecto especifico activo
python run/start.py --namespace ecommerce-web --project mi-tienda

# Tarea puntual sin sesion
python run/task.py --namespace ecommerce-web --project mi-tienda \
  --task "crear endpoint GET /products con paginacion"
```

## Comandos en sesion interactiva

| Comando | Accion |
|---|---|
| `<texto libre>` | Ejecutar tarea |
| `proyecto <nombre>` | Cambiar proyecto activo |
| `estado` | Refrescar dashboard |
| `salir` / `q` | Terminar sesion |

## Estructura del proyecto

```
agent-workspace/
├── agents/          # Definicion de roles (sube a git)
├── core/            # Motor de orquestacion (sube a git)
├── dashboard/       # UI de terminal (sube a git)
├── tools/           # MCPs y skills (sube a git)
├── templates/       # Plantillas para namespaces (sube a git)
├── run/             # Scripts de entrada (sube a git)
├── namespaces/      # Contexto local — NO sube a git
├── logs/            # Logs de sesion — NO sube a git
└── memory/          # Estado persistente — NO sube a git
```

## Agregar un namespace nuevo en otro PC

```bash
git clone <este-repo>
bash setup.sh
python run/init.py --name ecommerce-web
# Rellenar las preguntas del wizard
# Agregar symlinks a los repos locales
python run/start.py --namespace ecommerce-web
```

## Costos aproximados

| Uso | Modelo | Costo/mes aprox |
|---|---|---|
| Ligero (consultas, snippets) | Haiku | < $5 |
| Normal (desarrollo activo) | Haiku + Sonnet | $15-40 |
| Intenso (multi-agente full) | Sonnet | $50-150 |

El modelo por defecto es Haiku (economico). El agente `architect` usa Sonnet
por defecto porque toma decisiones complejas. Puedes cambiar esto en `agents/*.yaml`.
