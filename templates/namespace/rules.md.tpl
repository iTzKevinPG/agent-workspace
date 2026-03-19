# Reglas — {{name}}

> Los agentes leen este archivo al inicio de cada sesión.
> Sé explícito: lo que no está escrito aquí, los agentes lo asumirán.

## Lo que los agentes PUEDEN hacer
- Leer y escribir archivos dentro de `projects_path`
- Crear archivos nuevos siguiendo los estándares definidos
- Ejecutar comandos de build y tests dentro del proyecto
- Sugerir cambios de arquitectura (como propuesta, no implementar sin confirmar)

## Lo que los agentes NUNCA deben hacer
- Hacer commits o push (eso lo hace el desarrollador)
- Borrar archivos sin confirmación explícita
- Modificar archivos fuera de `projects_path`
- Instalar dependencias globales sin confirmación

## Restricciones adicionales
{{main_restrictions}}

## Decisiones ya tomadas (no re-debatir)
<!-- Ejemplo:
- ORM: Prisma (no TypeORM)
- Auth: JWT con refresh tokens
- API: REST (no GraphQL en este proyecto)
-->

## Contexto adicional
{{extra_context}}
