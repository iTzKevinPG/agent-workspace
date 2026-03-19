name: {{name}}
description: "{{description}}"

# Ruta local a los proyectos de este namespace (no se versiona)
projects_path: "{{projects_path}}"

stack: {{stack}}

workflow:
  methodology: {{methodology}}
  branching:   {{branching}}
  commits:     {{commits}}

# Agentes activos — deben existir como agents/<nombre>.yaml
agents: {{agents}}

# MCPs habilitados en este namespace
# Descomenta los que necesites — filesystem siempre activo
mcps:
  - filesystem          # lectura/escritura de archivos (requerido)
  - git                 # inspección del repo (solo lectura)
  - fetch               # documentación y URLs
  - shell               # build, tests, linting (whitelist configurable)
  - sequential_thinking # razonamiento estructurado (architect)
  - mermaid             # generación de diagramas (architect, devops)
  # - browser           # pruebas E2E — requiere BROWSER_BASE_URL en .env

# Skills disponibles para todos los agentes
skills:
  - codegen
  - testing
  - docs

# Namespace skills disponibles en este entorno
# Cada skill tiene una instrucción (setup.md) que cualquier agente puede leer
# para instalarla en un proyecto del namespace.
#
# Para agregar una skill: python run/add_namespace_skill.py --namespace <n> --skill <nombre>
# Para instalarla en un proyecto: dile al agente "instala la skill stripe en este proyecto"
#
namespace_skills: []
# Ejemplo:
# namespace_skills:
#   - name: stripe
#     description: "Integración de pagos con Stripe"
#     path: skills/stripe        # relativo a namespaces/<namespace>/
#     roles: [backend, devops]   # qué agentes pueden instalarla
