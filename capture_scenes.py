import pygame
import sys
import math
import random
from datetime import datetime

# Importamos as classes e assets originais do jogo
from Jogo.dino_env import (
    SCREEN_WIDTH, SCREEN_HEIGHT, GROUND_Y, BG_COLOR, TEXT_COLOR,
    load_assets, generate_distinct_colors, Dino, Obstacle, Cloud,
    IMG_GROUND_LIST, Mountain, Missile, FireVisual
)
import Jogo.dino_env as dino_env

# Constantes de interface
FONT_FAMILY = 'segoeui, arial, sans-serif'
FPS = 60

class Diorama:
    """Uma mini-cena individual para o Modo Foto, com sua própria física e animação."""
    def __init__(self, name, desc, color, d_type):
        self.name = name
        self.desc = desc
        self.type = d_type
        
        self.w = 160
        self.h = 130
        self.surface = pygame.Surface((self.w, self.h))
        self.ground_y = 110
        
        self.dino = Dino(x=20, color=color, name=name)
        self.dino.y = self.ground_y - 47
        
        self.obstacles = []
        self.missiles = []
        self.frame = 0
        
        if d_type in ["Gatilho Fácil", "Exterminador"]:
            self.dino.bazooka_out = True
            
        if d_type == "Furtivo":
            self.dino.duck()
            # Ajustar a posição Y pra quando tá abaixado no diorama (tamanho da sprite)
            self.dino.y = self.ground_y - self.dino.height
            
    def reset_dino(self):
        self.dino.y = self.ground_y - 47
        self.dino.vel_y = 0
        self.dino.is_jumping = False
        if self.type == "Furtivo":
            self.dino.duck()
            self.dino.y = self.ground_y - self.dino.height

    def update(self):
        self.frame += 1
        self.dino._anim += 1
        
        # 1. Movimento do cacto para os que usam cacto
        if self.type in ["O Aprendiz", "Kamikaze", "Medroso", "Calculista"]:
            if len(self.obstacles) == 0:
                obs = Obstacle(x=self.w + 20, game_speed=0, is_giant=False)
                # Força SEMPRE o mesmo cacto simples (o menorzinho) para previsibilidade
                obs.image = dino_env.IMG_CACTUS_SM
                obs.width = obs.image.get_width()
                obs.height = obs.image.get_height()
                obs.y = self.ground_y - obs.height
                
                if self.type == "Kamikaze":
                    import random
                    obs.kamikaze_will_jump = random.choice([True, False])
                    
                self.obstacles.append(obs)
                
            obs = self.obstacles[0]
            obs.x -= 6
            obs._anim += 1
            
            dist = obs.x - (self.dino.x + self.dino.width)
            
            # Lógica de pulo baseada na particularidade
            if not self.dino.is_jumping:
                if self.type == "Medroso" and dist < 120:
                    self.dino.vel_y = -8.5 # pulo custom
                    self.dino.is_jumping = True
                elif self.type == "Calculista" and dist < 85:
                    self.dino.vel_y = -8.5
                    self.dino.is_jumping = True
                elif self.type == "Kamikaze" and dist < 30:
                    if getattr(obs, 'kamikaze_will_jump', False):
                        self.dino.vel_y = -8.5
                        self.dino.is_jumping = True
                    
            if obs.x + obs.width < 0:
                self.obstacles.pop(0)
                
        # 2. Gatilho Fácil (Atira sem parar)
        elif self.type == "Gatilho Fácil":
            if self.frame % 30 == 0:
                # Dispara um missil localmente
                self.missiles.append(Missile(self.dino.x + self.dino.width, self.dino.y + 10, 0, 4, (255,0,0)))
                
        # 3. Exterminador (Atira no Cacto Gigante)
        elif self.type == "Exterminador":
            if len(self.obstacles) == 0:
                obs = Obstacle(x=self.w + 50, game_speed=0, is_giant=True)
                obs.y = self.ground_y - obs.height
                # Scale down o cacto gigante pro diorama
                obs.width = int(obs.width * 0.7)
                obs.height = int(obs.height * 0.7)
                obs.y = self.ground_y - obs.height
                self.obstacles.append(obs)
                
            obs = self.obstacles[0]
            if obs.x > 90:
                obs.x -= 2
            elif self.frame % 50 == 0:
                self.missiles.append(Missile(self.dino.x + self.dino.width, self.dino.y + 10, 0, 4, (255,0,0)))
                
            # Colisão do missil com o cacto no diorama
            for m in self.missiles[:]:
                m.x += 6
                if m.x > obs.x:
                    self.missiles.remove(m)
                    if len(self.obstacles) > 0:
                        self.obstacles.pop(0) # explode
                    break
                    
        # Update missiles genérico
        for m in self.missiles:
            m.x += 5
            if m.x > self.w and m in self.missiles:
                self.missiles.remove(m)
                
        # Física de pulo genérica
        if self.dino.is_jumping:
            self.dino.vel_y += 0.5
            self.dino.y += self.dino.vel_y
            if self.dino.y >= self.ground_y - 47:
                self.reset_dino()
                
    def draw(self):
        # Fundo do diorama sutilmente cinza para destacar o branco do OBS
        self.surface.fill((235, 235, 235))
        pygame.draw.line(self.surface, (150, 150, 150), (0, self.ground_y), (self.w, self.ground_y), 2)
        
        for obs in self.obstacles:
            obs.draw(self.surface)
        for m in self.missiles:
            m.draw(self.surface)
            
        self.dino.draw(self.surface)

class CaptureStudio:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Estúdio de Captura - Dino IA")
        
        load_assets()
        
        self.clock = pygame.time.Clock()
        self.font_title = pygame.font.SysFont(FONT_FAMILY, 36, bold=True)
        self.font_tooltip = pygame.font.SysFont(FONT_FAMILY, 14, bold=True)
        self.font_desc = pygame.font.SysFont(FONT_FAMILY, 16, italic=True)
        self.font_ui = pygame.font.SysFont(FONT_FAMILY, 20, bold=True)
        
        self.all_colors = generate_distinct_colors(30)
        
        self.running = True
        self.paused = False
        self.mode = 'menu'
        
        self.dinos = []
        self.obstacles = []
        self.clouds = []
        self.mountains = []
        self.ground_blocks = []
        self.dioramas = []
        self.missiles = []
        self.fires = []
        
        self._fill_ground()
        
    def _fill_ground(self):
        self.ground_blocks = []
        current_x = 0
        while current_x < SCREEN_WIDTH + 400:
            if not IMG_GROUND_LIST:
                break
            img = IMG_GROUND_LIST[len(self.ground_blocks) % len(IMG_GROUND_LIST)]
            self.ground_blocks.append({'x': current_x, 'img': img})
            current_x += img.get_width()

    def draw_ground(self):
        pygame.draw.line(self.screen, (83, 83, 83), (0, GROUND_Y), (SCREEN_WIDTH, GROUND_Y), 2)
        for block in self.ground_blocks:
            self.screen.blit(block['img'], (block['x'], GROUND_Y - 15))
            
    def save_screenshot(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"captura_{self.mode}_{timestamp}.png"
        pygame.image.save(self.screen, filename)
        print(f"✅ Foto salva: {filename}")

    def setup_start_mode(self):
        self.mode = 'start'
        self.dinos = []
        self.obstacles = []
        self.mountains = [Mountain() for _ in range(3)]
        self.clouds = [Cloud() for _ in range(12)]
        self.spawn_timer = 0
        self.dino_count = 0
        
        for i, m in enumerate(self.mountains):
            m.x = -100 + i * 500
        
        import random
        for i, c in enumerate(self.clouds):
            c.x = random.randint(50, SCREEN_WIDTH)
            c.y = random.randint(30, 250)
            
        for x_pos in [400, 800, 1150]:
            obs = Obstacle(x_pos, 0, is_giant=False)
            self.obstacles.append(obs)

    def setup_timelapse_meteor_mode(self):
        self.setup_start_mode()
        self.mode = 'timelapse_meteor'
        self.cycle_frames = 0
        import random
        self.stars = [{'x': random.randint(0, SCREEN_WIDTH), 'y': random.randint(0, GROUND_Y-100), 'size': random.randint(1, 3)} for _ in range(80)]
        self.raindrops = []

    def setup_timelapse_mode(self):
        self.setup_start_mode()
        self.mode = 'timelapse'
        self.cycle_frames = 0
        import random
        self.stars = [{'x': random.randint(0, SCREEN_WIDTH), 'y': random.randint(0, GROUND_Y-100), 'size': random.randint(1, 3)} for _ in range(80)]

    def setup_bazooka_rules_mode(self):
        self.setup_start_mode()
        self.mode = 'bazooka_rules'
        self.scene_timer = 0
        self.dino = Dino(x=100, color=(0, 255, 100))
        self.dino.bazooka_out = True
        self.dinos = [self.dino]
        self.dino_ammo = 1
        self.scene_text = ""
        self.obstacles = []
        self.missiles = []

    def setup_population_mode(self):
        self.mode = 'population'
        self.pop_dinos = []
        
        cores = generate_distinct_colors(100)
        import random
        import Jogo.dino_env as dino_env
        
        for i in range(100):
            row = i // 10
            col = i % 10
            
            x_start = col * 140
            y_start = row * 70
            
            ground_y = y_start + 65 # Chão quase no fundo da célula
            
            dino = Dino(x=x_start + 15, color=cores[i])
            dino.y = ground_y - 47
            dino._anim = random.randint(0, 20)
            
            obs = Obstacle(x=x_start + 140 + random.randint(0, 100), game_speed=0, is_giant=False)
            obs.image = dino_env.IMG_CACTUS_SM
            obs.width = obs.image.get_width() if obs.image else 25
            obs.height = obs.image.get_height() if obs.image else 50
            obs.y = ground_y - obs.height
            
            r = random.random()
            if r < 0.15: strategy = 'perfect'
            elif r < 0.35: strategy = 'early'
            elif r < 0.55: strategy = 'late'
            elif r < 0.75: strategy = 'duck'
            else: strategy = 'none'
            
            self.pop_dinos.append({
                'dino': dino,
                'obs': obs,
                'ground_y': ground_y,
                'x_start': x_start,
                'strategy': strategy,
                'is_dead': False
            })

    def setup_mutation_mode(self):
        self.mode = 'mutation'
        self.anim_state = 'swarm_running'
        self.anim_timer = 0
        self.mountains = [Mountain() for _ in range(3)]
        self.clouds = [Cloud() for _ in range(12)]
        
        import random
        for i, m in enumerate(self.mountains):
            m.x = -100 + i * 500
        for i, c in enumerate(self.clouds):
            c.x = random.randint(50, SCREEN_WIDTH)
            c.y = random.randint(30, 250)
        
        self.winner_idx = 45
        self.best_dino_color = (255, 50, 50)
        self.pop_dinos = []
        cores = generate_distinct_colors(100)
        
        # Estratégias: cada dino reage de forma diferente aos obstáculos
        strategies = []
        for i in range(100):
            if i == self.winner_idx:
                strategies.append('perfect')
            else:
                strategies.append(random.choice([
                    'early', 'early',      # Pula cedo demais (25%)
                    'late', 'late',        # Pula tarde demais (25%)  
                    'never',               # Nunca pula (12.5%)
                    'duck_only',           # Só abaixa, nunca pula (12.5%)
                    'random_bad',          # Aleatório ruim (12.5%)
                    'almost_perfect',      # Quase perfeito, morre no 3o ou 4o obs (12.5%)
                ]))
        
        for i in range(100):
            swarm_x = 50 + random.randint(0, 200)
            swarm_y = GROUND_Y - 47
            
            grid_x = (i % 10) * 140 + 15
            grid_y = (i // 10) * 70 + 65 - 47
            
            color = self.best_dino_color if i == self.winner_idx else cores[i]
            dino = Dino(x=swarm_x, color=color)
            dino.y = swarm_y
            
            self.pop_dinos.append({
                'dino': dino,
                'swarm_x': swarm_x,
                'swarm_y': swarm_y,
                'grid_x': grid_x,
                'grid_y': grid_y,
                'color': color,
                'floating_texts': [],
                'is_dead': False,
                'strategy': strategies[i],
                'obs_survived': 0,  # Quantos obstáculos já passou
                'die_at_obs': random.randint(2, 4) if strategies[i] == 'almost_perfect' else 999,
            })
            
        self._reset_swarm_state()
        
    def _reset_swarm_state(self):
        import random
        self.shared_obstacles = []
        self.obs_spawn_timer = 20
        self.swarm_frame = 0
        for i, item in enumerate(self.pop_dinos):
            item['is_dead'] = False
            item['dino'].x = item['swarm_x']
            item['dino'].y = item['swarm_y']
            item['dino'].is_jumping = False
            item['dino'].vel_y = 0
            if getattr(item['dino'], 'is_ducking', False):
                item['dino'].stand()
                item['dino'].is_ducking = False
            item['obs_survived'] = 0
            if item['strategy'] == 'almost_perfect':
                item['die_at_obs'] = random.randint(2, 4)

    def setup_photo_mode(self):
        self.mode = 'photo'
        self.dioramas = []
        
        perfis = [
            ("O Aprendiz", "Iniciante, morre cedo"),
            ("Kamikaze", "Pula tarde ou não pula"),
            ("Medroso", "Pula muito antes da hora"),
            ("Calculista", "Pulos precisos e exatos"),
            ("Furtivo", "Abaixa demais sem motivo"),
            ("Gatilho Fácil", "Atira atoa"),
            ("Exterminador", "Mata cactos gigantes")
        ]
        
        cores = generate_distinct_colors(len(perfis))
        
        for i, (titulo, desc) in enumerate(perfis):
            d = Diorama(titulo, desc, cores[i], titulo)
            self.dioramas.append(d)
            
    def setup_nn_mode(self):
        self.mode = 'nn'
        self.anim_timer = 0
        self.dino = Dino(x=150, color=(100,200,100))
        self.dino.y = GROUND_Y - 47
        self.obs_timer = 100
        self.obstacles = []
        self.nn_is_dead = False
        self.nn_dead_timer = 0
        self.nn_closest = None
        self.nn_will_fail = False
        
        import Jogo.dino_env as dino_env
        import random
        self.clouds = [dino_env.Cloud() for _ in range(3)]
        for i, c in enumerate(self.clouds): 
            c.x = 50 + i * 200
            c.y = random.randint(30, 120)
        
        self.mountains = [dino_env.Mountain() for _ in range(2)]
        for i, m in enumerate(self.mountains): m.x = -100 + i * 500
        
        # Estrutura didatica da rede neural espelhando o jogo real
        self.nn_inputs = [
            {"id": "dist", "label": "Dist. Obs.", "active": False, "val": 0.0},
            {"id": "alt", "label": "Alt. Obs.", "active": False, "val": 0.0},
            {"id": "larg", "label": "Larg. Obs.", "active": False, "val": 0.0},
            {"id": "vel", "label": "Velocidade", "active": False, "val": 0.0},
            {"id": "dinoy", "label": "Dino Y", "active": False, "val": 0.0},
            {"id": "jump", "label": "Pulando", "active": False, "val": 0.0},
            {"id": "duck", "label": "Abaixando", "active": False, "val": 0.0},
            {"id": "type", "label": "Tipo Obs.", "active": False, "val": 0.0},
        ]
        
        self.nn_hidden = [{} for _ in range(6)]
        
        self.nn_outputs = [
            {"id": "run", "label": "Correr", "active": False},
            {"id": "jump", "label": "Pular", "active": False},
            {"id": "duck", "label": "Abaixar", "active": False}
        ]
        
        self.nn_visual_weights = [
            {"layer": 0, "from": 0, "to": 1, "val": 2.8, "pos": 0.25},
            {"layer": 0, "from": 1, "to": 0, "val": 3.9, "pos": 0.55},
            {"layer": 0, "from": 3, "to": 2, "val": -4.6, "pos": 0.40},
            {"layer": 0, "from": 4, "to": 5, "val": 5.5, "pos": 0.30},
            {"layer": 0, "from": 5, "to": 4, "val": 1.2, "pos": 0.65},
            {"layer": 0, "from": 7, "to": 5, "val": 0.2, "pos": 0.50},
            {"layer": 1, "from": 0, "to": 0, "val": -2.2, "pos": 0.35},
            {"layer": 1, "from": 1, "to": 2, "val": 3.1, "pos": 0.60},
            {"layer": 1, "from": 4, "to": 1, "val": 0.4, "pos": 0.45},
            {"layer": 1, "from": 5, "to": 2, "val": -3.9, "pos": 0.25},
        ]
        
    def setup_bazooka_mode(self):
        self.mode = 'bazooka'
        self.dino = Dino(x=150, color=(100, 200, 100))
        self.dino.y = GROUND_Y - self.dino.height
        self.dino.bazooka_out = True
        
        self.obstacles = []
        self.missiles = []
        self.fires = []
        
        import Jogo.dino_env as dino_env
        import random
        self.clouds = [dino_env.Cloud() for _ in range(5)]
        for c in self.clouds:
            c.y = random.randint(30, 120)
            
        self.mountains = [dino_env.Mountain() for _ in range(3)]
        for i, m in enumerate(self.mountains):
            m.x = i * 400

    def setup_take_giant(self):
        self.mode = 'take_giant'
        import Jogo.dino_env as dino_env
        self.dino = dino_env.Dino(x=150, color=(100, 200, 100))
        self.dino.y = GROUND_Y - self.dino.height
        self.dino.bazooka_out = True
        self.obstacles = []
        self.missiles = []
        self.fires = []
        import random
        self.clouds = [dino_env.Cloud() for _ in range(5)]
        for c in self.clouds: c.y = random.randint(30, 120)
        self.mountains = [dino_env.Mountain() for _ in range(3)]
        for i, m in enumerate(self.mountains): m.x = i * 400

    def setup_take_behaviors(self):
        self.mode = 'take_behaviors'
        self.behavior_style = 1 # 1: Medroso, 2: Calculista, 3: Gatilho, 4: Kamikaze
        import Jogo.dino_env as dino_env
        self.dino = dino_env.Dino(x=150, color=(100, 200, 100))
        self.dino.y = GROUND_Y - self.dino.height
        self.dino.bazooka_out = True # Começa com bazuca visível
        self.obstacles = []
        self.missiles = []
        self.fires = []
        import random
        self.clouds = [dino_env.Cloud() for _ in range(5)]
        for c in self.clouds: c.y = random.randint(30, 120)
        self.mountains = [dino_env.Mountain() for _ in range(3)]
        for i, m in enumerate(self.mountains): m.x = i * 400

    def setup_take_hero(self):
        self.mode = 'take_hero'
        self.hero_timer = 0
        import Jogo.dino_env as dino_env
        self.dino = dino_env.Dino(x=150, color=(100, 200, 100))
        self.dino.y = GROUND_Y - self.dino.height
        self.dino.bazooka_out = True
        self.obstacles = []
        self.missiles = []
        self.fires = []
        import random
        self.clouds = [dino_env.Cloud() for _ in range(5)]
        for c in self.clouds: c.y = random.randint(30, 120)
        self.mountains = [dino_env.Mountain() for _ in range(3)]
        for i, m in enumerate(self.mountains): m.x = i * 400

    def setup_take_speed(self):
        self.mode = 'take_speed'
        self.speed_timer = 0
        import Jogo.dino_env as dino_env
        self.dino = dino_env.Dino(x=150, color=(100, 200, 100))
        self.dino.y = GROUND_Y - self.dino.height
        self.dino.bazooka_out = True
        self.obstacles = []
        self.missiles = []
        self.fires = []
        import random
        self.clouds = [dino_env.Cloud() for _ in range(5)]
        for c in self.clouds: c.y = random.randint(30, 120)
        self.mountains = [dino_env.Mountain() for _ in range(3)]
        for i, m in enumerate(self.mountains): m.x = i * 400

    def setup_thumbnail_mode(self):
        self.mode = 'thumbnail'
        self.dinos = []
        self.obstacles = []
        self.clouds = [Cloud() for _ in range(7)]
        self.mountains = [Mountain() for _ in range(3)]
        
        for i, m in enumerate(self.mountains):
            m.x = -100 + i * 500
            
        for i, c in enumerate(self.clouds):
            c.x = 50 + i * 200
            
        import Jogo.dino_env as dino_env
        
        # Cacto normal e um pássaro 
        obs1 = Obstacle(750, 0, is_giant=False)
        obs1.image = dino_env.IMG_CACTUS_LG
        obs1.width = obs1.image.get_width() if obs1.image else 50
        obs1.height = obs1.image.get_height() if obs1.image else 50
        obs1.y = GROUND_Y - obs1.height
        
        obs2 = Obstacle(950, 0, is_giant=False)
        obs2.type = "bird"
        obs2.image = dino_env.IMG_BIRD1
        obs2.width = obs2.image.get_width() if obs2.image else 45
        obs2.height = obs2.image.get_height() if obs2.image else 30
        obs2.y = GROUND_Y - 70 - obs2.height # Pássaro médio-alto (passa raspando!)
        
        self.obstacles.extend([obs1, obs2])
        
        import random
        num_swarm = 350
        num_arc = 100
        cores = generate_distinct_colors(num_swarm + num_arc)
        
        # 1. Swarm (Rampa densa de dinos na esquerda, empurrando pra cima)
        for i in range(num_swarm):
            x = random.randint(-50, 350)
            
            # Progresso horizontal na rampa (0 a 1)
            p = (x + 50) / 400.0 
            # A rampa sobe 113 pixels do chão até o topo (GROUND_Y - 160)
            ramp_y = (GROUND_Y - 47) - (p * 113) 
            
            # O dino é colocado em um lugar aleatório entre o chão e a altura da rampa naquele ponto X
            y = random.randint(int(ramp_y), GROUND_Y - 47)
            
            dino = Dino(x=x, color=cores[i])
            dino.y = y
            dino._anim = random.randint(0, 20)
            if y < GROUND_Y - 47 - 5:
                dino.is_jumping = True
            self.dinos.append(dino)
            
        # 2. O Arco (Trilha de dinos saindo milimetricamente do topo da rampa e pousando na direita)
        start_x = 350
        end_x = 1150
        h = 646 # Pico da parábola
        k = GROUND_Y - 220 # Altura máxima do pulo (razoável e não exagerado)
        a = 0.0006848 # Abertura exata para conectar (350,-160) a (1150,-47)
        
        for i in range(num_arc):
            progresso = i / num_arc
            x = start_x + (end_x - start_x) * progresso
            
            jitter_x = random.randint(-10, 10)
            jitter_y = random.randint(-10, 10)
            
            x_final = x + jitter_x
            y_final = a * ((x_final - h) ** 2) + k + jitter_y
            
            if y_final > GROUND_Y - 47:
                y_final = GROUND_Y - 47
                
            dino = Dino(x=x_final, color=cores[num_swarm + i])
            dino.y = y_final
            
            if dino.y < GROUND_Y - 47 - 5:
                dino.is_jumping = True
                
            self.dinos.append(dino)
            
        # Ordenar os dinos pelo eixo Y para os mais de baixo desenharem na frente dos de cima
        self.dinos.sort(key=lambda d: d.y)

    def render_ui(self):
        if self.mode == 'menu':
            self.screen.fill(BG_COLOR)
            text = self.font_title.render("ESCOLHA O MODO DE CAPTURA", True, TEXT_COLOR)
            self.screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, 50))
            
            opcoes = [
                "1 - Tela Inicial (Dinos e Cactos)",
                "2 - Modo Foto (Personalidades e Textos)",
                "3 - Thumbnail (Enxame de Dinos Pulo Épico)",
                "4 - Timelapse (Dia/Noite com Dinos)",
                "5 - Treinamento NEAT (Grid 100 Dinos)",
                "6 - Animação de Mutação (1 Vira 100)",
                "7 - Modo Neural (Visão Computacional e Pesos)",
                "8 - Modo Bazuca (Gravação OBS)",
                "9 - Take 1: Cacto Gigante",
                "0 - Take 2: Comportamentos",
                "- - Take 3: Hero Shot",
                "= - Take 4: Velocidade Infinita",
                "Q - Timelapse Meteoro",
                "W - Regras da Bazuca"
            ]
            
            for i, opt in enumerate(opcoes):
                t = self.font_ui.render(opt, True, TEXT_COLOR)
                self.screen.blit(t, (SCREEN_WIDTH//2 - t.get_width()//2, 120 + i * 40))
        else:
            # Overlay discreto removido para gravação no OBS!
            pass

    def _update_grid_dinos(self, loop_revive=True):
        import random
        import pygame
        for item in self.pop_dinos:
            dino = item['dino']
            obs = item['obs']
            
            # Reset Loop (próxima "geração" quando o obstáculo some)
            if obs.x + obs.width < item['x_start']:
                obs.x = item['x_start'] + 140 + random.randint(0, 50)
                if item['is_dead'] and loop_revive:
                    item['is_dead'] = False
                    dino.y = item['ground_y'] - dino.height
                    dino.is_jumping = False
                    dino.vel_y = 0
                    if getattr(dino, 'is_ducking', False):
                        dino.stand()
                        dino.is_ducking = False
            
            if item['is_dead']:
                obs.x -= 2.5
                continue
                
            dino._anim += 1
            obs.x -= 2.5 # Slower speed to observe!
            obs._anim += 1
            
            dist = obs.x - (dino.x + dino.width)
            
            if not dino.is_jumping and not getattr(dino, 'is_ducking', False):
                if item['strategy'] == 'perfect' and dist < 65:
                    dino.vel_y = -9.0
                    dino.is_jumping = True
                elif item['strategy'] == 'early' and dist < 120:
                    dino.vel_y = -9.0
                    dino.is_jumping = True
                elif item['strategy'] == 'late' and dist < 20:
                    dino.vel_y = -9.0
                    dino.is_jumping = True
                elif item['strategy'] == 'duck' and dist < 80:
                    dino.duck()
                    dino.is_ducking = True
                    
            if dino.is_jumping or dino.y < item['ground_y'] - dino.height:
                dino.vel_y += 0.6
                dino.y += dino.vel_y
                if dino.y >= item['ground_y'] - dino.height:
                    dino.y = item['ground_y'] - dino.height
                    dino.vel_y = 0.0
                    dino.is_jumping = False
                    
            if getattr(dino, 'is_ducking', False) and dist < -30:
                dino.stand()
                dino.is_ducking = False
                
            # Collision
            dino_rect = pygame.Rect(dino.x+8, dino.y+8, dino.width-16, dino.height-16)
            obs_rect = pygame.Rect(obs.x+5, obs.y+5, obs.width-10, obs.height-10)
            if dino_rect.colliderect(obs_rect):
                item['is_dead'] = True
                if getattr(dino, 'is_ducking', False):
                    dino.stand()
                    dino.is_ducking = False

    def update_animations(self):
        if self.paused:
            return
            
        if self.mode == 'nn':
            self.anim_timer += 1
            self.dino._anim += 1
            self.obs_timer -= 1
            
            import Jogo.dino_env as dino_env
            
            if self.nn_is_dead:
                self.nn_dead_timer += 1
                self.nn_outputs[0]["active"] = False
                self.nn_outputs[1]["active"] = False
                self.nn_outputs[2]["active"] = False
                
                if self.nn_dead_timer > 60: # 1 segundo depois de morrer
                    self.nn_is_dead = False
                    self.nn_will_fail = False
                    self.nn_dead_timer = 0
                    self.dino.y = GROUND_Y - 47
                    self.dino.vel_y = 0
                    self.dino.is_jumping = False
                    if getattr(self.dino, 'is_ducking', False):
                        self.dino.stand()
                        self.dino.is_ducking = False
                    self.obstacles = []
                    self.obs_timer = 50
                    
                    # MUTAÇÃO DOS PESOS visuais selecionados
                    import random
                    for w in self.nn_visual_weights:
                        w["val"] += random.uniform(-1.0, 1.0)
                return
                
            if self.anim_timer > 0 and self.anim_timer % 400 == 0:
                self.nn_will_fail = True
                
            for c in self.clouds:
                c.x -= 2
                if c.x < -100: c.x = 550
            for m in self.mountains:
                m.x -= 1
                if m.x < -200: m.x = 550
            
            if self.obs_timer <= 0:
                import random
                is_bird = random.random() < 0.4
                obs = Obstacle(x=550, game_speed=0, is_giant=False)
                if is_bird:
                    obs.type = "bird"
                    obs.image = dino_env.IMG_BIRD1
                    obs.width = obs.image.get_width()
                    obs.height = obs.image.get_height()
                    obs.y = GROUND_Y - 35 - obs.height # Pássaro
                else:
                    obs._cactus_variant = random.choice(["small", "large"])
                    obs.image = dino_env.IMG_CACTUS_SM if obs._cactus_variant == "small" else dino_env.IMG_CACTUS_LG
                    obs.width = obs.image.get_width()
                    obs.height = obs.image.get_height()
                    obs.y = GROUND_Y - obs.height
                self.obstacles.append(obs)
                self.obs_timer = random.randint(25, 45)
                
            for obs in self.obstacles:
                obs.x -= 15
                obs._anim += 1
            self.obstacles = [o for o in self.obstacles if o.x > -50]
            
            # Animação do dino mais rápida pra acompanhar a velocidade
            if not self.dino.is_jumping:
                self.dino._anim += 1
                
            closest = next((o for o in self.obstacles if o.x > self.dino.x - 20), None)
            self.nn_closest = closest
            
            # Reset states
            for node in self.nn_inputs: node["active"] = False
            self.nn_outputs[0]["active"] = False
            self.nn_outputs[1]["active"] = False
            self.nn_outputs[2]["active"] = False
            
            # Atualiza valores dinâmicos reais da rede neural
            if closest:
                self.nn_inputs[0]["val"] = max(0.0, min(1.0, (closest.x - self.dino.x)/600.0))
                self.nn_inputs[1]["val"] = closest.height / 50.0
                self.nn_inputs[2]["val"] = closest.width / 50.0
                self.nn_inputs[7]["val"] = 1.0 if closest.type == "bird" else 0.0
            else:
                self.nn_inputs[0]["val"] = 1.0
                self.nn_inputs[1]["val"] = 0.0
                self.nn_inputs[2]["val"] = 0.0
                self.nn_inputs[7]["val"] = 0.0
                
            self.nn_inputs[3]["val"] = 0.73 # Velocidade ficticia pro visual
            self.nn_inputs[4]["val"] = max(0.0, min(1.0, (GROUND_Y - 47 - self.dino.y) / 100.0))
            self.nn_inputs[5]["val"] = 1.0 if self.dino.is_jumping else 0.0
            self.nn_inputs[6]["val"] = 1.0 if getattr(self.dino, 'is_ducking', False) else 0.0
            
            for node in self.nn_inputs:
                if node["val"] >= 0.5:
                    node["active"] = True
                    
            is_bird_danger = closest and closest.type == "bird" and closest.y < GROUND_Y - 40
            
            # IA behavior com chance de erro (morre de propósito a cada ~7 segundos pra mostrar a mutação)
            will_fail = self.nn_will_fail
            
            if closest and closest.x - self.dino.x < 250 and not will_fail:
                if is_bird_danger:
                    if not self.dino.is_jumping:
                        self.dino.duck()
                        self.dino.is_ducking = True
                else:
                    if not self.dino.is_jumping and not getattr(self.dino, 'is_ducking', False):
                        self.dino.vel_y = -14.5
                        self.dino.is_jumping = True
                        
            if self.dino.is_jumping:
                self.nn_outputs[1]["active"] = True
                self.dino.vel_y += 1.0
                self.dino.y += self.dino.vel_y
                if self.dino.y >= GROUND_Y - 47:
                    self.dino.y = GROUND_Y - 47
                    self.dino.vel_y = 0
                    self.dino.is_jumping = False
            elif getattr(self.dino, 'is_ducking', False):
                self.nn_outputs[2]["active"] = True
                # Levantar se não houver perigo de pássaro próximo
                if not (closest and closest.type == "bird" and closest.x - self.dino.x < 250):
                    self.dino.stand()
                    self.dino.is_ducking = False
            else:
                self.nn_outputs[0]["active"] = True  # NADA / CORRER
                
            # Colisão (morrer)
            dino_rect = pygame.Rect(self.dino.x+8, self.dino.y+8, self.dino.width-16, self.dino.height-16)
            for obs in self.obstacles:
                obs_rect = pygame.Rect(obs.x+5, obs.y+5, obs.width-10, obs.height-10)
                if dino_rect.colliderect(obs_rect):
                    if getattr(self.dino, 'is_ducking', False) and obs.type == "bird":
                        continue # Ignora colisão por hitbox zoado se a animação tá certa
                    self.nn_is_dead = True
                    self.nn_dead_timer = 0
            
        elif self.mode in ['start', 'timelapse', 'timelapse_meteor']:
            self.spawn_timer += 1
            if self.mode in ['timelapse', 'timelapse_meteor']:
                self.cycle_frames += 1
                
            if self.spawn_timer > 30 and self.dino_count < 85:
                import random
                nova_cor = random.choice(self.all_colors)
                d = Dino(x=-50, color=nova_cor)
                d.y = GROUND_Y - 47
                self.dinos.append(d)
                self.spawn_timer = 0
                self.dino_count += 1
            
            for dino in self.dinos[:]:
                dino._anim += 1
                dino.x += 6
                
                if dino.x > SCREEN_WIDTH + 50:
                    self.dinos.remove(dino)
                    if self.mode in ['timelapse', 'timelapse_meteor']:
                        self.dino_count -= 1
                    continue
                
                if not dino.is_jumping:
                    for obs in self.obstacles:
                        if 30 < obs.x - dino.x < 140:
                            dino.jump()
                            break
                            
                if dino.is_jumping or dino.y < GROUND_Y - 47:
                    dino.vel_y += 0.6
                    dino.y += dino.vel_y
                    if dino.y >= GROUND_Y - 47:
                        dino.y = GROUND_Y - 47
                        dino.is_jumping = False
                        dino.vel_y = 0

        elif self.mode == 'bazooka_rules':
            self.scene_timer += 1
            t = self.scene_timer
            
            self.dino._anim += 1
            
            # Cena 0: Introdução
            if t < 40:
                self.scene_text = "MUNIÇÃO LIMITADA"
            
            # Cena 1: Atira e destrói o primeiro
            elif t == 40:
                self.scene_text = "Atirando no Cacto Pequeno!"
                obs = Obstacle(SCREEN_WIDTH + 50, 0, is_giant=False)
                self.obstacles.append(obs)
            elif t == 100: # Atirar!
                self.scene_text = "Ficou sem munição!"
                self.dino_ammo = 0
                mx = self.dino.x + self.dino.width
                my = self.dino.y + self.dino.height // 2 - 10
                self.missiles.append(Missile(mx, my, self.dino.id, 7.0, self.dino.color))
                
            # Cena 2: Aparecem VÁRIOS obstáculos pra desviar
            elif t == 170:
                self.scene_text = "Esquive se não tiver munição!"
                obs = Obstacle(SCREEN_WIDTH + 50, 0, is_giant=False)
                self.obstacles.append(obs)
            elif t == 250:
                obs = Obstacle(SCREEN_WIDTH + 50, 0, is_giant=False)
                self.obstacles.append(obs)
            elif t == 330:
                obs = Obstacle(SCREEN_WIDTH + 50, 0, is_giant=False)
                obs.type = 'bird'
                obs.y = GROUND_Y - 45
                self.obstacles.append(obs)
            elif t == 410:
                obs = Obstacle(SCREEN_WIDTH + 50, 0, is_giant=False)
                self.obstacles.append(obs)
            elif t == 490:
                obs = Obstacle(SCREEN_WIDTH + 50, 0, is_giant=False)
                obs.type = 'bird'
                obs.y = GROUND_Y - 45
                self.obstacles.append(obs)
                
            # Cena 3: Recarregamento e gigante
            elif t == 620:
                self.dino_ammo = 1
                self.scene_text = "RECARREGOU!"
                if not hasattr(self, 'reload_particles'):
                    self.reload_particles = []
                import random
                for _ in range(30):
                    self.reload_particles.append({
                        'x': self.dino.x + self.dino.width/2,
                        'y': self.dino.y + self.dino.height/2,
                        'vx': random.uniform(-3, 3),
                        'vy': random.uniform(-3, 3),
                        'life': 30
                    })
            elif t == 700:
                self.scene_text = "Guarde o tiro para o CACTO GIGANTE!"
                obs = Obstacle(SCREEN_WIDTH + 50, 0, is_giant=True)
                obs.type = 'giant_cactus'
                self.obstacles.append(obs)
            elif t == 770: # Atirar no gigante!
                self.dino_ammo = 0
                mx = self.dino.x + self.dino.width
                my = self.dino.y + self.dino.height // 2 - 10
                self.missiles.append(Missile(mx, my, self.dino.id, 7.0, self.dino.color))
                
            elif t > 920:
                self.scene_timer = 0 # Loop
                self.dino_ammo = 1
                self.obstacles = []
                self.missiles = []
                if hasattr(self, 'fires'): self.fires = []
                
            # Fisicas do Dino
            if self.dino.is_jumping:
                self.dino.vel_y += 0.6
                self.dino.y += self.dino.vel_y
                if self.dino.y >= GROUND_Y - 47:
                    self.dino.y = GROUND_Y - 47
                    self.dino.is_jumping = False
                    self.dino.vel_y = 0
                    
            # Auto-Dodge para obstáculos VIVOS
            if not self.dino.is_jumping and not self.dino.is_ducking:
                for obs in self.obstacles:
                    if not getattr(obs, 'is_dead', False):
                        dist = obs.x - (self.dino.x + self.dino.width)
                        if 0 < dist < 140:
                            if getattr(obs, 'type', '') == 'bird':
                                self.dino.duck()
                            else:
                                self.dino.vel_y = -11.0
                                self.dino.is_jumping = True
                            break
                            
            if self.dino.is_ducking:
                passed_all = True
                for obs in self.obstacles:
                    if not getattr(obs, 'is_dead', False) and getattr(obs, 'type', '') == 'bird':
                        dist = obs.x + obs.width - self.dino.x
                        if dist > 0 and obs.x - (self.dino.x + self.dino.width) < 140:
                            passed_all = False
                if passed_all:
                    self.dino.stand()
                    
            # Atualiza obstáculos
            for obs in self.obstacles[:]:
                obs.x -= 6
                if obs.x < -100:
                    self.obstacles.remove(obs)
                    
            # Atualiza mísseis
            for m in self.missiles[:]:
                m.x += m.speed
                if m.x > SCREEN_WIDTH + 50:
                    self.missiles.remove(m)
                    continue
                # Colisão missel e obstaculo
                m_rect = pygame.Rect(m.x, m.y, m.width, m.height)
                for obs in self.obstacles[:]:
                    if getattr(obs, 'is_dead', False):
                        continue
                    obs_rect = pygame.Rect(obs.x, obs.y, obs.width, obs.height)
                    if m_rect.colliderect(obs_rect):
                        obs.is_dead = True
                        if m in self.missiles:
                            self.missiles.remove(m)
                            
                        if not hasattr(self, 'fires'):
                            self.fires = []
                        self.fires.append(FireVisual(obs.x, obs.y + obs.height - 30))
                        
                        # Cria explosão se for o cacto gigante
                        if obs.type == 'giant_cactus' and not hasattr(self, 'giant_boom'):
                            self.giant_boom = {'x': obs.x, 'y': obs.y, 'timer': 20}
                        break
                        
            # Atualiza fogos
            if hasattr(self, 'fires'):
                for f in self.fires[:]:
                    f.update(6)
                    if f.is_off_screen():
                        self.fires.remove(f)
                        
            # Particulas recarga
            if hasattr(self, 'reload_particles'):
                for p in self.reload_particles[:]:
                    p['x'] += p['vx']
                    p['y'] += p['vy']
                    p['life'] -= 1
                    if p['life'] <= 0:
                        self.reload_particles.remove(p)

        elif self.mode == 'photo':
            for d in self.dioramas:
                d.update()

        else:
            if self.mode == 'mutation':
                self.anim_timer += 1
                
                if self.anim_state == 'swarm_running':
                    self.swarm_frame += 1
                    self.obs_spawn_timer -= 1
                    import Jogo.dino_env as dino_env
                    import random
                    
                    # Spawn contínuo de obstáculos (cactos e pássaros)
                    if self.obs_spawn_timer <= 0:
                        is_bird = random.random() < 0.25
                        obs = dino_env.Obstacle(x=SCREEN_WIDTH, game_speed=0, is_giant=False)
                        
                        if is_bird:
                            obs.type = "bird"
                            obs.image = dino_env.IMG_BIRD1
                            obs.width = obs.image.get_width() if obs.image else 45
                            obs.height = obs.image.get_height() if obs.image else 30
                            bird_y = random.choice([GROUND_Y - 5, GROUND_Y - 22, GROUND_Y - 55])
                            obs.y = bird_y - obs.height
                        else:
                            variant = random.choice(["small", "large"])
                            obs._cactus_variant = variant
                            obs.image = dino_env.IMG_CACTUS_SM if variant == "small" else dino_env.IMG_CACTUS_LG
                            obs.width = obs.image.get_width() if obs.image else 25
                            obs.height = obs.image.get_height() if obs.image else 50
                            obs.y = GROUND_Y - obs.height
                        obs._passed_dinos = set()  # Rastreia quais dinos já passaram por este obs
                        self.shared_obstacles.append(obs)
                        self.obs_spawn_timer = random.randint(50, 80)
                        
                    for obs in self.shared_obstacles:
                        obs.x -= 7
                        obs._anim += 1
                    self.shared_obstacles = [o for o in self.shared_obstacles if o.x > -100]
                    
                    alive_count = 0
                    for idx, item in enumerate(self.pop_dinos):
                        dino = item['dino']
                        if item['is_dead']:
                            dino.x -= 7
                            continue
                            
                        alive_count += 1
                        dino._anim += 1
                        
                        # Encontrar obstáculo mais próximo
                        closest_obs = None
                        for o in self.shared_obstacles:
                            if o.x + o.width > dino.x - 20:
                                closest_obs = o
                                break
                        
                        if closest_obs:
                            dist = closest_obs.x - (dino.x + dino.width)
                            is_bird = getattr(closest_obs, 'type', '') == 'bird'
                            is_bird_low = is_bird and closest_obs.y > GROUND_Y - 80
                            strategy = item['strategy']
                            
                            # === COMPORTAMENTO POR ESTRATÉGIA ===
                            if strategy == 'perfect':
                                if dist < 90 and dist > 0:
                                    if is_bird_low:
                                        if not getattr(dino, 'is_ducking', False) and not dino.is_jumping:
                                            dino.duck()
                                            dino.is_ducking = True
                                    elif not is_bird and not dino.is_jumping and not getattr(dino, 'is_ducking', False):
                                        dino.vel_y = -11
                                        dino.is_jumping = True
                                elif dist > 130 and getattr(dino, 'is_ducking', False):
                                    dino.stand()
                                    dino.is_ducking = False
                                    
                            elif strategy == 'almost_perfect':
                                if item['obs_survived'] >= item['die_at_obs']:
                                    pass  # Não faz nada, vai bater
                                elif dist < 90 and dist > 0:
                                    if is_bird_low:
                                        if not getattr(dino, 'is_ducking', False) and not dino.is_jumping:
                                            dino.duck()
                                            dino.is_ducking = True
                                    elif not is_bird and not dino.is_jumping and not getattr(dino, 'is_ducking', False):
                                        dino.vel_y = -11
                                        dino.is_jumping = True
                                elif dist > 130 and getattr(dino, 'is_ducking', False):
                                    dino.stand()
                                    dino.is_ducking = False
                                    
                            elif strategy == 'early':
                                if dist < 200 and dist > 100 and not is_bird:
                                    if not dino.is_jumping and not getattr(dino, 'is_ducking', False):
                                        dino.vel_y = -11
                                        dino.is_jumping = True
                                        
                            elif strategy == 'late':
                                if dist < 20 and dist > -10 and not is_bird:
                                    if not dino.is_jumping and not getattr(dino, 'is_ducking', False):
                                        dino.vel_y = -11
                                        dino.is_jumping = True
                                        
                            elif strategy == 'never':
                                pass  # Nunca pula, nunca abaixa
                                
                            elif strategy == 'duck_only':
                                if dist < 90 and dist > 0:
                                    if not getattr(dino, 'is_ducking', False) and not dino.is_jumping:
                                        dino.duck()
                                        dino.is_ducking = True
                                elif dist > 130 and getattr(dino, 'is_ducking', False):
                                    dino.stand()
                                    dino.is_ducking = False
                                    
                            elif strategy == 'random_bad':
                                if dist < 90 and dist > 0 and not is_bird:
                                    if random.random() < 0.3 and not dino.is_jumping:
                                        dino.vel_y = -11
                                        dino.is_jumping = True
                            
                            # === COLISÃO REAL ===
                            dino_h = dino.height
                            if getattr(dino, 'is_ducking', False):
                                dino_h = 26
                            dino_rect = pygame.Rect(dino.x + 8, dino.y + 8, dino.width - 16, dino_h - 16)
                            obs_rect = pygame.Rect(closest_obs.x + 5, closest_obs.y + 5, closest_obs.width - 10, closest_obs.height - 10)
                            
                            if dino_rect.colliderect(obs_rect):
                                item['is_dead'] = True
                                continue
                            
                            # Contar obstáculo como "passado" (para almost_perfect)
                            if closest_obs.x + closest_obs.width < dino.x and idx not in getattr(closest_obs, '_passed_dinos', set()):
                                closest_obs._passed_dinos.add(idx)
                                item['obs_survived'] += 1
                                        
                        if dino.is_jumping or dino.y < item['swarm_y']:
                            dino.vel_y += 0.6
                            dino.y += dino.vel_y
                            if dino.y >= item['swarm_y']:
                                dino.y = item['swarm_y']
                                dino.vel_y = 0
                                dino.is_jumping = False
                                
                    # Quando só sobrar o vencedor, transitar
                    if alive_count <= 1 and self.swarm_frame > 180:
                        self.anim_state = 'collapse'
                        self.anim_timer = 0
                        winner = self.pop_dinos[self.winner_idx]
                        self.collapse_start_x = winner['dino'].x
                        
                elif self.anim_state == 'collapse':
                    progress = min(1.0, self.anim_timer / 90.0)
                    p = progress * progress * (3 - 2 * progress)
                    
                    winner = self.pop_dinos[self.winner_idx]['dino']
                    winner._anim += 1
                    winner.x = self.collapse_start_x + (SCREEN_WIDTH//2 - 22 - self.collapse_start_x) * p
                    winner.y = GROUND_Y - 47 + (SCREEN_HEIGHT//2 + 47 - 47 - (GROUND_Y - 47)) * p
                    
                    if self.anim_timer > 90:
                        self.anim_state = 'center'
                        self.anim_timer = 0
                        
                elif self.anim_state == 'center':
                    winner = self.pop_dinos[self.winner_idx]['dino']
                    winner._anim += 1
                    if self.anim_timer > 330:  # 5.5 segundos na tela do vencedor
                        self.anim_state = 'splitting'
                        self.anim_timer = 0
                        for item in self.pop_dinos:
                            item['dino'].x = SCREEN_WIDTH//2
                            item['dino'].y = SCREEN_HEIGHT//2
                            item['is_dead'] = False
                            
                elif self.anim_state == 'splitting':
                    progress = min(1.0, self.anim_timer / 90.0)
                    p = progress * progress * (3 - 2 * progress)
                    
                    for item in self.pop_dinos:
                        item['dino']._anim += 1
                        item['dino'].x = (SCREEN_WIDTH//2) + (item['grid_x'] - SCREEN_WIDTH//2) * p
                        item['dino'].y = (SCREEN_HEIGHT//2) + (item['grid_y'] - (SCREEN_HEIGHT//2)) * p
                        
                    if self.anim_timer > 90:
                        self.anim_state = 'grid_showcase'
                        self.anim_timer = 0
                        import random
                        for item in self.pop_dinos:
                            item['showcase_timer'] = random.randint(10, 60)
                            item['showcase_action'] = random.choice(['jump', 'duck', 'run'])
                            
                elif self.anim_state == 'grid_showcase':
                    import random
                    for item in self.pop_dinos:
                        dino = item['dino']
                        dino._anim += 1
                        
                        item['showcase_timer'] -= 1
                        if item['showcase_timer'] <= 0:
                            item['showcase_timer'] = random.randint(30, 90)
                            
                            # Escolhe ação focada no comportamento da IA
                            item['showcase_action'] = random.choice(['jump_perfect', 'jump_early', 'jump_late', 'duck', 'run_fail'])
                            
                            if item['showcase_action'] == 'jump_perfect':
                                w = random.uniform(1.0, 3.5)
                            elif item['showcase_action'] == 'jump_early':
                                w = random.uniform(-1.0, 0.5)
                            elif item['showcase_action'] == 'jump_late':
                                w = random.uniform(-2.5, -0.5)
                            elif item['showcase_action'] == 'duck':
                                w = random.uniform(0.5, 2.5)
                            else:
                                w = random.uniform(-3.0, -1.0)
                                
                            txt = f"{w:+.1f}"
                            item['floating_texts'].append({'txt': txt, 'y': item['grid_y'], 'alpha': 255, 'color': (50, 200, 50) if w > 0 else (200, 50, 50)})
                            
                        action = item['showcase_action']
                        
                        if 'jump' in action and not dino.is_jumping and not getattr(dino, 'is_ducking', False):
                            if action == 'jump_perfect':
                                dino.vel_y = -9.0
                            elif action == 'jump_early':
                                dino.vel_y = -6.0
                            elif action == 'jump_late':
                                dino.vel_y = -11.0
                            dino.is_jumping = True
                        elif action == 'duck' and not dino.is_jumping:
                            dino.duck()
                            dino.is_ducking = True
                        elif action == 'run_fail' and getattr(dino, 'is_ducking', False):
                            dino.stand()
                            dino.is_ducking = False
                            
                        ground_y = item['grid_y'] + 47
                        if dino.is_jumping or dino.y < item['grid_y']:
                            dino.vel_y += 0.6
                            dino.y += dino.vel_y
                            if dino.y >= item['grid_y']:
                                dino.y = item['grid_y']
                                dino.vel_y = 0
                                dino.is_jumping = False
                                if item['showcase_action'] == 'duck':
                                    dino.duck()
                                    dino.is_ducking = True
                                    
                        for ft in item['floating_texts']:
                            ft['y'] -= 0.5
                            ft['alpha'] = max(0, ft['alpha'] - 2)
                            
                    if self.anim_timer > 480:  # 8 segundos na grade (2s só dinos + 6s com texto)
                        self.anim_state = 'merging'
                        self.anim_timer = 0
                        for item in self.pop_dinos:
                            if getattr(item['dino'], 'is_ducking', False):
                                item['dino'].stand()
                                item['dino'].is_ducking = False
                                
                elif self.anim_state == 'merging':
                    progress = min(1.0, self.anim_timer / 90.0)
                    p = progress * progress * (3 - 2 * progress)
                    
                    for item in self.pop_dinos:
                        item['dino']._anim += 1
                        item['dino'].x = item['grid_x'] + (item['swarm_x'] - item['grid_x']) * p
                        item['dino'].y = item['grid_y'] + (item['swarm_y'] - item['grid_y']) * p
                        
                    if self.anim_timer > 90:
                        self.anim_state = 'swarm_running'
                        self.anim_timer = 0
                        self._reset_swarm_state()
            
            elif self.mode == 'population':
                self._update_grid_dinos(loop_revive=True)
            elif self.mode in ['bazooka', 'take_giant', 'take_behaviors', 'take_hero', 'take_speed']:
                speed = 7.0
                if self.mode == 'take_speed':
                    self.speed_timer += 1
                    speed = 7.0 + (self.speed_timer / 60.0) * 1.5
                    
                if self.mode == 'take_hero':
                    self.hero_timer += 1
                    
                    # Roteiro do Hero Shot (aprox 15 segs = 900 frames)
                    if self.hero_timer == 180:
                        obs = Obstacle(SCREEN_WIDTH + 50, speed, is_giant=False)
                        obs.type = 'cactus'; obs._cactus_variant = 'large'
                        self.obstacles.append(obs)
                    elif self.hero_timer == 220:
                        self.dino.vel_y = -10.0
                        self.dino.is_jumping = True
                    elif self.hero_timer == 360:
                        obs = Obstacle(SCREEN_WIDTH + 50, speed, is_giant=False)
                        obs.type = 'cactus'; obs._cactus_variant = 'large'
                        self.obstacles.append(obs)
                    elif self.hero_timer == 420:
                        mx = self.dino.x + self.dino.width
                        my = self.dino.y + self.dino.height // 2 - 10
                        self.missiles.append(Missile(mx, my, self.dino.id, speed, self.dino.color))
                    elif self.hero_timer == 500:
                        obs = Obstacle(SCREEN_WIDTH + 50, speed, is_giant=True)
                        obs.type = 'giant_cactus'
                        self.obstacles.append(obs)
                    elif self.hero_timer == 560:
                        mx = self.dino.x + self.dino.width
                        my = self.dino.y + self.dino.height // 2 - 10
                        self.missiles.append(Missile(mx, my, self.dino.id, speed, self.dino.color))

                elif self.mode == 'take_speed':
                    if self.speed_timer % int(120 / (speed / 7.0)) == 0:
                        obs = Obstacle(SCREEN_WIDTH + 50, speed, is_giant=False)
                        obs.type = 'cactus'; obs._cactus_variant = 'large'
                        self.obstacles.append(obs)
                        
                elif self.mode == 'take_behaviors':
                    if len(self.obstacles) == 0 and random.random() < 0.01:
                        obs = Obstacle(SCREEN_WIDTH + 50, speed, is_giant=False)
                        obs.type = 'cactus'; obs._cactus_variant = 'large'
                        self.obstacles.append(obs)
                        
                # Atualização do Dino (apenas anim e física básica do pulo)
                self.dino._anim += 1
                if self.dino.is_jumping or self.dino.y < GROUND_Y - self.dino.height:
                    self.dino.vel_y += 0.6
                    self.dino.y += self.dino.vel_y
                    if self.dino.y >= GROUND_Y - self.dino.height:
                        self.dino.y = GROUND_Y - self.dino.height
                        self.dino.vel_y = 0.0
                        self.dino.is_jumping = False
                
                # Comportamentos Automáticos
                if self.mode == 'take_speed':
                    # Speed = pulo automático perfeito
                    if self.obstacles:
                        closest = self.obstacles[0]
                        if not self.dino.is_jumping and closest.x - self.dino.x < 150 + speed*5:
                            self.dino.vel_y = -10.0
                            self.dino.is_jumping = True
                
                elif self.mode == 'take_behaviors' and self.obstacles:
                    dist = self.obstacles[0].x - self.dino.x
                    
                    if self.behavior_style == 1: # Medroso
                        self.dino.bazooka_out = False
                        if not self.dino.is_jumping and dist < 280:
                            self.dino.vel_y = -10.0
                            self.dino.is_jumping = True
                    else:
                        self.dino.bazooka_out = True
                        if self.behavior_style == 2: # Calculista
                            if dist < 180 and len(self.missiles) == 0:
                                mx = self.dino.x + self.dino.width
                                my = self.dino.y + self.dino.height // 2 - 10
                                self.missiles.append(Missile(mx, my, self.dino.id, speed, self.dino.color))
                        elif self.behavior_style == 3: # Gatilho
                            if dist < 500 and len(self.missiles) == 0:
                                mx = self.dino.x + self.dino.width
                                my = self.dino.y + self.dino.height // 2 - 10
                                self.missiles.append(Missile(mx, my, self.dino.id, speed, self.dino.color))
                        elif self.behavior_style == 4: # Kamikaze
                            if not self.dino.is_jumping and dist < 40 and dist > 0:
                                self.dino.vel_y = -10.0
                                self.dino.is_jumping = True
                                
                for obs in self.obstacles:
                    obs.update(speed)
                for m in self.missiles:
                    m.update()
                for f in self.fires:
                    f.update(speed)
                    
                # Collision Missiles <-> Obstacles
                for m in self.missiles[:]:
                    m_rect = m.get_rect()
                    hit = False
                    for obs in self.obstacles[:]:
                        if m_rect.colliderect(obs.get_rect()):
                            hit = True
                            # Fogo aparece onde o míssil bateu (e não no y do cacto)
                            self.fires.append(FireVisual(m.x + m.width//2, m.y - 10))
                            if self.mode == 'take_giant':
                                # No Take Giant, o cacto morre
                                self.obstacles.remove(obs)
                            elif not getattr(obs, 'is_giant', False):
                                self.obstacles.remove(obs)
                            break
                    if hit and m in self.missiles:
                        self.missiles.remove(m)
                        
                # Clean offscreen
                self.obstacles = [o for o in self.obstacles if not o.is_off_screen()]
                self.missiles = [m for m in self.missiles if not m.is_off_screen()]
                self.fires = [f for f in self.fires if not f.is_off_screen()]
            else:
                for dino in self.dinos:
                    dino._anim += 1
            
        for cloud in self.clouds:
            cloud.x -= cloud.speed
            if cloud.x + cloud.width < 0:
                cloud.x = SCREEN_WIDTH + 50
                
        for m in self.mountains:
            m.x -= 0.5
            if m.x + m.width < 0:
                m.x = SCREEN_WIDTH + 50

    def draw_scene(self):
        if self.mode == 'menu':
            self.render_ui()
            return
            
        # Controle de Dia/Noite no Timelapse
        current_bg = BG_COLOR
        if self.mode == 'timelapse':
            ciclo = self.cycle_frames % 1200
            if ciclo < 600:
                progresso = max(0, (ciclo - 500) / 100)
                r = int(247 - (247 - 20) * progresso)
                g = int(247 - (247 - 20) * progresso)
                b = int(247 - (247 - 40) * progresso)
                current_bg = (r, g, b)
            else:
                progresso = max(0, (ciclo - 1100) / 100)
                r = int(20 + (247 - 20) * progresso)
                g = int(20 + (247 - 20) * progresso)
                b = int(40 + (247 - 40) * progresso)
                current_bg = (r, g, b)
        elif self.mode == 'timelapse_meteor':
            ciclo = self.cycle_frames % 1800
            if ciclo < 200: # Dia 1
                current_bg = BG_COLOR
            elif ciclo < 400: # Anoitecer 1
                progresso = (ciclo - 200) / 200.0
                r = int(247 - (247 - 20) * progresso)
                g = int(247 - (247 - 20) * progresso)
                b = int(247 - (247 - 40) * progresso)
                current_bg = (r, g, b)
            elif ciclo < 800: # Noite 1
                current_bg = (20, 20, 40)
            elif ciclo < 1000: # Amanhecer 2
                progresso = (ciclo - 800) / 200.0
                r = int(20 + (247 - 20) * progresso)
                g = int(20 + (247 - 20) * progresso)
                b = int(40 + (247 - 40) * progresso)
                current_bg = (r, g, b)
            elif ciclo < 1200: # Dia 2
                current_bg = BG_COLOR
            elif ciclo < 1400: # Anoitecer 2
                progresso = (ciclo - 1200) / 200.0
                r = int(247 - (247 - 20) * progresso)
                g = int(247 - (247 - 20) * progresso)
                b = int(247 - (247 - 40) * progresso)
                current_bg = (r, g, b)
            elif ciclo < 1560: # Noite 2
                current_bg = (20, 20, 40)
            else: # Explosão
                current_bg = (255, 255, 255)
        
        self.screen.fill(current_bg)
        
        if self.mode == 'timelapse':
            ciclo = self.cycle_frames % 1200
            if ciclo > 500 or ciclo < 100:
                alpha = 255
                if 500 < ciclo < 600: alpha = int(((ciclo - 500) / 100) * 255)
                elif 1100 < ciclo <= 1200: alpha = int((1 - (ciclo - 1100) / 100) * 255)
                elif ciclo < 100: alpha = int((1 - (ciclo / 100)) * 255)
                
                star_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                for s in self.stars:
                    pygame.draw.circle(star_surf, (255, 255, 255, alpha), (s['x'], s['y']), s['size'])
                self.screen.blit(star_surf, (0,0))
                
        elif self.mode == 'timelapse_meteor':
            ciclo = self.cycle_frames % 1800
            
            # Estrelas
            alpha = 0
            if 200 <= ciclo < 1000:
                alpha = 255
                if 200 <= ciclo < 400: alpha = int(((ciclo - 200) / 200) * 255)
                elif 800 <= ciclo < 1000: alpha = int((1 - (ciclo - 800) / 200) * 255)
            elif 1200 <= ciclo < 1560:
                alpha = 255
                if 1200 <= ciclo < 1400: alpha = int(((ciclo - 1200) / 200) * 255)
                
            if alpha > 0:
                star_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                for s in self.stars:
                    pygame.draw.circle(star_surf, (255, 255, 255, alpha), (s['x'], s['y']), s['size'])
                self.screen.blit(star_surf, (0,0))
                
            # Chuva apenas na Noite 1
            if 400 < ciclo < 800:
                import random
                for _ in range(5):
                    self.raindrops.append([random.randint(0, SCREEN_WIDTH+200), -50])
            
            if hasattr(self, 'raindrops'):
                for drop in self.raindrops[:]:
                    drop[0] -= 5
                    drop[1] += 20
                    pygame.draw.line(self.screen, (150, 150, 200, 150), (drop[0], drop[1]), (drop[0]-5, drop[1]+20), 1)
                    if drop[1] > GROUND_Y:
                        self.raindrops.remove(drop)
            
        if self.mode == 'photo':
            scale = 2
            dw = 160 * scale
            dh = 100 * scale
            espacamento_x = (SCREEN_WIDTH - (4 * dw)) // 5
            espacamento_y = 80
            for i, d in enumerate(self.dioramas):
                d.draw()
                x = espacamento_x + i * (dw + espacamento_x) if i < 4 else ((SCREEN_WIDTH - (3 * dw) - (2 * espacamento_x)) // 2) + (i - 4) * (dw + espacamento_x)
                y = 20 if i < 4 else 20 + dh + espacamento_y
                scaled_surf = pygame.transform.scale(d.surface, (dw, dh))
                pygame.draw.rect(self.screen, TEXT_COLOR, (x-4, y-4, dw+8, dh+8), border_radius=8)
                self.screen.blit(scaled_surf, (x, y))
                title_surf = self.font_ui.render(d.name, True, (0, 0, 0))
                desc_surf = self.font_desc.render(d.desc, True, (60, 60, 60))
                self.screen.blit(title_surf, (x + dw//2 - title_surf.get_width()//2, y + dh + 10))
                self.screen.blit(desc_surf, (x + dw//2 - desc_surf.get_width()//2, y + dh + 35))
                
        elif self.mode == 'population':
            self.screen.fill(BG_COLOR)
            for i, item in enumerate(self.pop_dinos):
                x = item['x_start']
                y = (i // 10) * 70
                
                # Clip rect para não vazar a tela da célula
                self.screen.set_clip(pygame.Rect(x, y, 140, 70))
                
                # Desenhar chão da célula
                pygame.draw.line(self.screen, (200, 200, 200), (x, item['ground_y']), (x+140, item['ground_y']), 1)
                
                # Desenhar obs e dino
                item['obs'].draw(self.screen)
                if item['is_dead']:
                    item['dino'].draw(self.screen, dead=True)
                else:
                    item['dino'].draw(self.screen)
                
                # Borda da célula
                pygame.draw.rect(self.screen, (220, 220, 220), (x, y, 140, 70), 1)
                
            # Remover o clipping pro resto da renderização
            self.screen.set_clip(None)
            
        elif self.mode == 'mutation':
            self.screen.fill(BG_COLOR)
            
            if self.anim_state == 'swarm_running':
                for m in self.mountains:
                    m.draw(self.screen)
                for cloud in self.clouds:
                    cloud.draw(self.screen)
                pygame.draw.circle(self.screen, (255, 230, 100), (SCREEN_WIDTH - 200, 120), 45)
                pygame.draw.circle(self.screen, (255, 210, 50), (SCREEN_WIDTH - 200, 120), 38)
                pygame.draw.circle(self.screen, (255, 240, 150), (SCREEN_WIDTH - 200, 120), 30)
                self.draw_ground()
                
                for obs in self.shared_obstacles:
                    obs.draw(self.screen)
                
                for item in self.pop_dinos:
                    if item['is_dead']:
                        item['dino'].draw(self.screen, dead=True)
                for item in self.pop_dinos:
                    if not item['is_dead']:
                        item['dino'].draw(self.screen)
                        
            elif self.anim_state == 'collapse':
                for m in self.mountains:
                    m.draw(self.screen)
                for cloud in self.clouds:
                    cloud.draw(self.screen)
                pygame.draw.circle(self.screen, (255, 230, 100), (SCREEN_WIDTH - 200, 120), 45)
                pygame.draw.circle(self.screen, (255, 210, 50), (SCREEN_WIDTH - 200, 120), 38)
                pygame.draw.circle(self.screen, (255, 240, 150), (SCREEN_WIDTH - 200, 120), 30)
                self.draw_ground()
                
                winner = self.pop_dinos[self.winner_idx]
                temp_surf = pygame.Surface((winner['dino'].width, winner['dino'].height), pygame.SRCALPHA)
                old_x, old_y = winner['dino'].x, winner['dino'].y
                winner['dino'].x, winner['dino'].y = 0, 0
                winner['dino'].draw(temp_surf)
                winner['dino'].x, winner['dino'].y = old_x, old_y
                
                scale = 1 + 2 * min(1.0, self.anim_timer / 90.0)
                scaled = pygame.transform.scale(temp_surf, (int(winner['dino'].width * scale), int(winner['dino'].height * scale)))
                self.screen.blit(scaled, (winner['dino'].x, winner['dino'].y - (scaled.get_height() - winner['dino'].height)))
                
            elif self.anim_state == 'center':
                title = self.font_title.render("O MELHOR INDIVÍDUO DA GERAÇÃO ANTERIOR", True, (0, 0, 0))
                subtitle = self.font_ui.render("Ele será copiado e sofrerá mutações aleatórias na próxima geração...", True, (100, 100, 100))
                self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 80))
                self.screen.blit(subtitle, (SCREEN_WIDTH//2 - subtitle.get_width()//2, 130))
                
                pygame.draw.line(self.screen, (150, 150, 150), (SCREEN_WIDTH//2 - 200, GROUND_Y), (SCREEN_WIDTH//2 + 200, GROUND_Y), 3)
                
                winner = self.pop_dinos[self.winner_idx]['dino']
                temp_surf = pygame.Surface((winner.width, winner.height), pygame.SRCALPHA)
                old_x, old_y = winner.x, winner.y
                winner.x, winner.y = 0, 0
                winner.draw(temp_surf)
                winner.x, winner.y = old_x, old_y
                
                scaled = pygame.transform.scale(temp_surf, (winner.width * 3, winner.height * 3))
                self.screen.blit(scaled, (SCREEN_WIDTH//2 - scaled.get_width()//2, SCREEN_HEIGHT//2 + 47 - scaled.get_height()))
                
            elif self.anim_state in ['splitting', 'grid_showcase', 'merging']:
                grid_alpha = 255
                if self.anim_state == 'splitting':
                    grid_alpha = int(min(1.0, self.anim_timer / 90.0) * 255)
                elif self.anim_state == 'merging':
                    grid_alpha = int(255 * (1 - min(1.0, self.anim_timer / 90.0)))
                    
                r = int(247 - (247-200) * (grid_alpha/255))
                r2 = int(247 - (247-220) * (grid_alpha/255))
                
                if self.anim_state == 'merging':
                    g_alpha = int(255 * min(1.0, self.anim_timer / 90.0))
                    c = int(247 - (247-150) * (g_alpha/255))
                    pygame.draw.line(self.screen, (c,c,c), (0, GROUND_Y), (SCREEN_WIDTH, GROUND_Y), 2)
                
                for i, item in enumerate(self.pop_dinos):
                    x = (i % 10) * 140
                    y = (i // 10) * 70
                    
                    if grid_alpha > 0:
                        pygame.draw.line(self.screen, (r,r,r), (x, y+65), (x+140, y+65), 1)
                        pygame.draw.rect(self.screen, (r2,r2,r2), (x, y, 140, 70), 1)
                        
                    item['dino'].draw(self.screen)
                    
                    if self.anim_state == 'grid_showcase':
                        for ft in item['floating_texts']:
                            if ft['alpha'] > 0:
                                txt_surf = self.font_tooltip.render(ft['txt'], True, ft['color'])
                                txt_surf.set_alpha(ft['alpha'])
                                self.screen.blit(txt_surf, (x + 10, int(ft['y'] - 10)))
                                
                # Desenhar o campeão GIGANTE no centro durante o splitting, grid e merging
                winner = self.pop_dinos[self.winner_idx]['dino']
                temp_surf = pygame.Surface((winner.width, winner.height), pygame.SRCALPHA)
                old_x, old_y = winner.x, winner.y
                winner.x, winner.y = 0, 0
                winner.draw(temp_surf)
                winner.x, winner.y = old_x, old_y
                scaled = pygame.transform.scale(temp_surf, (winner.width * 3, winner.height * 3))
                
                cx = SCREEN_WIDTH // 2
                cy = SCREEN_HEIGHT // 2 - 40
                
                # Fundo do campeão (retângulo com bordas arredondadas)
                bg_rect = pygame.Rect(0, 0, 200, 140)
                bg_rect.center = (cx, cy)
                pygame.draw.rect(self.screen, (255, 255, 255), bg_rect, border_radius=20)
                pygame.draw.rect(self.screen, (0, 0, 0), bg_rect, 4, border_radius=20)
                
                # Centraliza o dino sobre o retângulo
                self.screen.blit(scaled, (cx - scaled.get_width()//2, cy - scaled.get_height()//2))
                                
                if self.anim_state == 'grid_showcase':
                    # Texto didático no topo da tela sempre presente
                    top_text = self.font_title.render("O CAMPEÃO É CLONADO COM MUTAÇÕES PARA A NOVA GERAÇÃO", True, (0, 0, 0))
                    top_rect = pygame.Rect(SCREEN_WIDTH//2 - top_text.get_width()//2 - 30, 20, top_text.get_width() + 60, top_text.get_height() + 20)
                    pygame.draw.rect(self.screen, (255, 255, 255), top_rect, border_radius=15)
                    pygame.draw.rect(self.screen, (0, 0, 0), top_rect, 3, border_radius=15)
                    self.screen.blit(top_text, (SCREEN_WIDTH//2 - top_text.get_width()//2, 30))
                    
                if self.anim_state == 'grid_showcase' and self.anim_timer > 120:
                    # Fundo escuro translúcido moderno movido para a parte INFERIOR (não cobre o dino)
                    panel_h = 180
                    panel_y = SCREEN_HEIGHT//2 + 40
                    panel_surf = pygame.Surface((SCREEN_WIDTH, panel_h), pygame.SRCALPHA)
                    panel_surf.fill((0, 0, 0, 210))  # Preto translúcido
                    
                    # Gradientes sutis / bordas no painel
                    pygame.draw.line(panel_surf, (100, 255, 100, 150), (0, 0), (SCREEN_WIDTH, 0), 3)
                    pygame.draw.line(panel_surf, (100, 255, 100, 150), (0, panel_h-3), (SCREEN_WIDTH, panel_h-3), 3)
                    
                    self.screen.blit(panel_surf, (0, panel_y))
                    
                    # Fontes gigantes criadas na hora para impacto visual
                    font_giant = pygame.font.SysFont(FONT_FAMILY, 56, bold=True)
                    font_big = pygame.font.SysFont(FONT_FAMILY, 26, bold=False)
                    
                    t1 = font_giant.render("ATRIBUINDO PESOS ÀS AÇÕES", True, (255, 255, 255))
                    t2 = font_big.render("Pulos perfeitos e no timing exato geram pontos positivos (+)", True, (150, 255, 150))
                    t3 = font_big.render("Erros, colisões e pulos atrasados/adiantados tiram pontos (-)", True, (255, 150, 150))
                    
                    self.screen.blit(t1, (SCREEN_WIDTH//2 - t1.get_width()//2, panel_y + 15))
                    self.screen.blit(t2, (SCREEN_WIDTH//2 - t2.get_width()//2, panel_y + 90))
                    self.screen.blit(t3, (SCREEN_WIDTH//2 - t3.get_width()//2, panel_y + 135))
                    
        elif self.mode == 'nn':
            self.screen.fill(BG_COLOR)
            
            # Sol amarelo brilhante
            pygame.draw.circle(self.screen, (255, 215, 0), (350, 200), 40)
            
            for m in self.mountains:
                m.draw(self.screen)
            for c in self.clouds:
                c.draw(self.screen)
                
            # Cobre o lado direito pra não vazar as nuvens
            pygame.draw.rect(self.screen, BG_COLOR, (500, 0, SCREEN_WIDTH - 500, SCREEN_HEIGHT))
            
            # Lado Esquerdo: O Jogo
            pygame.draw.line(self.screen, (150, 150, 150), (0, GROUND_Y), (500, GROUND_Y), 3)
            pygame.draw.line(self.screen, (200, 200, 200), (500, 0), (500, SCREEN_HEIGHT), 2)
            
            # Visão Computacional (linha vermelha)
            if getattr(self, 'nn_closest', None):
                start_pos = (self.dino.x + 30, self.dino.y + 15)
                end_pos = (self.nn_closest.x, self.nn_closest.y + 10)
                
                # Só desenha se o obstáculo estiver na tela esquerda
                if end_pos[0] < 500:
                    pygame.draw.line(self.screen, (255, 50, 50), start_pos, end_pos, 1)
                    pygame.draw.circle(self.screen, (255, 0, 0), end_pos, 4)
                    
                    dist = max(0, self.nn_closest.x - self.dino.x)
                    dist_txt = self.font_tooltip.render(f"dst: {dist}px", True, (255, 50, 50))
                    self.screen.blit(dist_txt, (end_pos[0] - 10, end_pos[1] - 25))
            
            self.dino.draw(self.screen)
            for obs in self.obstacles:
                obs.draw(self.screen)
                
            if self.nn_is_dead:
                # X Vermelho na tela de jogo
                pygame.draw.line(self.screen, (255, 0, 0), (self.dino.x - 10, self.dino.y - 10), (self.dino.x + 50, self.dino.y + 50), 8)
                pygame.draw.line(self.screen, (255, 0, 0), (self.dino.x + 50, self.dino.y - 10), (self.dino.x - 10, self.dino.y + 50), 8)
                
                font_giant = pygame.font.SysFont(FONT_FAMILY, 36, bold=True)
                t_mut = font_giant.render("MUTAÇÃO! AJUSTANDO PESOS...", True, (255, 50, 50))
                self.screen.blit(t_mut, (890 - t_mut.get_width()//2, 100))
                
            # Info Jogo (O que a rede vê)
            t_see = self.font_ui.render("O JOGO (ENTRADAS SENSORIAIS)", True, (100, 100, 100))
            self.screen.blit(t_see, (250 - t_see.get_width()//2, 120))
            
            # Lado Direito: A Rede Neural
            font_giant = pygame.font.SysFont(FONT_FAMILY, 36, bold=True)
            t_brain = font_giant.render("O CÉREBRO DA IA (REDE NEURAL NEAT)", True, (0, 0, 0))
            self.screen.blit(t_brain, (890 - t_brain.get_width()//2, 40))
            
            in_x = 740
            hid_x = 920
            out_x = 1100
            
            start_y_in = 160
            space_in = 55
            
            start_y_hid = 200
            space_hid = 70
            
            start_y_out = 200
            space_out = 135
            
            # Lógica de ativação sequencial (Input -> Hidden -> Output)
            active_inputs = {i for i, node in enumerate(self.nn_inputs) if node.get("active", False)}
            
            active_conns_l0 = {}
            for w in self.nn_visual_weights:
                if w["layer"] == 0 and w["from"] in active_inputs:
                    active_conns_l0[(w["from"], w["to"])] = w["val"]

            active_hidden = {t for (f, t) in active_conns_l0.keys()}
            
            active_conns_l1 = {}
            for w in self.nn_visual_weights:
                if w["layer"] == 1 and w["from"] in active_hidden:
                    active_conns_l1[(w["from"], w["to"])] = w["val"]

            import math
            blink = (math.sin(self.anim_timer * 0.15) + 1) / 2.0  # 0 a 1

            # Desenhar conexões finas (fully connected)
            for i in range(8):
                y1 = start_y_in + i * space_in
                for j in range(6):
                    y2 = start_y_hid + j * space_hid
                    if (i, j) in active_conns_l0:
                        r = int(180 + 75 * blink)
                        g = int(50 + 50 * blink)
                        b = int(50 * blink)
                        pygame.draw.line(self.screen, (r, g, b), (in_x, y1), (hid_x, y2), 2)
                    else:
                        pygame.draw.line(self.screen, (220, 220, 220), (in_x, y1), (hid_x, y2), 1)
                    
            for i in range(6):
                y1 = start_y_hid + i * space_hid
                for j in range(3):
                    y2 = start_y_out + j * space_out
                    if (i, j) in active_conns_l1:
                        r = int(180 + 75 * blink)
                        g = int(50 + 50 * blink)
                        b = int(50 * blink)
                        pygame.draw.line(self.screen, (r, g, b), (hid_x, y1), (out_x, y2), 2)
                    else:
                        pygame.draw.line(self.screen, (220, 220, 220), (hid_x, y1), (out_x, y2), 1)
                    
            # Desenhar os pesos textuais flutuantes
            for w in self.nn_visual_weights:
                if w["layer"] == 0:
                    x1 = in_x; y1 = start_y_in + w["from"] * space_in
                    x2 = hid_x; y2 = start_y_hid + w["to"] * space_hid
                else:
                    x1 = hid_x; y1 = start_y_hid + w["from"] * space_hid
                    x2 = out_x; y2 = start_y_out + w["to"] * space_out
                
                p = w["pos"]
                mx = x1 + (x2 - x1) * p
                my = y1 + (y2 - y1) * p
                
                color = (50, 200, 50) if w["val"] > 0 else (200, 50, 50)
                wt_surf = self.font_tooltip.render(f"{w['val']:+.1f}", True, (255,255,255))
                pygame.draw.rect(self.screen, color, (mx - 15, my - 10, wt_surf.get_width() + 10, wt_surf.get_height() + 4), border_radius=6)
                self.screen.blit(wt_surf, (mx - 10, my - 8))
                    
            # Desenhar Nós de Entrada
            for i, node in enumerate(self.nn_inputs):
                y = start_y_in + i * space_in
                bg_col = (255, 100, 50) if node["active"] else (30, 30, 30)
                if node["active"]:
                    pygame.draw.circle(self.screen, (255, 200, 150), (in_x, y), 18)
                pygame.draw.circle(self.screen, bg_col, (in_x, y), 12)
                
                # Label + Valor na esquerda
                txt = f"{node['label']}: {node['val']:.2f}"
                lbl = self.font_ui.render(txt, True, (120, 120, 120))
                self.screen.blit(lbl, (in_x - lbl.get_width() - 25, y - lbl.get_height()//2))
                
            # Desenhar Nós Ocultos
            for i in range(6):
                y = start_y_hid + i * space_hid
                if i in active_hidden:
                    halo_r, halo_g, halo_b = int(255), int(150 + 50 * blink), int(100 + 50 * blink)
                    in_r, in_g, in_b = int(200 + 55 * blink), int(50 + 50 * blink), int(20 + 30 * blink)
                    pygame.draw.circle(self.screen, (halo_r, halo_g, halo_b), (hid_x, y), 18)
                    pygame.draw.circle(self.screen, (in_r, in_g, in_b), (hid_x, y), 12)
                else:
                    pygame.draw.circle(self.screen, (30, 30, 30), (hid_x, y), 12)
                
            # Desenhar Nós de Saída
            for i, node in enumerate(self.nn_outputs):
                y = start_y_out + i * space_out
                bg_col = (255, 100, 50) if node.get("active", False) else (30, 30, 30)
                if node.get("active", False):
                    pygame.draw.circle(self.screen, (255, 200, 150), (out_x, y), 22)
                pygame.draw.circle(self.screen, bg_col, (out_x, y), 15)
                
                font_out = pygame.font.SysFont(FONT_FAMILY, 30, bold=True)
                lbl = font_out.render(node["label"], True, (0, 0, 0))
                self.screen.blit(lbl, (out_x + 30, y - lbl.get_height()//2))
                
        elif self.mode in ['bazooka', 'take_giant', 'take_behaviors', 'take_hero', 'take_speed']:
            for m in self.mountains:
                m.draw(self.screen)
            for cloud in self.clouds:
                cloud.draw(self.screen)
                
            self.draw_ground()
            
            for obs in self.obstacles:
                obs.draw(self.screen)
                
            self.dino.draw(self.screen)
            
            for m in self.missiles:
                m.draw(self.screen)
                
            for f in self.fires:
                f.draw(self.screen)
                
        else:
            for m in self.mountains:
                m.draw(self.screen)
            for cloud in self.clouds:
                cloud.draw(self.screen)

            if self.mode in ['start', 'timelapse', 'thumbnail', 'bazooka_rules']:
                ciclo = self.cycle_frames % 1200 if self.mode == 'timelapse' else 0
                if ciclo < 600 or self.mode in ['start', 'thumbnail', 'bazooka_rules']:
                    sun_y = 120 + ((ciclo - 500) * 2 if self.mode == 'timelapse' and ciclo > 500 else 0)
                    pygame.draw.circle(self.screen, (255, 230, 100), (SCREEN_WIDTH - 200, sun_y), 45)
                    pygame.draw.circle(self.screen, (255, 210, 50), (SCREEN_WIDTH - 200, sun_y), 38)
                    pygame.draw.circle(self.screen, (255, 240, 150), (SCREEN_WIDTH - 200, sun_y), 30)
                
                if self.mode == 'timelapse' and (ciclo >= 500 or ciclo < 100):
                    moon_y = 120 + ((100 - (ciclo - 500)) * 2 if 500 <= ciclo < 600 else ((ciclo - 1100) * 2 if 1100 <= ciclo < 1200 else 200))
                    if moon_y < 350:
                        pygame.draw.circle(self.screen, (220, 220, 230), (SCREEN_WIDTH - 200, moon_y), 45)
                        pygame.draw.circle(self.screen, current_bg, (SCREEN_WIDTH - 215, moon_y - 15), 45)

            elif self.mode == 'timelapse_meteor':
                ciclo = self.cycle_frames % 1800
                
                # Sol 1 (Dia 1) e Sol 2 (Dia 2)
                if ciclo < 400 or (800 <= ciclo < 1400):
                    if ciclo < 400:
                        sun_y = 120 + ((ciclo - 200) * 1.5 if ciclo > 200 else 0)
                    else: # 800 a 1400
                        if ciclo < 1000:
                            sun_y = 120 + ((1000 - ciclo) * 1.5)
                        elif ciclo > 1200:
                            sun_y = 120 + ((ciclo - 1200) * 1.5)
                        else:
                            sun_y = 120
                    if sun_y < 350:
                        pygame.draw.circle(self.screen, (255, 230, 100), (SCREEN_WIDTH - 200, sun_y), 45)
                        pygame.draw.circle(self.screen, (255, 210, 50), (SCREEN_WIDTH - 200, sun_y), 38)
                        pygame.draw.circle(self.screen, (255, 240, 150), (SCREEN_WIDTH - 200, sun_y), 30)
                
                # Lua 1 (Noite 1) e Lua 2 (Noite 2)
                if (200 < ciclo < 1000) or (1200 < ciclo < 1600):
                    if 200 < ciclo < 1000:
                        if ciclo < 400:
                            moon_y = 120 + ((400 - ciclo) * 1.5)
                        elif ciclo > 800:
                            moon_y = 120 + ((ciclo - 800) * 1.5)
                        else:
                            moon_y = 120
                    else: # 1200 a 1600
                        if ciclo < 1400:
                            moon_y = 120 + ((1400 - ciclo) * 1.5)
                        else:
                            moon_y = 120
                            
                    if moon_y < 350:
                        pygame.draw.circle(self.screen, (220, 220, 230), (SCREEN_WIDTH - 200, moon_y), 45)
                        pygame.draw.circle(self.screen, current_bg, (SCREEN_WIDTH - 215, moon_y - 15), 45)
                        
                if 1100 < ciclo <= 1560:
                    fall_prog = (ciclo - 1100) / 460.0
                    m_size = int(10 + fall_prog * 120)
                    m_x = -100 + int(fall_prog * (SCREEN_WIDTH // 2 + 200))
                    m_y = -200 + int(fall_prog * (GROUND_Y + 150))
                    
                    import random
                    for i in range(12):
                        tail_size = int(m_size * (1.0 - i/12.0))
                        if tail_size > 0:
                            tail_x = m_x - int(i * m_size * 0.9) + random.randint(-8, 8)
                            tail_y = m_y - int(i * m_size * 0.7) + random.randint(-8, 8)
                            alpha = int(255 * (1.0 - i/12.0))
                            
                            surf = pygame.Surface((tail_size*2, tail_size*2), pygame.SRCALPHA)
                            pygame.draw.circle(surf, (255, random.randint(50, 150), 0, alpha), (tail_size, tail_size), tail_size)
                            self.screen.blit(surf, (tail_x - tail_size, tail_y - tail_size))
                    
                    pygame.draw.circle(self.screen, (255, 100, 0), (m_x, m_y), m_size)
                    pygame.draw.circle(self.screen, (255, 200, 50), (m_x, m_y), int(m_size * 0.7))
                    pygame.draw.circle(self.screen, (255, 255, 255), (m_x, m_y), int(m_size * 0.4))
                    
                    for _ in range(8):
                        px = m_x + random.randint(-m_size, m_size)
                        py = m_y + random.randint(-m_size, m_size)
                        pygame.draw.circle(self.screen, (255, 255, 200), (px, py), random.randint(2, 5))
            
            self.draw_ground()
                
            for obs in self.obstacles:
                obs.draw(self.screen)
            for dino in self.dinos:
                dino.draw(self.screen)
            for m in getattr(self, 'missiles', []):
                m.draw(self.screen)
            for f in getattr(self, 'fires', []):
                f.draw(self.screen)

            if self.mode == 'timelapse_meteor':
                ciclo = self.cycle_frames % 1800
                if ciclo > 1560:
                    boom_prog = (ciclo - 1560) / 240.0
                    
                    if getattr(self, 'meteor_particles', None) is None or ciclo == 1561:
                        self.meteor_particles = []
                        import random, math
                        hit_x = -100 + int((1.0) * (SCREEN_WIDTH // 2 + 200))
                        hit_y = -200 + int((1.0) * (GROUND_Y + 150))
                        for _ in range(300):
                            angle = random.uniform(0, math.pi * 2)
                            speed = random.uniform(15, 60)
                            self.meteor_particles.append({
                                'x': float(hit_x), 'y': float(hit_y),
                                'vx': math.cos(angle) * speed,
                                'vy': math.sin(angle) * speed,
                                'size': random.randint(4, 18),
                                'color': random.choice([(255, 100, 0), (255, 200, 50), (255, 255, 200), (255,255,255)])
                            })
                            
                    for p in self.meteor_particles:
                        p['x'] += p['vx']
                        p['y'] += p['vy']
                        pygame.draw.circle(self.screen, p['color'], (int(p['x']), int(p['y'])), p['size'])
                        
                    if boom_prog > 0.15:
                        self.screen.fill((255, 255, 255))

            elif self.mode == 'bazooka_rules':
                # Particulas recarga
                if hasattr(self, 'reload_particles'):
                    for p in self.reload_particles:
                        pygame.draw.circle(self.screen, (100, 255, 100), (int(p['x']), int(p['y'])), 4)
                        
                # Desenhar explosao do gigante
                if hasattr(self, 'giant_boom'):
                    if self.giant_boom['timer'] > 0:
                        pygame.draw.circle(self.screen, (255, 150, 0), (int(self.giant_boom['x']), int(self.giant_boom['y'])), 80 - self.giant_boom['timer']*3)
                        self.giant_boom['timer'] -= 1
                        
                # HUD da Bazuca
                hud_x = SCREEN_WIDTH // 2
                hud_y = 80
                b_color = (50, 255, 50) if getattr(self, 'dino_ammo', 1) > 0 else (255, 50, 50)
                hud_text = "MUNIÇÃO: [ 1 / 1 ]" if getattr(self, 'dino_ammo', 1) > 0 else "MUNIÇÃO: [ VAZIA ]"
                font_hud = pygame.font.SysFont("Arial", 40, bold=True)
                txt_surf = font_hud.render(hud_text, True, b_color)
                txt_rect = txt_surf.get_rect(center=(hud_x, hud_y))
                # Fundo HUD
                pygame.draw.rect(self.screen, (30, 30, 30), txt_rect.inflate(20, 10), border_radius=5)
                pygame.draw.rect(self.screen, b_color, txt_rect.inflate(20, 10), 3, border_radius=5)
                self.screen.blit(txt_surf, txt_rect)
                
                # Texto da cena
                if getattr(self, 'scene_text', ""):
                    font_cena = pygame.font.SysFont("Arial", 45, bold=True)
                    t_surf = font_cena.render(self.scene_text, True, (255,255,255))
                    t_rect = t_surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 100))
                    
                    # Fundo do texto
                    bg_rect = t_rect.inflate(40, 20)
                    pygame.draw.rect(self.screen, (30, 30, 30), bg_rect, border_radius=15)
                    pygame.draw.rect(self.screen, (150, 150, 150), bg_rect, 2, border_radius=15)
                    self.screen.blit(t_surf, t_rect)

        self.render_ui()

    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.mode = 'menu'
                    elif event.key == pygame.K_1:
                        self.setup_start_mode()
                    elif event.key == pygame.K_2:
                        self.setup_photo_mode()
                    elif event.key == pygame.K_3:
                        self.setup_thumbnail_mode()
                    elif event.key == pygame.K_4:
                        self.setup_timelapse_mode()
                    elif event.key == pygame.K_5:
                        self.setup_population_mode()
                    elif event.key == pygame.K_6:
                        self.setup_mutation_mode()
                    elif event.key == pygame.K_7:
                        self.setup_nn_mode()
                    elif event.key == pygame.K_8:
                        self.setup_bazooka_mode()
                    elif event.key == pygame.K_9:
                        self.setup_take_giant()
                    elif event.key == pygame.K_0:
                        self.setup_take_behaviors()
                    elif event.key == pygame.K_MINUS:
                        self.setup_take_hero()
                    elif event.key == pygame.K_EQUALS:
                        self.setup_take_speed()
                    elif event.key == pygame.K_q:
                        self.setup_timelapse_meteor_mode()
                    elif event.key == pygame.K_w:
                        self.setup_bazooka_rules_mode()
                    elif event.key == pygame.K_SPACE and self.mode != 'menu':
                        if self.mode in ['bazooka', 'take_giant', 'take_behaviors', 'take_hero']:
                            # Atirar missel (centro da bazuca)

                            mx = self.dino.x + self.dino.width
                            my = self.dino.y + self.dino.height // 2 - 10
                            missile = Missile(mx, my, self.dino.id, 7.0, self.dino.color)
                            self.missiles.append(missile)
                        else:
                            self.paused = not self.paused
                    elif event.key == pygame.K_t and self.mode == 'bazooka':

                        obs = Obstacle(SCREEN_WIDTH + 50, 7.0, is_giant=False)
                        obs.type = 'cactus'; obs._cactus_variant = 'large'
                        self.obstacles.append(obs)
                    elif event.key == pygame.K_r:
                        if self.mode == 'bazooka':

                            obs = Obstacle(SCREEN_WIDTH + 50, 7.0, is_giant=True)
                            obs.type = 'giant_cactus'
                            self.obstacles.append(obs)
                        elif self.mode == 'take_giant':
                            self.setup_take_giant()
                        elif self.mode == 'take_behaviors':
                            style = self.behavior_style
                            self.setup_take_behaviors()
                            self.behavior_style = style
                        elif self.mode == 'take_hero':
                            self.setup_take_hero()
                        elif self.mode == 'take_speed':
                            self.setup_take_speed()
                    
                    elif self.mode == 'take_behaviors':
                        if event.key == pygame.K_1: self.behavior_style = 1
                        elif event.key == pygame.K_2: self.behavior_style = 2
                        elif event.key == pygame.K_3: self.behavior_style = 3
                        elif event.key == pygame.K_4: self.behavior_style = 4
                        
                    elif event.key == pygame.K_s and self.mode != 'menu':
                        self.draw_scene()
                        self.save_screenshot()

            self.update_animations()
            self.draw_scene()
            
            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    studio = CaptureStudio()
    studio.run()
