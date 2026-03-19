import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import Stripe from 'stripe';

@Injectable()
export class StripeService {
  private readonly stripe: Stripe;
  private readonly logger = new Logger(StripeService.name);

  constructor(private readonly configService: ConfigService) {
    this.stripe = new Stripe(
      this.configService.getOrThrow<string>('STRIPE_SECRET_KEY'),
      {
        apiVersion: (this.configService.get<string>('STRIPE_API_VERSION') ??
          '2024-06-20') as Stripe.LatestApiVersion,
      },
    );
  }

  /**
   * Crea un PaymentIntent en Stripe.
   *
   * @param amount   Monto en la unidad mínima de la moneda (centavos para USD/EUR).
   * @param currency Código ISO 4217 de la moneda, en minúsculas. Ej: 'usd', 'eur'.
   * @param metadata Metadatos opcionales para asociar al PaymentIntent.
   * @returns        El objeto PaymentIntent creado por Stripe.
   * @throws         Error si Stripe rechaza la solicitud.
   */
  async createPaymentIntent(
    amount: number,
    currency: string,
    metadata?: Stripe.MetadataParam,
  ): Promise<Stripe.PaymentIntent> {
    try {
      const paymentIntent = await this.stripe.paymentIntents.create({
        amount,
        currency: currency.toLowerCase(),
        metadata,
        automatic_payment_methods: { enabled: true },
      });
      this.logger.log(`PaymentIntent creado: ${paymentIntent.id}`);
      return paymentIntent;
    } catch (error) {
      this.handleStripeError(error, 'createPaymentIntent');
    }
  }

  /**
   * Recupera un PaymentIntent existente por su ID.
   *
   * @param paymentIntentId ID del PaymentIntent a recuperar (prefijo `pi_`).
   * @returns               El objeto PaymentIntent actualizado desde Stripe.
   * @throws                Error si el PaymentIntent no existe o la solicitud falla.
   */
  async retrievePaymentIntent(
    paymentIntentId: string,
  ): Promise<Stripe.PaymentIntent> {
    try {
      return await this.stripe.paymentIntents.retrieve(paymentIntentId);
    } catch (error) {
      this.handleStripeError(error, 'retrievePaymentIntent');
    }
  }

  /**
   * Construye y valida un evento de webhook recibido de Stripe.
   * Usar en el endpoint POST que recibe webhooks para verificar la firma.
   *
   * @param payload   Cuerpo raw del request (Buffer o string). En NestJS,
   *                  usar `@RawBody()` o `express.raw()` en el middleware.
   * @param signature Valor del header `stripe-signature` del request entrante.
   * @returns         El objeto Stripe.Event validado.
   * @throws          Error si la firma no es válida o el payload está malformado.
   */
  constructWebhookEvent(
    payload: Buffer | string,
    signature: string,
  ): Stripe.Event {
    const webhookSecret = this.configService.getOrThrow<string>(
      'STRIPE_WEBHOOK_SECRET',
    );
    try {
      return this.stripe.webhooks.constructEvent(
        payload,
        signature,
        webhookSecret,
      );
    } catch (error) {
      this.handleStripeError(error, 'constructWebhookEvent');
    }
  }

  /**
   * Maneja errores de la API de Stripe con mensajes descriptivos.
   * Lanza siempre una excepción tipada.
   */
  private handleStripeError(error: unknown, method: string): never {
    if (error instanceof Stripe.errors.StripeError) {
      this.logger.error(
        `Stripe error en ${method}: [${error.type}] ${error.message}`,
        { code: error.code, statusCode: error.statusCode },
      );
      throw new Error(`Stripe ${error.type}: ${error.message}`);
    }
    this.logger.error(`Error inesperado en ${method}`, error);
    throw error;
  }
}
