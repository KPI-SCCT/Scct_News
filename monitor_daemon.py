# monitor_daemon.py
import sys
import os
import time
import subprocess

# Adiciona a pasta raiz ao PATH para encontrar os módulos
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from config import LOGS_DIR

FLAG_FILE = os.path.join(LOGS_DIR, 'trigger_monitor.flag')

def main():
    print("🛡️  Vigia do Monitor iniciado. Pressione CTRL+C para parar.")
    print(f"👀 Vigilando o sinalizador em: {FLAG_FILE}")

    while True:
        try:
            # Verifica se o arquivo de sinalizador existe
            if os.path.exists(FLAG_FILE):
                print("🚀 Sinalizador detectado! Iniciando o monitoramento...")
                
                # Apaga o sinalizador para não executar de novo
                os.remove(FLAG_FILE)
                
                # Executa o script de monitoramento como um subprocesso
                # Usamos 'python -m' para manter a consistência
                parent_dir = os.path.dirname(PROJECT_ROOT)
                command = [sys.executable, '-m', 'Scct_News.monitor']
                subprocess.run(command, cwd=parent_dir)
                
                print("✅ Ciclo de monitoramento concluído. Voltando a vigiar...")
            
            # Espera 5 segundos antes de verificar novamente
            time.sleep(5)

        except KeyboardInterrupt:
            print("\n🛑 Vigia do Monitor interrompido pelo usuário.")
            break
        except Exception as e:
            print(f"❌ Ocorreu um erro no vigia: {e}. Continuando a vigiar...")

if __name__ == '__main__':
    main()