#!/usr/bin/env python3
"""
generate_assets.py
==================
Gera os sprites PNG para o Jogo do Dinossauro usando pixel art fiel ao original.
Execute UMA VEZ para criar a pasta assets/ com todos os PNGs necessários.

Uso:
    py generate_assets.py
"""
import pygame
import os

pygame.init()

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)

# Cor padrão do dino original (#535353)
DINO_COLOR = (83, 83, 83)
WHITE      = (255, 255, 255, 0)  # transparente

def make_surface(w, h):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    s.fill((0, 0, 0, 0))
    return s

def px(surf, x, y, w=1, h=1, color=DINO_COLOR):
    pygame.draw.rect(surf, color, (x, y, w, h))

def save(surf, name):
    path = os.path.join(ASSETS_DIR, name)
    pygame.image.save(surf, path)
    print(f"  Criado: {name}  ({surf.get_width()}x{surf.get_height()})")

# ──────────────────────────────────────────────────────────────────────────────
# Escala: cada "pixel" do Google Dino = 6px reais → dino fica ~88px alto
# ──────────────────────────────────────────────────────────────────────────────
S = 6  # escala de pixel

def draw_trex_body(surf, px_fn, leg_frame=1, dead=False):
    """
    Desenha o corpo completo do T-Rex.
    leg_frame: 1 = perna dianteira pra frente, 2 = perna traseira pra frente
    Coordenadas em pixels do sprite (S=1), depois escaladas.
    """
    C = DINO_COLOR
    # Cabeça (pixels sprite: col 5-12, row 0-5)
    head_pixels = [
        (5,0,8,1),(5,1,8,1),(5,2,8,1),
        (5,3,7,1),(5,4,6,1),
        # bico / queixo
        (9,3,4,1),(10,4,3,1),
        # olho (fundo branco dentro da cabeça)
    ]
    body_pixels = [
        # Pescoço
        (5,5,2,1),
        # Ombros + corpo
        (0,6,14,1),(0,7,14,1),(0,8,12,1),
        # Braço curto
        (4,9,3,1),
        # Corpo / barriga
        (5,9,7,1),(5,10,7,1),(5,11,5,1),
        # Quadril
        (5,12,3,1),(8,12,2,1),
    ]
    # Pernas
    if leg_frame == 1:
        leg_pixels = [
            # perna dianteira (direita)
            (7,13,2,1),(7,14,2,1),(7,15,2,1),(7,16,3,1),
            # perna traseira (esquerda)
            (5,12,2,1),(5,13,2,1),(5,14,2,1),(4,15,3,1),
        ]
    elif leg_frame == 2:
        leg_pixels = [
            # perna dianteira
            (7,13,2,1),(8,14,2,1),(8,15,2,1),(7,16,3,1),
            # perna traseira
            (5,12,2,1),(5,13,2,1),(6,14,2,1),(5,15,3,1),
        ]
    else:  # morto
        leg_pixels = [
            (7,13,2,1),(7,14,2,1),(7,15,2,1),(7,16,3,1),
            (5,12,2,1),(5,13,2,1),(5,14,2,1),(4,15,3,1),
        ]

    for grp in [head_pixels, body_pixels, leg_pixels]:
        for (cx, cy, cw, ch) in grp:
            pygame.draw.rect(surf, C,
                             (cx * S, cy * S, cw * S, ch * S))

    # Olho branco
    if not dead:
        pygame.draw.rect(surf, (247, 247, 247),
                         (8 * S, 1 * S, 2 * S, 2 * S))
    else:
        # Olho de X
        pygame.draw.rect(surf, (247, 247, 247),
                         (8 * S, 1 * S, 2 * S, 2 * S))
        pygame.draw.line(surf, C,
                         (8 * S, 1 * S), (10 * S - 1, 3 * S - 1), 2)
        pygame.draw.line(surf, C,
                         (10 * S - 1, 1 * S), (8 * S, 3 * S - 1), 2)


# ── Dino Run Frame 1 ──────────────────────────────────────────────
W, H = 14 * S, 18 * S
s = make_surface(W, H)
draw_trex_body(s, px, leg_frame=1)
save(s, "dino_run1.png")

# ── Dino Run Frame 2 ──────────────────────────────────────────────
s = make_surface(W, H)
draw_trex_body(s, px, leg_frame=2)
save(s, "dino_run2.png")

# ── Dino Dead ─────────────────────────────────────────────────────
s = make_surface(W, H)
draw_trex_body(s, px, leg_frame=1, dead=True)
save(s, "dino_dead.png")

# ── Dino Duck Frame 1 (corpo abaixado, pernas alternando) ─────────
# Layout horizontal: maior largura, menor altura
DW, DH = 20 * S, 12 * S
s = make_surface(DW, DH)
C = DINO_COLOR
# Cabeça (mais à direita, inclinada)
duck_head = [(12,0,8,1),(12,1,8,1),(12,2,8,1),(12,3,6,1),(14,3,4,1)]
# Corpo comprido
duck_body = [
    (0,4,22,1),(0,5,22,1),(0,6,22,1),
    (0,7,18,1),
]
duck_legs1 = [
    (14,8,2,1),(14,9,2,1),(14,10,2,1),(13,11,3,1),
    (10,8,2,1),(10,9,2,1),(10,10,2,1),(9,11,3,1),
]
for grp in [duck_head, duck_body, duck_legs1]:
    for (cx, cy, cw, ch) in grp:
        pygame.draw.rect(s, C, (cx * S, cy * S, cw * S, ch * S))
# Olho
pygame.draw.rect(s, (247, 247, 247), (17 * S, 1 * S, 2 * S, 2 * S))
save(s, "dino_duck1.png")

# ── Dino Duck Frame 2 ─────────────────────────────────────────────
s = make_surface(DW, DH)
duck_legs2 = [
    (14,8,2,1),(15,9,2,1),(15,10,2,1),(14,11,3,1),
    (10,8,2,1),(10,9,2,1),(11,10,2,1),(10,11,3,1),
]
for grp in [duck_head, duck_body, duck_legs2]:
    for (cx, cy, cw, ch) in grp:
        pygame.draw.rect(s, C, (cx * S, cy * S, cw * S, ch * S))
pygame.draw.rect(s, (247, 247, 247), (17 * S, 1 * S, 2 * S, 2 * S))
save(s, "dino_duck2.png")

# ──────────────────────────────────────────────────────────────────
# PTERODÁCTILO — fiel à imagem de referência
# ──────────────────────────────────────────────────────────────────
PS = 5  # escala do ptero

def make_ptero(wing_up=True):
    PW, PH = 18 * PS, 10 * PS
    s = make_surface(PW, PH)
    C = DINO_COLOR
    # Corpo horizontal
    body = [(6,4,8,1),(6,5,8,1),(6,6,6,1)]
    # Bico
    bico = [(14,4,4,1),(15,5,3,1)]
    # Cauda
    cauda = [(2,5,4,1),(0,6,4,1)]

    if wing_up:
        # Asa levantada em triângulo acima do corpo
        asa = [
            (8,0,2,1),
            (7,1,4,1),
            (5,2,6,1),
            (4,3,8,1),
        ]
    else:
        # Asa abaixada
        asa = [
            (5,7,6,1),
            (4,8,8,1),
            (5,9,6,1),
        ]

    for grp in [body, bico, cauda, asa]:
        for (cx, cy, cw, ch) in grp:
            pygame.draw.rect(s, C, (cx * PS, cy * PS, cw * PS, ch * PS))
    return s

save(make_ptero(wing_up=True),  "bird1.png")
save(make_ptero(wing_up=False), "bird2.png")

# ──────────────────────────────────────────────────────────────────
# CACTOS — fiel às imagens de referência (tronco fino, braços laterais)
# ──────────────────────────────────────────────────────────────────
CS = 5  # escala do cacto

def draw_cactus_single(surf, col_offset, scale):
    """Desenha um cacto simples centrado em col_offset."""
    C = DINO_COLOR
    arm_left  = [(0,4,2,1),(0,5,2,1),(0,6,2,1)]
    arm_right = [(4,6,2,1),(4,7,2,1),(4,8,2,1)]
    junction  = [(0,7,6,1)]
    trunk     = [(2,0,2,1),(2,1,2,1),(2,2,2,1),(2,3,2,1),
                 (2,8,2,1),(2,9,2,1),(2,10,2,1),(2,11,2,1),
                 (2,12,2,1),(2,13,2,1),(2,14,2,1),(2,15,2,1),
                 (1,15,4,1)]  # base alargada

    for grp in [arm_left, arm_right, junction, trunk]:
        for (cx, cy, cw, ch) in grp:
            pygame.draw.rect(surf, C,
                             ((col_offset + cx) * scale, cy * scale,
                              cw * scale, ch * scale))

# Cacto pequeno (1 único)
CW, CH = 6 * CS, 16 * CS
s = make_surface(CW, CH)
draw_cactus_single(s, 0, CS)
save(s, "cactus_small.png")

# Cacto grande (2 juntos + um menor)
CW2 = 15 * CS
s = make_surface(CW2, CH)
draw_cactus_single(s, 0, CS)   # cacto 1
draw_cactus_single(s, 7, CS)   # cacto 2 (maior — trunco mais alto)
# mini-cacto no meio
mini = [(2,3,2,1),(2,4,2,1),(2,5,2,1),(2,6,2,1),(2,7,2,1),
        (2,8,2,1),(2,9,2,1),(2,10,2,1),(2,11,2,1),(1,11,4,1)]
for (cx, cy, cw, ch) in mini:
    pygame.draw.rect(s, DINO_COLOR,
                     ((3 + cx) * CS, (4 + cy) * CS, cw * CS, ch * CS))
save(s, "cactus_large.png")

# ──────────────────────────────────────────────────────────────────
# NUVEM
# ──────────────────────────────────────────────────────────────────
CLS = 3
cloud_pixels = [
    (2,1,3,1),(4,0,3,1),
    (1,2,7,1),
    (0,3,9,1),
    (0,4,9,1),
]
s = make_surface(9 * CLS, 5 * CLS)
for (cx, cy, cw, ch) in cloud_pixels:
    pygame.draw.rect(s, (200, 200, 200), (cx * CLS, cy * CLS, cw * CLS, ch * CLS))
save(s, "cloud.png")

print("\nTodos os assets foram gerados com sucesso em:", ASSETS_DIR)
pygame.quit()
