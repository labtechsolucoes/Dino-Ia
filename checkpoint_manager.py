import os
import pickle
import time

CHECKPOINTS_DIR = os.path.join(os.path.dirname(__file__), "checkpoints")

def save_checkpoint(filename, ai_type, model_payload, env_state, is_auto=False):
    """
    Salva o modelo da IA (seja genoma do NEAT ou estado do DQN/PPO) junto com as variáveis 
    exatas da interface no momento do save (tempos, ranking, recordes).
    """
    if not os.path.exists(CHECKPOINTS_DIR):
        os.makedirs(CHECKPOINTS_DIR)

    # Se for auto, colocamos um sufixo
    if is_auto:
        if ai_type == "NEAT":
            filename = f"{filename}_auto_gen{env_state.get('generation', 0)}"
        else:
            # DQN e PPO usam episódios (n_games) guardados na mesma variável "generation" para a UI
            filename = f"{filename}_auto_ep{env_state.get('generation', 0)}"

    filepath = os.path.join(CHECKPOINTS_DIR, f"{filename}.pkl")

    data = {
        "ai_type": ai_type,
        "genome": model_payload, # mantemos a chave 'genome' por retrocompatibilidade no arquivo, mas ela guarda o payload
        "env_state": env_state,
        "timestamp": time.time()
    }

    with open(filepath, "wb") as f:
        pickle.dump(data, f)
        
    return filepath

def load_checkpoint(filepath):
    """
    Carrega o arquivo .pkl do checkpoint e retorna (ai_type, model_payload, env_state).
    Para saves antigos que não tinham ai_type, assume-se "NEAT".
    """
    with open(filepath, "rb") as f:
        data = pickle.load(f)
        
    ai_type = data.get("ai_type", "NEAT")
    model_payload = data.get("genome") # Puxamos do genome por retrocompatibilidade
    env_state = data.get("env_state", {})
    
    return ai_type, model_payload, env_state

def list_checkpoints():
    """
    Lista todos os arquivos .pkl disponíveis na pasta /checkpoints, ordenados do mais novo pro mais antigo.
    """
    if not os.path.exists(CHECKPOINTS_DIR):
        return []
        
    files = [f for f in os.listdir(CHECKPOINTS_DIR) if f.endswith(".pkl")]
    # Ordenar por data de modificação
    files.sort(key=lambda x: os.path.getmtime(os.path.join(CHECKPOINTS_DIR, x)), reverse=True)
    return files
