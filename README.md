# agent-workspace

Orquestador de agentes multi-rol basado en CrewAI + Claude.
Diseñado para trabajar sobre proyectos locales sin versionar contexto sensible.

## Cómo funciona

- Defines **namespaces** (un dominio de trabajo, ej: ecommerce-web)
- Cada namespace apunta a una carpeta local con tus repos
- El orquestador carga el namespace, arma el equipo de agentes, y se queda **esperando tareas**
- Tú das instrucciones en lenguaje natural; los agentes planifican y ejecutan sobre tus archivos
- Tú revisas, haces commit y abres el MR — los agentes no tocan git

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

El wizard te pregunta: stack, metodología, path a tus proyectos, agentes a activar.
Genera `namespaces/<nombre>/` localmente (no se versiona).

Luego agrega symlinks a tus repos:
```bash
ln -s /ruta/a/mi-tienda namespaces/ecommerce-web/projects/mi-tienda
```

## Arrancar el orquestador

```bash
# Sesión interactiva (se mantiene encendida)
python run/start.py --namespace ecommerce-web

# Con proyecto específico activo
python run/start.py --namespace ecommerce-web --project mi-tienda

# Tarea puntual sin sesión
python run/task.py --namespace ecommerce-web --project mi-tienda \
  --task "crear endpoint GET /products con paginación"
```

## Comandos en sesión interactiva

| Comando | Acción |
|---|---|
| `<texto libre>` | Ejecutar tarea |
| `proyecto <nombre>` | Cambiar proyecto activo |
| `estado` | Refrescar dashboard |
| `salir` / `q` | Terminar sesión |

## Estructura del proyecto

```
agent-workspace/
├── agents/          # Definición de roles (sube a git)
├── core/            # Motor de orquestación (sube a git)
├── dashboard/       # UI de terminal (sube a git)
├── tools/           # MCPs y skills (sube a git)
├── templates/       # Plantillas para namespaces (sube a git)
├── run/             # Scripts de entrada (sube a git)
├── namespaces/      # Contexto local — NO sube a git
├── logs/            # Logs de sesión — NO sube a git
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
| Normal (desarrollo activo) | Haiku + Sonnet | $15–40 |
| Intenso (multi-agente full) | Sonnet | $50–150 |

El modelo por defecto es Haiku (económico). El agente `architect` usa Sonnet
por defecto porque toma decisiones complejas. Puedes cambiar esto en `agents/*.yaml`.
