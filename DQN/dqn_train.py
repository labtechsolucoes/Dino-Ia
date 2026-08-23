import os
import sys
import torch
import pygame
import time
import numpy as np

# Adiciona o diretório raiz ao sys.path para conseguir importar Jogo.dino_env
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Jogo.dino_env import DinoGame, BG_COLOR, ACTION_NONE, ACTION_JUMP, ACTION_DUCK, MAX_SPEED
from DQN.agent import DQNAgent

def run_dqn(unlimited_speed=False, initial_model_payload=None, initial_state=None):
    # Força use_bazooka=False pois a arquitetura do DQN está fixa em 8 inputs e 3 outputs
    env = DinoGame(render=True, unlimited_speed=unlimited_speed, use_bazooka=False)
    agent = DQNAgent()
    
    import checkpoint_manager
    
    # Se carregou via Galeria
    if initial_model_payload is not None:
        agent.model.load_state_dict(initial_model_payload['model_state'])
        agent.trainer.optimizer.load_state_dict(initial_model_payload['optimizer_state'])
        agent.n_games = initial_model_payload.get('n_games', 0)
        agent.epsilon = initial_model_payload.get('epsilon', 1.0)
        agent.model.train() # Garante modo treino
        
        if initial_state is not None:
            env.generation = initial_state.get('generation', agent.n_games)
            env.hi_score = initial_state.get('hi_score', 0)
            env.hi_speed = initial_state.get('hi_speed', 0.0)
            env.history_best_scores = initial_state.get('history_best_scores', [])
            env.history_best_speeds = initial_state.get('history_best_speeds', [])
            env.history_avg_scores = initial_state.get('history_avg_scores', [])
            env.total_simulated_frames = initial_state.get('total_simulated_frames', 0)
            offset = initial_state.get('start_time_offset', 0)
            env.start_time = time.time() - offset
            
    # Try to load existing local model if not loaded from gallery
    else:
        model_path = os.path.join(os.path.dirname(__file__), 'dqn_model.pth')
        if os.path.exists(model_path):
            print("Carregando modelo DQN existente (dqn_model.pth)...")
            agent.model.load_state_dict(torch.load(model_path, weights_only=True))
            agent.model.eval()
            agent.n_games = 50 

    record = env.hi_score if hasattr(env, 'hi_score') else 0
    training_start = env.start_time if hasattr(env, 'start_time') else time.time()
    episode_start = time.time()
    
    env.reset()
    state_old = agent.get_state(env)
    
    running = True
    score_at_max_speed = None  # Rastreia quando a velocidade máxima foi atingida
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_t:
                    env.turbo_mode = not getattr(env, 'turbo_mode', False)
                if event.key == pygame.K_ESCAPE:
                    elapsed = time.time() - training_start
                    menu_action = env._show_pause_menu(agent.n_games, record, len(agent.memory), agent.memory.maxlen, elapsed, mode="DQN")
                    if menu_action == "SAVE":
                        env_state = {
                            'generation': agent.n_games,
                            'start_time_offset': time.time() - training_start,
                            'total_simulated_frames': env.total_simulated_frames,
                            'hi_score': env.hi_score,
                            'hi_speed': getattr(env, 'hi_speed', 0.0),
                            'history_best_scores': env.history_best_scores,
                            'history_best_speeds': getattr(env, 'history_best_speeds', []),
                            'history_avg_scores': env.history_avg_scores
                        }
                        payload = {
                            'model_state': agent.model.state_dict(),
                            'optimizer_state': agent.trainer.optimizer.state_dict(),
                            'n_games': agent.n_games,
                            'epsilon': agent.epsilon
                        }
                        
                        import checkpoint_manager
                        saved_path = checkpoint_manager.save_checkpoint("dqn_checkpoint", "DQN", payload, env_state, is_auto=False)
                        print("\n" + "="*50)
                        print(f"✅ SIMULAÇÃO INTERROMPIDA! Modelo DQN salvo em '{saved_path}'")
                        print("="*50 + "\n")
                        running = False
                        pygame.quit()
                        sys.exit(0)

        if not running:
            break

        # Pega a ação do agente baseada no estado atual
        final_move = agent.get_action(state_old)
        
        # Mapeamento do final_move (0: Run, 1: Jump, 2: Duck)
        action = ACTION_NONE
        if final_move == 1:
            action = ACTION_JUMP
        elif final_move == 2:
            action = ACTION_DUCK

        # Avança 1 frame na simulação
        state_new_tuple, reward, done, score = env.play_step(action)
        state_new = np.array(state_new_tuple, dtype=float)
        
        # Marca o score quando a velocidade máxima é atingida pela primeira vez
        if env.game_speed >= MAX_SPEED and score_at_max_speed is None:
            score_at_max_speed = env.score
        
        # Treina memória curta (passo atual)
        agent.train_short_memory(state_old, final_move, reward, state_new, done)
        
        # Armazena na memória longa
        agent.remember(state_old, final_move, reward, state_new, done)
        
        state_old = state_new
        
        # ── Renderização da Tela ──
        if not getattr(env, 'turbo_mode', False) or env.frame_count % 10 == 0:
            env.display.fill(BG_COLOR)
            for c in env.clouds: c.draw(env.display)
            env._draw_ground()
            for obs in env.obstacles: obs.draw(env.display)
            
            if done:
                env.dino.draw(env.display, dead=True, alpha=128)
            else:
                env.dino.draw(env.display)
                
            env._draw_hud(env.score)
            
            # Passa a ativação para desenhar a rede neural na HUD
            tensor_state = torch.tensor(state_old, dtype=torch.float)
            prediction = agent.model(tensor_state)
            
            with torch.no_grad():
                h1 = torch.nn.functional.relu(agent.model.linear1(tensor_state))
                # Passa a atividade real de TODOS os 256 neurônios!
                hidden_acts = [min(1.0, val.item()) for val in h1]
            
            activations = {
                'input': state_old.tolist(),
                'hidden': hidden_acts, 
                'output': torch.softmax(prediction, dim=0).tolist()
            }
            env._draw_neural_network(tuple(state_old), 0, activations=activations)
            
            # ── PAINEL DQN (ZONA ESQUERDA, SEM fundo) ──
            px = 20
            py = 15
            
            # Métricas
            eps_pct = max(0.0, min(1.0, agent.epsilon))
            max_mem = agent.memory.maxlen
            mem_pct = min(1.0, len(agent.memory) / max_mem)
            dist_px = int(env.score)
            spd_px = env.game_speed
            elapsed_ep = time.time() - episode_start
            elapsed_total = time.time() - training_start
            ep_min, ep_sec = divmod(int(elapsed_ep), 60)
            tot_min, tot_sec = divmod(int(elapsed_total), 60)
            tot_hr, tot_min = divmod(tot_min, 60)
            
            sim_time = env.total_simulated_frames / 60.0
            sim_min, sim_sec = divmod(int(sim_time), 60)
            sim_hr, sim_min = divmod(sim_min, 60)
            
            # 1. Título
            env.display.blit(env.FONT_SUBTITLE.render(f"DQN  ·  EPISÓDIO {agent.n_games}", True, (80, 80, 80)), (px, py))
            
            py += 30
            timer_str = f"Simulado (IA): {sim_hr}h {sim_min}m {sim_sec}s   |   Real: {tot_hr}h {tot_min}m {tot_sec}s"
            env.display.blit(env.FONT_BODY.render(timer_str, True, (80, 80, 80)), (px, py))
            
            # 2. Barra Epsilon
            py += 40
            exploit_pct = 1.0 - eps_pct
            env.display.blit(env.FONT_BODY.render("Exploração (Epsilon):", True, (80, 80, 80)), (px, py))
            py += 25
            pygame.draw.rect(env.display, (200, 200, 200), (px, py, 200, 16), border_radius=4)
            if exploit_pct > 0:
                pygame.draw.rect(env.display, (200, 50, 50), (px, py, int(200 * exploit_pct), 16), border_radius=4)
            env.display.blit(env.FONT_BODY.render(f"{int(exploit_pct*100)}%", True, (80, 80, 80)), (px + 215, py))
            
            # 3. Barra Memória
            py += 40
            env.display.blit(env.FONT_BODY.render(f"Memória: {len(agent.memory)}/{max_mem}", True, (80, 80, 80)), (px, py))
            py += 25
            pygame.draw.rect(env.display, (200, 200, 200), (px, py, 200, 16), border_radius=4)
            if mem_pct > 0:
                pygame.draw.rect(env.display, (80, 130, 220), (px, py, int(200 * mem_pct), 16), border_radius=4)
            env.display.blit(env.FONT_BODY.render(f"{int(mem_pct*100)}%", True, (80, 80, 80)), (px + 215, py))
            
            # 4. Métricas de Jogo
            py += 40
            env.display.blit(env.FONT_BODY.render(f"Recompensa: {reward:.1f}", True, (70, 70, 70)), (px, py))
            py += 32
            env.display.blit(env.FONT_BODY.render(f"Distância: {dist_px} px", True, (80, 80, 80)), (px, py))
            py += 32
            kmh = (spd_px * 60 / 10.75) * 3.6
            env.display.blit(env.FONT_BODY.render(f"Velocidade: {spd_px:.1f} px/f ({kmh:.0f} km/h)", True, (80, 80, 80)), (px, py))
            py += 32
            env.display.blit(env.FONT_BODY.render(f"Tempo Ciclo: {ep_min:02d}:{ep_sec:02d}", True, (80, 80, 80)), (px, py))

            # 5. Q-Values
            py += 45
            q_probs = torch.softmax(prediction, dim=0).tolist()
            q_labels = ["Correr", "Pular", "Abaixar"]
            q_colors = [(50, 180, 50), (180, 50, 50), (50, 100, 200)]
            
            env.display.blit(env.FONT_SUBTITLE.render("Decisão (Q-Values):", True, (80, 80, 80)), (px, py))
            py += 35
            
            for idx, (prob, lbl, cor) in enumerate(zip(q_probs, q_labels, q_colors)):
                if idx == final_move:
                    env.FONT_BODY.set_bold(True)
                    lbl_surf = env.FONT_BODY.render(lbl, True, (40, 40, 40)) # Um pouco mais escuro para destacar o negrito
                    env.FONT_BODY.set_bold(False)
                else:
                    lbl_surf = env.FONT_BODY.render(lbl, True, (130, 130, 130)) # Cinza claro para os não selecionados
                
                env.display.blit(lbl_surf, (px, py))
                pygame.draw.rect(env.display, (200, 200, 200), (px + 100, py + 3, 140, 14), border_radius=3)
                if prob > 0:
                    pygame.draw.rect(env.display, cor, (px + 100, py + 3, int(140 * prob), 14), border_radius=3)
                env.display.blit(env.FONT_BODY.render(f"{int(prob*100)}%", True, (80, 80, 80)), (px + 250, py + 1))
                py += 28
            
            hints_text = "[T] TURBO: LIGADO   |   [ESC] Sair" if getattr(env, 'turbo_mode', False) else "[T] TURBO: DESLIGADO   |   [ESC] Sair"
            hints_color = (255, 140, 0) if getattr(env, 'turbo_mode', False) else (130, 130, 130)
            hints_lbl = env.FONT_BODY.render(hints_text, True, hints_color)
            env.display.blit(hints_lbl, (20, env.display.get_height() - 35))
            
            # -- VERIFICAÇÃO SE A IA "APRENDEU" (30k pixels após velocidade máxima) --
            pixels_at_max = (env.score - score_at_max_speed) if score_at_max_speed is not None else 0
            if pixels_at_max >= 468000 and not env.unlimited_speed:  # ~10 minutos na velocidade máxima
                learned_surf = env.FONT_COURIER_LEARNED.render("IA APRENDEU!", True, (0, 150, 0))
                env.display.blit(learned_surf, learned_surf.get_rect(center=(env.display.get_width() // 2, 70)))
                
                sub_learned = env.FONT_BODY.render("(Atingiu domínio absoluto. Pressione ESC para salvar e sair)", True, (100, 100, 100))
                env.display.blit(sub_learned, sub_learned.get_rect(center=(env.display.get_width() // 2, 105)))
            
            pygame.display.flip()
            
            if not getattr(env, 'turbo_mode', False):
                env.clock.tick(60)

        # ── Se o dinossauro morrer ──
        if done:
            # Graph history logic for DQN
            env.history_best_scores.append(env.score)
            if hasattr(env, 'history_best_speeds'):
                env.history_best_speeds.append(env.game_speed)
            env.history_avg_scores.append(env.score)
            
            env.reset()
            agent.n_games += 1
            agent.train_long_memory()
            episode_start = time.time()  # Reseta timer do ciclo
            score_at_max_speed = None  # Reseta rastreamento de velocidade máxima
            
            if score > record:
                record = score
                agent.model.save('dqn_model.pth') # Local quick save
                print(f"NOVO RECORDE DQN! Pontuação: {score} no Jogo: {agent.n_games}")
                
            # Auto-save a cada 10 episódios
            if agent.n_games % 10 == 0:
                env_state = {
                    'generation': agent.n_games,
                    'start_time_offset': time.time() - training_start,
                    'total_simulated_frames': env.total_simulated_frames,
                    'hi_score': env.hi_score,
                    'hi_speed': getattr(env, 'hi_speed', 0.0),
                    'history_best_scores': env.history_best_scores,
                    'history_best_speeds': getattr(env, 'history_best_speeds', []),
                    'history_avg_scores': env.history_avg_scores
                }
                payload = {
                    'model_state': agent.model.state_dict(),
                    'optimizer_state': agent.trainer.optimizer.state_dict(),
                    'n_games': agent.n_games,
                    'epsilon': agent.epsilon
                }
                import checkpoint_manager
                saved_path = checkpoint_manager.save_checkpoint("dqn_checkpoint", "DQN", payload, env_state, is_auto=True)
                print(f"\n[AUTO-SAVE] Checkpoint DQN do Episódio {agent.n_games} salvo em: {saved_path}")
            
            print(f"Episódio {agent.n_games} | Score: {score} | Recorde: {record} | Memória: {len(agent.memory)}")
            state_old = agent.get_state(env)

if __name__ == '__main__':
    run_dqn(unlimited_speed=True)
