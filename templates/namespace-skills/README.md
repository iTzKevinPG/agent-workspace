# Namespace Skills

Una **namespace skill** es una instruccion versionada que cualquier agente puede leer
para instalar una integracion especifica (Stripe, Auth0, SendGrid, etc.) en un proyecto
del namespace. El agente no inventa nada: lee `setup.md` y sabe exactamente que hacer.

---

## Las tres capas

```
skill/
└── stripe/
    ├── setup.md        ← instruccion (OBLIGATORIO)
    ├── templates/       ← archivos base listos para copiar (OPCIONAL)
    │   ├── stripe.service.ts.tpl
    │   └── .env.stripe.example
    └── skill.py         ← helpers Python ejecutables (OPCIONAL)
```

| Capa | Cuando usarla |
|------|---------------|
| `setup.md` | Siempre. Es lo que el agente lee. Sin esto no hay skill. |
| `templates/` | Cuando hay archivos que el agente debe copiar al proyecto (servicios, modulos, configs). Los archivos `.tpl` son plantillas que el agente adapta al stack. |
| `skill.py` | Cuando hay logica Python que automatizar (ej. generar un secreto, validar una API key, hacer un request de setup). |

---

## Como crear una skill desde cero

```bash
# 1. Copiar el template vacio
python run/add_namespace_skill.py --namespace mi-namespace --skill mi-skill

# 2. Editar la instruccion
nano namespaces/mi-namespace/skills/mi-skill/setup.md

# 3. Agregar templates si aplica
# Crear archivos en namespaces/mi-namespace/skills/mi-skill/templates/
```

O desde el repositorio (para contribuir una skill reutilizable):

```
templates/namespace-skills/
└── mi-skill/
    ├── setup.md          ← instruccion completa
    └── templates/
        └── *.tpl         ← archivos con extension .tpl
```

Luego agregar al namespace con:

```bash
python run/add_namespace_skill.py --namespace mi-namespace --skill mi-skill --from-template
```

---

## Como agregar una skill existente a un namespace

```bash
# Desde template versionado en este repo:
python run/add_namespace_skill.py --namespace ecommerce-web --skill stripe --from-template

# Desde una carpeta externa (acepta SKILL.md o setup.md):
python run/add_namespace_skill.py --namespace ecommerce-web --skill mi-skill --from-path /ruta/a/mi-skill

# Skill vacia para escribir desde cero:
python run/add_namespace_skill.py --namespace ecommerce-web --skill auth0
```

El script copia los archivos a `namespaces/<namespace>/skills/<skill>/` y agrega
la entrada al `namespace.yaml`.

> **Nota sobre SKILL.md:** si la carpeta fuente usa `SKILL.md` en lugar de `setup.md`
> (formato alternativo), el script lo renombra automaticamente a `setup.md` al copiar.

---

## Como decirle al agente que instale una skill

Una vez que el namespace tiene la skill configurada, cualquiera de estas frases funciona:

- `"instala la skill stripe en este proyecto"`
- `"configura Stripe siguiendo la instruccion del namespace"`
- `"el proyecto necesita procesar pagos, revisa las skills disponibles"`
- `"integra Stripe en el modulo de pagos"`

El agente recibe la instruccion completa de `setup.md` en su contexto y ejecuta
los pasos listados ahi: verifica variables de entorno, instala dependencias, copia
templates, adapta el codigo al stack, verifica que compila.

---

## Convenciones para archivos .tpl

- Extension `.tpl` en todos los archivos de `templates/`
- El agente elimina la extension `.tpl` al copiar al proyecto
- Usar `{{VARIABLE}}` para placeholders que el agente debe reemplazar
- El nombre del archivo indica el destino: `stripe.service.ts.tpl` → `stripe.service.ts`

---

## Skills disponibles en este repo

| Skill | Descripcion |
|-------|-------------|
| `stripe` | Integracion de pagos con Stripe para NestJS + TypeScript |

Para contribuir una skill nueva, crea la carpeta en `templates/namespace-skills/`
siguiendo la estructura del ejemplo `stripe/`.
