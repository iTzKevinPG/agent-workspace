# Skill: stripe

## Que hace
Instala una integracion completa de Stripe en un proyecto NestJS + TypeScript:
servicio, modulo, y configuracion de variables de entorno.

## Cuando usarla
Cuando el proyecto necesita procesar pagos con tarjeta de credito/debito.
Aplica a cualquier proyecto NestJS que use `@nestjs/config` para leer variables
de entorno.

## Variables de entorno requeridas
Agrega estas lineas al `.env` del proyecto antes de ejecutar los pasos:

| Variable | Descripcion | Ejemplo |
|----------|-------------|---------|
| `STRIPE_SECRET_KEY` | Clave secreta de la API de Stripe | `sk_test_51...` |
| `STRIPE_WEBHOOK_SECRET` | Secreto para verificar webhooks de Stripe | `whsec_...` |
| `STRIPE_API_VERSION` | Version de la API de Stripe a usar | `2024-06-20` |

Obten las claves en: https://dashboard.stripe.com/apikeys
Obten el webhook secret en: https://dashboard.stripe.com/webhooks

## Lo que esta skill instala

### Archivos que crea
Rutas relativas al `project_root` del proyecto activo:

- `src/payments/stripe.service.ts` — servicio con los metodos principales de Stripe
- `src/payments/stripe.module.ts` — modulo NestJS que provee StripeService
- `.env.stripe.example` — referencia de variables de entorno

Los templates de estos archivos estan en `skills/stripe/templates/` (relativo al
directorio del namespace). Leelos con el filesystem MCP antes de copiarlos.

### Dependencias que instala
```bash
npm install stripe
npm install --save-dev @types/stripe
```

### Lo que NO hace esta skill
- No configura webhooks en el dashboard de Stripe (requiere URL publica)
- No crea tablas de base de datos para pagos
- No implementa logica de negocio especifica (ej. suscripciones, reembolsos)
- No agrega autenticacion ni autorizacion a los endpoints
- No registra el modulo en `AppModule` (el agente debe hacerlo manualmente)

## Pasos de instalacion

El agente ejecuta estos pasos en orden:

1. **Verificar variables de entorno**: confirmar que `STRIPE_SECRET_KEY`,
   `STRIPE_WEBHOOK_SECRET`, y `STRIPE_API_VERSION` estan definidas en el `.env`
   del proyecto. Si no estan, advertir al developer y continuar igual para
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
   - Escribir `src/payments/stripe.service.ts` (sin la extension `.tpl`)
   - Escribir `src/payments/stripe.module.ts`
   - Escribir `.env.stripe.example` en la raiz del proyecto
   - Adaptar los imports si el proyecto usa alias de paths (`@/`, `~/`, etc.)

5. **Verificar compilacion**: ejecutar `npm run build` o `npx tsc --noEmit`.
   Si hay errores de tipo, corregirlos antes de reportar el resultado.

## Como verificar que funciono
La instalacion fue exitosa si:
- `src/payments/stripe.service.ts` existe y contiene `StripeService`
- `src/payments/stripe.module.ts` existe y exporta `StripeModule`
- `.env.stripe.example` existe en la raiz del proyecto
- `npm run build` (o `npx tsc --noEmit`) pasa sin errores de tipo
- El `package.json` tiene `stripe` en las dependencias

## Proximos pasos (para el developer)
Despues de instalar la skill:

1. Importar `StripeModule` en `AppModule` o en el modulo que lo necesite:
   ```typescript
   import { StripeModule } from './payments/stripe.module';
   ```

2. Inyectar `StripeService` donde se necesite:
   ```typescript
   constructor(private readonly stripeService: StripeService) {}
   ```

3. Configurar el webhook en el dashboard de Stripe apuntando a tu endpoint publico.
