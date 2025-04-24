import subprocess
import os

def run_script(script_name):
    script_path = os.path.join(base_dir, script_name)
    try:
        result = subprocess.run(['python3', script_path], check=True)
        print(f"{script_name} executed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while executing {script_name}: {e}")

# Caminho base (diretório onde este script está localizado)
base_dir = os.path.dirname(os.path.abspath(__file__))

# Lista de scripts a serem executados sequencialmente
scripts = [
    'find_charge.py',
    'contact_manager.py',
    'send_mensage.py'
]

for script in scripts:
    run_script(script)
