import json
import os
import mtranslate as mt
from dotenv import load_dotenv

# Define GROQ_API using the config logic from jarvis.py
def get_api():
    try:
        with open('config/config.json') as config_file:
            config = json.load(config_file)
            API = config.get('GROQ_API')
            if API is None:
                raise ValueError("GROQ_API URL not found in config file")
            return API
    except Exception as e:
        print(f"Error reading config file: {e}")
    return None

os.environ['GROQ_API'] = get_api()
load_dotenv()

# We must import these after setting up os.environ['GROQ_API']
from backend.modules.automodel import Operate
from backend.modules.basic.listenpy import Listen

InputLanguage = os.environ.get('InputLanguage', 'pt-br')

def UniversalTranslator(Text: str) -> str:
    if not Text: return ""
    english_translation = mt.translate(Text, 'en', 'auto')
    return english_translation.capitalize()

def main():
    print("=" * 50)
    print("Iniciando JARVIS no Terminal...")
    print("Diga algo no microfone para enviar comandos.")
    print("Diga 'desligar' ou 'sair' para encerrar.")
    print("=" * 50)
    
    while True:
        try:
            print("\nAguardando comando de voz...")
            text = Listen()
            
            if text:
                text_lower = text.lower()
                # Verification to exit the loop
                if any(word in text_lower for word in ['desligar', 'sair', 'fechar', 'parar', 'exit', 'quit', 'stop']):
                    print("Desligando JARVIS...")
                    break
                
                Query = UniversalTranslator(text) if 'en' not in InputLanguage.lower() else text.capitalize()
                print(f"Processando comando traduzido: {Query}")
                
                Decision = Operate(Query)
                print(f"JARVIS concluiu a tarefa. Tag(s) operadas: {Decision}")
                
        except KeyboardInterrupt:
            print("\nDesligando JARVIS (interrompido pelo usuário)...")
            break
        except Exception as e:
            print(f"\nErro inesperado: {e}")

if __name__ == '__main__':
    main()
