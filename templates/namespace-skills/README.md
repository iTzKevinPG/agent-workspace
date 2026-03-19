# Namespace Skills

Una **namespace skill** es una instrucción versionada que cualquier agente puede leer
para instalar una integración específica (Stripe, Auth0, SendGrid, etc.) en un proyecto
del namespace. El agente no inventa nada: lee `setup.md` y sabe exactamente qué hacer.

---

## Las tres capas

```
skill/
└── stripe/
    ├── setup.md        ← instrucción (OBLIGATORIO)
    ├── templates/       ← archivos base listos para copiar (OPCIONAL)
    │   ├── stripe.service.ts.tpl
    │   └── .env.stripe.example
    └── skill.py         ← helpers Python ejecutables (OPCIONAL)
```

| Capa | Cuándo usarla |
|------|---------------|
| `setup.md` | Siempre. Es lo que el agente lee. Sin esto no hay skill. |
| `templates/` | Cuando hay archivos que el agente debe copiar al proyecto (servicios, módulos, configs). Los archivos `.tpl` son plantillas que el agente adapta al stack. |
| `skill.py` | Cuando hay lógica Python que automatizar (ej. generar un secreto, validar una API key, hacer un request de setup). |

---

## Cómo crear una skill desde cero

```bash
# 1. Copiar el template vacío
python run/add_namespace_skill.py --namespace mi-namespace --skill mi-skill

# 2. Editar la instrucción
nano namespaces/mi-namespace/skills/mi-skill/setup.md

# 3. Agregar templates si aplica
# Crear archivos en namespaces/mi-namespace/skills/mi-skill/templates/
```

O desde el repositorio (para contribuir una skill reutilizable):

```
templates/namespace-skills/
└── mi-skill/
    ├── setup.md          ← instrucción completa
    └── templates/
        └── *.tpl         ← archivos con extensión .tpl
```

Luego agregar al namespace con:

```bash
python run/add_namespace_skill.py --namespace mi-namespace --skill mi-skill --from-template
```

---

## Cómo agregar una skill existente a un namespace

```bash
# Desde template versionado en este repo:
python run/add_namespace_skill.py --namespace ecommerce-web --skill stripe --from-template

# Skill vacía para escribir desde cero:
python run/add_namespace_skill.py --namespace ecommerce-web --skill auth0
```

El script copia los archivos a `namespaces/<namespace>/skills/<skill>/` y agrega
la entrada al `namespace.yaml`.

---

## Cómo decirle al agente que instale una skill

Una vez que el namespace tiene la skill configurada, cualquiera de estas frases funciona:

- `"instala la skill stripe en este proyecto"`
- `"configura Stripe siguiendo la instrucción del namespace"`
- `"el proyecto necesita procesar pagos, revisa las skills disponibles"`
- `"integra Stripe en el módulo de pagos"`

El agente recibe la instrucción completa de `setup.md` en su contexto y ejecuta
los pasos listados ahí: verifica variables de entorno, instala dependencias, copia
templates, adapta el código al stack, verifica que compila.

---

## Convenciones para archivos .tpl

- Extensión `.tpl` en todos los archivos de `templates/`
- El agente elimina la extensión `.tpl` al copiar al proyecto
- Usar `{{VARIABLE}}` para placeholders que el agente debe reemplazar
- El nombre del archivo indica el destino: `stripe.service.ts.tpl` → `stripe.service.ts`

---

## Skills disponibles en este repo

| Skill | Descripción |
|-------|-------------|
| `stripe` | Integración de pagos con Stripe para NestJS + TypeScript |

Para contribuir una skill nueva, crea la carpeta en `templates/namespace-skills/`
siguiendo la estructura del ejemplo `stripe/`.
