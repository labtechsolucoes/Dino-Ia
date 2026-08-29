import pygame
import sys
from Jogo.dino_env import DinoGame

if __name__ == "__main__":
    pygame.init()
    
    # Configurações padrão do jogador humano
    unlimited_speed = False
    use_bazooka = True
    
    env = DinoGame(render=True, unlimited_speed=unlimited_speed, use_bazooka=use_bazooka)
    env.play_human_mode()
    
    pygame.quit()
    sys.exit(0)
