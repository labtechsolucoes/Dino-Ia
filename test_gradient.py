import pygame
pygame.display.set_mode((1,1))
img = pygame.image.load('Jogo/assets/fogo1.bmp').convert()
bg_r, bg_g, bg_b, _ = img.get_at((0,0))
w,h = img.get_size()
match=0
total=w*h
for x in range(w):
 for y in range(h):
  r,g,b,_ = img.get_at((x,y))
  if abs(r-bg_r)<60 and abs(g-bg_g)<60 and abs(b-bg_b)<60: match+=1
print('Matches:', match, 'Total:', total)
