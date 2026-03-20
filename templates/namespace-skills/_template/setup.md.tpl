# Skill: {{SKILL_NAME}}

## Que hace
Descripcion de una linea de que configura esta skill en el proyecto.

## Cuando usarla
Describe en que contexto tiene sentido instalar esta skill.
Ejemplo: "cuando el proyecto necesita procesar pagos con tarjeta".

## Variables de entorno requeridas
Lista las vars que el developer debe agregar al .env del proyecto:

| Variable | Descripcion | Ejemplo |
|----------|-------------|---------|
| VAR_NAME | que es | valor-ejemplo |

## Lo que esta skill instala

### Archivos que crea
Lista exacta de rutas relativas al project_root donde se crean archivos:
- `src/module/example.service.ts` — servicio principal
- `.env.example` — variables de entorno de referencia

Los templates de estos archivos estan en `skills/{{SKILL_NAME}}/templates/`
(relativo al directorio del namespace). Usa el filesystem MCP para leerlos
antes de copiarlos al proyecto.

### Dependencias que instala
Lista de paquetes npm o pip a instalar:
- `paquete` — descripcion

### Lo que NO hace esta skill
Se explicito sobre los limites:
- No configura nada en el dashboard del servicio externo
- No crea tablas de base de datos
- No agrega autenticacion

## Pasos de instalacion

El agente ejecuta estos pasos en orden:

1. Verificar que las variables de entorno esten definidas en .env
2. Instalar dependencias listadas arriba
3. Leer los archivos de `skills/{{SKILL_NAME}}/templates/` usando el filesystem MCP
4. Copiar y adaptar los archivos al stack del proyecto (nombres de modulo, imports, rutas)
5. Verificar que el proyecto compila sin errores

## Como verificar que funciono
Que debe existir o pasar para confirmar que la instalacion fue exitosa:
- El archivo de servicio principal existe en la ruta indicada
- El build del proyecto pasa sin errores de tipo
- Las variables de entorno estan documentadas en el README del proyecto
