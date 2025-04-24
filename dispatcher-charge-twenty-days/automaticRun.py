import subprocess

def run_script(script_name):
    try:
        result = subprocess.run(['python3', script_name], check=True)
        print(f"{script_name} executed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while executing {script_name}: {e}")

# Lista de scripts a serem executados sequencialmente
scripts = ['dispatcher-charge-twenty-days/find_charge.py', 'dispatcher-charge-twenty-days/contact_manager.py', 'dispatcher-charge-twenty-days/send_mensage.py']

for script in scripts:
    run_script(script)