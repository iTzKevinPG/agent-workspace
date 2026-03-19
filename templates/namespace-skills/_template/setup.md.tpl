# Skill: {{SKILL_NAME}}

## Qué hace
Descripción de una línea de qué configura esta skill en el proyecto.

## Cuándo usarla
Describe en qué contexto tiene sentido instalar esta skill.
Ejemplo: "cuando el proyecto necesita procesar pagos con tarjeta".

## Variables de entorno requeridas
Lista las vars que el developer debe agregar al .env del proyecto:

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| VAR_NAME | qué es | valor-ejemplo |

## Lo que esta skill instala

### Archivos que crea
Lista exacta de rutas relativas al project_root donde se crean archivos:
- `src/module/example.service.ts` — servicio principal
- `.env.example` — variables de entorno de referencia

Los templates de estos archivos están en `skills/{{SKILL_NAME}}/templates/`
(relativo al directorio del namespace). Usa el filesystem MCP para leerlos
antes de copiarlos al proyecto.

### Dependencias que instala
Lista de paquetes npm o pip a instalar:
- `paquete` — descripción

### Lo que NO hace esta skill
Sé explícito sobre los límites:
- No configura nada en el dashboard del servicio externo
- No crea tablas de base de datos
- No agrega autenticación

## Pasos de instalación

El agente ejecuta estos pasos en orden:

1. Verificar que las variables de entorno estén definidas en .env
2. Instalar dependencias listadas arriba
3. Leer los archivos de `skills/{{SKILL_NAME}}/templates/` usando el filesystem MCP
4. Copiar y adaptar los archivos al stack del proyecto (nombres de módulo, imports, rutas)
5. Verificar que el proyecto compila sin errores

## Cómo verificar que funcionó
Qué debe existir o pasar para confirmar que la instalación fue exitosa:
- El archivo de servicio principal existe en la ruta indicada
- El build del proyecto pasa sin errores de tipo
- Las variables de entorno están documentadas en el README del proyecto
