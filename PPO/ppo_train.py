import os
import sys
import time
import pygame
import torch
import numpy as np

from Jogo.dino_env import DinoGame, ACTION_NONE, ACTION_JUMP, ACTION_DUCK, BG_COLOR, MAX_SPEED
from PPO.agent import PPOAgent

# PPO Hiperparâmetros
K_EPOCHS = 4
EPS_CLIP = 0.2
GAMMA = 0.99
LR = 0.0003
UPDATE_TIMESTEP = 2000 # Atualizar a cada 2000 frames de interação

def run_ppo(unlimited_speed=False, initial_model_payload=None, initial_state=None):
    # Força use_bazooka=False pois o PPO foi construído para as 8 dimensões base
    env = DinoGame(render=True, unlimited_speed=unlimited_speed, use_bazooka=False)
    state_dim = 8
    action_dim = 3
    
    agent = PPOAgent(state_dim, action_dim, LR, GAMMA, K_EPOCHS, EPS_CLIP)
    
    time_step = 0
    i_episode = 0
    
    import checkpoint_manager
    
    if initial_model_payload is not None:
        agent.policy.load_state_dict(initial_model_payload['policy_state'])
        agent.optimizer.load_state_dict(initial_model_payload['optimizer_state'])
        agent.policy_old.load_state_dict(agent.policy.state_dict())
        agent.n_updates = initial_model_payload.get('n_updates', 0)
        i_episode = initial_model_payload.get('i_episode', 0)
        
        if initial_state is not None:
            env.generation = initial_state.get('generation', i_episode)
            env.hi_score = initial_state.get('hi_score', 0)
            env.hi_speed = initial_state.get('hi_speed', 0.0)
            env.history_best_scores = initial_state.get('history_best_scores', [])
            env.history_best_speeds = initial_state.get('history_best_speeds', [])
            env.history_avg_scores = initial_state.get('history_avg_scores', [])
            env.total_simulated_frames = initial_state.get('total_simulated_frames', 0)
            offset = initial_state.get('start_time_offset', 0)
            env.start_time = time.time() - offset
    else:
        model_path = os.path.join(os.path.dirname(__file__), 'ppo_model.pth')
        if os.path.exists(model_path):
            print("Carregando modelo PPO existente (ppo_model.pth)...")
            agent.policy.load_state_dict(torch.load(model_path, weights_only=True))
            agent.policy_old.load_state_dict(agent.policy.state_dict())
            i_episode = 50

    training_start = env.start_time if hasattr(env, 'start_time') else time.time()
    
    running = True
    while running:
        env.reset()
        state_old_tuple = env._get_state()
        state_old = np.array(state_old_tuple, dtype=float)
        
        done = False
        score = 0
        episode_reward = 0
        episode_start = time.time()
        score_at_max_speed = None  # Rastreia quando a velocidade máxima foi atingida
        
        while not done:
            # Escutar Modo Turbo e Pause
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    done = True
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        elapsed = time.time() - training_start
                        menu_action = env._show_pause_menu(i_episode, env.hi_score, agent.n_updates, 0, elapsed, mode="PPO")
                        if menu_action == "SAVE":
                            env_state = {
                                'generation': i_episode,
                                'start_time_offset': time.time() - training_start,
                                'total_simulated_frames': env.total_simulated_frames,
                                'hi_score': env.hi_score,
                                'hi_speed': getattr(env, 'hi_speed', 0.0),
                                'history_best_scores': env.history_best_scores,
                                'history_best_speeds': getattr(env, 'history_best_speeds', []),
                                'history_avg_scores': env.history_avg_scores
                            }
                            payload = {
                                'policy_state': agent.policy.state_dict(),
                                'optimizer_state': agent.optimizer.state_dict(),
                                'n_updates': agent.n_updates,
                                'i_episode': i_episode
                            }
                            import checkpoint_manager
                            saved_path = checkpoint_manager.save_checkpoint("ppo_checkpoint", "PPO", payload, env_state, is_auto=False)
                            print("\n" + "="*50)
                            print(f"✅ SIMULAÇÃO INTERROMPIDA! Modelo PPO salvo em '{saved_path}'")
                            print("="*50 + "\n")
                            running = False
                            done = True
                            pygame.quit()
                            sys.exit(0)
                        # Se o usuário escolheu continuar, ele sai do if e o loop prossegue.
                    if event.key == pygame.K_t:
                        env.turbo_mode = not getattr(env, 'turbo_mode', False)
            
            if not running:
                break
                
            time_step += 1
            
            # PPO Amostrando a Ação
            action_idx, action_probs, critic_value = agent.select_action(state_old)
            
            # Mapear para o ambiente
            action = ACTION_NONE
            if action_idx == 1:
                action = ACTION_JUMP
            elif action_idx == 2:
                action = ACTION_DUCK
                
            state_new_tuple, raw_reward, done, score = env.play_step(action)
            state_new = np.array(state_new_tuple, dtype=float)
            
            # Marca o score quando a velocidade máxima é atingida pela primeira vez
            if env.game_speed >= MAX_SPEED and score_at_max_speed is None:
                score_at_max_speed = env.score
            
            # REWARD SHAPING rigoroso
            reward = 0.1 # Recompensa pequena por sobreviver 1 frame
            if done:
                reward = -100.0 # Punição severa
                
            agent.memory.rewards.append(reward)
            agent.memory.is_terminals.append(done)
            
            state_old = state_new
            state_old_tuple = state_new_tuple
            episode_reward += reward
            
            # Atualizar rede neural se encheu o buffer
            if time_step % UPDATE_TIMESTEP == 0:
                agent.update()
                time_step = 0
                
            # RENDERIZAÇÃO
            is_turbo = getattr(env, 'turbo_mode', False)
            if not is_turbo or env.frame_count % 10 == 0:
                env.display.fill(BG_COLOR)
                for c in env.clouds: c.draw(env.display)
                env._draw_ground()
                for obs in env.obstacles: obs.draw(env.display)
                
                if done:
                    env.dino.draw(env.display, dead=True, alpha=128)
                else:
                    env.dino.draw(env.display)
                    
                env._draw_hud(env.score)
                
                # Montar dados e desenhar HUD exclusiva PPO
                elapsed_total = time.time() - training_start
                tot_min, tot_sec = divmod(int(elapsed_total), 60)
                tot_hr, tot_min = divmod(tot_min, 60)
                
                sim_time = env.total_simulated_frames / 60.0
                sim_min, sim_sec = divmod(int(sim_time), 60)
                sim_hr, sim_min = divmod(sim_min, 60)
                
                elapsed_ep = time.time() - episode_start
                ep_min, ep_sec = divmod(int(elapsed_ep), 60)
                
                state_data = {
                    'episode': i_episode,
                    'action_probs': action_probs,
                    'chosen_action': action_idx,
                    'critic_value': critic_value,
                    'reward': reward,
                    'ep_min': ep_min, 'ep_sec': ep_sec,
                    'tot_hr': tot_hr, 'tot_min': tot_min, 'tot_sec': tot_sec,
                    'sim_hr': sim_hr, 'sim_min': sim_min, 'sim_sec': sim_sec,
                    'state_obs': state_old_tuple
                }
                env._draw_ppo_hud(env.display, state_data)
                
                # -- VERIFICAÇÃO SE A IA "APRENDEU" (30k pixels após velocidade máxima) --
                pixels_at_max = (env.score - score_at_max_speed) if score_at_max_speed is not None else 0
                if pixels_at_max >= 468000 and not env.unlimited_speed:  # ~10 minutos na velocidade máxima
                    learned_surf = env.FONT_COURIER_LEARNED.render("IA APRENDEU!", True, (0, 150, 0))
                    env.display.blit(learned_surf, learned_surf.get_rect(center=(env.display.get_width() // 2, 70)))
                    
                    sub_learned = env.FONT_BODY.render("(Atingiu domínio absoluto. Pressione ESC para salvar e sair)", True, (100, 100, 100))
                    env.display.blit(sub_learned, sub_learned.get_rect(center=(env.display.get_width() // 2, 105)))
                
                pygame.display.flip()
                
            # COMPATIBILIDADE COM TURBO MODE
            if is_turbo:
                env.clock.tick(0)
            else:
                env.clock.tick(60)
                
        env.history_best_scores.append(score)
        if hasattr(env, 'history_best_speeds'):
            env.history_best_speeds.append(env.game_speed)
        env.history_avg_scores.append(score)
        
        i_episode += 1
        print(f"PPO Episódio {i_episode} | Score: {score:.1f} | Reward Acumulado: {episode_reward:.1f} | N Updates: {agent.n_updates}")
        
        if score > env.hi_score:
            env.hi_score = score
            agent.save('ppo_model.pth') # Local quick save
            
        # Auto-save a cada 10 episódios
        if i_episode % 10 == 0:
            env_state = {
                'generation': i_episode,
                'start_time_offset': time.time() - training_start,
                'total_simulated_frames': env.total_simulated_frames,
                'hi_score': env.hi_score,
                'hi_speed': getattr(env, 'hi_speed', 0.0),
                'history_best_scores': env.history_best_scores,
                'history_best_speeds': getattr(env, 'history_best_speeds', []),
                'history_avg_scores': env.history_avg_scores
            }
            payload = {
                'policy_state': agent.policy.state_dict(),
                'optimizer_state': agent.optimizer.state_dict(),
                'n_updates': agent.n_updates,
                'i_episode': i_episode
            }
            import checkpoint_manager
            saved_path = checkpoint_manager.save_checkpoint("ppo_checkpoint", "PPO", payload, env_state, is_auto=True)
            print(f"\n[AUTO-SAVE] Checkpoint PPO do Episódio {i_episode} salvo em: {saved_path}")
        
    pygame.quit()
