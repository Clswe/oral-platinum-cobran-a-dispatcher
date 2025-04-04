import os
import requests
import json
import logging
from dotenv import load_dotenv

# Carrega as variáveis de ambiente a partir do arquivo .env
load_dotenv()

# Configuração do logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_URL = 'https://api.sendpulse.com/whatsapp/contacts'
BOT_ID = os.getenv('BOT_ID')
VARIABLE_ID_BOLETO = os.getenv('VARIABLE_ID_BOLETO')
VARIABLE_ID_DUE_DATE = os.getenv('VARIABLE_ID_DUE_DATE')

CONTACTS_FILE = 'dispatcher-charge-five-days/contatos/contacts.json'
IGNORED_FILE = 'ignored_boletos.json'


def get_access_token(client_id, secret_id):
    url = 'https://api.sendpulse.com/oauth/access_token'
    headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
    data = {'grant_type': 'client_credentials', 'client_id': client_id, 'client_secret': secret_id}
    
    response = requests.post(url, headers=headers, data=json.dumps(data))
    
    if response.status_code == 200:
        return response.json().get('access_token')
    
    logger.error(f'Erro ao obter o token de acesso. Status code: {response.status_code}')
    logger.error(f'Resposta da API: {response.text}')
    return None


def format_phone_number(phone_number):
    if not phone_number:
        return None
    phone_number = phone_number.replace(" ", "").replace("-", "")
    if phone_number.startswith("55"):
        phone_number = phone_number[2:]
    return "55" + phone_number


def check_contact_existence(phone_number, token):
    headers = {'Accept': 'application/json', 'Authorization': f'Bearer {token}'}
    params = {'phone': phone_number, 'bot_id': BOT_ID}
    
    response = requests.get(API_URL + '/getByPhone', headers=headers, params=params)
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success', False) and data.get('data', {}):
            contact_id = data['data']['id']
            logger.info(f'O número {phone_number} já existe na base. ID: {contact_id}')
            return contact_id
        return None
    elif response.status_code == 400:
        return None
    else:
        logger.error(f'Erro ao verificar contato. Status code: {response.status_code}')
        logger.error(f'Resposta da API: {response.text}')
        return None


def create_contact(phone_number, name, bot_id, token):
    headers = {'Accept': 'application/json', 'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    data = {'phone': phone_number, 'name': name, 'bot_id': bot_id}
    
    response = requests.post(API_URL, headers=headers, data=json.dumps(data))
    
    if response.status_code == 200:
        contact_id = response.json()['id']
        logger.info(f'Contato criado: {response.json()}')
        return contact_id
    
    logger.error(f'Erro ao criar contato. Status code: {response.status_code}')
    logger.error(f'Resposta da API: {response.text}')
    return None


def set_variable(contact_id, variable_id, variable_value, token):
    headers = {'Accept': 'application/json', 'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    data = {'contact_id': contact_id, 'variable_id': variable_id, 'variable_value': variable_value}
    
    response = requests.post(API_URL + '/setVariable', headers=headers, data=json.dumps(data))
    
    if response.status_code == 200:
        logger.info(f'Variável definida com sucesso para o contato {contact_id}. Valor: {variable_value}')
        return True
    
    logger.error(f'Erro ao definir variável para o contato {contact_id}. Status code: {response.status_code}')
    logger.error(f'Resposta da API: {response.text}')
    return False


def save_to_json(data, filename):
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def main():
    client_id = os.getenv('SENDPULSE_CLIENT_ID')
    client_secret = os.getenv('SENDPULSE_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        logger.error('As variáveis de ambiente CLIENT_ID e SECRET_ID não estão definidas')
        return
    
    token = get_access_token(client_id, client_secret)
    
    if not token:
        logger.error('Falha ao obter o token de acesso.')
        return
    
    json_file = 'dispatcher-charge-five-days/debitos/listDebit.json'
    
    if not os.path.exists(json_file):
        logger.error(f'O arquivo {json_file} não foi encontrado.')
        return
    
    with open(json_file, 'r', encoding='utf-8') as file:
        boletos = json.load(file)
    
    processed_contacts = []
    ignored_boletos = []
    
    for boleto in boletos:
        payer_phone = boleto.get('PayerPhone')
        payer_name = boleto.get('PayerName', 'Desconhecido')
        boleto_url = boleto.get('BoletoUrl')
        due_date = boleto.get('DueDate')
        
        # Verificação antes de formatar
        if not payer_phone:
            logger.warning(f'Boleto sem telefone. Nome: {payer_name}. Pulando...')
            ignored_boletos.append(boleto)
            continue
        
        phone_number = format_phone_number(payer_phone)
        
        # Verifica se o contato já existe
        contact_id = check_contact_existence(phone_number, token)
        
        # Se não existir, cria um novo
        if not contact_id:
            contact_id = create_contact(phone_number, payer_name, BOT_ID, token)
        
        # Se conseguiu obter um contact_id, define as variáveis
        if contact_id:
            set_variable(contact_id, VARIABLE_ID_BOLETO, boleto_url, token)
            set_variable(contact_id, VARIABLE_ID_DUE_DATE, due_date, token)
            
            processed_contacts.append({
                'contact_id': contact_id,
                'phone': phone_number,
                'name': payer_name,
                'boleto_url': boleto_url,
                'due_date': due_date
            })
            logger.info(f'Boleto processado para {payer_name} ({phone_number})')

    # Salva os contatos processados
    if processed_contacts:
        save_to_json(processed_contacts, CONTACTS_FILE)
        logger.info(f'Arquivo {CONTACTS_FILE} atualizado com {len(processed_contacts)} contatos.')

    # Salva os boletos ignorados
    if ignored_boletos:
        save_to_json(ignored_boletos, IGNORED_FILE)
        logger.warning(f'Arquivo {IGNORED_FILE} criado com {len(ignored_boletos)} boletos ignorados.')

    logger.info('Processamento concluído.')


if __name__ == '__main__':
    main()
