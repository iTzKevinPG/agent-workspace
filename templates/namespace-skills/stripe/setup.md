# Skill: stripe

## Qué hace
Instala una integración completa de Stripe en un proyecto NestJS + TypeScript:
servicio, módulo, y configuración de variables de entorno.

## Cuándo usarla
Cuando el proyecto necesita procesar pagos con tarjeta de crédito/débito.
Aplica a cualquier proyecto NestJS que use `@nestjs/config` para leer variables
de entorno.

## Variables de entorno requeridas
Agrega estas líneas al `.env` del proyecto antes de ejecutar los pasos:

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `STRIPE_SECRET_KEY` | Clave secreta de la API de Stripe | `sk_test_51...` |
| `STRIPE_WEBHOOK_SECRET` | Secreto para verificar webhooks de Stripe | `whsec_...` |
| `STRIPE_API_VERSION` | Versión de la API de Stripe a usar | `2024-06-20` |

Obtén las claves en: https://dashboard.stripe.com/apikeys
Obtén el webhook secret en: https://dashboard.stripe.com/webhooks

## Lo que esta skill instala

### Archivos que crea
Rutas relativas al `project_root` del proyecto activo:

- `src/payments/stripe.service.ts` — servicio con los métodos principales de Stripe
- `src/payments/stripe.module.ts` — módulo NestJS que provee StripeService
- `.env.stripe.example` — referencia de variables de entorno

Los templates de estos archivos están en `skills/stripe/templates/` (relativo al
directorio del namespace). Léelos con el filesystem MCP antes de copiarlos.

### Dependencias que instala
```bash
npm install stripe
npm install --save-dev @types/stripe
```

### Lo que NO hace esta skill
- No configura webhooks en el dashboard de Stripe (requiere URL pública)
- No crea tablas de base de datos para pagos
- No implementa lógica de negocio específica (ej. suscripciones, reembolsos)
- No agrega autenticación ni autorización a los endpoints
- No registra el módulo en `AppModule` (el agente debe hacerlo manualmente)

## Pasos de instalación

El agente ejecuta estos pasos en orden:

1. **Verificar variables de entorno**: confirmar que `STRIPE_SECRET_KEY`,
   `STRIPE_WEBHOOK_SECRET`, y `STRIPE_API_VERSION` están definidas en el `.env`
   del proyecto. Si no están, advertir al developer y continuar igual para
   que vea el ejemplo.

2. **Instalar dependencias**: ejecutar `npm install stripe` en el directorio
   del proyecto. Verificar que `package.json` queda actualizado.

3. **Leer templates**: usar el filesystem MCP para leer los tres archivos de
   `skills/stripe/templates/`:
   - `stripe.service.ts.tpl`
   - `stripe.module.ts.tpl`
   - `.env.stripe.example`

4. **Crear directorio y copiar archivos**:
   - Crear `src/payments/` si no existe
   - Escribir `src/payments/stripe.service.ts` (sin la extensión `.tpl`)
   - Escribir `src/payments/stripe.module.ts`
   - Escribir `.env.stripe.example` en la raíz del proyecto
   - Adaptar los imports si el proyecto usa alias de paths (`@/`, `~/`, etc.)

5. **Verificar compilación**: ejecutar `npm run build` o `npx tsc --noEmit`.
   Si hay errores de tipo, corregirlos antes de reportar el resultado.

## Cómo verificar que funcionó
La instalación fue exitosa si:
- `src/payments/stripe.service.ts` existe y contiene `StripeService`
- `src/payments/stripe.module.ts` existe y exporta `StripeModule`
- `.env.stripe.example` existe en la raíz del proyecto
- `npm run build` (o `npx tsc --noEmit`) pasa sin errores de tipo
- El `package.json` tiene `stripe` en las dependencias

## Próximos pasos (para el developer)
Después de instalar la skill:

1. Importar `StripeModule` en `AppModule` o en el módulo que lo necesite:
   ```typescript
   import { StripeModule } from './payments/stripe.module';
   ```

2. Inyectar `StripeService` donde se necesite:
   ```typescript
   constructor(private readonly stripeService: StripeService) {}
   ```

3. Configurar el webhook en el dashboard de Stripe apuntando a tu endpoint público.
