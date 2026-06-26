from flask import Flask, request, jsonify
import requests
import os
from urllib.parse import urlencode
from datetime import datetime
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Configuration - Load from environment variables
PAGBRASIL_SECRET = os.environ.get("PAGBRASIL_SECRET")
PAGBRASIL_PBTOKEN = os.environ.get("PAGBRASIL_PBTOKEN")
PAGBRASIL_API_URL = os.environ.get("PAGBRASIL_SUBSCRIPTION_GET_URL", "https://connect.pagbrasil.com/api/pagstream/subscription/get")
# Adicione no início do arquivo, com as outras configurações
KLAVIYO_API_KEY = os.environ.get("KLAVIYO_API_KEY")
KLAVIYO_API_URL = "https://a.klaviyo.com/api/events/"

# Mapeamentos para os códigos
STATUS_MAP = {
    0: "Waiting for first payment",
    1: "Active", 
    2: "Pending payment",
    3: "Inactive/Cancelled",
    4: "Expired",
    5: "Paused"
}

PAYMENT_METHOD_MAP = {
    "C": "Credit card",
    "D": "Debit card",
    "B": "Boleto Bancário",
    "F": "Boleto Flash®",
    "X": "Pix"
}

ORDER_STATUS_MAP = {
    "WP": "Payment requested but not processed yet",
    "PA": "Payment pre-authorized but not captured yet",
    "PC": "Payment Completed",
    "PF": "Payment Failed",
    "PR": "Payment Rejected",
    "RR": "Refund Requested",
    "RP": "Refund Processed",
    "CB": "Chargeback"
}

BILLING_CYCLE_MAP = {
    "T": "Trimestral",
    "M": "Mensal",
    "S": "Semestral",
}

def get_subscription_info(subscription_id: str):
    """Busca informações da assinatura na API da PagBrasil"""
    
    # Log das credenciais (parcial)
    app.logger.info(f"API URL: {PAGBRASIL_API_URL}")
    app.logger.info(f"Secret (first 10): {PAGBRASIL_SECRET[:10] if PAGBRASIL_SECRET else 'None'}")
    app.logger.info(f"PBToken (first 10): {PAGBRASIL_PBTOKEN[:10] if PAGBRASIL_PBTOKEN else 'None'}")
    app.logger.info(f"Subscription ID: {subscription_id}")
    
    payload = {
        'secret': PAGBRASIL_SECRET,
        'pbtoken': PAGBRASIL_PBTOKEN,
        'subscription': subscription_id,
        'response_type': 'JSON'
    }
    
    encoded_payload = urlencode(payload)
    app.logger.info(f"Full payload: {encoded_payload}")
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0 (compatible)'
    }
    
    try:
        response = requests.post(
            PAGBRASIL_API_URL,
            data=encoded_payload,
            headers=headers,
            timeout=30
        )
        
        app.logger.info(f"Response Status: {response.status_code}")
        app.logger.info(f"Response Headers: {dict(response.headers)}")
        app.logger.info(f"Raw Response: {response.text}")
        
        return response.json()
    except Exception as e:
        app.logger.error(f"Error: {str(e)}")
        return {"error": str(e)}
    
def send_to_klaviyo(subscription_data, webhook_data):
    """
    Envia os dados da assinatura para o Klaviyo como um evento
    """
    try:
        # Pega o status e converte para nome
        status_code = subscription_data.get('status')
        status_name = STATUS_MAP.get(status_code, f"Unknown ({status_code})")
        
        # Pega o primeiro produto (principal)
        products = subscription_data.get('products', [])
        main_product = products[0] if products else {}
        
        # Pega a primeira recorrência (mais recente)
        recurrences = subscription_data.get('recurrences', [])
        latest_recurrence = recurrences[-1] if recurrences else {}
        
        # Prepara as propriedades do evento
        event_properties = {
            "billing_cycle": BILLING_CYCLE_MAP.get(subscription_data.get('billing_cycle'), subscription_data.get('billing_cycle')),
            "cancellation_date": subscription_data.get('cancellation_date'),
            "effective_cancellation_date": subscription_data.get('effective_cancellation_date'),
            "next_billing_date": subscription_data.get('next_billing_date'),
            "number_recurrences": subscription_data.get('number_recurrences'),
            "subscription": subscription_data.get('subscription'),
            "product_sku": main_product.get('sku'),
            "payment_method": PAYMENT_METHOD_MAP.get(latest_recurrence.get('payment_method'), latest_recurrence.get('payment_method')),
            "order_status": ORDER_STATUS_MAP.get(latest_recurrence.get('order_status'), latest_recurrence.get('order_status')),
            "order": latest_recurrence.get('order'),
            "link": latest_recurrence.get('link'),
            "customer_name": subscription_data.get('customer_name'),
            "customer_phone": subscription_data.get('customer_phone'),
            "pix_rec_id": subscription_data.get('pix_rec_id'),
            "limit": subscription_data.get('limit')
        }
        
        # Remove campos None
        event_properties = {k: v for k, v in event_properties.items() if v is not None}
        
        # Prepara o payload do Klaviyo
        klaviyo_payload = {
            "data": {
                "type": "event",
                "attributes": {
                    "properties": event_properties,
                    "backfill": False,
                    "metric": {
                        "data": {
                            "type": "metric",
                            "attributes": {
                                "name": "Subscription " + status_name  # Usa o nome do status como nome do evento
                            }
                        }
                    },
                    "profile": {
                        "data": {
                            "type": "profile",
                            "attributes": {
                                "email": subscription_data.get('customer_email'),
                                "properties": {
                                    "Subscription Last Status": status_name,
                                    "Subscription Recorrency": subscription_data.get('number_recurrences'),
                                    "Subscription Type": BILLING_CYCLE_MAP.get(subscription_data.get('billing_cycle'), subscription_data.get('billing_cycle'))
                                    }
                            }
                        }
                    },
                    "value_currency": "BRL",
                    "value": float(subscription_data.get('amount_brl', 0)),
                    "time": datetime.now().isoformat()  # Data/hora atual em formato ISO
                }
            }
        }
        
        # Headers para a API do Klaviyo
        headers = {
            "Authorization": f"Klaviyo-API-Key {KLAVIYO_API_KEY}",
            "Content-Type": "application/json",
            "revision": "2025-01-15"  # Versão mais recente da API
        }
        
        # Log do que está sendo enviado
        app.logger.info(f"Enviando evento para Klaviyo: {status_name}")
        app.logger.debug(f"Payload Klaviyo: {klaviyo_payload}")
        
        # Envia para o Klaviyo
        response = requests.post(
            KLAVIYO_API_URL,
            json=klaviyo_payload,
            headers=headers,
            timeout=30
        )
        
        if response.status_code in [200, 201, 202]:
            app.logger.info(f"✅ Evento enviado com sucesso para Klaviyo")
            return {"success": True, "status_code": response.status_code, "response": response.json() if response.text else {}}
        else:
            app.logger.error(f"❌ Erro ao enviar para Klaviyo: {response.status_code} - {response.text}")
            return {"success": False, "status_code": response.status_code, "error": response.text}
            
    except Exception as e:
        app.logger.error(f"❌ Exceção ao enviar para Klaviyo: {str(e)}")
        return {"success": False, "error": str(e)}

@app.route('/webhook/pagbrasil', methods=['POST'])
def handle_webhook():
    try:
        webhook_data = request.get_json()
        
        if not webhook_data:
            return jsonify({'error': 'No JSON data received'}), 400
        
        app.logger.info(f"Webhook received: {webhook_data}")
        
        subscription_id = webhook_data.get('subscription')
        if not subscription_id:
            return jsonify({'error': 'No subscription ID in webhook'}), 400
        
        subscription_details = get_subscription_info(subscription_id)
        
        # 🔥 ENVIA PARA O KLAVIYO 🔥
        klaviyo_result = send_to_klaviyo(subscription_details, webhook_data)
        
        return jsonify({
            'status': 'success',
            'message': 'Webhook processed successfully',
            'subscription_id': subscription_id,
            'webhook_received': {
                'amount_brl': webhook_data.get('amount_brl'),
                'status': webhook_data.get('status'),
                'next_billing_date': webhook_data.get('next_billing_date')
            },
            'subscription_details': subscription_details,
            'klaviyo_integration': klaviyo_result
        }), 200
        
    except Exception as e:
        app.logger.error(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500




@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200

@app.route('/', methods=['GET'])
def root():
    return jsonify({
        'service': 'PagBrasil Webhook Handler',
        'version': '1.0.0',
        'endpoints': {
            'webhook': '/webhook/pagbrasil (POST)',
            'health': '/health (GET)',
            'test': '/test (GET)'
        }
    })

@app.route('/test', methods=['GET'])
def test_api():
    """Endpoint de teste direto"""
    test_subscription = "99fc3374f17ffaea"
    result = get_subscription_info(test_subscription)
    return jsonify({
        'test_subscription': test_subscription,
        'api_url': PAGBRASIL_API_URL,
        'result': result
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)