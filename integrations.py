# Archivo: integrations.py (CORREGIDO FINAL con HTTPX)

import httpx 
import base64
from config import settings
from typing import Dict, Any
from fastapi import HTTPException
import time
# Eliminamos requests, ya no se usa.

PAYPAL_API_BASE = {
    # CORRECCIÓN URL: Usamos api-m para la API REST
    'sandbox': 'https://api-m.sandbox.paypal.com', 
    'live': 'https://api-m.paypal.com'
}

# 1. FUNCIÓN ASÍNCRONA PARA OBTENER TOKEN
async def obtener_token_acceso(client: httpx.AsyncClient) -> str:
    """Obtiene el token de acceso de PayPal de forma asíncrona."""
    auth = base64.b64encode(f"{settings.PAYPAL_CLIENT_ID}:{settings.PAYPAL_SECRET}".encode()).decode()
    url = PAYPAL_API_BASE[settings.PAYPAL_MODE] + '/v1/oauth2/token'
    
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Basic {auth}'
    }
    data = {'grant_type': 'client_credentials'}
    
    response = await client.post(url, headers=headers, data=data) 
    response.raise_for_status()
    return response.json()['access_token']

# 2. FUNCIÓN ASÍNCRONA PARA CREAR ORDEN
async def crear_orden_paypal(cotizacion: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea una orden de pago en PayPal, ahora de forma totalmente asíncrona.
    """
    try:
        # Usamos AsyncClient para manejar todas las operaciones HTTP
        async with httpx.AsyncClient() as client:
            
            # 1. Obtener Token
            token = await obtener_token_acceso(client) 
            
            # 2. Crear Orden
            url = PAYPAL_API_BASE[settings.PAYPAL_MODE] + '/v2/checkout/orders'
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            }
            
            total_precio = str(round(cotizacion['precio_base'], 2))
            
            payload = {
                'intent': 'CAPTURE',
                'purchase_units': [{
                    'amount': {
                        'currency_code': cotizacion['moneda'],
                        'value': total_precio
                    },
                    'custom_id': 'curso-personalizado-' + str(int(time.time())),
                    'description': cotizacion.get('curso_propuesto', 'Curso de Capacitación Automático')
                }],
                'application_context': {
                # URLs de Producción de Lovable
                'return_url': 'https://centrodecapacitacion.lovable.app/pago-exitoso', 
                'cancel_url': 'https://centrodecapacitacion.lovable.app/pago-cancelado',
                'user_action': 'PAY_NOW'
            }
            }
            
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status() # Esto lanza httpx.HTTPStatusError si falla
            
            order_data = response.json()
            print(f"[CORAZÓN PAYPAL] -> Orden Creada. ID: {order_data['id']}")
            
            return {
                "order_id": order_data['id'],
                "approval_link": next((link['href'] for link in order_data['links'] if link['rel'] == 'approve'), None)
            }

    # CORRECCIÓN CLAVE: Usamos la excepción de HTTPX, no la de requests
    except httpx.HTTPStatusError as e:
        error_details = e.response.json()
        print(f"[ERROR PAYPAL] -> {error_details}")
        raise HTTPException(status_code=400, detail=f"Error en la pasarela de PayPal: {error_details.get('message', 'Error desconocido')}")
    except Exception as e:
        print(f"[ERROR INTERNO] -> {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno al crear la orden de PayPal: {e}")