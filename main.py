import pygame
import sys
import os

# Importa a engine do NEAT
from NEAT.neat_train import run_neat

def show_gallery(screen, clock):
    import checkpoint_manager
    import neat
    
    font_title = pygame.font.SysFont("courier new", 50, bold=True)
    font_item = pygame.font.SysFont("courier new", 28)
    font_small = pygame.font.SysFont("courier new", 20)
    
    files = checkpoint_manager.list_checkpoints()
    selected_idx = 0
    
    SCREEN_WIDTH = screen.get_width()
    SCREEN_HEIGHT = screen.get_height()
    
    running = True
    while running:
        screen.fill((247, 247, 247))
        
        title_surf = font_title.render("GALERIA DE CAMPEÕES", True, (83, 83, 83))
        screen.blit(title_surf, (SCREEN_WIDTH//2 - title_surf.get_width()//2, 50))
        
        if not files:
            msg = font_item.render("Nenhum checkpoint encontrado na pasta /checkpoints", True, (150, 50, 50))
            screen.blit(msg, (SCREEN_WIDTH//2 - msg.get_width()//2, 200))
        else:
            y_offset = 150
            for i, f in enumerate(files):
                if i == selected_idx:
                    color = (50, 150, 50)
                    prefix = ">> "
                else:
                    color = (100, 100, 100)
                    prefix = "   "
                    
                item_surf = font_item.render(f"{prefix}{f}", True, color)
                screen.blit(item_surf, (SCREEN_WIDTH//2 - 300, y_offset))
                y_offset += 40
                
        help_surf = font_small.render("[SETAS] Selecionar   |   [ENTER] Carregar   |   [ESC] Voltar", True, (120, 120, 120))
        screen.blit(help_surf, (SCREEN_WIDTH//2 - help_surf.get_width()//2, SCREEN_HEIGHT - 50))
        
        pygame.display.flip()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return
                if files:
                    if event.key == pygame.K_UP:
                        selected_idx = max(0, selected_idx - 1)
                    elif event.key == pygame.K_DOWN:
                        selected_idx = min(len(files) - 1, selected_idx + 1)
                    elif event.key == pygame.K_RETURN:
                        # Load file and start endless mode
                        filepath = os.path.join(checkpoint_manager.CHECKPOINTS_DIR, files[selected_idx])
                        ai_type, model_payload, env_state = checkpoint_manager.load_checkpoint(filepath)
                        
                        from Jogo.dino_env import DinoGame
                        import torch
                        import numpy as np
                        
                        champion_ai = None
                        
                        if ai_type == "NEAT":
                            # Load NEAT config
                            local_dir = os.path.dirname(__file__)
                            config_path = os.path.join(local_dir, 'NEAT', 'config-feedforward.txt')
                            config = neat.config.Config(neat.DefaultGenome, neat.DefaultReproduction,
                                                        neat.DefaultSpeciesSet, neat.DefaultStagnation,
                                                        config_path)
                                                        
                            # Detect if it was trained with 8 or 10 inputs
                            is_bazooka = env_state.get('use_bazooka', True)
                            if not is_bazooka:
                                config.genome_config.num_inputs = 8
                                config.genome_config.num_outputs = 3
                                config.genome_config.input_keys = [-i for i in range(1, 9)]
                                config.genome_config.output_keys = [i for i in range(3)]
                                
                            net = neat.nn.FeedForwardNetwork.create(model_payload, config)
                            def champion_ai(state):
                                output = net.activate(state)
                                return output.index(max(output))
                            env = DinoGame(render=True, unlimited_speed=False, use_bazooka=is_bazooka)
                            
                        elif ai_type == "DQN":
                            from DQN.agent import DQNAgent
                            dummy_agent = DQNAgent()
                            dummy_agent.model.load_state_dict(model_payload['model_state'])
                            dummy_agent.model.eval()
                            def champion_ai(state):
                                state_t = torch.tensor(state, dtype=torch.float)
                                return torch.argmax(dummy_agent.model(state_t)).item()
                            env = DinoGame(render=True, unlimited_speed=False, use_bazooka=False)
                            
                        elif ai_type == "PPO":
                            from PPO.agent import PPOAgent
                            dummy_agent = PPOAgent(8, 3, 0, 0, 0, 0)
                            dummy_agent.policy.load_state_dict(model_payload['policy_state'])
                            dummy_agent.policy.eval()
                            def champion_ai(state):
                                state_t = torch.FloatTensor(state).unsqueeze(0)
                                action_probs = dummy_agent.policy.actor(state_t)
                                return torch.argmax(action_probs, dim=-1).item()
                            env = DinoGame(render=True, unlimited_speed=False, use_bazooka=False)
                            
                        # Toca o Replay Glorioso uma vez!
                        env.play_champion_endless(champion_ai, str(env_state.get('generation', 0)), "", checkpoint_state=env_state, play_once=True)
                        
                        # Após morrer, retoma o treinamento a partir daquele ponto
                        pygame.quit()
                        
                        if ai_type == "NEAT":
                            from NEAT.neat_train import run_neat
                            run_neat(config_path, custom_pop_size=None, unlimited_speed=False, human_in_loop=False, use_bazooka=env_state.get('use_bazooka', True), initial_genome=model_payload, initial_state=env_state)
                        elif ai_type == "DQN":
                            from DQN.dqn_train import run_dqn
                            run_dqn(unlimited_speed=False, initial_model_payload=model_payload, initial_state=env_state)
                        elif ai_type == "PPO":
                            from PPO.ppo_train import run_ppo
                            run_ppo(unlimited_speed=False, initial_model_payload=model_payload, initial_state=env_state)
                            
                        sys.exit(0)

        clock.tick(60)

def show_menu():
    pygame.init()
    
    # Aproveita as mesmas dimensões da tela de treinamento
    SCREEN_WIDTH = 1400
    SCREEN_HEIGHT = 700
    
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE | pygame.SCALED)
    pygame.display.set_caption("Dino AI - Menu Principal")
    clock = pygame.time.Clock()
    
    font_title = pygame.font.SysFont("courier new", 70, bold=True)
    font_menu = pygame.font.SysFont("courier new", 32, bold=True)
    font_small = pygame.font.SysFont("courier new", 22)
    
    pop_size = 20
    unlimited_speed = False
    use_bazooka = True
    
    while True:
        # Fundo limpo
        screen.fill((247, 247, 247))
        
        # ── TÍTULO ──
        title_surf = font_title.render("DINO AI - HUB PRINCIPAL", True, (83, 83, 83))
        screen.blit(title_surf, (SCREEN_WIDTH//2 - title_surf.get_width()//2, 50))
        
        # ── OPÇÕES DE IA ──
        opt1 = font_menu.render("[1] Iniciar NEAT (Algoritmo Genético)", True, (50, 150, 50))
        opt2 = font_menu.render("[2] Iniciar DQN (Deep Q-Network)", True, (50, 100, 200))
        opt3 = font_menu.render("[3] Iniciar PPO (Proximal Policy)", True, (200, 100, 50))
        opt4 = font_menu.render("[4] Jogador Humano", True, (0, 150, 0))
        opt5 = font_menu.render("[5] Duelo: Humano vs IA Campeã", True, (150, 0, 150))
        opt6 = font_menu.render("[6] Treino Interativo: Humano + Enxame NEAT", True, (200, 150, 0))
        opt7 = font_menu.render("[7] Galeria de Campeões (Carregar Checkpoint)", True, (255, 140, 0))
        
        screen.blit(opt1, (SCREEN_WIDTH//2 - opt1.get_width()//2, 110))
        screen.blit(opt2, (SCREEN_WIDTH//2 - opt2.get_width()//2, 155))
        screen.blit(opt3, (SCREEN_WIDTH//2 - opt3.get_width()//2, 200))
        screen.blit(opt4, (SCREEN_WIDTH//2 - opt4.get_width()//2, 245))
        screen.blit(opt5, (SCREEN_WIDTH//2 - opt5.get_width()//2, 290))
        screen.blit(opt6, (SCREEN_WIDTH//2 - opt6.get_width()//2, 335))
        screen.blit(opt7, (SCREEN_WIDTH//2 - opt7.get_width()//2, 380))
        
        # ── SELETOR DINÂMICO DE POPULAÇÃO ──
        pop_surf = font_menu.render(f"População NEAT: < {pop_size} dinossauros >", True, (50, 50, 200))
        screen.blit(pop_surf, (SCREEN_WIDTH//2 - pop_surf.get_width()//2, 450))
        
        help_surf = font_small.render("(Use <- e -> para alterar a quantidade)", True, (120, 120, 120))
        screen.blit(help_surf, (SCREEN_WIDTH//2 - help_surf.get_width()//2, 480))
        
        # ── SELETOR DE LIMITE DE VELOCIDADE ──
        vel_text = "ILIMITADA (Infinita)" if unlimited_speed else "LIMITADA (13.0 MAX)"
        speed_surf = font_menu.render(f"Velocidade: [ {vel_text} ]", True, (200, 100, 50))
        screen.blit(speed_surf, (SCREEN_WIDTH//2 - speed_surf.get_width()//2, 530))
        
        speed_help_surf = font_small.render("(Use setas CIMA e BAIXO para alternar)", True, (120, 120, 120))
        screen.blit(speed_help_surf, (SCREEN_WIDTH//2 - speed_help_surf.get_width()//2, 560))

        # ── SELETOR DE MODO DE JOGO (BAZUCA) ──
        baz_text = "COM BAZUCA (Missil + Cacto Gigante)" if use_bazooka else "SEM BAZUCA (Original)"
        baz_surf = font_menu.render(f"Modo: [ {baz_text} ]", True, (255, 100, 100))
        screen.blit(baz_surf, (SCREEN_WIDTH//2 - baz_surf.get_width()//2, 590))
        
        baz_help_surf = font_small.render("(Pressione 'B' para alternar o Modo de Jogo)", True, (120, 120, 120))
        screen.blit(baz_help_surf, (SCREEN_WIDTH//2 - baz_help_surf.get_width()//2, 620))
        
        esc_surf = font_small.render("[ESC] Sair", True, (200, 50, 50))
        screen.blit(esc_surf, (SCREEN_WIDTH//2 - esc_surf.get_width()//2, 650))
        
        pygame.display.flip()
        
        # ── CAPTURA DE EVENTOS ──
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)
                
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit(0)
                    
                # Aumenta a população (máx 100)
                elif event.key == pygame.K_RIGHT:
                    # Se for 1, pula direto para 10 para arredondar. Senão sobe de 10 em 10.
                    if pop_size == 1:
                        pop_size = 10
                    else:
                        pop_size = min(100, pop_size + 10)
                        
                # Diminui a população (mín 10)
                elif event.key == pygame.K_LEFT:
                    if pop_size <= 20:
                        pop_size = 10
                    else:
                        pop_size = max(10, pop_size - 10)
                        
                # Alternar Limite de Velocidade
                elif event.key == pygame.K_UP or event.key == pygame.K_DOWN:
                    unlimited_speed = not unlimited_speed
                        
                # Alternar Bazuca
                elif event.key == pygame.K_b:
                    use_bazooka = not use_bazooka
                        
                # Inicia o Modo NEAT
                elif event.key == pygame.K_1:
                    pygame.quit()
                    local_dir = os.path.dirname(__file__)
                    config_path = os.path.join(local_dir, 'NEAT', 'config-feedforward.txt')
                    run_neat(config_path, custom_pop_size=pop_size, unlimited_speed=unlimited_speed, human_in_loop=False, use_bazooka=use_bazooka)
                    sys.exit(0)
                    
                # Inicia o Modo DQN
                elif event.key == pygame.K_2:
                    pygame.quit()
                    from DQN.dqn_train import run_dqn
                    run_dqn(unlimited_speed=unlimited_speed)
                    sys.exit(0)
                    
                # Inicia o Modo PPO
                elif event.key == pygame.K_3:
                    pygame.quit()
                    from PPO.ppo_train import run_ppo
                    run_ppo(unlimited_speed=unlimited_speed)
                    sys.exit(0)
                    
                # Inicia o Modo NEAT Interativo
                elif event.key == pygame.K_6:
                    pygame.quit()
                    local_dir = os.path.dirname(__file__)
                    config_path = os.path.join(local_dir, 'NEAT', 'config-feedforward.txt')
                    run_neat(config_path, custom_pop_size=pop_size, unlimited_speed=unlimited_speed, human_in_loop=True, use_bazooka=use_bazooka)
                    sys.exit(0)
                    
                # Abre a Galeria de Campeões
                elif event.key == pygame.K_7:
                    show_gallery(screen, clock)
                    
                # Inicia Modo Humano
                elif event.key == pygame.K_4:
                    from Jogo.dino_env import DinoGame
                    env = DinoGame(render=True, unlimited_speed=unlimited_speed, use_bazooka=use_bazooka)
                    env.play_human_mode()
                    # Ao retornar, reestabelece a janela do menu
                    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE | pygame.SCALED)
                    pygame.display.set_caption("Dino AI - Menu Principal")
                    
                # Inicia Modo Torneio
                elif event.key == pygame.K_5:
                    from Jogo.dino_env import DinoGame
                    import torch
                    
                    champions = {}
                    local_dir = os.path.dirname(__file__)
                    
                    # Carrega NEAT
                    try:
                        from NEAT.neat_train import load_champion
                        config_path = os.path.join(local_dir, 'NEAT', 'config-feedforward.txt')
                        champions['NEAT'] = load_champion(config_path)
                    except Exception as e:
                        pass
                        
                    # Carrega DQN
                    try:
                        from DQN.model import Linear_QNet
                        dqn_model = Linear_QNet(6, 64, 3)
                        dqn_model.load_state_dict(torch.load('dqn_model.pth', weights_only=True))
                        dqn_model.eval()
                        champions['DQN'] = dqn_model
                    except Exception as e:
                        pass
                        
                    # Carrega PPO
                    try:
                        from PPO.agent import PPOAgent
                        # lr e outros hyps não importam só pra inferência, mas precisamos instanciar
                        ppo_agent = PPOAgent(state_dim=6, action_dim=3, lr=0.0003, gamma=0.99, K_epochs=4, eps_clip=0.2)
                        checkpoint = torch.load('ppo_model.pth', weights_only=True)
                        ppo_agent.policy.load_state_dict(checkpoint['policy'])
                        ppo_agent.policy.eval()
                        ppo_agent.policy_old.load_state_dict(checkpoint['policy_old'])
                        ppo_agent.policy_old.eval()
                        champions['PPO'] = ppo_agent
                    except Exception as e:
                        pass
                        
                    env = DinoGame(render=True, unlimited_speed=unlimited_speed, use_bazooka=use_bazooka)
                    env.play_tournament_mode(champions)
                    
                    # Ao retornar, reestabelece a janela do menu
                    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE | pygame.SCALED)
                    pygame.display.set_caption("Dino AI - Menu Principal")
                    
        # Mantém leve (60 frames é suficiente e nao gasta CPU)
        clock.tick(60)

if __name__ == "__main__":
    show_menu()
