import os
import neat
import sys
import pickle

# Adiciona o diretório raiz ao sys.path para conseguir importar Jogo.dino_env
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Jogo.dino_env import DinoGame

# Variável global para rastrear a geração atual
GERACAO_ATUAL = 0

class SaveAndExit(Exception): 
    def __init__(self, genome, env_state):
        self.genome = genome
        self.env_state = env_state

# Inicia o ambiente globalmente para manter o histórico e a janela abertos fluidamente
env = None
UNLIMITED_SPEED = False
HUMAN_IN_LOOP = False
USE_BAZOOKA = True

def eval_genomes(genomes, config):
    global GERACAO_ATUAL, env, UNLIMITED_SPEED, HUMAN_IN_LOOP, USE_BAZOOKA
    if env is None:
        env = DinoGame(render=True, unlimited_speed=UNLIMITED_SPEED, use_bazooka=USE_BAZOOKA)
    GERACAO_ATUAL += 1
    
    ai_list = []
    # 1. Cria a função interpretadora para cada DNA
    for genome_id, genome in genomes:
        # Cria a rede neural feed-forward baseada no genoma
        net = neat.nn.FeedForwardNetwork.create(genome, config)
        
        # Como o NEAT avalia todos os dinos no mesmo loop, precisamos de uma closure
        def make_predict(neural_net):
            def predict_func(state):
                # Ativa a rede passando os 8 inputs do estado atual do Dino
                output = neural_net.activate(state)
                # Retorna a ação, outputs brutos e valores internos de TODOS os neurônios
                return output.index(max(output)), output, neural_net.values
            return predict_func
            
        ai_list.append(make_predict(net))
        
    # 2. Roda a simulação com toda a população na mesma tela!
    # Passamos os IDs dos genomas como labels para aparecerem bonitinhos na HUD
    labels = [str(genome_id) for genome_id, genome in genomes]
    results = env.play_population_mode(ai_list, generation=GERACAO_ATUAL, labels=labels, human_in_loop=HUMAN_IN_LOOP) 
    
    import time
    import checkpoint_manager

    # 3. Atribui o fitness de sobrevivência de volta ao DNA do NEAT
    scores = results['scores'][:len(genomes)] if HUMAN_IN_LOOP else results['scores']
    for i, (genome_id, genome) in enumerate(genomes):
        genome.fitness = scores[i]

    best_genome = max(genomes, key=lambda x: x[1].fitness)[1]
    env_state = {
        'generation': GERACAO_ATUAL,
        'start_time_offset': time.time() - env.start_time,
        'total_simulated_frames': env.total_simulated_frames,
        'hi_score': env.hi_score,
        'hi_speed': getattr(env, 'hi_speed', 0.0),
        'history_best_scores': env.history_best_scores,
        'history_best_speeds': getattr(env, 'history_best_speeds', []),
        'history_avg_scores': env.history_avg_scores,
        'use_bazooka': USE_BAZOOKA
    }

    if GERACAO_ATUAL % 10 == 0:
        saved_path = checkpoint_manager.save_checkpoint("neat_checkpoint", "NEAT", best_genome, env_state, is_auto=True)
        print(f"\n[AUTO-SAVE] Checkpoint da Geração {GERACAO_ATUAL} salvo em: {saved_path}")

    if results.get("save_and_exit"):
        raise SaveAndExit(best_genome, env_state)

def run_neat(config_file, custom_pop_size=None, unlimited_speed=False, human_in_loop=False, use_bazooka=True, initial_genome=None, initial_state=None):
    global UNLIMITED_SPEED, HUMAN_IN_LOOP, USE_BAZOOKA
    UNLIMITED_SPEED = unlimited_speed
    HUMAN_IN_LOOP = human_in_loop
    USE_BAZOOKA = use_bazooka
    
    # Carrega a configuração
    config = neat.config.Config(neat.DefaultGenome, neat.DefaultReproduction,
                                neat.DefaultSpeciesSet, neat.DefaultStagnation,
                                config_file)
                                
    # Adapta a rede neural dinamicamente se a bazuca estiver desativada
    if not USE_BAZOOKA:
        config.genome_config.num_inputs = 8
        config.genome_config.num_outputs = 3
        config.genome_config.input_keys = [-i for i in range(1, 9)]
        config.genome_config.output_keys = [i for i in range(3)]

    # Injeção Dinâmica da População (vinda do Menu Principal)
    if custom_pop_size is not None:
        config.pop_size = custom_pop_size - 1 if human_in_loop else custom_pop_size

    # Cria a população principal baseada na configuração
    p = neat.Population(config)
    
    # Seeding (Clonagem do Campeão)
    if initial_genome is not None:
        import copy
        for genome in p.population.values():
            genome.connections = copy.deepcopy(initial_genome.connections)
            genome.nodes = copy.deepcopy(initial_genome.nodes)
            
    # Restaurar estado da interface/Engine se houver
    global GERACAO_ATUAL, env
    if initial_state is not None:
        GERACAO_ATUAL = initial_state.get('generation', 0)
        # Forçamos a criação do env para podermos injetar o histórico antes da primeira avaliação
        env = DinoGame(render=True, unlimited_speed=UNLIMITED_SPEED, use_bazooka=USE_BAZOOKA)
        env.generation = GERACAO_ATUAL
        env.hi_score = initial_state.get('hi_score', 0)
        env.hi_speed = initial_state.get('hi_speed', 0.0)
        env.history_best_scores = initial_state.get('history_best_scores', [])
        env.history_best_speeds = initial_state.get('history_best_speeds', [])
        env.history_avg_scores = initial_state.get('history_avg_scores', [])
        
        import time
        offset = initial_state.get('start_time_offset', 0)
        env.start_time = time.time() - offset
        env.total_simulated_frames = initial_state.get('total_simulated_frames', 0)

    # Adiciona repórteres para vermos o progresso no terminal
    p.add_reporter(neat.StdOutReporter(True))
    stats = neat.StatisticsReporter()
    p.add_reporter(stats)

    # Roda o algoritmo por até 100000 gerações (praticamente infinito, até atingir o fitness_threshold)
    print("Iniciando Treinamento NEAT...")
    try:
        winner = p.run(eval_genomes, 100000)
        print('\nMelhor genoma encontrado:\n{!s}'.format(winner))
        
        with open("best_neat_ai.pkl", "wb") as f:
            pickle.dump(winner, f)
        print("✅ IA Campeã salva em 'best_neat_ai.pkl' na raiz do projeto!")
        
        # Mostra a tela de campeã antes de fechar!
        if env is not None:
            import time
            net = neat.nn.FeedForwardNetwork.create(winner, config)
            def champion_ai(state):
                output = net.activate(state)
                return output.index(max(output))
            
            elapsed = time.time() - env.start_time
            tot_min, tot_sec = divmod(int(elapsed), 60)
            tot_hr, tot_min = divmod(tot_min, 60)
            time_str = f"{tot_hr}h {tot_min}m {tot_sec}s"
            
            env.play_champion_endless(champion_ai, str(GERACAO_ATUAL), time_str)
    except SaveAndExit as e:
        print("\n" + "="*50)
        print("SIMULAÇÃO INTERROMPIDA PARA SALVAMENTO")
        print("="*50)
        nome = input("Digite o nome para o arquivo de save (ex: treino_dia1): ")
        if not nome:
            nome = "checkpoint"
            
        e.env_state['use_bazooka'] = USE_BAZOOKA
        import checkpoint_manager
        saved_path = checkpoint_manager.save_checkpoint(nome, "NEAT", e.genome, e.env_state, is_auto=False)
        print(f"\n✅ Checkpoint manual salvo com sucesso! Arquivo: {saved_path}")
        print("Você poderá carregar esse arquivo no futuro pela opção Galeria de Campeões.")
        
        import pygame
        pygame.quit()
        sys.exit(0)

def load_champion(config_file):
    config = neat.config.Config(neat.DefaultGenome, neat.DefaultReproduction,
                                neat.DefaultSpeciesSet, neat.DefaultStagnation,
                                config_file)
    with open("best_neat_ai.pkl", "rb") as f:
        winner = pickle.load(f)
    return neat.nn.FeedForwardNetwork.create(winner, config)

if __name__ == '__main__':
    local_dir = os.path.dirname(__file__)
    config_path = os.path.join(local_dir, 'config-feedforward.txt')
    run_neat(config_path)
