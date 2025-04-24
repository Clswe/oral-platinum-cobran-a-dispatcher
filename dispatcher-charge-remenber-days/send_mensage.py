import os
import json
import logging
import requests
from dotenv import load_dotenv
from datetime import datetime

# Carrega as variáveis de ambiente
load_dotenv()

FLOW_ID = os.getenv('FLOW_ID', '')  # Mantendo como string

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_auth_token(client_id, client_secret):
    """ Obtém o token de autenticação na API SendPulse """
    auth_url = 'https://api.sendpulse.com/oauth/access_token'
    auth_data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret
    }
    try:
        response = requests.post(auth_url, data=auth_data)
        response.raise_for_status()
        return response.json().get('access_token')
    except requests.exceptions.RequestException as e:
        logging.error(f'Erro ao obter token de autorização: {e}')
        return None

def format_due_date(due_date):
    """ Formata a data de vencimento para DD/MM/YYYY """
    try:
        return datetime.fromisoformat(due_date.replace("Z", "")).strftime('%d/%m/%Y')
    except ValueError:
        return 'Data inválida'

def send_whatsapp_message(contact_id, phone, name, boleto_url, due_date, token):
    """ Envia uma mensagem WhatsApp utilizando o template correto """
    try:
        send_message_url = 'https://api.sendpulse.com/whatsapp/contacts/sendTemplate'
        formatted_date = format_due_date(due_date)

        send_message_payload = {
            "contact_id": contact_id,
            "template": {
                "name": "lembrete_vencimento_fatura",
                "language": {
                    "policy": "deterministic",
                    "code": "pt_BR"
                },
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": name}
                        ]
                    },
                    {
                        "type": "button",
                        "sub_type": "quick_reply",
                        "index": 0,
                        "parameters": [
                            {
                                "type": "payload",
                                "payload": {
                                    "to_chain_id":"678705b4cfe336449105da5b"
                                }
                            }
                        ]
                    },
                    {
                        "type": "button",
                        "sub_type": "quick_reply",
                        "index": 1,
                        "parameters": [
                            {
                                "type": "payload",
                                "payload": {
                                    "to_chain_id": "6787060e316f5ff9830e5f33"
                                }
                            }
                        ]
                    }
                ]
            }
        }
        
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

        response = requests.post(send_message_url, headers=headers, json=send_message_payload)
        response.raise_for_status()
        logging.info(f'Mensagem enviada para {name} ({phone})')

        # 🔹 Chamada da API para iniciar o fluxo do WhatsApp
        flow_url = 'https://api.sendpulse.com/whatsapp/flows/run'
        flow_payload = {
            "contact_id": contact_id,
            "flow_id": FLOW_ID,
            "external_data": {"tracking_number": boleto_url}
        }
        flow_response = requests.post(flow_url, headers=headers, json=flow_payload)
        flow_response.raise_for_status()
        logging.info(f'Fluxo iniciado para {name} ({phone})')

    except requests.exceptions.RequestException as e:
        logging.error(f'Erro ao enviar mensagem ou iniciar fluxo para {name} ({phone}): {e}')

def main():
    """ Executa o envio de mensagens para todos os contatos no arquivo JSON """
    client_id = os.getenv('SENDPULSE_CLIENT_ID')
    client_secret = os.getenv('SENDPULSE_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        logging.error('Variáveis de ambiente SENDPULSE_CLIENT_ID e SENDPULSE_CLIENT_SECRET não definidas')
        return
    
    token = get_auth_token(client_id, client_secret)
    if not token:
        return
    
    contacts_file = 'dispatcher-charge-remenber-days/contatos/contacts.json'

    try:
        with open(contacts_file, 'r', encoding='utf-8') as file:
            contacts_data = json.load(file)
    except FileNotFoundError:
        logging.error(f'Arquivo {contacts_file} não encontrado')
        return
    except json.JSONDecodeError:
        logging.error(f'Erro ao ler o JSON de {contacts_file}')
        return
    
    for contact_info in contacts_data:
        contact_id = contact_info.get('contact_id')
        phone = contact_info.get('phone')
        name = contact_info.get('name', 'Cliente')
        boleto_url = contact_info.get('boleto_url', 'Sem link')
        due_date = contact_info.get('due_date', 'Sem data')

        if not contact_id or not phone:
            logging.warning(f'Contato inválido encontrado. Pulando...')
            continue
        
        send_whatsapp_message(contact_id, phone, name, boleto_url, due_date, token)

if __name__ == "__main__":
    main()
