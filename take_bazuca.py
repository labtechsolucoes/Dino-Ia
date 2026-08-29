import sys
import os
import pygame
import random

# Adiciona o diretório atual ao path para poder importar Jogo.dino_env
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from Jogo.dino_env import (
    load_assets, Dino, Obstacle, Missile, FireVisual, Cloud, Mountain,
    SCREEN_WIDTH, SCREEN_HEIGHT, GROUND_Y, BG_COLOR, INITIAL_SPEED
)

def run():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Take Bazuca")
    
    # Carrega assets de imagem
    load_assets()
    
    clock = pygame.time.Clock()
    game_speed = INITIAL_SPEED
    
    dino = Dino(x=150, color=(100, 200, 100))
    dino.y = GROUND_Y - dino.height
    dino.bazooka_out = True
    
    obstacles = []
    missiles = []
    fires = []
    
    clouds = [Cloud() for _ in range(5)]
    for c in clouds:
        c.y = random.randint(30, 120)
        
    mountains = [Mountain() for _ in range(3)]
    for i, m in enumerate(mountains):
        m.x = i * 400
        
    def spawn_cactus(is_giant=False):
        # Cria um cacto sempre fora da tela
        obs = Obstacle(SCREEN_WIDTH + 50, game_speed, is_giant=is_giant)
        if hasattr(obs, 'type'):
            obs.type = 'giant_cactus' if is_giant else 'cactus'
        obstacles.append(obs)
        
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    # Atirar missel (centro da bazuca)
                    mx = dino.x + dino.width
                    my = dino.y + dino.height // 2 - 10
                    missile = Missile(mx, my, dino.id, game_speed, dino.color)
                    missiles.append(missile)
                elif event.key == pygame.K_t:
                    # Spawn cacto normal
                    spawn_cactus(is_giant=False)
                elif event.key == pygame.K_r:
                    # Spawn cacto gigante
                    spawn_cactus(is_giant=True)
                    
        # Update elements
        dino._anim += 1
        
        for c in clouds:
            c.update(game_speed)
            if c.x < -100:
                c.x = SCREEN_WIDTH + 50
                c.y = random.randint(30, 120)
                
        for m in mountains:
            m.x -= game_speed * 0.2
            if m.x < -1000:
                m.x = SCREEN_WIDTH + 50
                
        for obs in obstacles:
            obs.update(game_speed)
            
        for m in missiles:
            m.update()
            
        for f in fires:
            f.update(game_speed)
            
        # Collision Missiles <-> Obstacles
        for m in missiles[:]:
            m_rect = m.get_rect()
            hit = False
            for obs in obstacles[:]:
                if m_rect.colliderect(obs.get_rect()):
                    hit = True
                    # Substitui cacto por explosao
                    fires.append(FireVisual(obs.x, obs.y))
                    obstacles.remove(obs)
                    break
            if hit and m in missiles:
                missiles.remove(m)
                
        # Clean offscreen
        obstacles = [o for o in obstacles if not o.is_off_screen()]
        missiles = [m for m in missiles if not m.is_off_screen()]
        fires = [f for f in fires if not f.is_off_screen()]
        
        # Draw background
        screen.fill(BG_COLOR)
        
        # Background objects
        for m in mountains:
            m.draw(screen)
        for c in clouds:
            c.draw(screen)
            
        # Ground
        pygame.draw.line(screen, (150, 150, 150), (0, GROUND_Y), (SCREEN_WIDTH, GROUND_Y), 3)
        
        # Actors
        for obs in obstacles:
            obs.draw(screen)
            
        dino.draw(screen)
        
        for m in missiles:
            m.draw(screen)
            
        for f in fires:
            f.draw(screen)
            
        pygame.display.flip()
        clock.tick(60)
        
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    run()
