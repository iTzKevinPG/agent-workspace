# Changelog

## v1.0.0 — inicial

### MCPs incluidos

| MCP | Descripción |
|-----|-------------|
| `filesystem` | Lectura/escritura de archivos del proyecto activo (sandboxed) |
| `git` | Inspección del repo local: status, diff, log, branches, show-file (solo lectura) |
| `fetch` | Documentación oficial de librerías y contenido de URLs (urllib, sin deps) |
| `shell` | Build, tests y linting sandboxed con whitelist configurable |
| `sequential_thinking` | Razonamiento estructurado para problemas de diseño complejos |
| `mermaid` | Generación y guardado de diagramas (flowchart, sequence, class, ER, git) |

### Skills incluidas

| Skill | Métodos principales |
|-------|---------------------|
| `codegen` | `apply_standards`, `generate_file_header`, `detect_stack` |
| `testing` | `run_tests`, `get_coverage_report`, `detect_test_runner` |
| `docs` | `generate_readme_section`, `extract_endpoints`, `generate_jsdoc` |

### Agentes

| Agente | Modelo | MCPs |
|--------|--------|------|
| `architect` | claude-sonnet-4-6 | filesystem, git, fetch, sequential_thinking, mermaid |
| `backend` | claude-haiku-4-5-20251001 | filesystem, git, fetch, shell |
| `frontend` | claude-haiku-4-5-20251001 | filesystem, git, fetch, shell |
| `qa` | claude-haiku-4-5-20251001 | filesystem, git, shell |
| `devops` | claude-haiku-4-5-20251001 | filesystem, git, fetch, shell, mermaid |

### Arquitectura

- Registry central de MCPs (`tools/mcps/registry.py`) — el orquestador carga tools por agente dinámicamente
- Registry central de Skills (`tools/skills/registry.py`) — instanciación lazy de skills
- Orchestrator usa `_load_tools_for_agent()` — sin hardcodeo de tools
- Todos los MCPs son Python puro (stdlib + crewai.tools) — sin servidores externos
- Namespaces locales no versionados (`namespaces/` en `.gitignore`)
