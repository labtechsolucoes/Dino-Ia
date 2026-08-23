#!/usr/bin/env python3
"""
dino_env.py — Clone do Jogo do Dinossauro do Google (Python + Pygame)
=====================================================================

Arquitetura com dois modos de execução:

  1. MODO TREINAMENTO (RL):
     - Sem renderização, alta velocidade.
     - Interface: reset() → state, play_step(action) → (state, reward, done, score)

  2. MODO DUELO (Humano vs IA):
     - Renderização 60 FPS, dois dinossauros simultâneos.
     - Interface: play_versus_mode(ai_predict_function)

Execução:
  python dino_env.py --mode versus    (Humano vs IA — padrão)
  python dino_env.py --mode train     (RL sem renderização)
  python dino_env.py --mode play      (Jogar sozinho)

Autor: Gerado via IA
"""

import pygame
import random
import sys
import colorsys

# ╔═══════════════════════════════════════════════════════════════╗
# ║              GERADOR DE CORES DISTINTAS                      ║
# ╚═══════════════════════════════════════════════════════════════╝

def generate_distinct_colors(n: int) -> list:
    """
    Gera N cores visualmente distintas e vibrantes distribuídas
    uniformemente na roda de cores HSV.

    Usado pelo play_population_mode() para colorir automaticamente
    cada dino de uma geração com uma cor única.

    Args:
        n: Número de cores a gerar.

    Returns:
        Lista de N tuplas RGB (r, g, b), cada valor em [0, 255].

    Exemplo:
        cores = generate_distinct_colors(100)
        for i, cor in enumerate(cores):
            dino = Dino(x=80, color=cor, name=f"Agente_{i}")
    """
    colors = []
    for i in range(n):
        # Distribui hue uniformemente em [0, 1)
        hue = i / n
        # Saturação e brilho altos para cores vivas e legíveis
        # Alterna levemente para evitar cores muito semelhantes quando n é grande
        saturation = 0.85 + 0.10 * ((i % 3) / 3.0)
        value      = 0.90 + 0.08 * ((i % 2) / 2.0)
        r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
        colors.append((int(r * 255), int(g * 255), int(b * 255)))
    return colors


# ╔═══════════════════════════════════════════════════════════════╗
# ║                    CONSTANTES DO JOGO                        ║
# ╚═══════════════════════════════════════════════════════════════╝

SCREEN_WIDTH  = 1400
SCREEN_HEIGHT = 700
GROUND_Y      = 630        # Linha do chão puxada um pouco para baixo
FPS           = 60

# Zona reservada para visualização da Rede Neural
# Os primeiros NN_PANEL_H pixels do topo são área livre (BG_COLOR, sem game objects)
NN_PANEL_H    = 480        # Ajustado para acomodar o pulo do Dino sem cortar a cabeça

# --- Paleta monocromática fiel ao original do Google ---
BG_COLOR       = (247, 247, 247)   # Fundo branco-cinza
DINO_COLOR     = (83,  83,  83)    # Cinza escuro original (#535353)
OBSTACLE_COLOR = (83,  83,  83)
GROUND_COLOR   = (83,  83,  83)
CLOUD_COLOR    = (210, 210, 210)
WHITE          = (247, 247, 247)
TEXT_COLOR     = (83,  83,  83)

# No modo versus, IA fica azul para diferenciar
PLAYER_COLOR   = (83,  83,  83)
AI_COLOR       = (60,  100, 160)

# Pixel margin for hitbox calculations (kept for RL state normalization)
P = 2

# --- Dimensões base do Dinossauro (tamanho nativo dos BMPs do Google) ---
DINO_W      = 40    # dino0.bmp largura
DINO_H      = 43    # dino0.bmp altura
DINO_DUCK_W = 56    # dino2.bmp largura
DINO_DUCK_H = 25    # dino2.bmp altura

# --- Física ---
GRAVITY        = 0.6
JUMP_VELOCITY  = -10.0
INITIAL_SPEED  = 6.0
MAX_SPEED      = 13.0
SPEED_INCREMENT= 0.001

# --- Obstáculos ---
MIN_OBSTACLE_GAP = 350
MAX_OBSTACLE_GAP = 700
# Pássaros voam em 3 alturas: rente ao chão (agachar), médio, alto (pular)
BIRD_Y_OPTIONS   = [GROUND_Y - 5, GROUND_Y - 22, GROUND_Y - 55]

# --- Ações do Agente RL ---
ACTION_NONE = 0
ACTION_JUMP = 1
ACTION_DUCK = 2
ACTION_SHOOT = 3


# ╔═══════════════════════════════════════════════════════════════╗
# ║              SISTEMA DE CARREGAMENTO DE IMAGENS               ║
# ╚═══════════════════════════════════════════════════════════════╝

import os as _os
ASSETS_DIR = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "assets")

# Imágenes globais (inicializadas por load_assets() após pygame.init())
IMG_DINO_RUN1  = None
IMG_DINO_RUN2  = None
IMG_DINO_DUCK1 = None
IMG_DINO_DUCK2 = None
IMG_DINO_DEAD  = None
IMG_DINO_BAZUCA1 = None
IMG_DINO_BAZUCA2 = None
IMG_BIRD1      = None
IMG_BIRD2      = None
IMG_CACTUS_SM  = None
IMG_CACTUS_LG  = None
IMG_CLOUD      = None
IMG_NEURON     = None
IMG_FOGO1      = None
IMG_FOGO2      = None
IMG_MISSEL1    = None
IMG_MISSEL2    = None
IMG_GROUND_LIST= []


def load_img(path):
    try:
        img = pygame.image.load(path).convert()
        # Pega a exata cor do pixel superior esquerdo (o fundo rosa) e define como transparente
        color = img.get_at((0, 0))
        img.set_colorkey(color, pygame.RLEACCEL)
        return img
    except Exception as e:
        print(f"Erro ao carregar imagem {path}: {e}")
        # Retorna um fallback para não quebrar o jogo
        surf = pygame.Surface((40, 40))
        surf.fill((255, 0, 0))
        return surf


def load_assets():
    """
    Carrega todos os assets PNG para as variáveis globais de imagem.
    DEVE ser chamada DEPOIS de pygame.init().
    PNGs ficam em assets/ ao lado deste arquivo.
    """
    global IMG_DINO_RUN1, IMG_DINO_RUN2, IMG_DINO_DUCK1, IMG_DINO_DUCK2
    global IMG_DINO_DEAD, IMG_DINO_BAZUCA1, IMG_DINO_BAZUCA2
    global IMG_BIRD1, IMG_BIRD2
    global IMG_CACTUS_SM, IMG_CACTUS_LG, IMG_CLOUD
    global IMG_NEURON, IMG_GROUND_LIST
    global IMG_FOGO1, IMG_FOGO2, IMG_MISSEL1, IMG_MISSEL2

    IMG_GROUND_LIST = []
    for i in range(1, 7):
        try:
            IMG_GROUND_LIST.append(load_img(_os.path.join(ASSETS_DIR, f"chao{i}.bmp")))
        except:
            pass

    IMG_NEURON     = pygame.transform.scale(load_img(_os.path.join(ASSETS_DIR, "neuronio.png")), (20, 20))

    IMG_DINO_RUN1  = load_img(_os.path.join(ASSETS_DIR, "dino0.bmp"))
    IMG_DINO_RUN2  = load_img(_os.path.join(ASSETS_DIR, "dino1.bmp"))
    IMG_DINO_DUCK1 = load_img(_os.path.join(ASSETS_DIR, "dino2.bmp"))
    IMG_DINO_DUCK2 = load_img(_os.path.join(ASSETS_DIR, "dino3.bmp"))
    IMG_DINO_DEAD  = load_img(_os.path.join(ASSETS_DIR, "dino4.bmp"))
    IMG_DINO_BAZUCA1 = load_img(_os.path.join(ASSETS_DIR, "dino0bazuca.bmp"))
    IMG_DINO_BAZUCA2 = load_img(_os.path.join(ASSETS_DIR, "dino1bazuca.bmp"))
    IMG_BIRD1      = pygame.transform.scale(load_img(_os.path.join(ASSETS_DIR, "passaro1.bmp")), (45, 30))
    IMG_BIRD2      = pygame.transform.scale(load_img(_os.path.join(ASSETS_DIR, "passaro2.bmp")), (45, 30))
    IMG_CACTUS_SM  = pygame.transform.scale(load_img(_os.path.join(ASSETS_DIR, "cactus1.bmp")), (25, 50))
    IMG_CACTUS_LG  = pygame.transform.scale(load_img(_os.path.join(ASSETS_DIR, "cactus5.bmp")), (50, 50))
    IMG_CLOUD      = load_img(_os.path.join(ASSETS_DIR, "nuvem.bmp"))
    IMG_FOGO1      = load_img(_os.path.join(ASSETS_DIR, "fogo1.bmp"))
    IMG_FOGO2      = load_img(_os.path.join(ASSETS_DIR, "fogo2.bmp"))
    IMG_MISSEL1    = load_img(_os.path.join(ASSETS_DIR, "missel1.bmp"))
    IMG_MISSEL2    = load_img(_os.path.join(ASSETS_DIR, "missil2.bmp"))

def _tint_image(img, color):
    if img is None:
        surf = pygame.Surface((40, 40), pygame.SRCALPHA)
        surf.fill((color[0], color[1], color[2], 255))
        return surf
        
    # Copia a imagem original (mantendo o colorkey e transparência)
    tinted = img.copy()
    
    # Substitui apenas a cor branca (o corpo do dino original) pela cor da IA
    # Assim, a bazuca (que é verde/marrom) mantém suas cores intactas!
    try:
        pa = pygame.PixelArray(tinted)
        pa.replace((255, 255, 255), color[:3])
        del pa
    except:
        pass
        
    # Retorna com suporte a alpha para fade-out dos mortos
    return tinted.convert_alpha()

def _remove_gradient_bg(img):
    if img is None: return img
    img_copy = img.copy()
    img_copy.set_colorkey(None)
    img_copy = img_copy.convert_alpha()
    w, h = img_copy.get_size()
    bg_r, bg_g, bg_b, _ = img_copy.get_at((0, 0))
    for x in range(w):
        for y in range(h):
            r, g, b, a = img_copy.get_at((x, y))
            # Se for bem parecido com a cor do canto (fundo rosa/gradiente)
            if abs(r - bg_r) < 85 and abs(g - bg_g) < 85 and abs(b - bg_b) < 85:
                img_copy.set_at((x, y), (0, 0, 0, 0))
    return img_copy


# ╔═══════════════════════════════════════════════════════════════╗
# ╔═══════════════════════════════════════════════════════════════╗
# ║                    CLASSE: Dino                              ║
# ╚═══════════════════════════════════════════════════════════════╝

_GHOST_CACHE = {}

class Dino:
    """Classe que representa o dinossauro (jogador ou IA)."""
    def __init__(self, x=50, color=(100, 100, 100), name="", is_human=False):
        self.x = x
        self.y = GROUND_Y - 47
        self.width  = 44
        self.height = 47
        self.color = color
        self.name = name
        self.is_human = is_human
        
        if self.is_human:
            self.x = 550
            self.color = (0, 255, 0)
            
        self.vel_y = 0
        self.is_jumping = False
        self.is_ducking = False
        self.alive      = True
        self.score      = 0
        self._anim      = 0
        
        # Injetando as imagens tingidas como atributos para bater com a função draw
        self.image_run1  = _tint_image(IMG_DINO_RUN1, color)
        self.image_run2  = _tint_image(IMG_DINO_RUN2, color)
        self.image_duck1 = _tint_image(IMG_DINO_DUCK1, color)
        self.image_duck2 = _tint_image(IMG_DINO_DUCK2, color)
        self.image_dead  = _tint_image(IMG_DINO_DEAD, color)
        self.image_bazuca1 = _tint_image(IMG_DINO_BAZUCA1, color)
        self.image_bazuca2 = _tint_image(IMG_DINO_BAZUCA2, color)

        self.id = id(self)
        self.ammo = 1.0
        self.bazooka_out = False
        self.fitness_bonus = 0

        # Rastreadores de Comportamento (Personalidade Genética)
        self.jump_distances = []
        self.duck_on_ground_frames = 0
        self.total_frames_on_ground = 0
        self.action_switches = 0
        self.last_action = None
        self.bird_jumps = 0
        self.duck_distances = []
        self.paranoid_jumps = 0
        self.jump_count = 0
        self.giant_kills = 0
        self.wasted_shots = 0
        self.shots_fired = 0

    def reset(self):
        """Retorna ao estado inicial (em pé, no chão)."""
        self.vel_y      = 0.0
        self.is_jumping = False
        self.is_ducking = False
        self.alive      = True
        self.score      = 0
        self._anim      = 0
        self.width      = DINO_W
        self.height     = DINO_H
        self.y          = GROUND_Y - self.height
        self.ammo       = 1.0
        self.bazooka_out = False
        self.fitness_bonus = 0
        self.giant_kills = 0
        self.wasted_shots = 0
        self.shots_fired = 0

    def shoot(self):
        """Dispara a bazuca se tiver munição."""
        if self.ammo >= 1.0:
            self.bazooka_out = True
            self.ammo = 0.0
            self.shots_fired += 1
            self.fitness_bonus += 0 # A ser processado pelo manager global
            return True # Retorna True se disparou para instanciar o Míssil no GameLoop
        return False

    def jump(self):
        """Inicia pulo se estiver no chão."""
        if not self.is_jumping:
            self.vel_y      = JUMP_VELOCITY
            self.is_jumping = True
            self.is_ducking = False
            self.width      = DINO_W
            self.height     = DINO_H

    def duck(self):
        """Abaixa o dino."""
        if not self.is_jumping:
            self.is_ducking = True
            if IMG_DINO_DUCK1:
                self.width  = IMG_DINO_DUCK1.get_width()
                self.height = IMG_DINO_DUCK1.get_height()
            else:
                self.width  = DINO_DUCK_W
                self.height = DINO_DUCK_H
            self.y = GROUND_Y - self.height

    def stand(self):
        """Sai do estado abaixado."""
        if self.is_ducking:
            self.is_ducking = False
            if IMG_DINO_RUN1:
                self.width  = IMG_DINO_RUN1.get_width()
                self.height = IMG_DINO_RUN1.get_height()
            else:
                self.width  = DINO_W
                self.height = DINO_H
            self.y = GROUND_Y - self.height

    def update(self, action=None, closest_obs_dist=None, closest_obs_type=None, game_speed=0.0):
        """Aplica física de gravidade e coleta dados."""
        # Recarga de munição removida (agora só recarrega ao passar pelo cacto gigante)

        if self.is_jumping or self.y < GROUND_Y - self.height:
            self.vel_y += GRAVITY
            self.y     += self.vel_y
            if self.y >= GROUND_Y - self.height:
                self.y          = GROUND_Y - self.height
                self.vel_y      = 0.0
                self.is_jumping = False
        self._anim += 1

        # COLETA DE DADOS COMPORTAMENTAIS
        if action is not None:
            if self.y == GROUND_Y - self.height:
                self.total_frames_on_ground += 1
                if self.last_action is not None and action != self.last_action:
                    self.action_switches += 1
                self.last_action = action
                
                # ACTION_DUCK == 2 (baseado nas constantes)
                if action == 2:
                    self.duck_on_ground_frames += 1
            
            # Borda de subida do pulo (ACTION_JUMP == 1)
            if action == 1 and self.last_action != 1:
                self.jump_count += 1
                if closest_obs_dist is not None:
                    self.jump_distances.append(closest_obs_dist)
                    if closest_obs_dist > 450:
                        self.paranoid_jumps += 1
                    if closest_obs_type == "bird":
                        self.bird_jumps += 1
                        
            # Borda de descida para abaixar (ACTION_DUCK == 2)
            if action == 2 and self.last_action != 2:
                if closest_obs_dist is not None:
                    self.duck_distances.append(closest_obs_dist)

    def get_trait_label(self):
        """Classifica a personalidade genética da IA, restrito a 6 perfis."""
        if self.giant_kills > 0:
            return "[ Exterminador ]"
            
        if self.shots_fired >= 2:
            return "[ Gatilho Fácil ]"
            
        if self.total_frames_on_ground > 0 and (self.duck_on_ground_frames / self.total_frames_on_ground) > 0.6:
            return "[ Furtivo ]"
            
        if len(self.jump_distances) >= 3:
            recent_jumps = self.jump_distances[-3:]
            if (max(recent_jumps) - min(recent_jumps)) <= 35:
                return "[ Calculista ]"
                
        if len(self.jump_distances) > 0:
            avg_dist = sum(self.jump_distances) / len(self.jump_distances)
            if avg_dist >= 120:
                return "[ Medroso ]"
            else:
                return "[ Kamikaze ]"
                
        return "[ O Aprendiz ]"

    def get_rect(self) -> pygame.Rect:
        padding = 8
        return pygame.Rect(
            int(self.x) + padding,
            int(self.y) + padding,
            self.width  - padding * 2,
            self.height - padding * 2,
        )

    def draw(self, surface, dead=False, alpha=255):
        # 1. Seleciona a imagem correta baseada no estado atual
        if dead:
            img = self.image_dead
        elif self.is_ducking:
            img = self.image_duck1 if (self._anim // 8) % 2 == 0 else self.image_duck2
        elif self.bazooka_out:
            img = self.image_bazuca1 if (self._anim // 8) % 2 == 0 else self.image_bazuca2
        else:
            img = self.image_run1 if (self._anim // 8) % 2 == 0 else self.image_run2

        # 2. Renderiza na tela lidando com o conflito do Alpha
        if alpha < 255:
            cache_key = (id(img), alpha)
            if cache_key not in _GHOST_CACHE:
                # Cria uma lousa transparente do tamanho exato da imagem
                tmp = pygame.Surface(img.get_size(), pygame.SRCALPHA)
                tmp.fill((255, 255, 255, 0)) 
                # Desenha a imagem na lousa (o colorkey já age aqui e remove o fundo)
                tmp.blit(img, (0, 0))
                # Aplica a transparência no dinossauro limpo
                tmp.set_alpha(alpha)
                _GHOST_CACHE[cache_key] = tmp
            
            # Joga na tela principal a partir do cache
            surface.blit(_GHOST_CACHE[cache_key], (self.x, self.y))
        else:
            # Se for o dinossauro principal (sem transparência), desenha direto
            surface.blit(img, (self.x, self.y))


# ╔═══════════════════════════════════════════════════════════════╗
# ║                   CLASSE: Obstacle                           ║
# ╚═══════════════════════════════════════════════════════════════╝

class Obstacle:
    """
    Obstáculo: cacto (chão) ou pterodáctilo (ar).
    Usa imagens PNG reais da pasta assets/.
    """

    # Tamanhos base (em pixels) usados antes dos PNGs carregarem
    _CACTUS_SIZES = {
        "small": (30, 80),
        "large": (75, 80),
    }
    _BIRD_SIZE = (90, 50)

    def __init__(self, x: float, game_speed: float, is_giant=False):
        self.x     = x
        self._anim = 0
        self.destruido_por = []
        self.is_giant = is_giant

        if random.random() < 0.28 and game_speed > 7.0:
            # ─ Pássaro ────────────────────────────────────────────
            self.type  = "bird"
            self.image = IMG_BIRD1
            self.width  = self.image.get_width() if self.image else self._BIRD_SIZE[0]
            self.height = self.image.get_height() if self.image else self._BIRD_SIZE[1]
            self.y      = random.choice(BIRD_Y_OPTIONS) - self.height
        elif is_giant:
            # ─ Cacto Gigante ─────────────────────────────────────────
            self.type       = "giant_cactus"
            self._cactus_variant = "giant"
            self.image = IMG_CACTUS_LG # Reusa a imagem grande
            self.width  = self.image.get_width() if self.image else self._CACTUS_SIZES["large"][0]
            self.height = 150 # Impossível pular
            # Como a imagem pode não ter 150px, esticamos na hora de desenhar
            self.y      = GROUND_Y - self.height
        else:
            # ─ Cacto Comum ──────────────────────────────────────────
            self.type       = "cactus"
            self._cactus_variant = random.choice(["small", "large"])
            self.image = IMG_CACTUS_SM if self._cactus_variant == "small" else IMG_CACTUS_LG
            
            self.width  = self.image.get_width() if self.image else self._CACTUS_SIZES[self._cactus_variant][0]
            self.height = self.image.get_height() if self.image else self._CACTUS_SIZES[self._cactus_variant][1]
            # Força o recálculo do Y pra encostar perfeitamente no chão
            self.y      = GROUND_Y - self.height

    def update(self, speed: float):
        self.x    -= speed
        self._anim += 1

    def get_rect(self) -> pygame.Rect:
        padding = 8
        return pygame.Rect(
            int(self.x) + padding,
            int(self.y) + padding,
            self.width  - padding * 2,
            self.height - padding * 2,
        )

    def draw(self, surface: pygame.Surface):
        frame = (self._anim // 10) % 2
        if self.type == "bird":
            img = IMG_BIRD1 if frame == 0 else IMG_BIRD2
        else:
            img = IMG_CACTUS_SM if self._cactus_variant == "small" else IMG_CACTUS_LG

        if img is not None:
            img = _tint_image(img, OBSTACLE_COLOR)
            if self.is_giant:
                # Estica a imagem para o tamanho gigante
                img = pygame.transform.scale(img, (self.width, self.height))
            surface.blit(img, (int(self.x), int(self.y)))
        else:
            # Fallback visual enquanto assets não estão carregados
            pygame.draw.rect(surface, OBSTACLE_COLOR,
                             (int(self.x), int(self.y), self.width, self.height))

    def is_off_screen(self) -> bool:
        return self.x + self.width + 10 < 0


# ╔═══════════════════════════════════════════════════════════════╗
# ║                     CLASSE: Cloud                            ║
# ╚═══════════════════════════════════════════════════════════════╝

class Mountain:
    def __init__(self):
        # Montanha simples gerada com polígonos
        self.width = random.randint(300, 600)
        self.height = random.randint(100, 200)
        self.x = SCREEN_WIDTH
        self.y = GROUND_Y - self.height
        
        self.surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        # Tons de cinza bem claros para ficar no fundo
        color = (225, 225, 225)
        # Três picos
        points = [
            (0, self.height),
            (self.width * 0.2, self.height * 0.3),
            (self.width * 0.4, self.height * 0.6),
            (self.width * 0.7, 0),
            (self.width, self.height)
        ]
        pygame.draw.polygon(self.surface, color, points)
        pygame.draw.polygon(self.surface, (200, 200, 200), points, 2)

    def update(self, speed):
        # Move-se mais devagar que as nuvens (paralaxe)
        self.x -= speed * 0.2

    def draw(self, surface):
        surface.blit(self.surface, (int(self.x), int(self.y)))


class Cloud:
    """Nuvem decorativa em estilo pixelado, usando PNG."""

    def __init__(self):
        self.x     = SCREEN_WIDTH + random.randint(20, 250)
        # Nuvens ficam só na faixa do jogo (abaixo do painel da Rede Neural)
        self.y     = random.randint(NN_PANEL_H + 20, GROUND_Y - 70)
        self.speed = random.uniform(0.5, 1.2)
        self.scale = random.choice([1, 2])   # escala relativa ao PNG base
        self.width = IMG_CLOUD.get_width() * self.scale if IMG_CLOUD else 60

    def update(self, game_speed):
        self.x -= self.speed + (game_speed * 0.1)

    def draw(self, surface: pygame.Surface):
        if IMG_CLOUD is None:
            return
            
        img = _tint_image(IMG_CLOUD, CLOUD_COLOR)
        
        if self.scale == 1:
            surface.blit(img, (int(self.x), self.y))
        else:
            w, h = img.get_size()
            scaled = pygame.transform.scale(img, (w * self.scale, h * self.scale))
            surface.blit(scaled, (int(self.x), self.y))

    def is_off_screen(self) -> bool:
        return self.x + self.width < 0


# ╔═══════════════════════════════════════════════════════════════╗
# ║                   CLASSE: Missile                            ║
# ╚═══════════════════════════════════════════════════════════════╝

class Missile:
    def __init__(self, x, y, dino_id, game_speed, color):
        self.x = x
        self.y = y
        self.dino_id = dino_id
        self.speed = game_speed * 1.8
        self._anim = 0
        
        # Não aplicamos _tint_image no míssil para não destruir o colorkey rosa 
        # nem achatar as cores internas (ele terá sua própria cor original)
        self.image1 = _remove_gradient_bg(IMG_MISSEL1)
        self.image2 = _remove_gradient_bg(IMG_MISSEL2)
        self.width = self.image1.get_width() if self.image1 else 20
        self.height = self.image1.get_height() if self.image1 else 10

    def update(self):
        self.x += self.speed
        self._anim += 1

    def draw(self, surface):
        img = self.image1 if (self._anim // 5) % 2 == 0 else self.image2
        if img:
            surface.blit(img, (int(self.x), int(self.y)))
        else:
            pygame.draw.rect(surface, (255, 0, 0), (int(self.x), int(self.y), self.width, self.height))

    def get_rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    def is_off_screen(self):
        return self.x > SCREEN_WIDTH


# ╔═══════════════════════════════════════════════════════════════╗
# ║                  CLASSE: FireVisual                          ║
# ╚═══════════════════════════════════════════════════════════════╝

class FireVisual:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self._anim = 0
        
        self.image1 = _remove_gradient_bg(IMG_FOGO1)
        self.image2 = _remove_gradient_bg(IMG_FOGO2)
        self.width = self.image1.get_width() if self.image1 else 30

    def update(self, game_speed):
        self.x -= game_speed
        self._anim += 1

    def draw(self, surface):
        img = self.image1 if (self._anim // 5) % 2 == 0 else self.image2
        if img:
            surface.blit(img, (int(self.x), int(self.y)))

    def is_off_screen(self):
        return self.x + self.width < 0


# ╔═══════════════════════════════════════════════════════════════╗
# ║                 CLASSE PRINCIPAL: DinoGame                   ║
# ╚═══════════════════════════════════════════════════════════════╝

class DinoGame:
    """
    Ambiente do Jogo do Dinossauro — compatível com Reinforcement Learning.

    ┌─────────────────────────────────────────────────────────────┐
    │  MODO 1 — TREINAMENTO RL (sem renderização, alta velocidade)│
    │                                                             │
    │    env = DinoGame(render=False)                             │
    │    state = env.reset()                                      │
    │    while True:                                              │
    │        action = agent.predict(state)  # ← PLUGAR IA AQUI  │
    │        state, reward, done, score = env.play_step(action)   │
    │        if done:                                             │
    │            state = env.reset()                              │
    │                                                             │
    │  MODO 2 — DUELO HUMANO vs IA (renderização 60 FPS)         │
    │                                                             │
    │    env = DinoGame(render=True)                              │
    │    env.play_versus_mode(minha_ia)  # ← PLUGAR IA AQUI     │
    └─────────────────────────────────────────────────────────────┘

    Estado retornado — tupla de 8 floats normalizados [0.0, 1.0]:
        0: dist_obst   — distância horizontal ao obstáculo mais próximo
        1: height_obst — posição Y do obstáculo (menor = mais alto)
        2: width_obst  — largura do obstáculo
        3: speed       — velocidade do jogo
        4: dino_y      — posição Y do dino
        5: is_jumping  — 1.0 se pulando
        6: is_ducking  — 1.0 se abaixado
        7: obst_type   — 0.0 cacto / 1.0 pássaro

    Ações: 0 = Correr, 1 = Pular, 2 = Abaixar
    """

    def __init__(self, render=False, unlimited_speed=False, use_bazooka=True):
        self.turbo_mode = False
        self.unlimited_speed = unlimited_speed
        self.use_bazooka = use_bazooka
        self.render_game = render
        self.display     = None
        self.clock       = None
        self.font        = None
        self.font_big    = None

        if self.render_game:
            pygame.init()
            self.display = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE | pygame.SCALED)
            load_assets()  # Carrega imagens PNG (DEVE ser depois do set_mode)
            pygame.display.set_caption("Dino Game")
            self.clock   = pygame.time.Clock()
            self._init_fonts()

        self.dino        = Dino(x=80, color=DINO_COLOR, name="Player")
        self.obstacles   = []
        self.clouds      = []
        self.mountains   = []
        self.game_speed  = INITIAL_SPEED
        self.score       = 0
        self.hi_score    = 0
        self.hi_speed    = 0.0
        self.frame_count = 0
        self.total_simulated_frames = 0
        self.game_over   = False

        self.ground_blocks = []
        if self.render_game:
            self._fill_ground()
        self.generation = 1
        self.history_best_scores = []
        self.history_best_speeds = []
        self.history_avg_scores = []
        import time
        self.start_time = time.time()

    def _init_fonts(self):
        font_family = 'segoeui, arial, sans-serif'
        self.FONT_TITLE = pygame.font.SysFont(font_family, 36, bold=True)
        self.FONT_SUBTITLE = pygame.font.SysFont(font_family, 24, bold=True)
        self.FONT_BODY = pygame.font.SysFont(font_family, 18, bold=False)
        self.FONT_BOLD = pygame.font.SysFont(font_family, 18, bold=True)
        
        self.FONT_NOTE = pygame.font.SysFont(font_family, 13, italic=True)
        self.FONT_LEGEND = pygame.font.SysFont("arial", 11)
        self.FONT_TOOLTIP = pygame.font.SysFont("arial", 12, bold=True)
        self.FONT_COURIER_LARGE = pygame.font.SysFont("courier new", 40, bold=True)
        self.FONT_COURIER_NORMAL = pygame.font.SysFont("courier new", 20)
        self.FONT_COURIER_LEARNED = pygame.font.SysFont("courier new", 45, bold=True)
        self.FONT_COURIER_INFO = pygame.font.SysFont("courier new", 28, bold=True)
        
        # Mantém aliases para o resto do código que ainda usa
        self.font = self.FONT_BODY
        self.font_big = self.FONT_TITLE

    def _fill_ground(self):
        current_x = 0
        if self.ground_blocks:
            current_x = self.ground_blocks[-1]['x'] + self.ground_blocks[-1]['img'].get_width()
        
        while current_x < SCREEN_WIDTH + 400:
            if not IMG_GROUND_LIST:
                break
            img = random.choice(IMG_GROUND_LIST)
            self.ground_blocks.append({'x': current_x, 'img': img})
            current_x += img.get_width()

    def _update_ground(self):
        if not self.render_game or not hasattr(self, 'ground_blocks'):
            return
            
        for block in self.ground_blocks:
            block['x'] -= self.game_speed
            
        # Remover blocos fora da tela e preencher novos
        if self.ground_blocks and self.ground_blocks[0]['x'] + self.ground_blocks[0]['img'].get_width() < 0:
            self.ground_blocks.pop(0)
            self._fill_ground()

    # ────────────────────────────────────────────────────────
    #  INTERFACE RL: reset() e play_step(action)
    # ────────────────────────────────────────────────────────

    def reset(self) -> tuple:
        """
        Reseta o jogo ao estado inicial.
        Returns: state (tuple de 8 floats normalizados).
        """
        self.dino.reset()
        self.obstacles.clear()
        self.clouds.clear()
        self.mountains.clear()
        self.game_speed  = INITIAL_SPEED
        self.score       = 0
        self.frame_count = 0
        self.game_over   = False
        self._spawn_obstacle()
        return self._get_state()

    def play_step(self, action: int) -> tuple:
        """
        Executa UM frame do jogo com a ação fornecida.

        ╔═══════════════════════════════════════════════════╗
        ║  INTERFACE PRINCIPAL PARA REINFORCEMENT LEARNING ║
        ║  Plugue seu agente aqui para treinar a IA.       ║
        ╚═══════════════════════════════════════════════════╝

        Args:
            action: 0 = Correr, 1 = Pular, 2 = Abaixar.

        Returns:
            (state, reward, game_over, score)
        """
        reward = 0.1

        if action == ACTION_JUMP:
            self.dino.jump()
        elif action == ACTION_DUCK:
            self.dino.duck()
        else:
            self.dino.stand()

        self.dino.update()

        for obs in self.obstacles:
            obs.update(self.game_speed)
        
        self._update_ground()

        new_obs = []
        for obs in self.obstacles:
            if obs.is_off_screen():
                reward += 1.5
            else:
                new_obs.append(obs)
        self.obstacles = new_obs

        self._maybe_spawn_obstacle()
        
        # --- Atualiza Nuvens e Montanhas ---
        self._update_clouds()

        if self.unlimited_speed:
            self.game_speed += SPEED_INCREMENT
        else:
            self.game_speed = min(MAX_SPEED, self.game_speed + SPEED_INCREMENT)

        done = self._check_collision(self.dino)
        if done:
            reward     = -100.0
            self.game_over = True

        # Contagem de frames do jogo
        self.frame_count += 1
        self.total_simulated_frames += 1
        self.score += self.game_speed
        if self.score > self.hi_score:
            self.hi_score = self.score
            
        self.hi_speed = max(getattr(self, 'hi_speed', 0.0), self.game_speed)

        return self._get_state(), reward, done, self.score

    # ────────────────────────────────────────────────────────
    #  OBSERVAÇÃO / ESTADO
    # ────────────────────────────────────────────────────────

    def _get_state(self, dino=None) -> tuple:
        """
        Calcula o vetor de estado (observação) para o agente RL.
        """
        if dino is None:
            dino = self.dino

        nearest  = None
        min_dist = float('inf')
        second_nearest = None
        min_dist_2 = float('inf')
        
        for obs in self.obstacles:
            dist = obs.x - dino.x
            if dist > -obs.width:
                if dist < min_dist:
                    second_nearest = nearest
                    min_dist_2 = min_dist
                    min_dist = dist
                    nearest = obs
                elif dist < min_dist_2:
                    min_dist_2 = dist
                    second_nearest = obs

        def obs_to_state(obs):
            if obs is not None:
                dist_n   = max(0.0, min(1.0, (obs.x - dino.x) / SCREEN_WIDTH))
                height_n = max(0.0, min(1.0, obs.y / SCREEN_HEIGHT))
                width_n  = max(0.0, min(1.0, obs.width / 150.0))
                # Tipo: 0.0=cacto, 0.5=passaro, 1.0=cacto gigante
                if obs.type == "giant_cactus": type_n = 1.0
                elif obs.type == "bird": type_n = 0.5
                else: type_n = 0.0
                return dist_n, height_n, width_n, type_n
            return 1.0, 1.0, 0.0, 0.0

        d1, h1, w1, t1 = obs_to_state(nearest)
        d2, h2, w2, t2 = obs_to_state(second_nearest)

        if self.use_bazooka:
            return (
                max(0.0, min(1.0, dino.y / SCREEN_HEIGHT)),
                max(0.0, min(1.0, self.game_speed / MAX_SPEED)),
                d1, t1, w1,
                d2, t2,
                dino.ammo,
                1.0 if dino.bazooka_out else 0.0,
                1.0 if dino.is_jumping else 0.0
            )
        else:
            return (
                max(0.0, min(1.0, dino.y / SCREEN_HEIGHT)),
                max(0.0, min(1.0, self.game_speed / MAX_SPEED)),
                d1, t1, w1,
                d2, t2,
                1.0 if dino.is_jumping else 0.0
            )

    # ────────────────────────────────────────────────────────
    #  LÓGICA INTERNA
    # ────────────────────────────────────────────────────────

    def _maybe_spawn_obstacle(self):
        if not self.obstacles:
            self._spawn_obstacle()
            return
        rightmost = max(self.obstacles, key=lambda o: o.x)
        gap = random.randint(MIN_OBSTACLE_GAP, MAX_OBSTACLE_GAP)
        if SCREEN_WIDTH - rightmost.x >= gap:
            self._spawn_obstacle()

    def _spawn_obstacle(self):
        x = SCREEN_WIDTH + random.randint(20, 120)
        # 10% de chance de spawnar um cacto gigante se o jogo permitir bazucas (verificado globalmente via config, assumimos sempre para este ambiente modificado ou se preferir podemos vincular ao use_bazooka).
        # Vamos assumir que use_bazooka é um atributo instanciado ou apenas gera globalmente.
        use_bazooka = getattr(self, 'use_bazooka', True)
        # 10% de chance de cacto gigante APENAS se a velocidade for > 8.0 (Fase 3)
        if use_bazooka and self.game_speed > 8.0 and random.random() < 0.10:
            self.obstacles.append(Obstacle(x, self.game_speed, is_giant=True))
        else:
            self.obstacles.append(Obstacle(x, self.game_speed, is_giant=False))

    def _check_collision(self, dino) -> bool:
        dr = dino.get_rect()
        for obs in self.obstacles:
            if dino.id in getattr(obs, 'destruido_por', []):
                continue
            if dr.colliderect(obs.get_rect()):
                return True
        return False

    # ────────────────────────────────────────────────────────
    #  RENDERIZAÇÃO
    # ────────────────────────────────────────────────────────

    def _draw_ground(self):
        """Parallax Scrolling com montanhas/chão."""
        pygame.draw.line(self.display, (220, 220, 220),
                         (0, NN_PANEL_H), (SCREEN_WIDTH, NN_PANEL_H), 1)

        pygame.draw.line(self.display, GROUND_COLOR,
                         (0, GROUND_Y), (SCREEN_WIDTH, GROUND_Y), 2)
        
        if hasattr(self, 'ground_blocks'):
            for block in self.ground_blocks:
                img = block['img']
                self.display.blit(img, (int(block['x']), GROUND_Y - img.get_height()))

    def _update_clouds(self):
        # Spawna Nuvens
        if self.frame_count % 150 == 0 and len(self.clouds) < 6:
            self.clouds.append(Cloud())
            
        # Spawna Montanhas
        if len(self.mountains) == 0 or self.mountains[-1].x < SCREEN_WIDTH - random.randint(800, 1500):
            if random.random() < 0.005:
                self.mountains.append(Mountain())

        for c in self.clouds:
            c.update(self.game_speed)
        self.clouds = [c for c in self.clouds if not c.is_off_screen()]
        
        for m in self.mountains:
            m.update(self.game_speed)
        self.mountains = [m for m in self.mountains if m.x + m.width > 0]

    def _draw_hud(self, score: float, hi: float = None):
        """HUD de Odômetro (Minimalista/Científico)."""
        if hi is None:
            hi = self.hi_score
            
        def format_dist(pixels):
            # Escala real do T-Rex (4.0m de altura)
            pixels_per_meter = 43 / 4.0  # DINO_H = 43
            metros = int(pixels / pixels_per_meter)
            if metros >= 1000:
                return f"{metros / 1000.0:.2f} km"
            return f"{str(metros).zfill(5)} m"
            
        hi_str = format_dist(hi)
        curr_str = format_dist(score)
        
        label = f"HI: {hi_str}   |   ATUAL: {curr_str}"
        # Usa TEXT_COLOR que é Cinza Escuro (83, 83, 83) e alinha exatamente no mesmo Y que os outros (20)
        surf = self.FONT_SUBTITLE.render(label, True, TEXT_COLOR)
        rect = surf.get_rect(topright=(SCREEN_WIDTH - 20, 20))
        self.display.blit(surf, rect)

    def _draw_ranking_table(self, current_best: float):
        """Desenha a tabela Top 10 das melhores gerações na direita da tela."""
        if not hasattr(self, 'history_best_scores'):
            return
            
        def format_dist(pixels):
            pixels_per_meter = 43 / 4.0
            metros = int(pixels / pixels_per_meter)
            if metros >= 1000:
                return f"{metros / 1000.0:.2f} km"
            return f"{str(metros).zfill(5)} m"
            
        # Combina histórico com o melhor atual da geração atual
        rankings = []
        for i, score in enumerate(self.history_best_scores):
            spd = self.history_best_speeds[i] if hasattr(self, 'history_best_speeds') and i < len(self.history_best_speeds) else 13.0
            rankings.append((score, i + 1, spd))
            
        if current_best > 0:
            rankings.append((current_best, self.generation, self.game_speed))
            
        gen_to_data = {}
        for score, gen, spd in rankings:
            if gen not in gen_to_data or score > gen_to_data[gen][0]:
                gen_to_data[gen] = (score, spd)
                
        sorted_ranks = sorted(gen_to_data.items(), key=lambda x: x[1][0], reverse=True)[:10]
        if not sorted_ranks:
            return
            
        table_x = 1400 - 310  # Ajustado para a lista começar exatamente alinhada com o título
        table_y = 80
        
        title_surf = self.FONT_BOLD.render("RANKING TOP 10 GERAÇÕES", True, (83, 83, 83))
        self.display.blit(title_surf, title_surf.get_rect(midtop=(table_x + 120, table_y)))
        
        y_offset = table_y + 35
        for i, (gen, (score, spd)) in enumerate(sorted_ranks):
            # Cores Ouro, Prata, Bronze escurecidos para contrastar com o fundo claro
            if i == 0: color = (200, 160, 0)
            elif i == 1: color = (130, 130, 130)
            elif i == 2: color = (180, 100, 50)
            else: color = (100, 100, 100)
                
            pos_str = f"{i+1}º"
            gen_str = f"G{gen}"
            dist_str = format_dist(score)
            
            # Converte velocidade
            spd_kmh = (spd * 60.0 / 10.75) * 3.6
            spd_str = f"{spd_kmh:.0f} km/h"
            
            # Se for a geração atual, destaca visualmente
            if gen == self.generation:
                row_str = f"{pos_str} [ATUAL] {dist_str} | {spd_str}"
                row_surf = self.FONT_BOLD.render(row_str, True, (0, 0, 0)) # Negrito e Preto
            else:
                row_str = f"{pos_str} {gen_str} - {dist_str} | {spd_str}"
                row_surf = self.FONT_BODY.render(row_str, True, color)
                
            self.display.blit(row_surf, (table_x, y_offset))
            y_offset += 25

    def _draw_game_over_screen(self, surface):
        """Tela de Game Over, centrada na área livre (Y=250)."""
        # Centro vertical na metade da área branca (área livre)
        game_cy = 250

        # "GAME OVER" com letras espaçadas
        go_surf = self.font_big.render("G A M E   O V E R", True, TEXT_COLOR)
        go_rect = go_surf.get_rect(center=(SCREEN_WIDTH // 2, game_cy - 30))
        surface.blit(go_surf, go_rect)

        # Botão de restart (quadrado cinza com seta branca)
        btn_cx, btn_cy, btn_r = SCREEN_WIDTH // 2, game_cy + 20, 18
        pygame.draw.rect(surface, TEXT_COLOR,
                         (btn_cx - btn_r - 2, btn_cy - btn_r - 2,
                          (btn_r + 2) * 2, (btn_r + 2) * 2), border_radius=4)
        arrow = [(btn_cx - 7, btn_cy - 9),
                 (btn_cx - 7, btn_cy + 9),
                 (btn_cx + 10, btn_cy)]
        pygame.draw.polygon(surface, BG_COLOR, arrow)

    def _draw_graph(self, current_best=None, current_avg=None, best_dino=None):
        """Desenha o gráfico de aprendizado no lado esquerdo superior."""
        if self.display is None:
            return
            
        # 1. DESTAQUE DA GERAÇÃO (HUD)
        gen_surf = self.FONT_TITLE.render(f"GERAÇÃO: {self.generation}", True, TEXT_COLOR)
        self.display.blit(gen_surf, (20, 20))
            
        # 2. REPOSICIONAMENTO DO GRÁFICO
        gx, gy, gw, gh = 20, 110, 550, 220
        
        # Fundo e borda
        pygame.draw.rect(self.display, (255, 255, 255), (gx, gy, gh, gh))
        pygame.draw.rect(self.display, (180, 180, 180), (gx, gy, gw, gh), 1)
        
        # Grid lines
        for i in range(1, 10):
            # linhas verticais
            vx = gx + i * (gw // 10)
            pygame.draw.line(self.display, (230, 230, 230), (vx, gy), (vx, gy + gh))
            # linhas horizontais
            vy = gy + i * (gh // 10)
            pygame.draw.line(self.display, (230, 230, 230), (gx, vy), (gx + gw, vy))
            

        # Preparar dados unindo o histórico com o valor vivo atual
        best_data = list(self.history_best_scores)
        if current_best is not None:
            best_data.append(current_best)
            
        avg_data = list(self.history_avg_scores)
        if current_avg is not None:
            avg_data.append(current_avg)
            
        # 4. LÓGICA DO GRÁFICO DE LINHA
        max_score = 10
        if best_data:
            max_score = max(10, max(best_data))
            
        def plot_line(data, color, draw_labels=False):
            if not data: return
            
            if len(data) == 1:
                pygame.draw.circle(self.display, color, (gx, int(gy + gh - (data[0]/max_score)*gh)), 3)
                if draw_labels:
                    lbl = small_font.render(f"G1", True, TEXT_COLOR)
                    self.display.blit(lbl, (gx, gy + gh + 5))
            else:
                pts = []
                for idx, val in enumerate(data):
                    px = gx + (idx / (len(data) - 1)) * gw
                    py = gy + gh - (val / max_score) * gh
                    pts.append((px, int(py)))
                pygame.draw.lines(self.display, color, False, pts, 2)
        
        plot_line(best_data, (50, 50, 180))
        plot_line(avg_data, (180, 50, 50))
        
        # Rótulo Eixo Y (Rotacionado)
        y_label = self.font.render("Distância", True, TEXT_COLOR)
        y_label_rot = pygame.transform.rotate(y_label, 90)
        self.display.blit(y_label_rot, (gx - 18, gy + gh//2 - y_label_rot.get_height()//2))
        
        # Textos abaixo do gráfico (Empurrados mais para baixo para dar espaço aos números)
        text_y = gy + gh + 25
        # Matemática Arcade: converte pixels/frame para km/h
        # 1 frame = 1/60 seg. Então px/seg = game_speed * 60
        # Metros/seg = px_seg / 10.75. km/h = m_s * 3.6
        kmh = (self.game_speed * 60 / 10.75) * 3.6
        hi_speed = getattr(self, 'hi_speed', 0.0)
        hi_kmh = (hi_speed * 60 / 10.75) * 3.6
        
        labels = [
            f"Clock: {self.frame_count / FPS:.3f} segundo",
            f"Velocidade Atual: {self.game_speed:.2f} px/f ({kmh:.0f} km/h)",
            f"Velocidade Recorde: {hi_speed:.2f} px/f ({hi_kmh:.0f} km/h)",
            f"Distância Recorde: {int(self.hi_score)} pixels",
            f"Distância Atual: {int(self.score)} pixels"
        ]
        
        y_offset = text_y
        for text in labels:
            surf = self.FONT_BODY.render(text, True, TEXT_COLOR)
            self.display.blit(surf, (gx, y_offset))
            y_offset += 25
            
        if best_dino:
            # Expandiu a Visão Computacional em largura e altura para preencher o vazio
            self._draw_dino_vision(best_dino, 350, gy + gh + 30, 650, 115)

    def _draw_dino_vision(self, best_dino, x, y, width, height):
        """Renderiza a 'Visão Computacional' (Hitboxes e Raycast) do dinossauro focado."""
        if not best_dino: return
        
        cam_surf = pygame.Surface((width, height))
        cam_surf.fill((240, 240, 240)) # Fundo cinza bem claro
        
        # Borda fina azul-acinzentada
        pygame.draw.rect(cam_surf, (150, 160, 180), (0, 0, width, height), 2)
        
        # Titulo da Câmera
        title = self.FONT_TOOLTIP.render("VISÃO COMPUTACIONAL DA IA", True, (100, 110, 130))
        cam_surf.blit(title, (width//2 - title.get_width()//2, 8))
        
        # Lógica da Câmera Virtual
        dino_cam_x = 60 # Dino fica fixo aqui
        
        # Fator de escala adaptado para a câmera estendida (maior = mais zoom)
        scale = 0.8
        
        # O offset baseia-se na posição do dino
        offset_x = best_dino.x - (dino_cam_x / scale)
        offset_y = GROUND_Y - ((height - 15) / scale) # Chão fica no fundo
        
        # Chão
        ground_py = int((GROUND_Y - offset_y) * scale)
        pygame.draw.line(cam_surf, (100, 100, 100), (0, ground_py), (width, ground_py), 2)
        
        # Obstáculos
        closest_obs = None
        min_dist = float('inf')
        for obs in self.obstacles:
            # Checa o mais próximo para o Raycast
            dist = obs.x - best_dino.x
            if dist > -obs.width and dist < min_dist:
                min_dist = dist
                closest_obs = obs

            # Desenhar Hitbox do obstáculo
            obs_cam_x = int((obs.x - offset_x) * scale)
            obs_cam_y = int((obs.y - offset_y) * scale)
            obs_w = int(obs.width * scale)
            obs_h = int(obs.height * scale)
            
            if -obs_w < obs_cam_x < width:
                # Retângulo Vermelho translúcido
                s = pygame.Surface((obs_w, obs_h), pygame.SRCALPHA)
                s.fill((255, 50, 50, 80))
                pygame.draw.rect(s, (255, 0, 0, 255), (0, 0, obs_w, obs_h), 2)
                cam_surf.blit(s, (obs_cam_x, obs_cam_y))
                
        # Dino Hitbox
        dino_cam_y = int((best_dino.y - offset_y) * scale)
        d_w = int(best_dino.width * scale)
        d_h = int(best_dino.height * scale)
        
        s_dino = pygame.Surface((d_w, d_h), pygame.SRCALPHA)
        s_dino.fill((50, 255, 50, 80))
        pygame.draw.rect(s_dino, (0, 200, 0, 255), (0, 0, d_w, d_h), 2)
        cam_surf.blit(s_dino, (dino_cam_x, dino_cam_y))
        
        # Raycast Laser
        if closest_obs:
            obs_cam_x = int((closest_obs.x - offset_x) * scale)
            obs_cam_y = int((closest_obs.y - offset_y) * scale)
            
            start_pos = (dino_cam_x + d_w, dino_cam_y + d_h//2)
            end_pos = (obs_cam_x, obs_cam_y + int((closest_obs.height * scale) // 2))
            
            pygame.draw.line(cam_surf, (255, 0, 0), start_pos, end_pos, 2)
            pygame.draw.circle(cam_surf, (255, 0, 0), end_pos, 4)
            
            # Texto da Distância (No meio do raio)
            mid_x = (start_pos[0] + end_pos[0]) // 2
            mid_y = (start_pos[1] + end_pos[1]) // 2 - 15
            dist_text = self.FONT_NOTE.render(f"Dist: {int(min_dist)}", True, (200, 0, 0))
            cam_surf.blit(dist_text, (mid_x - dist_text.get_width()//2, mid_y))

        self.display.blit(cam_surf, (x, y))

    def _draw_neural_network(self, state, action, activations=None):
        """Desenha a simulação da Rede Neural na área superior."""
        if self.display is None:
            return
            
        inputs = [
            ("Dist. Obs.", state[0]), ("Alt. Obs.", state[1]), ("Larg. Obs.", state[2]),
            ("Velocidade", state[3]), ("Dino Y", state[4]), ("Pulando", state[5]),
            ("Abaixando", state[6]), ("Tipo Obs.", state[7])
        ]
        # Se for estado expandido (Bazuca)
        if len(state) >= 10:
            inputs.append(("Munição", state[8]))
            inputs.append(("Bazuca Sacada", state[9]))
            
        outputs_labels = ["Correr", "Pular", "Abaixar", "Atirar"]
        
        if activations is None:
            activations = {
                'input': list(state),
                'hidden': [random.random() for _ in range(6)],
                'output': [1.0 if k == action else 0.0 for k in range(4)]
            }
            
        # Oculta "Atirar" se Bazuca estiver desligada
        if not getattr(self, 'use_bazooka', True):
            outputs_labels = ["Correr", "Pular", "Abaixar"]
            activations = dict(activations) # shallow copy
            activations['output'] = list(activations['output'][:3])
            
        input_nodes = len(activations['input'])
        output_nodes = len(activations['output'])
        hidden_acts = activations['hidden']
        is_matrix_mode = len(hidden_acts) > 20
        hidden_nodes = 6 if not is_matrix_mode else len(hidden_acts)
        
        # ── LAYOUT ──
        if is_matrix_mode:
            # DQN: Cérebro à DIREITA (com ramificações completas)
            
            matrix_size = int(len(hidden_acts) ** 0.5)  # 16
            cell_size = 20  # Restaurado para o tamanho grande
            grid_w = matrix_size * cell_size  # 320px
            grid_h = matrix_size * cell_size  # 320px
            
            # Posicionar o grid centralizado na metade direita
            matrix_x = 880
            matrix_y = 110  # Respeita a Zona do Cabeçalho
            
            # Inputs à esquerda do grid, outputs à direita
            input_x = matrix_x - 160
            output_x = matrix_x + grid_w + 80
            nn_y_start = matrix_y - 10
            nn_height = grid_h + 20
            
            escala_y_in = nn_height / max(1, input_nodes - 1)
            escala_y_out = nn_height / max(1, output_nodes - 1)
            
            # ── RAMIFICAÇÕES: Input → cada ROW do grid ──
            for i in range(input_nodes):
                act_in = activations['input'][i]
                in_y = int(nn_y_start + i * escala_y_in)
                
                for row in range(matrix_size):
                    row_y = matrix_y + row * cell_size + cell_size // 2
                    row_start = row * matrix_size
                    row_acts = hidden_acts[row_start:row_start + matrix_size]
                    row_avg = sum(row_acts) / max(1, len(row_acts))
                    
                    if act_in > 0.4 and row_avg > 0.2:
                        cor = (255, 80, 80, 180)
                        thick = 2
                    else:
                        cor = (220, 220, 220)
                        thick = 1
                    
                    pygame.draw.line(self.display, cor[:3],
                                    (input_x + 10, in_y),
                                    (matrix_x - 2, row_y), thick)
            
            # ── GRID HEATMAP (Camada Oculta) ──
            pygame.draw.rect(self.display, (70, 70, 90),
                            (matrix_x - 4, matrix_y - 4, grid_w + 8, grid_h + 8),
                            width=2, border_radius=6)
            
            grid_title = self.FONT_SUBTITLE.render(f"CAMADA OCULTA  ·  {len(hidden_acts)} neurônios", True, (70, 70, 70))
            self.display.blit(grid_title, grid_title.get_rect(midbottom=(matrix_x + grid_w // 2, matrix_y - 10)))
            
            for i, act_hid in enumerate(hidden_acts):
                row = i // matrix_size
                col = i % matrix_size
                r_x = matrix_x + col * cell_size
                r_y = matrix_y + row * cell_size
                
                # Paleta gradiente
                if act_hid <= 0: r_color = (20, 20, 30)
                elif act_hid < 0.2: t = act_hid / 0.2; r_color = (int(20 + 10*t), int(20 + 30*t), int(30 + 120*t))
                elif act_hid < 0.4: t = (act_hid - 0.2) / 0.2; r_color = (int(30*(1-t)), int(50 + 180*t), int(150 + 105*t))
                elif act_hid < 0.6: t = (act_hid - 0.4) / 0.2; r_color = (int(200*t), int(230 + 25*t), int(255*(1-t)))
                elif act_hid < 0.8: t = (act_hid - 0.6) / 0.2; r_color = (int(200 + 55*t), int(255), int(0))
                else: t = (act_hid - 0.8) / 0.2; r_color = (255, int(255*(1-t)), 0)
                pygame.draw.rect(self.display, r_color, (r_x + 1, r_y + 1, cell_size - 2, cell_size - 2))
            
            # ── LEGENDA DE CORES (Heatmap Scale) ──
            legend_y = matrix_y + grid_h + 15
            legend_x = matrix_x
            legend_w = grid_w
            legend_h = 12
            
            steps = 60
            for s in range(steps):
                t_norm = s / (steps - 1)
                if t_norm <= 0: c = (20, 20, 30)
                elif t_norm < 0.2: t = t_norm / 0.2; c = (int(20 + 10*t), int(20 + 30*t), int(30 + 120*t))
                elif t_norm < 0.4: t = (t_norm - 0.2) / 0.2; c = (int(30*(1-t)), int(50 + 180*t), int(150 + 105*t))
                elif t_norm < 0.6: t = (t_norm - 0.4) / 0.2; c = (int(200*t), int(230 + 25*t), int(255*(1-t)))
                elif t_norm < 0.8: t = (t_norm - 0.6) / 0.2; c = (int(200 + 55*t), int(255), int(0))
                else: t = (t_norm - 0.8) / 0.2; c = (255, int(255*(1-t)), 0)
                
                sx = legend_x + int(s * legend_w / steps)
                sw = max(1, int(legend_w / steps) + 1)
                pygame.draw.rect(self.display, c, (sx, legend_y, sw, legend_h))
            
            # Borda da legenda
            pygame.draw.rect(self.display, (100, 100, 120), (legend_x, legend_y, legend_w, legend_h), width=1)
            
            # Labels da escala
            self.display.blit(self.FONT_BODY.render("0.0 Inativo", True, (100, 100, 100)), (legend_x, legend_y + legend_h + 3))
            lbl_max = self.FONT_BODY.render("1.0 Máximo", True, (100, 100, 100))
            self.display.blit(lbl_max, (legend_x + legend_w - lbl_max.get_width(), legend_y + legend_h + 3))
            lbl_mid = self.FONT_BODY.render("Ativação", True, (100, 100, 100))
            self.display.blit(lbl_mid, (legend_x + legend_w // 2 - lbl_mid.get_width() // 2, legend_y + legend_h + 3))
            
            # ── RAMIFICAÇÕES: cada COLUMN do grid → Output ──
            for col in range(matrix_size):
                col_acts = [hidden_acts[row * matrix_size + col] for row in range(matrix_size)]
                col_avg = sum(col_acts) / max(1, len(col_acts))
                col_x = matrix_x + grid_w + 2
                col_y_src = matrix_y + col * cell_size + cell_size // 2
                
                for k in range(output_nodes):
                    act_out = activations['output'][k]
                    out_y = int(nn_y_start + k * escala_y_out)
                    
                    if col_avg > 0.2 and act_out > 0.3:
                        cor = (255, 80, 80)
                        thick = 2
                    else:
                        cor = (220, 220, 220)
                        thick = 1
                    
                    pygame.draw.line(self.display, cor,
                                    (col_x, col_y_src),
                                    (output_x - 10, out_y), thick)
            
            # ── NÓS DE INPUT (com labels à esquerda) ──
            for i, (label, val) in enumerate(inputs):
                nx = input_x
                ny = int(nn_y_start + i * escala_y_in)
                act = activations['input'][i]
                
                if act > 0.5 and IMG_NEURON is not None:
                    s = IMG_NEURON.copy()
                    s.fill((255, 255, 255, 255), special_flags=pygame.BLEND_RGBA_MULT)
                    self.display.blit(s, s.get_rect(center=(nx, ny)))
                else:
                    pygame.draw.circle(self.display, (30, 30, 30), (nx, ny), 8)
                
                text_surf = self.FONT_BODY.render(f"{label}: {val:.2f}", True, TEXT_COLOR)
                self.display.blit(text_surf, text_surf.get_rect(midright=(nx - 15, ny)))
            
            # ── NÓS DE OUTPUT (com labels à direita) ──
            for k, label in enumerate(outputs_labels):
                nx = output_x
                ny = int(nn_y_start + k * escala_y_out)
                act = activations['output'][k] if k < len(activations['output']) else 0.0
                
                if act > 0.5 and IMG_NEURON is not None:
                    s = IMG_NEURON.copy()
                    s.fill((255, 255, 255, 255), special_flags=pygame.BLEND_RGBA_MULT)
                    self.display.blit(s, s.get_rect(center=(nx, ny)))
                else:
                    pygame.draw.circle(self.display, (30, 30, 30), (nx, ny), 8)
                
                if act > 0.5:
                    text_surf = self.FONT_SUBTITLE.render(label, True, (0, 0, 0))
                else:
                    text_surf = self.FONT_BODY.render(label, True, TEXT_COLOR)
                self.display.blit(text_surf, text_surf.get_rect(midleft=(nx + 15, ny)))
                
        else:
            # ── MODO NEAT (Nós Clássicos — sem alteração) ──
            x_origem = SCREEN_WIDTH - 650
            y_origem = 110
            largura_pintura = 180
            altura_pintura = 220
            
            escala_y_in = altura_pintura / max(1, input_nodes - 1)
            escala_y_out = altura_pintura / max(1, output_nodes - 1)
            escala_x = largura_pintura / 2.0
            escala_y_hid = altura_pintura / max(1, hidden_nodes - 1)
            
            for i in range(input_nodes):
                for j in range(hidden_nodes):
                    act_in = activations['input'][i]
                    act_hid = hidden_acts[j]
                    if act_in > 0.4 and act_hid > 0.4:
                        cor = (255, 60, 60)
                        thick = 2
                    else:
                        cor = (200, 200, 200)
                        thick = 1
                    pygame.draw.line(self.display, cor, 
                                     (x_origem, y_origem + i * escala_y_in), 
                                     (x_origem + escala_x, y_origem + j * escala_y_hid), thick)
                                     
            for j in range(hidden_nodes):
                for k in range(output_nodes):
                    act_hid = hidden_acts[j]
                    act_out = activations['output'][k]
                    if act_hid > 0.4 and act_out > 0.4:
                        cor = (255, 60, 60)
                        thick = 2
                    else:
                        cor = (200, 200, 200)
                        thick = 1
                    pygame.draw.line(self.display, cor, 
                                     (x_origem + escala_x, y_origem + j * escala_y_hid), 
                                     (x_origem + 2 * escala_x, y_origem + k * escala_y_out), thick)
            
            # Nós e Labels (NEAT)
            def draw_neuron(nx, ny, act_val):
                if act_val > 0.5 and IMG_NEURON is not None:
                    s = IMG_NEURON.copy()
                    s.fill((255, 255, 255, 255), special_flags=pygame.BLEND_RGBA_MULT)
                    self.display.blit(s, s.get_rect(center=(int(nx), int(ny))))
                else:
                    pygame.draw.circle(self.display, (30, 30, 30), (int(nx), int(ny)), 8)

            for i, (label, val) in enumerate(inputs):
                nx = x_origem
                ny = y_origem + i * escala_y_in
                draw_neuron(nx, ny, activations['input'][i])
                text_surf = self.FONT_BODY.render(f"{label}: {val:.2f}", True, TEXT_COLOR)
                self.display.blit(text_surf, text_surf.get_rect(midright=(nx - 15, ny)))

            for j in range(hidden_nodes):
                nx = x_origem + escala_x
                ny = y_origem + j * escala_y_hid
                draw_neuron(nx, ny, hidden_acts[j])

            for k, label in enumerate(outputs_labels):
                nx = x_origem + 2 * escala_x
                ny = y_origem + k * escala_y_out
                act = activations['output'][k] if k < len(activations['output']) else 0.0
                draw_neuron(nx, ny, act)
                if act > 0.5:
                    text_surf = self.FONT_SUBTITLE.render(label, True, (0, 0, 0))
                else:
                    text_surf = self.FONT_BODY.render(label, True, TEXT_COLOR)
                self.display.blit(text_surf, text_surf.get_rect(midleft=(nx + 15, ny)))

            # ── BARRAS DE DECISÃO (Abaixo do Ranking) ──
            import math
            n_outs = len(outputs_labels)
            raw_out = activations['output'][:n_outs]
            while len(raw_out) < n_outs: raw_out.append(0.0)
            
            # Applica Softmax para ter porcentagens reais de probabilidade
            max_out = max(raw_out)
            exp_out = [math.exp(x - max_out) for x in raw_out]
            sum_exp = sum(exp_out)
            probs = [x / sum_exp for x in exp_out]
            
            # Ranking termina em y=330, x=1090. Vamos colocar logo abaixo
            bar_y_start = 380 
            bar_x = 1130
            bar_w = 140
            bar_h = 10
            
            dec_title = self.FONT_BODY.render("Decisão (Probabilidade)", True, (100, 100, 100))
            self.display.blit(dec_title, (bar_x, bar_y_start))
            
            for k, label in enumerate(outputs_labels):
                val = probs[k]
                by = bar_y_start + 30 + k * 18
                
                # Fundo cinza
                pygame.draw.rect(self.display, (220, 220, 220), (bar_x, by, bar_w, bar_h), border_radius=4)
                
                fill_w = int(val * bar_w)
                is_best = (k == raw_out.index(max_out))
                
                if fill_w > 0:
                    color = (255, 80, 80) if is_best else (180, 180, 180)
                    pygame.draw.rect(self.display, color, (bar_x, by, fill_w, bar_h), border_radius=4)
                    
                lbl = self.FONT_BODY.render(f"{label} {val*100:.1f}%", True, (70, 70, 70))
                # Centraliza perfeitamente o texto em relação ao meio da barra
                self.display.blit(lbl, lbl.get_rect(midleft=(bar_x + bar_w + 5, by + bar_h // 2)))

    def _draw_ppo_hud(self, surface, state_data):
        """HUD Exclusiva do PPO (Ator-Crítico)."""
        px = 20
        py = 15
        
        # Textos devem ser estritamente renderizados em Cinza Escuro (70, 70, 70)
        text_color = (70, 70, 70)
        
        # 1. Título do PPO
        ep = state_data.get('episode', 0)
        title_surf = self.FONT_SUBTITLE.render(f"PPO  ·  EPISÓDIO {ep}", True, text_color)
        surface.blit(title_surf, (px, py))
        py += 30
        
        # Tempos
        tot_hr = state_data.get('tot_hr', 0)
        tot_min = state_data.get('tot_min', 0)
        tot_sec = state_data.get('tot_sec', 0)
        sim_hr = state_data.get('sim_hr', 0)
        sim_min = state_data.get('sim_min', 0)
        sim_sec = state_data.get('sim_sec', 0)
        timer_str = f"Simulado (IA): {sim_hr}h {sim_min}m {sim_sec}s   |   Real: {tot_hr}h {tot_min}m {tot_sec}s"
        surface.blit(self.FONT_BODY.render(timer_str, True, text_color), (px, py))
        
        # Equivalência de Status (Recompensa, Distância, Velocidade, Tempo Ciclo)
        py += 25
        reward = state_data.get('reward', 0.0)
        dist_px = int(self.score)
        spd_px = self.game_speed
        ep_min = state_data.get('ep_min', 0)
        ep_sec = state_data.get('ep_sec', 0)
        
        surface.blit(self.FONT_BODY.render(f"Recompensa Acum.: {reward:.1f}", True, text_color), (px, py))
        py += 28
        surface.blit(self.FONT_BODY.render(f"Distância: {dist_px} px", True, text_color), (px, py))
        py += 28
        kmh = (spd_px * 60 / 10.75) * 3.6
        surface.blit(self.FONT_BODY.render(f"Velocidade: {spd_px:.1f} px/f ({kmh:.0f} km/h)", True, text_color), (px, py))
        py += 28
        surface.blit(self.FONT_BODY.render(f"Tempo Ciclo: {ep_min:02d}:{ep_sec:02d}", True, text_color), (px, py))
        
        py += 25
        # ATOR (Probabilidades)
        surface.blit(self.FONT_SUBTITLE.render("ATOR: Probabilidades", True, text_color), (px, py))
        py += 35
        
        action_probs = state_data.get('action_probs', [0.0, 0.0, 0.0])
        labels = ["Correr", "Pular", "Abaixar"]
        for k, prob in enumerate(action_probs):
            lbl_surf = self.FONT_BODY.render(f"{labels[k]}: {prob*100:.1f}%", True, text_color)
            surface.blit(lbl_surf, (px, py))
            
            # Barra curta
            bar_x = px + 125
            bar_w = 110
            bar_h = 14
            pygame.draw.rect(surface, (220, 220, 220), (bar_x, py + 4, bar_w, bar_h), border_radius=4)
            fill_w = int(prob * bar_w)
            if fill_w > 0:
                color = (80, 130, 220) if k == 1 else ((220, 130, 80) if k == 2 else (130, 220, 80)) # Cores vibrantes
                pygame.draw.rect(surface, color, (bar_x, py + 4, fill_w, bar_h), border_radius=4)
                
            py += 28
            
        py += 15
        # CRÍTICO (Valor do Risco)
        surface.blit(self.FONT_SUBTITLE.render("CRÍTICO: Avaliação de Risco", True, text_color), (px, py))
        py += 35
        
        critic_val = state_data.get('critic_value', 0.0)
        # 1. BUG DA BARRA PRETA (Normalização de -1.0 a 1.0)
        norm_val = max(0.0, min(1.0, (critic_val + 1.0) / 2.0))
        
        bar_w_crit = 230
        bar_h_crit = 20
        pygame.draw.rect(surface, (220, 220, 220), (px, py, bar_w_crit, bar_h_crit), border_radius=4)
        fill_w_crit = max(0, int(norm_val * bar_w_crit))
        
        if fill_w_crit > 0:
            # Cor: Vermelho em 0.0, Verde em 1.0
            r = min(255, int(255 * (1.0 - norm_val)))
            g = min(255, int(255 * norm_val))
            pygame.draw.rect(surface, (r, g, 50), (px, py, fill_w_crit, bar_h_crit), border_radius=4)
            
        val_str = f"Valor: {critic_val:.2f}"
        surface.blit(self.FONT_BODY.render(val_str, True, text_color), (px + bar_w_crit + 10, py))

        # MÉTRICAS INTERNAS (PPO)
        py += 40
        surface.blit(self.FONT_SUBTITLE.render("MÉTRICAS INTERNAS (PPO)", True, text_color), (px, py))
        py += 35
        
        import math
        entropy = sum(-p * math.log(p) for p in action_probs if p > 0)
        
        if not hasattr(self, 'last_critic_val'):
            self.last_critic_val = critic_val
        adv = reward + (0.99 * critic_val) - self.last_critic_val
        self.last_critic_val = critic_val
        
        surface.blit(self.FONT_BODY.render(f"Entropia (Exploração): {entropy:.3f}", True, text_color), (px, py))
        py += 28
        surface.blit(self.FONT_BODY.render(f"Vantagem (Advantage): {adv:.3f}", True, text_color), (px, py))

        # ---------------------------------------------------------------------
        # PAINEL DIREITO (O Cérebro "Actor-Critic" - Deep Neural Network)
        # ---------------------------------------------------------------------
        # Inicializa o histórico do Crítico (Cardiograma) se não existir
        if not hasattr(self, 'critic_history'):
            self.critic_history = []
        self.critic_history.append(norm_val)
        if len(self.critic_history) > 50:
            self.critic_history.pop(0)

        # Coordenadas X exatas (Ancoragem pelo Centro)
        center_x = SCREEN_WIDTH // 2
        input_x = center_x - 50
        x_hidden_1 = center_x + 100
        x_hidden_2 = center_x + 200
        x_outputs = center_x + 350
        
        input_labels = ["Dist. Obs.", "Alt. Obs.", "Larg. Obs.", "Velocidade", "Dino Y", "Pulando", "Abaixando", "Tipo Obs."]
        state_obs = state_data.get('state_obs', [0]*8)
        
        # Coordenadas Y: Distribuindo de 120 a 320
        input_pts = [(input_x, int(120 + i * 28.5)) for i in range(8)]
        h1_pts = [(x_hidden_1, int(120 + i * 28.5)) for i in range(8)]
        h2_pts = [(x_hidden_2, int(120 + i * 28.5)) for i in range(8)]
        
        # CABEÇAS
        actor_pts = [(x_outputs, 120 + i * 30) for i in range(3)] # Y: 120, 150, 180
        critic_pt = (x_outputs, 300) # Y: 300
        
        # Encontra a ação amostrada
        action_probs = state_data.get('action_probs', [0.0, 0.0, 0.0])
        best_action_idx = state_data.get('chosen_action')
        if best_action_idx is None:
            best_action_idx = 0
            max_prob = -1
            for i, p in enumerate(action_probs):
                if p > max_prob:
                    max_prob = p
                    best_action_idx = i
                    
        color_action = (80, 220, 80) if best_action_idx == 0 else ((80, 160, 255) if best_action_idx == 1 else (255, 160, 80))
        c_color = (int(255*(1-norm_val)), int(255*norm_val), 50)
        
        # ==========================================
        # RENDERIZAÇÃO ESTREITA (LINHAS -> NÓS -> TEXTOS)
        # ==========================================
        
        # 1. LINHAS (Sinapses Fundo e Ativas)
        for p1 in input_pts:
            for p2 in h1_pts:
                pygame.draw.line(surface, (220, 220, 220), p1, p2, 1)
        for p1 in h1_pts:
            for p2 in h2_pts:
                pygame.draw.line(surface, (220, 220, 220), p1, p2, 1)
        for p1 in h2_pts:
            for p2 in actor_pts:
                pygame.draw.line(surface, (220, 220, 220), p1, p2, 1)
            pygame.draw.line(surface, (220, 220, 220), p1, critic_pt, 1)

        # 2. ILUMINAÇÃO DOS NÓS OCULTOS
        active_h1 = set()
        active_h2 = set()
        
        for i, val in enumerate(state_obs):
            if val > 0.05:
                for j, p2 in enumerate(h1_pts):
                    if (i + j) % 3 == 0:
                        pygame.draw.line(surface, color_action, input_pts[i], p2, 1)
                        active_h1.add(j)
                        
        for i, p1 in enumerate(h1_pts):
            for j, p2 in enumerate(h2_pts):
                if (i + j) % 3 == 0:
                    if i in active_h1:
                        pygame.draw.line(surface, color_action, p1, p2, 1)
                        active_h2.add(j)
                        
        # 3. ANIMAÇÃO DO FLUXO DE DADOS PARA O CRÍTICO
        t_base = (pygame.time.get_ticks() % 1000) / 1000.0
        for i, p1 in enumerate(h2_pts):
            if i in active_h2:
                pygame.draw.line(surface, color_action, p1, actor_pts[best_action_idx], 2)
            
            # Efeito de "Filamentos" (Dados Fluindo) para o Crítico
            pygame.draw.line(surface, c_color, p1, critic_pt, 1) # Fio guia mais fino
            
            # Pulso de energia viajando pela linha
            t = (t_base + (i * 0.15)) % 1.0
            px_pulse = p1[0] + (critic_pt[0] - p1[0]) * t
            py_pulse = p1[1] + (critic_pt[1] - p1[1]) * t
            pygame.draw.circle(surface, (255, 255, 255), (int(px_pulse), int(py_pulse)), 3)

        # 2. CÍRCULOS (Sólidos, sem glow)
        for i, val in enumerate(state_obs):
            color_in = color_action if val > 0.05 else (150, 150, 150)
            pygame.draw.circle(surface, (40, 40, 40), input_pts[i], 6)
            pygame.draw.circle(surface, color_in, input_pts[i], 4)

        for j, pt in enumerate(h1_pts):
            c_fill = color_action if j in active_h1 else (100, 100, 100)
            pygame.draw.circle(surface, (40, 40, 40), pt, 6)
            pygame.draw.circle(surface, c_fill, pt, 4)
            
        for j, pt in enumerate(h2_pts):
            c_fill = color_action if j in active_h2 else (100, 100, 100)
            pygame.draw.circle(surface, (40, 40, 40), pt, 6)
            pygame.draw.circle(surface, c_fill, pt, 4)

        for i, apt in enumerate(actor_pts):
            c = (80, 220, 80) if i == 0 else ((80, 160, 255) if i == 1 else (255, 160, 80))
            pygame.draw.circle(surface, (40, 40, 40), apt, 8)
            pygame.draw.circle(surface, c, apt, 6)

        pygame.draw.circle(surface, (40, 40, 40), critic_pt, 10)
        pygame.draw.circle(surface, c_color, critic_pt, 8)

        # 3. TEXTOS E GRÁFICOS
        for i, lbl in enumerate(input_labels):
            lbl_surf = self.FONT_BODY.render(f"{lbl}: {state_obs[i]:.2f}", True, (90, 90, 90))
            surface.blit(lbl_surf, (input_x - lbl_surf.get_width() - 15, input_pts[i][1] - 7))

        for i, apt in enumerate(actor_pts):
            lbl_surf = self.FONT_BODY.render(labels[i], True, (90, 90, 90))
            surface.blit(lbl_surf, (x_outputs + 15, apt[1] - 7))

        # Isolamento de Eixo Y dos Títulos
        lbl_actor = self.FONT_SUBTITLE.render("CABEÇA DO ATOR (Política)", True, (50, 50, 50))
        surface.blit(lbl_actor, lbl_actor.get_rect(midbottom=(x_outputs, 100)))

        lbl_critic = self.FONT_SUBTITLE.render("CABEÇA DO CRÍTICO (Valor)", True, (50, 50, 50))
        surface.blit(lbl_critic, lbl_critic.get_rect(midtop=(x_outputs, 330)))

        # Gráfico (Sem fundo preto, vazado)
        graph_w, graph_h = 160, 30
        graph_x = x_outputs - graph_w // 2
        graph_y = 360 
        
        if len(self.critic_history) > 1:
            min_v = min(self.critic_history)
            max_v = max(self.critic_history)
            range_v = max_v - min_v
            if range_v < 0.001: range_v = 0.001
            pts = []
            for idx, hist_v in enumerate(self.critic_history):
                px_g = graph_x + (idx / 49.0) * graph_w
                dyn_v = (hist_v - min_v) / range_v
                py_g = graph_y + graph_h - (dyn_v * graph_h)
                pts.append((px_g, py_g))
            pygame.draw.lines(surface, c_color, False, pts, 2)
            
        # 4. POLIMENTO DE TEXTOS
        lbl_osc = self.FONT_BODY.render("Histórico de Risco", True, (120, 120, 120))
        surface.blit(lbl_osc, lbl_osc.get_rect(midtop=(x_outputs, graph_y + graph_h + 18)))

        # 4. FOOTER (DICAS)
        hints_surf = self.FONT_BODY.render("[T] TURBO: LIG/DESL   |   [ESC] Pausar / Salvar", True, (130, 130, 130))
        surface.blit(hints_surf, (20, SCREEN_HEIGHT - 35))
        
        # Nota Explicativa da Escala (Rodapé Direito)
        note_font = self.FONT_NOTE
        note1 = note_font.render("* Escala física baseada no Sprite (1m = 10.75 px).", True, (130, 130, 130))
        note2 = note_font.render("* A velocidade e metros refletem a extrema aceleração Arcade do jogo.", True, (130, 130, 130))
        surface.blit(note1, (SCREEN_WIDTH - note1.get_width() - 20, SCREEN_HEIGHT - 45))
        surface.blit(note2, (SCREEN_WIDTH - note2.get_width() - 20, SCREEN_HEIGHT - 25))

    def _render_solo(self):
        """Renderiza um frame do modo solo."""
        if self.display is None:
            return

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()

        self.display.fill(BG_COLOR)
        
        # Desenhar Gráfico Temporal
        self._draw_graph(current_best=self.score, current_avg=self.score, best_dino=self.dino)
        
        # Desenhar Rede Neural (modo solo)
        st = self._get_state()
        self._draw_neural_network(st, 0)
        
        self._update_clouds()
        for c in self.clouds:
            c.draw(self.display)
        self._draw_ground()
        for obs in self.obstacles:
            obs.draw(self.display)
        self.dino.draw(self.display)
        self._draw_hud(self.score)
        pygame.display.flip()

    # ╔═══════════════════════════════════════════════════════════╗
    # ║         MODO DUELO — HUMANO VS IA                        ║
    # ╚═══════════════════════════════════════════════════════════╝

    def play_human_mode(self):
        """Modo apenas jogador humano."""
        if not self.render_game: return
        pygame.init()
        if self.display is None:
            self.display = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE | pygame.SCALED)
        pygame.display.set_caption("Dino Game — Jogador Humano")
        if self.clock is None: self.clock = pygame.time.Clock()
        self._init_fonts()

        self.reset()
        self.dino.color = (0, 255, 0) # Verde
        self.dino.name = "Humano"

        running = True
        while running:
            action = ACTION_NONE
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    sys.exit(0)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False

            keys = pygame.key.get_pressed()
            if keys[pygame.K_SPACE] or keys[pygame.K_UP]:
                action = ACTION_JUMP
            elif keys[pygame.K_DOWN]:
                action = ACTION_DUCK

            state, reward, game_over, score = self.play_step(action)
            
            self.display.fill(BG_COLOR)
            for c in self.clouds: c.draw(self.display)
            self._draw_ground()
            for obs in self.obstacles: obs.draw(self.display)
            
            if game_over:
                self.dino.draw(self.display, dead=True, alpha=128)
            else:
                self.dino.draw(self.display)
                
            self._draw_hud(self.score)
            pygame.display.flip()
            self.clock.tick(FPS)
            
            if game_over:
                # Desenha o texto de GAME OVER
                self._draw_human_game_over_screen(self.display)
                
                pygame.display.flip()
                
                # Aguarda input do jogador
                waiting = True
                while waiting and running:
                    for e in pygame.event.get():
                        if e.type == pygame.QUIT:
                            running = False
                            sys.exit(0)
                        if e.type == pygame.KEYDOWN:
                            if e.key == pygame.K_SPACE or e.key == pygame.K_UP:
                                self.reset()
                                self.dino.color = (0, 255, 0) # Verde
                                self.dino.name = "Humano"
                                waiting = False
                            elif e.key == pygame.K_ESCAPE:
                                running = False
                                waiting = False

    def play_versus_mode(self, ai_network):
        """Modo Duelo: Humano (Verde) vs IA Campeã (Magenta)."""
        if not self.render_game: return
        pygame.init()
        if self.display is None:
            self.display = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE | pygame.SCALED)
        pygame.display.set_caption("Dino Game — Humano vs IA Campeã")
        if self.clock is None: self.clock = pygame.time.Clock()
        self._init_fonts()

        # Reseta o mundo usando as variáveis normais
        self.obstacles.clear()
        self.clouds.clear()
        self.game_speed = INITIAL_SPEED
        self.score = 0
        self.frame_count = 0
        self._spawn_obstacle()

        # Cria os dois dinos com uma distância entre eles
        self.human_dino = Dino(x=200, color=(0, 255, 0), name="Humano")
        self.ai_dino = Dino(x=350, color=(255, 0, 255), name="IA")

        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    sys.exit(0)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False

            # ── Ação Humana ──
            if self.human_dino.alive:
                keys = pygame.key.get_pressed()
                if keys[pygame.K_SPACE] or keys[pygame.K_UP]:
                    self.human_dino.jump()
                elif keys[pygame.K_DOWN]:
                    self.human_dino.duck()
                else:
                    self.human_dino.stand()
                self.human_dino.update()
            else:
                self.human_dino.x -= self.game_speed # Desliza morto

            # ── Ação da IA ──
            ai_activations = None
            if self.ai_dino.alive:
                ai_state = self._get_state(self.ai_dino)
                output = ai_network.activate(ai_state)
                ai_action = output.index(max(output))
                
                # Monta as ativações para a HUD
                hidden_keys = [k for k in ai_network.values.keys() if k > 2]
                hidden_acts = [ai_network.values[k] for k in hidden_keys]
                while len(hidden_acts) < 6: hidden_acts.append(0.0)
                
                ai_activations = {
                    'input': list(ai_state),
                    'hidden': hidden_acts[:6],
                    'output': output
                }
                
                if ai_action == ACTION_JUMP: self.ai_dino.jump()
                elif ai_action == ACTION_DUCK: self.ai_dino.duck()
                else: self.ai_dino.stand()
                self.ai_dino.update()
            else:
                self.ai_dino.x -= self.game_speed # Desliza morto

            # ── Mundo e Colisões ──
            for obs in self.obstacles: obs.update(self.game_speed)
            self._update_ground()
            self.obstacles = [o for o in self.obstacles if not o.is_off_screen()]
            self._maybe_spawn_obstacle()
            self._update_clouds()
            if self.unlimited_speed:
                self.game_speed += SPEED_INCREMENT
            else:
                self.game_speed = min(MAX_SPEED, self.game_speed + SPEED_INCREMENT)

            human_hit = self.human_dino.alive and self._check_collision(self.human_dino)
            ai_hit = self.ai_dino.alive and self._check_collision(self.ai_dino)
            
            if human_hit and ai_hit:
                self.human_dino.alive = False
                self.ai_dino.alive = False
                if getattr(self, 'winner', None) is None:
                    self.winner = "EMPATE"
            elif human_hit:
                self.human_dino.alive = False
                if getattr(self, 'winner', None) is None:
                    self.winner = "IA"
            elif ai_hit:
                self.ai_dino.alive = False
                if getattr(self, 'winner', None) is None:
                    self.winner = "HUMANO"

            self.frame_count += 1
            self.score = self.frame_count // 6

            # ── Renderização ──
            self.display.fill(BG_COLOR)
            
            # ── Desenha o Mundo Primeiro ──
            for c in self.clouds: c.draw(self.display)
            self._draw_ground()
            for obs in self.obstacles: obs.draw(self.display)

            # Só desenha mortos translúcidos por baixo, e vivos por cima
            if not self.human_dino.alive: self.human_dino.draw(self.display, dead=True, alpha=128)
            if not self.ai_dino.alive: self.ai_dino.draw(self.display, dead=True, alpha=128)
            if self.human_dino.alive: self.human_dino.draw(self.display)
            if self.ai_dino.alive: self.ai_dino.draw(self.display)
            
            self._draw_hud(self.score)

            # ── HUD do Jogador e da IA ──
            if self.ai_dino.alive:
                if ai_activations is not None:
                    self._draw_neural_network(tuple(ai_activations['input']), 0, activations=ai_activations)
            else:
                msg_ai = "IA PERDEU" if getattr(self, 'winner', None) == "HUMANO" else "IA VENCEU!"
                if getattr(self, 'winner', None) == "EMPATE": msg_ai = "EMPATE"
                c_msg_ai = (255, 0, 255) if msg_ai != "IA PERDEU" else (150, 0, 150)
                go_surf = self.FONT_COURIER_LARGE.render(msg_ai, True, c_msg_ai)
                self.display.blit(go_surf, (SCREEN_WIDTH - 300, 200))
                
            if self.human_dino.alive:
                hx, hy = 50, 150
                keys = pygame.key.get_pressed()
                up_pressed = keys[pygame.K_SPACE] or keys[pygame.K_UP]
                down_pressed = keys[pygame.K_DOWN]
                
                c_up = (0, 255, 0) if up_pressed else (100, 100, 100)
                c_down = (0, 255, 0) if down_pressed else (100, 100, 100)
                
                lbl_ctrl = self.FONT_SUBTITLE.render("CONTROLES JOGADOR", True, (0, 255, 0))
                self.display.blit(lbl_ctrl, (hx, hy))
                
                pygame.draw.rect(self.display, c_up, (hx, hy + 40, 40, 40), border_radius=5)
                if not up_pressed: pygame.draw.rect(self.display, (40, 40, 40), (hx+2, hy + 42, 36, 36), border_radius=5)
                txt_up = self.FONT_SUBTITLE.render("PULAR", True, c_up)
                self.display.blit(txt_up, (hx + 50, hy + 45))
                
                pygame.draw.rect(self.display, c_down, (hx, hy + 90, 40, 40), border_radius=5)
                if not down_pressed: pygame.draw.rect(self.display, (40, 40, 40), (hx+2, hy + 92, 36, 36), border_radius=5)
                txt_down = self.FONT_SUBTITLE.render("ABAIXAR", True, c_down)
                self.display.blit(txt_down, (hx + 50, hy + 95))
            else:
                msg_hu = "JOGADOR PERDEU" if getattr(self, 'winner', None) == "IA" else "JOGADOR VENCEU!"
                if getattr(self, 'winner', None) == "EMPATE": msg_hu = "EMPATE"
                c_msg_hu = (0, 255, 0) if msg_hu != "JOGADOR PERDEU" else (0, 150, 0)
                go_surf = self.FONT_COURIER_LARGE.render(msg_hu, True, c_msg_hu)
                self.display.blit(go_surf, (50, 200))
            
            # Etiquetas
            p_lbl = self.font.render("JOGADOR", True, (0, 255, 0))
            ai_lbl = self.font.render("IA CAMPEÃ", True, (255, 0, 255))
            self.display.blit(p_lbl, (12, 12))
            self.display.blit(ai_lbl, (12, 34))

            pygame.display.flip()
            self.clock.tick(FPS)

            if not self.human_dino.alive and not self.ai_dino.alive:
                pygame.time.delay(1500)
                break

    # ╔═══════════════════════════════════════════════════════════╗
    # ║         MODO TORNEIO — MULTIPLAS IAS + HUMANO             ║
    # ╚═══════════════════════════════════════════════════════════╝
    
    def play_tournament_mode(self, champions: dict):
        """Modo Torneio: Humano vs NEAT vs DQN vs PPO"""
        if not self.render_game: return
        pygame.init()
        if self.display is None:
            self.display = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE | pygame.SCALED)
        pygame.display.set_caption("Dino Game — Torneio Batalha Real")
        if self.clock is None: self.clock = pygame.time.Clock()
        self._init_fonts()
        
        self.obstacles.clear()
        self.clouds.clear()
        self.game_speed = INITIAL_SPEED
        self.score = 0
        self.frame_count = 0
        self._spawn_obstacle()
        
        import torch
        
        # Dicionário de Participantes
        self.tourney_dinos = {}
        self.tourney_dinos['Humano'] = Dino(x=50, color=(0, 255, 0), name="Humano")
        
        if 'NEAT' in champions:
            self.tourney_dinos['NEAT'] = Dino(x=150, color=(255, 0, 255), name="NEAT")
        if 'DQN' in champions:
            self.tourney_dinos['DQN'] = Dino(x=250, color=(0, 255, 255), name="DQN")
        if 'PPO' in champions:
            self.tourney_dinos['PPO'] = Dino(x=350, color=(255, 165, 0), name="PPO")
            
        alive_count = len(self.tourney_dinos)
        dead_order = [] # Guarda quem morreu e em que momento
        
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    sys.exit(0)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False
                    
            # ── Ações ──
            
            # Humano
            if self.tourney_dinos['Humano'].alive:
                keys = pygame.key.get_pressed()
                if keys[pygame.K_SPACE] or keys[pygame.K_UP]: self.tourney_dinos['Humano'].jump()
                elif keys[pygame.K_DOWN]: self.tourney_dinos['Humano'].duck()
                else: self.tourney_dinos['Humano'].stand()
                self.tourney_dinos['Humano'].update()
            else:
                self.tourney_dinos['Humano'].x -= self.game_speed
                
            # NEAT
            if 'NEAT' in self.tourney_dinos:
                dino = self.tourney_dinos['NEAT']
                if dino.alive:
                    state = self._get_state(dino)
                    output = champions['NEAT'].activate(state)
                    action = output.index(max(output))
                    if action == ACTION_JUMP: dino.jump()
                    elif action == ACTION_DUCK: dino.duck()
                    else: dino.stand()
                    dino.update()
                else:
                    dino.x -= self.game_speed
                    
            # DQN
            if 'DQN' in self.tourney_dinos:
                dino = self.tourney_dinos['DQN']
                if dino.alive:
                    state = self._get_state(dino)
                    state_tensor = torch.tensor(state, dtype=torch.float).unsqueeze(0)
                    with torch.no_grad():
                        output = champions['DQN'](state_tensor)
                        action = torch.argmax(output).item()
                    if action == ACTION_JUMP: dino.jump()
                    elif action == ACTION_DUCK: dino.duck()
                    else: dino.stand()
                    dino.update()
                else:
                    dino.x -= self.game_speed
                    
            # PPO
            if 'PPO' in self.tourney_dinos:
                dino = self.tourney_dinos['PPO']
                if dino.alive:
                    state = self._get_state(dino)
                    state_tensor = torch.FloatTensor(state).unsqueeze(0)
                    with torch.no_grad():
                        features = champions['PPO'].policy.base(state_tensor)
                        action_probs = champions['PPO'].policy.actor(features)
                        action = torch.argmax(action_probs, dim=-1).item()
                    if action == ACTION_JUMP: dino.jump()
                    elif action == ACTION_DUCK: dino.duck()
                    else: dino.stand()
                    dino.update()
                else:
                    dino.x -= self.game_speed
                    
            # ── Mundo e Colisões ──
            for obs in self.obstacles: obs.update(self.game_speed)
            self._update_ground()
            self.obstacles = [o for o in self.obstacles if not o.is_off_screen()]
            self._maybe_spawn_obstacle()
            self._update_clouds()
            if self.unlimited_speed: self.game_speed += SPEED_INCREMENT
            else: self.game_speed = min(MAX_SPEED, self.game_speed + SPEED_INCREMENT)
            
            # Check colisões
            for name, dino in self.tourney_dinos.items():
                if dino.alive and self._check_collision(dino):
                    dino.alive = False
                    dead_order.append(name)
                    alive_count -= 1
                    
            self.frame_count += 1
            self.score = self.frame_count // 6
            
            # ── Renderização ──
            self.display.fill(BG_COLOR)
            
            for c in self.clouds: c.draw(self.display)
            self._draw_ground()
            for obs in self.obstacles: obs.draw(self.display)
            
            # Desenha mortos primeiro, depois vivos
            for dino in self.tourney_dinos.values():
                if not dino.alive: dino.draw(self.display, dead=True, alpha=128)
            for dino in self.tourney_dinos.values():
                if dino.alive: dino.draw(self.display)
                
            self._draw_hud(self.score)
            
            # ── Scoreboard do Torneio ──
            y_offset = 20
            title = self.FONT_SUBTITLE.render("PLACAR DO TORNEIO", True, TEXT_COLOR)
            self.display.blit(title, (20, y_offset))
            y_offset += 30
            
            for name, dino in self.tourney_dinos.items():
                if dino.alive:
                    txt = f"{name}: VIVO"
                    cor = dino.color
                else:
                    rank = len(self.tourney_dinos) - dead_order.index(name)
                    txt = f"{name}: ELIMINADO ({rank}º Lugar)"
                    cor = (120, 120, 120)
                    
                lbl = self.font.render(txt, True, cor)
                self.display.blit(lbl, (20, y_offset))
                y_offset += 25
                
            # Mostra Vencedor
            if alive_count <= 1 and len(dead_order) > 0:
                winner = None
                if alive_count == 1:
                    # Encontra quem tá vivo
                    for n, d in self.tourney_dinos.items():
                        if d.alive: winner = n
                else:
                    # Todo mundo morreu
                    winner = dead_order[-1] + " (EMPATE FINAL)"
                    
                font_go = self.FONT_COURIER_LARGE
                go_surf = font_go.render(f"VENCEDOR: {winner}", True, (255, 215, 0))
                self.display.blit(go_surf, (SCREEN_WIDTH//2 - go_surf.get_width()//2, 200))
                
            pygame.display.flip()
            self.clock.tick(FPS)
            
            if alive_count == 0:
                pygame.time.delay(3000)
                break

    # ╔═══════════════════════════════════════════════════════════╗
    # ║         MODO POPULAÇÃO — N AGENTES SIMULTÂNEOS           ║
    # ╚═══════════════════════════════════════════════════════════╝

    def play_population_mode(
        self,
        ai_list: list,
        generation: int = 1,
        labels: list = None,
        human_in_loop=False,
    ):
        """
        Roda o jogo para N dinossauros controlados simultaneamente por N redes neurais.
        """
        n_ai = len(ai_list)
        if n_ai == 0 and not human_in_loop:
            return {"scores": [], "best_score": 0, "alive_frames": []}

        if not self.render_game:
            print("ERRO: play_population_mode requer DinoGame(render=True)")
            return {}

        self.generation = generation

        pygame.init()
        if self.display is None:
            self.display = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE | pygame.SCALED)
        pygame.display.set_caption(f"Dino Game — Populacao ({n_ai} IA{' + 1 Humano' if human_in_loop else ''})")
        if self.clock is None:
            self.clock = pygame.time.Clock()
        self._init_fonts()

        # ── Gerar cores distintas para cada agente ──────────────────
        colors = generate_distinct_colors(n_ai)
        if labels is None:
            labels = [f"#{i}" for i in range(n_ai)]

        # ── Criar dinossauros com pequeno jitter no X (Pelotão) ──────────
        dinos = []
        for i in range(n_ai):
            spawn_x = 350 + random.randint(-120, 120)
            dinos.append(Dino(x=spawn_x, color=colors[i], name=labels[i]))
            
        if human_in_loop:
            dinos.append(Dino(name="Humano", is_human=True))

        total_dinos = len(dinos)
        # Estatísticas por agente
        alive_frames = [0] * total_dinos     # Frames que cada agente sobreviveu
        final_scores = [0] * total_dinos     # Score final de cada agente

        import time

        # Reiniciar estado do mundo
        self.obstacles.clear()
        self.clouds.clear()
        self.game_speed  = INITIAL_SPEED
        self.score       = 0
        self.frame_count = 0
        self.game_over   = False
        self._spawn_obstacle()
        
        # Rastreia quando a velocidade máxima foi atingida para validar "IA APRENDEU"
        score_at_max_speed = None
        
        missiles = []
        fires = []

        round_over = False
        running    = True

        while running:
            # ── Eventos ──────────────────────────────────────────────
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_t:
                        self.turbo_mode = not getattr(self, 'turbo_mode', False)
                    if event.key == pygame.K_ESCAPE:
                        menu_action = self._show_pause_menu(generation, self.hi_score, n_alive, n_ai, time.time() - self.start_time)
                        if menu_action == "SAVE":
                            return {"save_and_exit": True}

            if not running:
                break

            best_alive_idx = -1
            best_alive_score = -1
            best_activations = None
            
            keys = pygame.key.get_pressed()

            # ── Decisão de cada agente vivo ──────────────────────────
            for i, dino in enumerate(dinos):
                if not dino.alive:
                    continue

                if dino.is_human:
                    if keys[pygame.K_SPACE] or keys[pygame.K_UP]:
                        action = ACTION_JUMP
                    elif keys[pygame.K_DOWN]:
                        action = ACTION_DUCK
                    else:
                        action = ACTION_NONE
                else:
                    state  = self._get_state(dino)
                    prediction = ai_list[i](state)
                    
                    if isinstance(prediction, tuple):
                        if len(prediction) == 3:
                            action, raw_outputs, net_values = prediction
                        else:
                            action, raw_outputs = prediction
                            net_values = {}
                    else:
                        action = prediction
                        raw_outputs = [1.0 if k == action else 0.0 for k in range(4)]
                        net_values = {}
                        
                    # Rastrear o melhor para acender a Rede Neural na HUD
                    if dino.score >= best_alive_score:
                        best_alive_score = dino.score
                        best_alive_idx = i
                        
                        # Extrair os neurônios ocultos reais do NEAT (cujas chaves são > 2)
                        hidden_keys = [k for k in net_values.keys() if k > 2]
                        hidden_acts = [net_values[k] for k in hidden_keys]
                        while len(hidden_acts) < 6:
                            hidden_acts.append(0.0)
                        
                    best_activations = {
                        'input': list(state),
                        'hidden': hidden_acts[:6], # Mapeia até 6 neurônios reais para a HUD
                        'output': raw_outputs
                    }

                # Calcular distância para o obstáculo mais próximo (para Fenótipos)
                closest_obs_dist = None
                closest_obs_type = None
                min_dist = float('inf')
                for obs in self.obstacles:
                    dist = obs.x - dino.x
                    if dist > -obs.width and dist < min_dist:
                        min_dist = dist
                        closest_obs_type = obs.type
                if min_dist != float('inf'):
                    closest_obs_dist = min_dist

                if action == ACTION_JUMP:
                    dino.jump()
                elif action == ACTION_DUCK:
                    dino.duck()
                elif action == ACTION_SHOOT:
                    if dino.bazooka_out:
                        dino.fitness_bonus -= 1
                    elif getattr(self, 'use_bazooka', True):
                        if dino.shoot():
                            missiles.append(Missile(dino.x + dino.width, dino.y + 10, dino.id, self.game_speed, dino.color))
                        else:
                            dino.fitness_bonus -= 1
                else:
                    dino.stand()

                dino.update(action=action, closest_obs_dist=closest_obs_dist, closest_obs_type=closest_obs_type, game_speed=self.game_speed)
                alive_frames[i] += 1

            # ── Atualizar mundo ──────────────────────────────────────
            for obs in self.obstacles:
                obs.update(self.game_speed)
                
            for m in missiles:
                m.update()
            for f in fires:
                f.update(self.game_speed)
                
            self._update_ground()
            new_obstacles = []
            for o in self.obstacles:
                if o.is_off_screen():
                    # Recarrega a munição de todos os dinossauros vivos ao passar por QUALQUER obstáculo,
                    # EXCETO se o dinossauro foi quem destruiu este obstáculo!
                    for d in dinos:
                        if d.alive and d.id not in o.destruido_por:
                            d.ammo = 1.0
                else:
                    new_obstacles.append(o)
            self.obstacles = new_obstacles
            for m in missiles:
                if m.is_off_screen():
                    for d in dinos:
                        if d.id == m.dino_id:
                            d.bazooka_out = False
            missiles = [m for m in missiles if not m.is_off_screen()]
            fires = [f for f in fires if not f.is_off_screen()]
            
            # Checar colisão de míssil com cactos
            for m in missiles[:]:
                m_rect = m.get_rect()
                hit = False
                for obs in self.obstacles:
                    if obs.is_giant and m_rect.colliderect(obs.get_rect()):
                        hit = True
                        if m.dino_id not in obs.destruido_por:
                            obs.destruido_por.append(m.dino_id)
                            fires.append(FireVisual(obs.x, obs.y + obs.height - 30))
                            # Bônus para o dino que atirou
                            for d in dinos:
                                if d.id == m.dino_id:
                                    d.fitness_bonus += 20
                                    d.giant_kills += 1
                                    d.bazooka_out = False
                        break
                    elif not obs.is_giant and m_rect.colliderect(obs.get_rect()):
                        hit = True
                        # Atirou em cacto comum ou pássaro
                        if m.dino_id not in obs.destruido_por:
                            obs.destruido_por.append(m.dino_id)
                            fires.append(FireVisual(obs.x, obs.y + obs.height - 30))
                        for d in dinos:
                            if d.id == m.dino_id:
                                d.fitness_bonus -= 5
                                d.wasted_shots += 1
                                d.bazooka_out = False
                        break
                if hit:
                    missiles.remove(m)
                    
            self._maybe_spawn_obstacle()
            self._update_clouds()
            if self.unlimited_speed:
                self.game_speed += SPEED_INCREMENT
            else:
                self.game_speed = min(MAX_SPEED, self.game_speed + SPEED_INCREMENT)
            
            # Marca o score no momento em que a velocidade máxima é atingida pela primeira vez
            if self.game_speed >= MAX_SPEED and score_at_max_speed is None:
                score_at_max_speed = self.score
            
            # Animação dos dinossauros mortos escorregando para trás
            for dino in dinos:
                if not dino.alive:
                    dino.x -= self.game_speed

            # ── Colisões ─────────────────────────────────────────────
            for i, dino in enumerate(dinos):
                if dino.alive and self._check_collision(dino):
                    dino.alive      = False
                    dino.y          = GROUND_Y - dino.height
                    dino.is_jumping = False
                    dino.vel_y      = 0
                    final_scores[i] = self.score + dino.fitness_bonus

            # ── Score ────────────────────────────────────────────────
            self.frame_count += 1
            self.total_simulated_frames += 1
            self.score += self.game_speed
            if self.score > self.hi_score:
                self.hi_score = self.score
                self.hi_speed = max(getattr(self, 'hi_speed', 0.0), self.game_speed)
                
            # Atualizar recorde de velocidade máximo absoluto
            self.hi_speed = max(getattr(self, 'hi_speed', 0.0), self.game_speed)

            # Contagem de vivos
            n_alive = sum(1 for d in dinos if d.alive)

            # ── Todos morreram? ──────────────────────────────────────
            if n_alive == 0:
                # Preencher scores dos últimos sobreviventes
                for i, d in enumerate(dinos):
                    if final_scores[i] == 0:
                        final_scores[i] = self.score + d.fitness_bonus
                self.history_best_scores.append(max(final_scores))
                if hasattr(self, 'history_best_speeds'):
                    self.history_best_speeds.append(self.game_speed)
                # Considerar apenas IA para media
                ai_scores = final_scores[:n_ai] if n_ai > 0 else [0]
                self.history_avg_scores.append(sum(ai_scores) / max(1, n_ai))
                break  # Auto-avanço automático para treinar!

            # ── Renderizar ───────────────────────────────────────────
            # Se o Turbo estiver ativado, pula 9 a cada 10 frames para ganhar extrema velocidade de CPU
            if not self.turbo_mode or self.frame_count % 10 == 0:
                self.display.fill(BG_COLOR)

                # Definir clipe para que objetos do jogo não invadam a área da rede neural/HUD
                game_rect = pygame.Rect(0, NN_PANEL_H, SCREEN_WIDTH, SCREEN_HEIGHT - NN_PANEL_H)
                self.display.set_clip(game_rect)

                for m in self.mountains:
                    m.draw(self.display)
                for c in self.clouds:
                    c.draw(self.display)
                self._draw_ground()
                for obs in self.obstacles:
                    obs.draw(self.display)
                for f in fires:
                    f.draw(self.display)
                for m in missiles:
                    m.draw(self.display)

                # Dinos mortos (translúcidos e escorregando para trás)
                for dino in dinos:
                    if not dino.alive and dino.x + dino.width > 0:
                        dino.draw(self.display, dead=True, alpha=128)

                # Dinos vivos da IA
                human_dino = None
                for dino in dinos:
                    if dino.alive:
                        if dino.is_human:
                            human_dino = dino
                        else:
                            dino.draw(self.display, alpha=255)

                # Dino Humano (primeiro plano, sempre na frente e brilhante)
                if human_dino is not None:
                    human_dino.color = (0, 255, 0) # Verde Neon
                    human_dino.draw(self.display, alpha=255)

                # Remover clipe para desenhar a HUD e tooltips normalmente
                self.display.set_clip(None)

                self._draw_hud(self.score)
                
                # Gráfico Temporal para População (Calculando métricas em tempo real)
                ai_scores = [self.score if d.alive else final_scores[i] for i, d in enumerate(dinos) if not d.is_human]
                current_best = max(ai_scores) if ai_scores else 0
                current_avg  = sum(ai_scores) / max(1, len(ai_scores))
                
                # Selecionar Dino para a Câmera
                cam_dino = None
                for d in dinos:
                    if d.alive:
                        cam_dino = d
                        if d.is_human: break
                        
                self._draw_graph(current_best=current_best, current_avg=current_avg, best_dino=cam_dino)
                
                if best_activations:
                    # Desenhar a Rede Neural do melhor dino vivo
                    self._draw_neural_network(best_activations['input'], 0, activations=best_activations)

                # Adiciona Tabela Top 10
                self._draw_ranking_table(current_best)

                # Info de tempo de treino e contagem de vivos (Deslocados para não sobrepor a Rede)
                # O Tempo Total agora é SIMULADO: acelera violentamente no Modo Turbo!
                simulated_time_seconds = self.total_simulated_frames / FPS
                real_time_seconds = time.time() - self.start_time
                
                # Acha a melhor geracao
                best_gen = self.generation
                best_past_score = max(self.history_best_scores) if hasattr(self, 'history_best_scores') and self.history_best_scores else -1
                if current_best <= best_past_score:
                    best_gen = self.history_best_scores.index(best_past_score) + 1
                    
                vivos_surf = self.FONT_TITLE.render(f"VIVOS: {n_alive}/{total_dinos}   |   Melhor: G{best_gen}", True, TEXT_COLOR)
                # Centraliza no topo da tela para distribuir bem os 3 elementos (Geração, Vivos, Recordes)
                self.display.blit(vivos_surf, vivos_surf.get_rect(midtop=(SCREEN_WIDTH // 2, 20)))
                
                # -- VERIFICAÇÃO SE A IA "APRENDEU" (30k pixels após velocidade máxima) --
                pixels_at_max = (self.score - score_at_max_speed) if score_at_max_speed is not None else 0
                if pixels_at_max >= 468000:  # ~10 minutos na velocidade máxima
                    if hasattr(self, 'ai_learned_text') and self.ai_learned_text:
                        # Modo Campeão: mostrar texto personalizado com info de treino
                        learned_surf = self.FONT_COURIER_INFO.render(self.ai_learned_text, True, (0, 150, 0))
                        bg_rect = learned_surf.get_rect(center=(SCREEN_WIDTH // 2, 70))
                        bg_rect.inflate_ip(30, 20)
                        pygame.draw.rect(self.display, (220, 220, 220), bg_rect, border_radius=10)
                        self.display.blit(learned_surf, learned_surf.get_rect(center=(SCREEN_WIDTH // 2, 70)))
                        
                        sub_learned = self.FONT_BODY.render("(Pressione ESC para salvar e sair)", True, (100, 100, 100))
                        self.display.blit(sub_learned, sub_learned.get_rect(center=(SCREEN_WIDTH // 2, 105)))
                    elif not self.unlimited_speed:
                        learned_surf = self.FONT_COURIER_LEARNED.render("IA APRENDEU!", True, (0, 150, 0))
                        self.display.blit(learned_surf, learned_surf.get_rect(center=(SCREEN_WIDTH // 2, 70)))
                        
                        sub_learned = self.FONT_BODY.render("(Atingiu domínio absoluto. Pressione ESC para salvar e sair)", True, (100, 100, 100))
                        self.display.blit(sub_learned, sub_learned.get_rect(center=(SCREEN_WIDTH // 2, 105)))
                
                timer_str = f"Simulado (IA): {int(simulated_time_seconds//3600)}h {int((simulated_time_seconds%3600)//60)}m {int(simulated_time_seconds%60)}s   |   Real: {int(real_time_seconds//3600)}h {int((real_time_seconds%3600)//60)}m {int(real_time_seconds%60)}s"
                timer_surf = self.FONT_SUBTITLE.render(timer_str, True, TEXT_COLOR)
                # Subtítulo colado logo acima do gráfico (x=20)
                self.display.blit(timer_surf, (20, 110 - timer_surf.get_height() - 5))

                # Dica do Modo Turbo e ESC
                if self.turbo_mode:
                    hints_text = "[T] TURBO: LIGADO   |   [ESC] Pausar / Salvar"
                    hints_color = (255, 140, 0) # Laranja de destaque
                else:
                    hints_text = "[T] TURBO: DESLIGADO   |   [ESC] Pausar / Salvar"
                    hints_color = (130, 130, 130) # Cinza escuro discreto
                hints_lbl = self.FONT_BODY.render(hints_text, True, hints_color)
                self.display.blit(hints_lbl, (20, SCREEN_HEIGHT - 35))

                # Nota Explicativa da Escala (Rodapé Direito)
                note_font = self.FONT_NOTE
                note1 = note_font.render("* Escala física baseada no Sprite (1m = 10.75 px).", True, (130, 130, 130))
                note2 = note_font.render("* A velocidade e metros refletem a extrema aceleração Arcade do jogo.", True, (130, 130, 130))
                self.display.blit(note1, (SCREEN_WIDTH - note1.get_width() - 20, SCREEN_HEIGHT - 45))
                self.display.blit(note2, (SCREEN_WIDTH - note2.get_width() - 20, SCREEN_HEIGHT - 25))


                # --- Sistema de Rótulos de Personalidade Genética (Tooltips) ---
                dinos_vivos = [d for d in dinos if d.alive and not d.is_human]
                if len(dinos_vivos) <= 5 and len(dinos_vivos) > 0:
                    font_tooltip = self.FONT_TOOLTIP
                    
                    for index, dino in enumerate(dinos_vivos):
                        label = dino.get_trait_label()
                        y_offset = 30 + (index * 25)
                        
                        text_surf = font_tooltip.render(label, True, (255, 255, 0)) # Amarela
                        bg_rect = text_surf.get_rect()
                        bg_rect.inflate_ip(10, 4)
                        bg_surf = pygame.Surface(bg_rect.size, pygame.SRCALPHA)
                        bg_surf.fill((0, 0, 0, 180)) # Escuro semitransparente
                        bg_rect.midbottom = (dino.get_rect().centerx, dino.get_rect().top - y_offset)
                        text_rect = text_surf.get_rect(center=bg_rect.center)
                        
                        self.display.blit(bg_surf, bg_rect)
                        self.display.blit(text_surf, text_rect)
                        
                    # Legenda de Personalidades
                    legend_texts = [
                        "[ Furtivo ]: Agachado >60%",
                        "[ Calculista ]: Pulos exatos",
                        "[ Medroso ]: Pula longe",
                        "[ Kamikaze ]: Pula em cima",
                        "[ Gatilho Fácil ]: Atira muito",
                        "[ Exterminador ]: Abate Gigante"
                    ]
                    font_legend = self.FONT_LEGEND
                    lx = 20
                    ly = GROUND_Y + 5
                    for i, lt in enumerate(legend_texts):
                        leg_surf = font_legend.render(lt, True, (150, 150, 150))
                        self.display.blit(leg_surf, (lx, ly))
                        lx += leg_surf.get_width() + 15
                        if i == 2:
                            lx = 20
                            ly += 18

                # ── HUD ──────────────────────────────────────────────────

                pygame.display.flip()

            # Controle de FPS
            if self.turbo_mode:
                self.clock.tick(0)
            else:
                self.clock.tick(FPS)

        # Retorna os resultados sem fechar o pygame, mantendo a janela viva!
        return {
            "scores":       final_scores,
            "best_score":   max(final_scores) if final_scores else 0,
            "alive_frames": alive_frames,
            "save_and_exit": False
        }

    def _show_pause_menu(self, gen, max_score, alive, total, elapsed, mode="NEAT"):
        paused = True
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.display.blit(overlay, (0, 0))
        
        font = pygame.font.SysFont("courier new", 28, bold=True)
        title = font.render("=== SIMULAÇÃO PAUSADA ===", True, (255, 255, 255))
        self.display.blit(title, title.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 60)))
        
        sim_time = self.total_simulated_frames / 60.0
        sim_min, sim_sec = divmod(int(sim_time), 60)
        sim_hr, sim_min = divmod(sim_min, 60)
        
        tot_min, tot_sec = divmod(int(elapsed), 60)
        tot_hr, tot_min = divmod(tot_min, 60)
        
        if mode == "NEAT":
            stats = [
                f"Geração Atual: {gen}",
                f"Dinossauros Vivos: {alive} / {total}",
                f"Tempo Simulado (IA): {sim_hr}h {sim_min}m {sim_sec}s",
                f"Tempo de Treino Real: {tot_hr}h {tot_min}m {tot_sec}s",
                f"Melhor Score Geral: {max_score}"
            ]
        elif mode == "DQN":
            stats = [
                f"Episódio Atual: {gen}",
                f"Memória Replay: {alive} / {total}",
                f"Tempo Simulado (IA): {sim_hr}h {sim_min}m {sim_sec}s",
                f"Tempo de Treino Real: {tot_hr}h {tot_min}m {tot_sec}s",
                f"Melhor Score Geral: {int(max_score)}"
            ]
        else: # PPO
            stats = [
                f"Episódio Atual: {gen}",
                f"Updates na Rede: {alive}",
                f"Tempo Simulado (IA): {sim_hr}h {sim_min}m {sim_sec}s",
                f"Tempo de Treino Real: {tot_hr}h {tot_min}m {tot_sec}s",
                f"Melhor Score Geral: {int(max_score)}"
            ]
        
        for i, s in enumerate(stats):
            lbl = self.font.render(s, True, (200, 200, 200))
            self.display.blit(lbl, lbl.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 10 + i*25)))
            
        hint = self.font.render("[ESPAÇO] Continuar   [S] Salvar Treino   [ESC/Q] Sair", True, (255, 255, 0))
        self.display.blit(hint, hint.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 130)))
        pygame.display.flip()
        
        while paused:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    import sys; sys.exit(0)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        paused = False
                    elif event.key == pygame.K_s:
                        return "SAVE"
                    elif event.key in (pygame.K_ESCAPE, pygame.K_q):
                        pygame.quit()
                        import sys; sys.exit(0)
            self.clock.tick(15)

    def play_champion_endless(self, champion_ai, generation_text, time_text, checkpoint_state=None, play_once=False):
        """Modo replay para a IA Campeã."""
        self.ai_learned_text = f"A IA APRENDEU! {generation_text} | {time_text}"
        
        if checkpoint_state:
            self.generation = checkpoint_state.get('generation', self.generation)
            self.hi_score = checkpoint_state.get('hi_score', self.hi_score)
            self.hi_speed = checkpoint_state.get('hi_speed', self.hi_speed)
            self.history_best_scores = checkpoint_state.get('history_best_scores', [])
            self.history_best_speeds = checkpoint_state.get('history_best_speeds', [])
            self.history_avg_scores = checkpoint_state.get('history_avg_scores', [])
            
            # Ajusta o tempo de início baseado no offset salvo
            import time
            offset = checkpoint_state.get('start_time_offset', 0)
            self.start_time = time.time() - offset
            self.total_simulated_frames = checkpoint_state.get('total_simulated_frames', 0)
            
            # Atualiza o texto da UI (Oculto conforme pedido)
            self.ai_learned_text = None
            generation_arg = self.generation
        else:
            generation_arg = "CAMPEÃO"
        
        while True:
            results = self.play_population_mode(
                ai_list=[champion_ai],
                generation=generation_arg,
                labels=["[ Campeão ]"],
                human_in_loop=False
            )
            if results.get("save_and_exit") or play_once:
                break
                
        self.ai_learned_text = None


# ╔═══════════════════════════════════════════════════════════════╗
# ║                   IA DE DEMONSTRAÇÃO                         ║
# ╚═══════════════════════════════════════════════════════════════╝

def demo_ai_simple(state: tuple) -> int:
    """
    IA de demonstração baseada em regras simples.

    ╔═══════════════════════════════════════════════════════════╗
    ║  SUBSTITUA ESTA FUNÇÃO PELA SUA IA TREINADA!             ║
    ║                                                          ║
    ║  Ela recebe o estado e deve retornar uma ação:           ║
    ║    0 = não fazer nada                                    ║
    ║    1 = pular                                             ║
    ║    2 = abaixar                                           ║
    ║                                                          ║
    ║  Exemplo com PyTorch:                                    ║
    ║    def minha_ia(state):                                  ║
    ║        tensor = torch.tensor(state, dtype=torch.float32) ║
    ║        with torch.no_grad():                             ║
    ║            q_values = modelo(tensor)                     ║
    ║        return q_values.argmax().item()                   ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    dist      = state[0]
    height    = state[1]
    speed     = state[3]
    is_jump   = state[5]
    obst_type = state[7]

    if obst_type == 1.0 and height > 0.65 and dist < 0.28:
        return ACTION_DUCK

    threshold = 0.12 + speed * 0.18
    if dist < threshold and is_jump < 0.5:
        return ACTION_JUMP

    return ACTION_NONE


# ╔═══════════════════════════════════════════════════════════════╗
# ║                    PONTO DE ENTRADA                          ║
# ╚═══════════════════════════════════════════════════════════════╝

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Dino Game — Clone fiel do Jogo do Dinossauro (Python + Pygame)"
    )
    parser.add_argument(
        "--mode",
        choices=["train", "versus", "play", "population"],
        default="versus",
        help="Modo: train (RL) | versus (Humano vs IA) | play (solo) | population (N dinos)"
    )
    parser.add_argument("--episodes", type=int, default=5)
    parser.add_argument("--agents",   type=int, default=50,
                        help="Numero de agentes para o modo population (padrao: 50)")
    args = parser.parse_args()

    # ═══════════════════════════════════════════════════
    #  MODO TREINAMENTO
    # ═══════════════════════════════════════════════════
    if args.mode == "train":
        print("=" * 55)
        print("  MODO TREINAMENTO — Sem renderização, alta velocidade")
        print("=" * 55)
        env = DinoGame(render=False)
        for ep in range(1, args.episodes + 1):
            state = env.reset()
            total_r, steps = 0.0, 0
            while True:
                # ╔═════════════════════════════════════╗
                # ║  >>> PLUGUE SEU AGENTE RL AQUI <<<  ║
                # ╚═════════════════════════════════════╝
                action = demo_ai_simple(state)
                state, reward, done, score = env.play_step(action)
                total_r += reward
                steps   += 1
                if done:
                    print(f"  Ep {ep:>3d}/{args.episodes}  Score: {score:>5d}  "
                          f"Reward: {total_r:>8.1f}  Steps: {steps:>6d}")
                    break
        print("Concluido!")

    # ═══════════════════════════════════════════════════
    #  MODO VERSUS
    # ═══════════════════════════════════════════════════
    elif args.mode == "versus":
        print("=" * 55)
        print("  MODO DUELO: Jogador (cinza) vs IA (azul)")
        print("  ESPACO/cima Pular  | baixo Abaixar  | R Reiniciar  | ESC Sair")
        print("=" * 55)
        env = DinoGame(render=True)
        # ╔═════════════════════════════════════════════╗
        # ║  Substitua demo_ai_simple pela sua IA real ║
        # ╚═════════════════════════════════════════════╝
        env.play_versus_mode(ai_predict_function=demo_ai_simple)

    # ═══════════════════════════════════════════════════
    #  MODO POPULAÇÃO
    # ═══════════════════════════════════════════════════
    elif args.mode == "population":
        n = args.agents
        print("=" * 55)
        print(f"  MODO POPULACAO: {n} agentes simultaneos")
        print("  R Reiniciar  |  ESC Sair")
        print("=" * 55)

        # Cada agente usa a mesma IA de demo — substitua por funções reais
        # ╔══════════════════════════════════════════════════════════╗
        # ║  Para NEAT, gere uma função por rede neural:            ║
        # ║    ai_list = [make_predict(net) for net in population]  ║
        # ╚══════════════════════════════════════════════════════════╝
        ai_list = [demo_ai_simple] * n

        env    = DinoGame(render=True)
        result = env.play_population_mode(
            ai_list    = ai_list,
            generation = 1,
            labels     = [str(i) for i in range(n)],
        )
        print(f"  Melhor score: {result['best_score']}")
        print(f"  Score médio:  {sum(result['scores'])/len(result['scores']):.1f}")

    # ═══════════════════════════════════════════════════
    #  MODO SOLO
    # ═══════════════════════════════════════════════════
    elif args.mode == "play":
        print("=" * 55)
        print("  MODO SOLO — ESPACO/cima Pular | baixo Abaixar | ESC Sair")
        print("=" * 55)
        pygame.init()
        env   = DinoGame(render=True)
        state = env.reset()

        # Tela de início
        waiting = True
        while waiting:
            env.display.fill(BG_COLOR)
            env._draw_ground()
            env.dino.draw(env.display)
            env._draw_hud(0)
            msg = env.font.render("PRESSIONE ESPACO PARA COMECAR", True, TEXT_COLOR)
            env.display.blit(msg, msg.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))
            pygame.display.flip()
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if ev.type == pygame.KEYDOWN:
                    if ev.key in (pygame.K_SPACE, pygame.K_UP):
                        waiting = False
                    if ev.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()
            env.clock.tick(FPS)

        running          = True
        game_over_screen = False

        while running:
            action = ACTION_NONE

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    if game_over_screen and event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_r):
                        state            = env.reset()
                        game_over_screen = False

            if game_over_screen:
                env.display.fill(BG_COLOR)
                
                # Manter gráficos na tela de morte no modo play
                env._draw_graph(best_dino=env.dino)
                env._draw_neural_network(env._get_state(), 0)
                
                env._update_clouds()
                for c in env.clouds:
                    c.draw(env.display)
                env._draw_ground()
                for obs in env.obstacles:
                    obs.draw(env.display)
                env.dino.draw(env.display, dead=True)
                env._draw_hud(env.score)
                env._draw_game_over_screen(env.display)
                pygame.display.flip()
                env.clock.tick(FPS)
                continue

            keys = pygame.key.get_pressed()
            if keys[pygame.K_SPACE] or keys[pygame.K_UP]:
                action = ACTION_JUMP
            elif keys[pygame.K_DOWN]:
                action = ACTION_DUCK

            state, _, done, score = env.play_step(action)

            if done:
                game_over_screen = True
                env.history_best_scores.append(env.score)
                env.history_avg_scores.append(env.score)
                env.generation += 1

        pygame.quit()
