import requests
import json
import logging
import os
from datetime import date, datetime, timedelta

# Configuração do logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constantes
API_URL = 'https://api.clinicorp.com/rest/v1/payment/list'
ACCEPT_HEADER = 'application/json'
AUTH_HEADER = 'Basic c29ycmlzb3NvZG9udG9sb2dpYToxZjNkMTA2MC0yNTJlLTQ4OTUtYjU2ZS1mNGYyYzliZDAwZDI='
OUTPUT_DIR = 'dispatcher-charge-ten-days/debitos'
OUTPUT_FILE = 'listDebit.json'

# Função para calcular os dias vencidos
def calculate_due_days(due_date):
    try:
        today = date.today()
        due_date_obj = datetime.strptime(due_date, '%Y-%m-%dT%H:%M:%S.%fZ').date()
        return (today - due_date_obj).days
    except ValueError as e:
        logger.error("Erro ao converter data: %s", e)
        return None

# Função para formatar número de telefone
def format_phone_number(phone):
    if phone:
        phone = ''.join(filter(str.isdigit, phone))
        if not phone.startswith('55'):
            phone = '55' + phone
        if len(phone) == 13 and phone.startswith('55'):
            phone = phone[:4] + phone[5:]  # Remove o primeiro zero após o DDD
        if len(phone) != 12:
            phone = phone.rjust(12, '0')
    return phone

# Função para obter pagamentos (ampliando o intervalo)
def get_monthly_payments():
    try:
        today = date.today()
        from_date = today - timedelta(days=60)  # Últimos 60 dias
        to_date = today

        params = {
            'subscriber_id': 'sorrisosodontologia',
            'from': from_date.strftime('%Y-%m-%d'),
            'to': to_date.strftime('%Y-%m-%d'),
            'search_type': 'DUE_DATE'
        }

        logger.info("Enviando requisição para: %s", API_URL)
        response = requests.get(API_URL, params=params, headers={'accept': ACCEPT_HEADER, 'Authorization': AUTH_HEADER})
        response.raise_for_status()
        
        data = response.json()
        logger.info("API retornou %d registros", len(data))
        return data if data else []
    except requests.exceptions.RequestException as e:
        logger.error("Erro na requisição: %s", e)
        return []

# Função para filtrar e salvar pagamentos (permitindo boletos vencidos há 30 dias ou mais)
def filter_and_save_payments():
    monthly_payments = get_monthly_payments()
    if monthly_payments:
        filtered_payments = []
        for payment in monthly_payments:
            due_date = payment.get('DueDate')
            if due_date:
                due_days = calculate_due_days(due_date)
                if 6 <= due_days <= 10:  # Aceita boletos vencidos há pelo menos 30 dias
                    payment['PayerPhone'] = format_phone_number(payment.get('PayerPhone'))
                    filtered_payments.append({
                        'PayerName': payment.get('PayerName'),
                        'ExternalStatus': payment.get('ExternalStatus'),
                        'BoletoUrl': payment.get('BoletoUrl'),
                        'PayerPhone': payment['PayerPhone'],
                        'DueDate': payment.get('DueDate'),
                        'DaysDue': due_days,
                        'BoletoDigitalLine': payment.get('BoletoDigitalLine')
                    })

        sorted_payments = sorted(filtered_payments, key=lambda x: x['DueDate'])

        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)

        try:
            with open(os.path.join(OUTPUT_DIR, OUTPUT_FILE), 'w') as file:
                json.dump(sorted_payments, file, indent=4, ensure_ascii=False)
                logger.info("Arquivo '%s' criado com sucesso. Total de registros: %d", OUTPUT_FILE, len(sorted_payments))
        except Exception as e:
            logger.error("Erro ao salvar os dados: %s", e)
    else:
        logger.warning("Nenhum pagamento encontrado.")

# Função principal
def main():
    filter_and_save_payments()

if __name__ == "__main__":
    main()
