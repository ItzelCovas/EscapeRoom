import pygame
from pygame.locals import *

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

import math
import time
import random
import objloader
import requests
import os
import re

os.chdir(os.path.dirname(__file__))

def reparar_mtl(obj_filename):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    obj_path = os.path.join(script_dir, obj_filename)

    if not os.path.exists(obj_path):
        print(f"No se encontró el archivo OBJ en: {obj_path}")
        return

    with open(obj_path, 'r', encoding='utf-8', errors='ignore') as f:
        mtl_name = None
        for line in f:
            if line.strip().lower().startswith('mtllib'):
                mtl_name = line.strip().split(maxsplit=1)[1]
                break

    if not mtl_name:
        return

    mtl_path = os.path.join(script_dir, mtl_name)
    if not os.path.exists(mtl_path):
        return

    with open(mtl_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    fixed_lines = []
    for line in lines:
        if line.strip().startswith("map_Kd"):
            parts = line.strip().split(maxsplit=1)
            if len(parts) == 2:
                tex_path = parts[1].strip().strip('"')
                if os.path.isabs(tex_path):
                    tex_name = os.path.basename(tex_path)
                    fixed_lines.append(f"map_Kd {tex_name}\n")
                    continue
        fixed_lines.append(line)

    with open(mtl_path, 'w', encoding='utf-8', errors='ignore') as f:
        f.writelines(fixed_lines)
    print(f"MTL reparado: {mtl_path}")


class Ghost:
    def __init__(self, plane_size=100):
        self.model = objloader.OBJ('ghost_low.obj'); self.model.generate()
        self.x = 0.0; self.y = 1.0; self.z = 0.0
        self.angle_y = 0.0

        # grid (1 - 10)
        self.grid_x = 5; self.grid_y = 5
        self.target_grid_x = 5; self.target_grid_y = 5
        self.target_x = 0.0; self.target_z = 0.0

        self.interpolation_speed = 5.0
        self.float_time = random.uniform(0, 10)
        self.base_y = self.y
        
        self.is_evil = False 

        self.x, self.z = self.grid_to_opengl(self.grid_x, self.grid_y)
        self.target_x, self.target_z = self.x, self.z

    def grid_to_opengl(self, grid_x, grid_y):
        return (grid_x - 5.5) * 2.2, (grid_y - 5.5) * 2.2

    def set_target_position(self, grid_x, grid_y):
        gx = max(1, min(10, int(grid_x)))
        gy = max(1, min(10, int(grid_y)))
        self.target_grid_x, self.target_grid_y = gx, gy
        self.target_x, self.target_z = self.grid_to_opengl(gx, gy)
        
    def update_state(self, is_evil):
        self.is_evil = is_evil

    def update(self, dt):
        dx = self.target_x - self.x
        dz = self.target_z - self.z
        dist = math.hypot(dx, dz)
        step = self.interpolation_speed * max(0.0, dt)

        if dist <= step or dist < 0.1:
            self.x, self.z = self.target_x, self.target_z
            self.grid_x, self.grid_y = self.target_grid_x, self.target_grid_y
        else:
            self.x += (dx / dist) * step
            self.z += (dz / dist) * step

        self.float_time += dt
        self.y = self.base_y + math.sin(self.float_time * 2.5) * 0.8
        
        self.x = max(-9.0, min(self.x, 9.0))
        self.z = max(-4.0, min(self.z, 12.0))

    def draw(self):
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        glRotatef(self.angle_y, 0.0, 1.0, 0.0)
        glScalef(0.3, 0.3, 0.3)
        
        # 1. Dibujar fantasma  
        glColor3f(1.0, 1.0, 1.0)
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_LIGHTING) 
        self.model.render()
        
        # 2. Dibujar aura roja (si es malo)
        if self.is_evil:
            # Guardamos estado (luces, texturas actuales)
            glPushAttrib(GL_ALL_ATTRIB_BITS)
            
            glDisable(GL_TEXTURE_2D)   # Apagar texturas (
            glDisable(GL_LIGHTING)     # Apagar luces
            glEnable(GL_BLEND)         # Transparencia
            glBlendFunc(GL_SRC_ALPHA, GL_ONE) 
            glDepthMask(GL_FALSE)      

            # COLOR ROJO SEMITRANSPARENTE
            glColor4f(1.0, 0.0, 0.0, 0.4) 

            # DIBUJAR ESFERA - radio (2.5) ajustar tamaño
            aura_radius = 3.5 
            #glutSolidSphere(aura_radius, 20, 20)
            
            glPopAttrib()
            
        glPopMatrix()

class Personaje:
    def __init__(self, model_paths):
        self.body = objloader.OBJ(model_paths['body'])
        self.arm_l = objloader.OBJ(model_paths['left_arm'])
        self.arm_r = objloader.OBJ(model_paths['right_arm'])
        self.leg_l = objloader.OBJ(model_paths['left_leg'])
        self.leg_r = objloader.OBJ(model_paths['right_leg'])
        
        self.body.generate(); self.arm_l.generate(); self.arm_r.generate()
        self.leg_l.generate(); self.leg_r.generate()

        self.x = 0.0; self.y = 0.0; self.z = 5.0
        self.angle_y = 180.0
        self.radius = 1.0
        self.walk_time = 0.0; self.walk_speed = 12.0

    def update(self, dt, is_moving):
        if is_moving: self.walk_time += dt
        self.y = 0.0

    def draw(self):
        try:
            glPushMatrix()
            glTranslatef(self.x, self.y, self.z)
            glRotatef(self.angle_y, 0.0, 1.0, 0.0)
            
            self.body.render()
            
            # Animación  de caminar
            angle = math.sin(self.walk_time * self.walk_speed) * 10.0 #10 es el ángulo máximo de oscilación de las extremidades 
            
            # Extremidades
            for part, a in [(self.arm_l, -angle), (self.arm_r, angle), 
                            (self.leg_l, angle), (self.leg_r, -angle)]:
                glPushMatrix()
                glRotatef(a if part in [self.arm_l, self.arm_r] else a, 1, 0, 0)
                part.render()
                glPopMatrix()
        finally:
            glPopMatrix()

class PropEstatico:
    def __init__(self, model_path, pos=[0,0,0], scale=1.0, rot=[0,0,0]):
        try:
            self.model = objloader.OBJ(model_path); self.model.generate()
            self.position = pos
            self.scale = [scale]*3 if isinstance(scale, (int, float)) else scale
            self.rotation = rot
        except:
            print(f"Error cargando {model_path}")

    def draw(self):
        glPushMatrix()
        glTranslatef(*self.position)
        glRotatef(self.rotation[0], 1, 0, 0)
        glRotatef(self.rotation[1], 0, 1, 0)
        glRotatef(self.rotation[2], 0, 0, 1)
        glScalef(*self.scale)
        self.model.render()
        glPopMatrix()

class Key:
    def __init__(self, model_path, pos=None, scale=1.0):
        self.model = objloader.OBJ(model_path); self.model.generate()
        self.x = pos[0]; self.y = pos[1]; self.z = pos[2]        
        
        self.grid_x = int((self.x / 2.2) + 5.5)
        self.grid_y = int((self.z / 2.2) + 5.5)
        
        self.grid_x = max(1, min(10, self.grid_x))
        self.grid_y = max(1, min(10, self.grid_y))
        
        self.scale = scale
        self.angle_y = 0.0
        
        self.is_visible = True
        self.is_collected = False
            
    def collect(self):
        if self.is_visible and not self.is_collected:
            self.is_visible = False
            self.is_collected = True
            return True
        return False

    def update(self, dt):
        if self.is_visible: 
            self.angle_y += 45 * dt

    def draw(self):
        if not self.is_visible: return
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        glRotatef(self.angle_y, 0, 1, 0)
        glScalef(self.scale, self.scale, self.scale)
        self.model.render()
        glPopMatrix()

class Puerta(PropEstatico):
    def __init__(self, model_path, pos=[0,0,0], scale=1.0):
        super().__init__(model_path, pos, scale)
        self.original_pos = list(pos)
        self.target_x = self.original_pos[0]
        self.move_speed = 2.0 # Velocidad de apertura

    def abrir(self, offset_x=-2.5): # Ajusta el offset según cuánto quieres que se abra
        self.target_x = self.original_pos[0] + offset_x

    def update(self, dt):
        # Si la posición actual es diferente al destino, muévela
        if abs(self.position[0] - self.target_x) > 0.05:
            direction = 1 if self.target_x > self.position[0] else -1
            self.position[0] += direction * self.move_speed * dt

# CONFIGURACIÓN GLOBAL
screen_width = 1050; screen_height = 800
FOVY = 75.0; ZNEAR = 0.1; ZFAR = 500.0

personaje = None; ghost = None
escenario = None; decoracion = None
props_escondite = [] 
mesa_prop = None 
keys_list = []
puerta_salida = None
collision_boxes = []

game_state = {
    'llaves_recogidas': 0, 'total_llaves': 3,
    'puerta_abierta': False, 'game_over': False, 'win': False    
}

ui_font = None
server_cooldown = 0.0

def get_game_state():
    try:
        res = requests.get("http://localhost:8000/update", timeout=0.1)
        data = res.json()
        
        ghost_tuple = (None, None, False)
        active_keys_grid = []

        # procesar fantasma
        if "ghosts" in data and len(data["ghosts"]) > 0:
            g_data = data["ghosts"][0]
            if isinstance(g_data, dict):
                pos = g_data["pos"]
                is_evil_server = g_data["is_evil"]
                ghost_tuple = (pos[0], pos[1], is_evil_server)

        # procesar Llaves
        if "keys" in data:
            active_keys_grid = [(k[0], k[1]) for k in data["keys"]]
            
        return ghost_tuple, active_keys_grid
            
    except Exception:
        return (None, None, False), []

def notify_evil_trigger():
    """Avisa a Julia que tocamos la mesa para volver malo al fantasma"""
    try:
        requests.post("http://localhost:8000/trigger_evil", json={}, timeout=1.0)
        print(">>> TRIGGER ENVIADO: ¡Fantasma Malo!")
    except Exception as e:
        print(f"Error trigger: {e}")

def init_keys_in_julia():
    global ghost, server_cooldown
    
    print("Realizando limpieza local del fantasma...")
    ghost.is_evil = False           
    ghost.set_target_position(5, 5)  
    ghost.x, ghost.z = ghost.target_x, ghost.target_z 
    
    server_cooldown = time.time() + 2.0 
    
    try:
        print("Enviando petición de reinicio a Julia...")
        key_positions = [(k.grid_x, k.grid_y) for k in keys_list]
        requests.post("http://localhost:8000/init_keys", json={"keys": key_positions}, timeout=1.0)
        print("Petición enviada.")
            
    except Exception as e:
        print(f"Error contactando a Julia (pero el reset local funcionará): {e}")

def notify_key_collected(gx, gy):
    try:
        requests.post("http://localhost:8000/collect_key", json={"x": gx, "y": gy})
    except: pass


# JUEGO 
def Init():
    global personaje, ghost, escenario, decoracion, props_escondite, mesa_prop, keys_list, puerta_salida, ui_font, collision_boxes
    
    # 1. Configuración de Ventana y OpenGL
    screen = pygame.display.set_mode((screen_width, screen_height), DOUBLEBUF | OPENGL)
    glutInit()
    pygame.display.set_caption("EscapeRoom: The Evil Table")
    
    glMatrixMode(GL_PROJECTION); glLoadIdentity()
    gluPerspective(FOVY, screen_width/screen_height, ZNEAR, ZFAR)
    glMatrixMode(GL_MODELVIEW); glLoadIdentity()
    
    glEnable(GL_DEPTH_TEST)
    glDisable(GL_LIGHTING); glEnable(GL_LIGHT0)
    glEnable(GL_COLOR_MATERIAL) 
    #glLightfv(GL_LIGHT0, GL_POSITION, (0, 200, 0, 0.0))
    
    ui_font = pygame.font.Font(None, 36)

    # 2. Cargar Escenario
    print("Cargando escenario...")
    reparar_mtl('habitacion.obj'); escenario = PropEstatico('habitacion.obj')
    reparar_mtl('decoracion.obj'); decoracion = PropEstatico('decoracion.obj')
    
    # 3. Cargar Personaje
    print("Cargando personaje...")
    personaje = Personaje({
        'body': 'body_head.obj', 'left_arm': 'arm_left.obj', 'right_arm': 'arm_right.obj',
        'left_leg': 'leg_left.obj', 'right_leg': 'leg_right.obj'
    })
    
    print("Cargando fantasma...")
    ghost = Ghost()
    
    reparar_mtl('barril.obj'); reparar_mtl('cajas.obj'); reparar_mtl('cofre.obj'); reparar_mtl('mesa.obj')
    
    p_barril = PropEstatico('barril.obj', pos=[0,0,0])
    p_cajas = PropEstatico('cajas.obj', pos=[0,0,0])
    p_cofre = PropEstatico('cofre.obj', pos=[0,0,0])
    
    mesa_prop = PropEstatico('mesa.obj', pos=[0, 0, 0], scale=1.0) 
    
    props_escondite = [p_barril, p_cajas, p_cofre, mesa_prop]
    
    print("Cargando llaves...")
    reparar_mtl('key.obj')
    keys_list = [
        Key('key.obj', pos=[-8.65, 1.0, -2.4], scale=1.5),
        Key('key.obj', pos=[9.0, 1.0, -3.1], scale=1.5),
        Key('key.obj', pos=[8.70, 1.0, 1.15], scale=1.5),
        Key('key.obj', pos=[-8.0, 1.0, 7.0], scale=1.5),
        Key('key.obj', pos=[6.0, 1.0, 7.0], scale=1.5)
    ]
    game_state['total_llaves'] = 3
    
    reparar_mtl('puerta.obj')
    puerta_salida = Puerta('puerta.obj', pos=[0,0,0])
    
    # Definir cajas de colisión (Paredes + Muebles) - [x_min, x_max, z_min, z_max]
    collision_boxes = [
        # Paredes del cuarto
        [-10.0, 12.15, 7.8, 9.25],   # Norte
        [-8.80, 8.90, -4.85, -4.75], # Sur
        [9.45, 9.55, -4.80, 13.20],  # Este
        [-9.85, -9.75, -4.50, 7.0],  # Oeste
        
        # Muebles 
        [-9.10, -8.20, -4.0, -2.80], # Barril
        [8.95, 9.05, -3.60, -2.60],  # Cajas
        [8.95, 9.05, -4.90, -4.80],  # Cofre
        [-2.70, -1.20, -1.60, 2.90]  # Mesa
    ]
    
    init_keys_in_julia()
    
    print("Inicialización completada.")
    
def check_collision(x, z, radius, boxes):
    for box in boxes:
        closest_x = max(box[0], min(x, box[1]))
        closest_z = max(box[2], min(z, box[3]))
        dist = (x - closest_x)**2 + (z - closest_z)**2
        if dist < radius**2: return True
    return False

def draw_text(text, x, y, color=(255, 255, 255)):
    try:
        surf = ui_font.render(text, True, color)
        data = pygame.image.tostring(surf, "RGBA", True)
        glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
        gluOrtho2D(0, screen_width, 0, screen_height)
        glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
        glDisable(GL_LIGHTING); glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_TEXTURE_2D)
        
        texid = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texid)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, surf.get_width(), surf.get_height(), 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(x, y)
        glTexCoord2f(1, 0); glVertex2f(x+surf.get_width(), y)
        glTexCoord2f(1, 1); glVertex2f(x+surf.get_width(), y+surf.get_height())
        glTexCoord2f(0, 1); glVertex2f(x, y+surf.get_height())
        glEnd()
        
        glDisable(GL_TEXTURE_2D); glDisable(GL_BLEND); glEnable(GL_LIGHTING)
        glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW); glPopMatrix()
        glDeleteTextures(1, [texid])
    except: pass

def lookat():
    glLoadIdentity()
    gluLookAt(0, 12, 18, 0, 0, 0, 0, 1, 0)

def display(dt, is_moving):
    global frame_count
    
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    lookat()
    
    puerta_salida.update(dt)

    escenario.draw()
    decoracion.draw()
    puerta_salida.draw()
    for p in props_escondite: p.draw()
    
    frame_count += 1
    
    can_update = time.time() > server_cooldown
    
    if can_update and frame_count % 5 == 0: 
        ghost_info, active_keys_from_julia = get_game_state()
        
        gx, gy, is_evil_server = ghost_info
        
        if gx is not None:
            # Actualizar posición objetivo del fantasma
            ghost.set_target_position(gx, gy)
            
            if not is_evil_server:
                #  a qué llave está yendo 
                dist_min = 999
                target_k = None
                for k in keys_list:
                    if not k.is_collected:
                        d = math.sqrt((gx - k.grid_x)**2 + (gy - k.grid_y)**2)
                        if d < dist_min:
                            dist_min = d
                            target_k = k
                
                estado = "Moviéndose"
                if dist_min == 0: estado = "Esperando en llave"
                
                print(f"debugg ({gx}, {gy}) -> {estado} | Distancia a llave: {dist_min:.1f}")
            
            # Actualizar estado (Malo/Bueno)
            ghost.update_state(is_evil_server)
            
            server_keys_set = set(active_keys_from_julia)
            
            for k in keys_list:
                if k.is_visible and not k.is_collected: #si la llave está visible
                    
                    if (k.grid_x, k.grid_y) not in server_keys_set:
                        
                        # se calcula distancia real entre fantasma y llave
                        dist_x = ghost.x - k.x
                        dist_z = ghost.z - k.z
                        dist_real = math.sqrt(dist_x*dist_x + dist_z*dist_z)
                        
                        #  ha sido comida por el fantasma sólo si está cerca, es malo y está a menos de 2 unidades
                        if is_evil_server and dist_real < 2.0:
                            print(f"Fantasma comió llave en {k.grid_x}, {k.grid_y}")
                            k.is_visible = False
                            k.is_collected = True
                            game_state['ghost_ate_key'] = True
                        else:
                            pass

    ghost.update(dt)
    personaje.update(dt, is_moving)
    
    # Dibujar y actualizar llaves
    for k in keys_list: 
        k.update(dt)
        k.draw()
    
    ghost.draw()     #se dibujará con esfera roja si is_evil=True
    personaje.draw()
    
    texto_llaves = f"Llaves: {game_state['llaves_recogidas']}/{game_state['total_llaves']}"
    draw_text(texto_llaves, 10, screen_height-40)

    # 6. Interfaz de Usuario (UI)
    #draw_text(f"Llaves: {game_state['llaves_recogidas']}/{game_state['total_llaves']}", 10, screen_height-40)
    
    if interaction_message:
        tw = ui_font.size(interaction_message)[0]
        draw_text(interaction_message, (screen_width-tw)/2, 50)
    
    if game_state['game_over']: 
        draw_text("¡PERDISTE!", 400, 400, (255,0,0))
    if game_state['win']: 
        draw_text("ESCAPASTE!", 400, 400, (0,255,0))
        
    #draw_text(f"X: {personaje.x:.2f} | Z: {personaje.z:.2f}", 10, 10, (255, 255, 0))

#  MAIN LOOP 
pygame.init(); pygame.font.init()
Init()
clock = pygame.time.Clock()
frame_count = 0
done = False
move_speed = 7.0; rotate_speed = 100.0
interaction_message = ""

print("JUEGO INICIADO. Toca la MESA para activar la maldición.")

server_has_started = False

while not done:
    dt = clock.tick(60) / 1000.0
    keys = pygame.key.get_pressed()
    is_moving = False
    
    if game_state['win'] or game_state['game_over']: dt = 0
    
    # Movimiento
    move_x = 0; move_z = 0
    if keys[pygame.K_UP]:
        move_x += math.sin(math.radians(personaje.angle_y)) * move_speed * dt
        move_z += math.cos(math.radians(personaje.angle_y)) * move_speed * dt
        is_moving = True
    if keys[pygame.K_DOWN]:
        move_x -= math.sin(math.radians(personaje.angle_y)) * move_speed * dt
        move_z -= math.cos(math.radians(personaje.angle_y)) * move_speed * dt
        is_moving = True
    if keys[pygame.K_LEFT]: personaje.angle_y += rotate_speed * dt
    if keys[pygame.K_RIGHT]: personaje.angle_y -= rotate_speed * dt
    
    if not check_collision(personaje.x + move_x, personaje.z, 1.0, collision_boxes): personaje.x += move_x
    if not check_collision(personaje.x, personaje.z + move_z, 1.0, collision_boxes): personaje.z += move_z

    interaction_message = ""
    
    # Distancia a la MESA (Trigger)
    dist_mesa = math.sqrt((personaje.x - mesa_prop.position[0])**2 + (personaje.z - mesa_prop.position[2])**2)
    if dist_mesa < 4.0 and not ghost.is_evil:
        interaction_message = "Presiona ESPACIO para tocar la MESA"

    # Distancia a LLAVES
    for k in keys_list:
        if k.is_collected: continue
        if math.sqrt((personaje.x - k.x)**2 + (personaje.z - k.z)**2) < 2.5:
            interaction_message = "Presiona ESPACIO para tomar LLAVE"
            break
            
    # 3. Salida
    if game_state['puerta_abierta']:
        dist_puerta = math.sqrt((personaje.x - puerta_salida.original_pos[0])**2 + (personaje.z - puerta_salida.original_pos[2])**2)
        if dist_puerta < 5.0: interaction_message = "Presiona ESPACIO para SALIR"

    for event in pygame.event.get():
        if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE): done = True
        
        if event.type == KEYDOWN and event.key == K_SPACE:
            #  Activar mesa
            if dist_mesa < 4.0:
                notify_evil_trigger()
            
            # Recoger Llave
            for k in keys_list:
                if not k.is_collected and math.sqrt((personaje.x - k.x)**2 + (personaje.z - k.z)**2) < 2.5:
                    if k.collect():
                        game_state['llaves_recogidas'] += 1
                        notify_key_collected(k.grid_x, k.grid_y)
            
            # Salir
            if game_state['puerta_abierta'] and dist_puerta < 5.0:
                game_state['win'] = True

    # Check fin juego (puerta)
    if game_state['llaves_recogidas'] == game_state['total_llaves'] and not game_state['puerta_abierta']:
        print("¡TODAS LAS LLAVES RECOGIDAS! Abriendo puerta...")
        puerta_salida.abrir() # Esto cambia el target_x de la puerta
        game_state['puerta_abierta'] = True

    if game_state['puerta_abierta']:
        dist_puerta = math.sqrt((personaje.x - puerta_salida.original_pos[0])**2 + (personaje.z - puerta_salida.original_pos[2])**2)
        if dist_puerta < 4.0: # Distancia para salir
            interaction_message = "¡CORRE! Presiona ESPACIO para SALIR"
            
            if keys[pygame.K_SPACE]: 
                game_state['win'] = True

    # Calculamos cuántas llaves quedan vivas + las que se tengan
    llaves_vivas = 0
    for k in keys_list:
        if k.is_visible and not k.is_collected: 
            llaves_vivas += 1
    
    posibles_totales = game_state['llaves_recogidas'] + llaves_vivas 
    
    if posibles_totales < game_state['total_llaves'] and not game_state['game_over']:
        print("Ya no quedan suficientes llaves en el mapa. GAME OVER.")
        game_state['game_over'] = True

    display(dt, is_moving)
    pygame.display.flip()

pygame.quit()