"""
ESCAPE ROOM 

CONTROLES:
- Flechas (Arriba/Abajo): Moverse hacia adelante/atrás.
- Flechas (Izquierda/Derecha): Girar (rotar) al personaje.
- Espacio: Interactuar con objetos (buscar llaves, recoger llaves, escapar).
- ESC: Salir del juego.
"""

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import math
import random
import objloader 
from transformations import OpMat 

class Ghost:
    def __init__(self, plane_size=100):
        """
        Constructor del Fantasma. Se llama al crear un 'new Ghost()'.
        """
        self.model = objloader.OBJ('visuales/ghost_low.obj')
        self.model.generate() 
        
        # Límites del área donde puede moverse
        self.min_val = -plane_size / 2
        self.max_val = plane_size / 2
        
        # Posición y rotación inicial
        self.x = 0.0
        self.y = 1.0 # Altura de flote
        self.z = 0.0
        self.angle_y = 0.0 # Rotacion inicial
        
        self.speed = 2.0 # Velocidad del fantasma
        
        self.target_x, self.target_z = 0, 0
        self.get_new_random_target() 

        # Variables para el efecto de flotación 
        self.float_time = random.uniform(0, 10) # Tiempo para la onda seno
        self.float_amplitude = 1.0  # Qué tanto sube y baja
        self.float_speed = 2.0      # Qué tan rápido lo hace
        self.base_y = self.y        # Altura base sobre la que flota
        self.radius = 0.5 # Radio de colisión (para chocar)

    def get_new_random_target(self):
        """Elige un nuevo punto aleatorio en el mapa para moverse hacia él."""
        self.target_x = random.uniform(self.min_val, self.max_val)
        self.target_z = random.uniform(self.min_val, self.max_val)

    def update(self, dt, collision_boxes):
        """
        Actualiza la lógica del fantasma cada frame.
        'dt' (delta time) es el tiempo pasado desde el último frame.
        """
        
        # LOGICA DE IA DEL FANTASMA (Simple Wander)
        dir_x = self.target_x - self.x
        dir_z = self.target_z - self.z
        distance = math.sqrt(dir_x**2 + dir_z**2)
        
        if distance < 3.0: 
            self.get_new_random_target()
        
        # 3. Normaliza el vector de dirección (para tener velocidad constante)
        norm_x = dir_x / max(distance, 1e-6) # max(..., 1e-6) evita dividir por cero
        norm_z = dir_z / max(distance, 1e-6)
        
        # Calcula la nueva posición potencial
        new_x = self.x + norm_x * self.speed * dt
        new_z = self.z + norm_z * self.speed * dt

        # 4. Chequea colisión en X
        if not check_collision(new_x, self.z, self.radius, collision_boxes):
            self.x = new_x # Si no choca, se mueve
        else:
            self.get_new_random_target() # Si choca, busca otro lado

        # 5. Chequea colisión en Z (separado de X, permite "deslizarse")
        if not check_collision(self.x, new_z, self.radius, collision_boxes):
            self.z = new_z # Si no choca, se mueve
        else:
            self.get_new_random_target() # Si choca, busca otro lado

        # 6. Rotacion suave (mira hacia donde se mueve)
        target_angle = math.degrees(math.atan2(norm_x, norm_z)) # Ángulo objetivo
        self.angle_y += (target_angle - self.angle_y) * 0.1 # Se acerca 10% al ángulo

        # 7. Flotacion (usando una onda seno)
        self.float_time += dt
        self.y = self.base_y + math.sin(self.float_time * self.float_speed) * self.float_amplitude

    def draw(self):
        """Dibuja el fantasma en la pantalla."""
        try:
            glPushMatrix() # Guarda la matriz de transformación actual
            
            # 1. Mueve el "lápiz" a la posición del fantasma
            glTranslatef(self.x, self.y, self.z) 
            # 2. Rota el "lápiz" para que mire en su dirección
            glRotatef(self.angle_y, 0.0, 1.0, 0.0)
            # 3. Escala el modelo (si es muy grande o pequeño)
            glScalef(0.3, 0.3, 0.3)  
            
            # 4. Dibuja el modelo
            self.model.render()
        finally:
            glPopMatrix() # Restaura la matriz de transformación original


class Personaje:
    def __init__(self, model_paths):
        """
        Constructor del Personaje.
        'model_paths' es un diccionario con las rutas a los .obj de cada parte.
        """
        self.body = objloader.OBJ(model_paths['body'])
        self.arm_l = objloader.OBJ(model_paths['left_arm'])
        self.arm_r = objloader.OBJ(model_paths['right_arm'])
        self.leg_l = objloader.OBJ(model_paths['left_leg'])
        self.leg_r = objloader.OBJ(model_paths['right_leg'])
        
        self.body.generate()
        self.arm_l.generate()
        self.arm_r.generate()
        self.leg_l.generate()
        self.leg_r.generate()

        # Posición inicial
        self.x = 0.0
        self.y = 0.0  # Altura fija sobre el suelo
        self.z = 5.0 # Posicion inicial (cerca de la puerta)
        self.angle_y = 180.0 # Mirando hacia el cuarto
        self.radius = 0.5 # Radio de colisión

        # Variables para la animación de caminar
        self.walk_time = 0.0      # Contador de tiempo (como self.float_time del fantasma)
        self.leg_amplitude = 20.0 # Grados que se mueven las piernas
        self.arm_amplitude = 8.0  # Grados que se mueven los brazos
        self.walk_speed = 8.0     # Rapidez de la animación

    def update(self, dt, is_moving):
        """
        Actualiza la lógica del personaje.
        'is_moving' es un booleano que viene del bucle principal.
        """
        if is_moving:
            self.walk_time += dt # Avanza el tiempo de animación solo si se mueve
        self.y = 0.0 # Se asegura de estar siempre en el suelo

    def draw(self):
        """
        Dibuja el personaje y todas sus partes animadas.
        Esta es la parte más compleja de dibujado.
        """
        try:
            # --- 1. Transformación del CUERPO (Padre) ---
            glPushMatrix() # Guarda la matriz (para todo el personaje)
            glTranslatef(self.x, self.y, self.z)
            glRotatef(self.angle_y, 0.0, 1.0, 0.0)
            glScalef(1.0, 1.0, 1.0) # ESCALA GENERAL DEL PERSONAJE

            self.body.render()
            
            base_angle = math.sin(self.walk_time * self.walk_speed)
            leg_angle = self.leg_amplitude * base_angle
            arm_angle = self.arm_amplitude * base_angle
            
            # Brazo Izquierdo
            glPushMatrix()
            glRotatef(-arm_angle, 1.0, 0.0, 0.0) # Rota en X
            self.arm_l.render()
            glPopMatrix()
            
            # Brazo Derecho
            glPushMatrix()
            glRotatef(arm_angle, 1.0, 0.0, 0.0) # Rota opuesto al izq
            self.arm_r.render()
            glPopMatrix()
            
            # Pierna Izquierda
            glPushMatrix()
            glRotatef(leg_angle, 1.0, 0.0, 0.0) # Rota opuesto al brazo izq
            self.leg_l.render()
            glPopMatrix()
            
            # Pierna Derecha
            glPushMatrix()
            glRotatef(-leg_angle, 1.0, 0.0, 0.0) # Rota opuesto a pierna izq
            self.leg_r.render()
            glPopMatrix()
            
        finally:
            glPopMatrix() # Restaura la matriz (de todo el personaje)

# CLASES DE PROPS (OBJETOS) 
class PropEstatico:
    def __init__(self, model_path, pos=[0,0,0], scale=1.0, rot=[0,0,0]):

        try:
            self.model = objloader.OBJ(model_path) 
            self.model.generate()
            self.position = pos # [x, y, z]
            # Permite escalar con un solo número (ej: 1.5) o [x, y, z]
            self.scale = [scale, scale, scale] if isinstance(scale, (int, float)) else scale
            self.rotation = rot # [rotX, rotY, rotZ]
        except Exception as e:
            print(f"Error cargando '{model_path}': {e}")
            pygame.quit()
            exit()

    def draw(self):
        """Dibuja el objeto estático."""
        try:
            glPushMatrix()
            # Aplica las transformaciones guardadas
            glTranslatef(self.position[0], self.position[1], self.position[2])
            glRotatef(self.rotation[0], 1, 0, 0) # Rot X
            glRotatef(self.rotation[1], 0, 1, 0) # Rot Y
            glRotatef(self.rotation[2], 0, 0, 1) # Rot Z
            glScalef(self.scale[0], self.scale[1], self.scale[2])
            
            self.model.render()
        finally:
            glPopMatrix()

class Key:
    """
    Clase para las llaves. Son el puzzle principal.
    Maneja su propio estado (escondida, visible, recogida).
    """
    def __init__(self, model_path, pos=[0,0,0], scale=1.0, rot=[0,0,0]):
        """Constructor. Carga el modelo y define su estado inicial."""
        try:
            self.model = objloader.OBJ(model_path)
            self.model.generate()
            self.position = pos
            self.scale = scale
            self.rotation = rot
            self.angle_y = 0.0 # Para la animación de giro
            
            #  ESTADO DE LA LLAVE 
            self.is_hidden = True     # Empieza  (invisible)
            self.is_visible = False   # ¿Ha aparecido en el mundo?
            self.is_collected = False # ¿Ya la tiene el jugador?
            
        except Exception as e:
            print(f"Error cargando '{model_path}': {e}")
            pygame.quit()
            exit()
            
    def make_visible(self):
        """El jugador la encontró (usando ESPACIO). La llave aparece."""
        if self.is_hidden and not self.is_collected:
            print("¡Llave encontrada!")
            self.is_hidden = False
            self.is_visible = True
            
    def collect(self):
        """El jugador la recogió (usando ESPACIO). La llave desaparece."""
        if self.is_visible and not self.is_collected:
            print("¡Llave recogida!")
            self.is_visible = False
            self.is_collected = True
            return True # Devuelve True para que el juego sume al contador
        return False

    def update(self, dt):
        """Actualiza la lógica de la llave (la animación de giro)."""
        if self.is_visible: # Solo gira si es visible
            self.angle_y += 45 * dt # Gira 45 grados por segundo
            if self.angle_y > 360:
                self.angle_y -= 360

    def draw(self):
        """Dibuja la llave SÓLO si es visible."""
        if not self.is_visible: 
            # Si no es visible (o ya se recogio), no la dibujes
            return
            
        try:
            glPushMatrix()
            glTranslatef(self.position[0], self.position[1], self.position[2])
            glRotatef(self.angle_y, 0, 1, 0) # <-- Animación de giro
            # Rotaciones estáticas (si el modelo viene chueco)
            glRotatef(self.rotation[0], 1, 0, 0)
            glRotatef(self.rotation[1], 0, 1, 0)
            glRotatef(self.rotation[2], 0, 0, 1)
            glScalef(self.scale, self.scale, self.scale)
            
            self.model.render()
        finally:
            glPopMatrix()

class Puerta(PropEstatico):
    """
    Clase para la puerta de salida. 
    Hereda de PropEstatico, pero añade lógica para ABRIRSE.
    Esta versión se desliza en X.
    """
    def __init__(self, model_path, pos=[0,0,0], scale=1.0, rot=[0,0,0]):
        # Llama al constructor de la clase padre (PropEstatico)
        super().__init__(model_path, pos, scale, rot)
        
        # Guardamos la posición original (dónde está el HUECO)
        self.original_pos = list(pos) 
        
        # 'target_x' es la posición X a la que queremos llegar
        self.target_x = self.original_pos[0] # Al inicio, es su propia pos
        
        self.move_speed = 3.0 # Velocidad de deslizamiento


    def abrir(self, offset_x=-5.0): 
        """
        Activa la puerta.
        """
        self.target_x = self.original_pos[0] + offset_x

    def update(self, dt):
        # Compara la posición actual (self.position[0]) con el objetivo
        if abs(self.position[0] - self.target_x) > 0.05: # Umbral de error
            
            # Decide si moverse a la izquierda o derecha
            if self.position[0] > self.target_x:
                self.position[0] -= self.move_speed * dt
                # Evita pasarse
                if self.position[0] < self.target_x:
                    self.position[0] = self.target_x
                        
            elif self.position[0] < self.target_x:
                self.position[0] += self.move_speed * dt
                # Evita pasarse
                if self.position[0] > self.target_x:
                    self.position[0] = self.target_x

    def draw(self):
        try:
            glPushMatrix()
            # La clave: usa self.position[0], que es actualizado por update()
            glTranslatef(self.position[0], self.position[1], self.position[2])
            
            # Aplica rotaciones iniciales (si el modelo está de lado)
            glRotatef(self.rotation[0], 1, 0, 0) 
            glRotatef(self.rotation[1], 0, 1, 0)
            glRotatef(self.rotation[2], 0, 0, 1)
            
            # Escalado
            glScalef(self.scale[0], self.scale[1], self.scale[2])
            self.model.render()
        finally:
            glPopMatrix()

# --- CONFIGURACION GLOBAL ---
# Variables que definen cómo se ve el juego
screen_width = 1050
screen_height = 800
FOVY = 75.0  # Field of View (Ángulo de visión de la cámara, en grados)
ZNEAR = 0.1 # Qué tan cerca se empieza a dibujar
ZFAR = 500.0# Qué tan lejos se deja de dibujar
DimBoard = 15 # Tamaño (dimension) del cuarto (se usa para colisiones)

#  VARIABLES GLOBALES
personaje = None
ghost = None
escenario = None
decoracion = None
props_escondite = [] # Lista para guardar barril, cajas, cofre
llaves_list = []     # Lista para guardar las 3 llaves
puerta_salida = None

# --- LISTA DE COLISIONES ---
# [x_min, x_max, z_min, z_max]
collision_boxes = []      # Cajas para el JUGADOR (paredes + muebles)
ghost_collision_boxes = []# Cajas para el FANTASMA (solo paredes)

move_speed = 7.0     # Velocidad del jugador
rotate_speed = 100.0 # Velocidad de giro del jugador

# ESTADO DEL JUEGO 
GAME_TIME_LIMIT = 100.0 # 100 segundos
time_remaining = GAME_TIME_LIMIT

game_state = {
    'llaves_recogidas': 0,
    'total_llaves': 3,
    'puerta_abierta': False,
    'game_over': False,
    'win': False    
}
ui_font = None # Fuente para el texto 2D
interaction_message = "" # Mensaje "Presiona ESPACIO"

# Inicializa Pygame (necesario para la fuente)
pygame.init()
pygame.font.init()

# --- FUNCIONES DE OPENGL Y JUEGO ---
def Axis():
    """Función de Debug: Dibuja los ejes X (Rojo), Y (Verde), Z (Azul)"""
    glDisable(GL_LIGHTING) # Apaga luces para colores puros
    glLineWidth(1.0)
    glColor3f(1.0,0.0,0.0); glBegin(GL_LINES); glVertex3f(-50,0,0); glVertex3f(50,0,0); glEnd()
    glColor3f(0.0,1.0,0.0); glBegin(GL_LINES); glVertex3f(0,-50,0); glVertex3f(0,50,0); glEnd()
    glColor3f(0.0,0.0,1.0); glBegin(GL_LINES); glVertex3f(0,0,-50); glVertex3f(0,0,50); glEnd()
    glEnable(GL_LIGHTING) # Vuelve a encender

def Init():
    global personaje, ghost, escenario, decoracion, props_escondite, llaves_list, puerta_salida, ui_font, collision_boxes, ghost_collision_boxes
    
    screen = pygame.display.set_mode(
        (screen_width, screen_height), DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Escape Room - Plan Simplificado")

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    # Define la perspectiva: (FOV, Aspect Ratio, Near, Far)
    gluPerspective(FOVY, screen_width/screen_height, ZNEAR, ZFAR)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    
    glClearColor(0.0, 0.0, 0.0, 1.0) # Color de fondo (negro)
    glEnable(GL_DEPTH_TEST) # Habilita el Z-Buffer (que lo de atrás se vea atrás)
    glPolygonMode(GL_FRONT_AND_BACK, GL_FILL) # Dibuja caras rellenas
    
    glLightfv(GL_LIGHT0, GL_POSITION,  (0, 200, 0, 0.0))
    glLightfv(GL_LIGHT0, GL_AMBIENT, (0.5, 0.5, 0.5, 1.0))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.5, 0.5, 0.5, 1.0)) 
    glEnable(GL_LIGHTING) 
    glEnable(GL_LIGHT0)   
    glEnable(GL_COLOR_MATERIAL) 
    glShadeModel(GL_SMOOTH) 

    ui_font = pygame.font.Font(None, 36) 

    escenario = PropEstatico('visuales/habitacion.obj', pos=[0, 0, 0], scale=1.0)
    decoracion = PropEstatico('visuales/decoracion.obj', pos=[0, 0, 0], scale=1.0)
    
    print("Cargando personaje...")
    model_paths = {
        'body': 'visuales/body_head.obj',
        'left_arm': 'visuales/arm_left.obj',
        'right_arm': 'visuales/arm_right.obj',
        'left_leg': 'visuales/leg_left.obj',
        'right_leg': 'visuales/leg_right.obj'
    }
    personaje = Personaje(model_paths)
    
    print("Cargando fantasma...")
    ghost = Ghost(plane_size=DimBoard * 2) # El fantasma puede salirse un poco
        
    pos_barril = [0, 0, 0] 
    pos_cajas = [0, 0, 0]
    pos_cofre = [0, 0, 0]
    pos_puerta = [0, 0, 0]
    pos_mesa = [0, 0, 0]

    # 1. Escondite BARRIL (y su llave asociada)
    props_escondite.append(PropEstatico('visuales/barril.obj', pos=pos_barril, scale=1.0))
    llave1 = Key('visuales/key.obj', pos=[-8.65, 1.0, -3.4], scale=1.5)

    # 2. Escondite CAJAS
    props_escondite.append(PropEstatico('visuales/cajas.obj', pos=pos_cajas, scale=1.0))
    llave2 = Key('visuales/key.obj', pos=[9.0, 1.0, -3.1], scale=1.5)

    # 3. Escondite COFRE
    props_escondite.append(PropEstatico('visuales/cofre.obj', pos=pos_cofre, scale=1.0))
    llave3 = Key('visuales/key.obj', pos=[8.70, 1.0, 1.15], scale=1.5)
    
    # 4. MESA  (sin llave)
    props_escondite.append(PropEstatico('visuales/mesa.obj', pos=pos_mesa, scale=1.0)) 

    llaves_list = [llave1, llave2, llave3]
    game_state['total_llaves'] = len(llaves_list)

    puerta_salida = Puerta('visuales/puerta.obj', pos=pos_puerta, scale=1.0)

    #  CAJAS DE COLISION ---    
    # --- Paredes ---
    wall_norte = [-10.0, 12.15, 7.8, 9.25]
    wall_sur = [-8.80, 8.80, -4.80, -4.80]
    wall_este = [9.50, 9.50, -4.80, 13.20]
    wall_oeste = [-9.80, -9.80, -4.50, 7.0]
    
    # Las paredes se añaden a AMBAS listas (jugador y fantasma)
    collision_boxes.extend([wall_norte, wall_sur, wall_este, wall_oeste])
    ghost_collision_boxes.extend([wall_norte, wall_sur, wall_este, wall_oeste])
    
    # --- Props (muebles) ---
    prop_barril = [-9.10, -8.20, -4.0, -2.80]
    prop_cajas = [9.0, 9.0, -3.60, -2.60]
    prop_cofre = [9.0, 9.0, -4.80, -4.90] 
    prop_mesa = [-2.70, -1.20, -1.60, 2.90]
    
    # Los muebles se añaden SÓLO a la lista del jugador
    # (El fantasma los ignora y los atraviesa)
    collision_boxes.extend([prop_barril, prop_cajas, prop_cofre, prop_mesa])


def check_collision(x, z, radius, boxes):

    for box in boxes: # Revisa cada caja en la lista
        # [xmin, xmax, zmin, zmax]
        
        # 1. Encuentra el punto más cercano en la caja al centro del círculo
        closest_x = max(box[0], min(x, box[1]))
        closest_z = max(box[2], min(z, box[3]))
        
        # 2. Calcula la distancia al cuadrado (es más rápido que la raíz)
        dist_x = x - closest_x
        dist_z = z - closest_z
        distance_squared = (dist_x**2) + (dist_z**2)
        
        # 3. Compara con el radio al cuadrado
        if distance_squared < (radius**2):
            return True # ¡Colisión!
    
    return False # No hubo colisión con ninguna caja

def lookat():
    """Define la posición de la CÁMARA (nuestros ojos)"""
    glLoadIdentity()
    #CAMARA FIJA
    gluLookAt(0, 7, 16, 0, 5, 0, 0, 1, 0) # Cámara fija elevada
    
def draw_text(text, x, y, color=(255, 255, 255)):
    try:
        text_surface = ui_font.render(text, True, color)
        text_data = pygame.image.tostring(text_surface, "RGBA", True)
    except Exception as e:
        return

    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, screen_width, 0, screen_height) 
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix() 
    glLoadIdentity()
    
    glDisable(GL_LIGHTING)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glEnable(GL_TEXTURE_2D)
    
    glColor3f(1.0, 1.0, 1.0) 
    
    texid = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, texid)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, text_surface.get_width(), text_surface.get_height(),
                0, GL_RGBA, GL_UNSIGNED_BYTE, text_data)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    
    glBegin(GL_QUADS)
    glTexCoord2f(0, 0); glVertex2f(x, y) 
    glTexCoord2f(1, 0); glVertex2f(x + text_surface.get_width(), y)
    glTexCoord2f(1, 1); glVertex2f(x + text_surface.get_width(), y + text_surface.get_height())
    glTexCoord2f(0, 1); glVertex2f(x, y + text_surface.get_height())
    glEnd()
    
    glDisable(GL_TEXTURE_2D)
    glDisable(GL_BLEND)
    glEnable(GL_LIGHTING)
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glPopMatrix() 
    glDeleteTextures(1, [texid]) 

def display(dt, is_moving):
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    
    lookat()
    
    # 3. Dibuja los ejes 
    # Axis() 

    #  ORDEN DE DIBUJADO 
    escenario.draw()
    decoracion.draw()

    for prop in props_escondite:
        prop.draw()
        
    puerta_salida.draw()
        
    # Items (Llaves)
    for llave in llaves_list:
        llave.draw()
        
    # Entidades (Jugador y Fantasma)
    personaje.draw()
    ghost.draw()
    
    #DIBUJAR UI (Texto 2D) 
    global interaction_message 
    draw_text(f"Tiempo restante: {int(time_remaining)}" " s", 10, screen_height - 40)
    draw_text(f"Llaves: {game_state['llaves_recogidas']} / {game_state['total_llaves']}", 10, screen_height - 70)
    
    if interaction_message:
        text_w = ui_font.size(interaction_message)[0] # Ancho del texto
        draw_text(interaction_message, (screen_width - text_w) / 2, 50)
        
    if game_state['game_over']:
        msg = "¡SE ACABÓ EL TIEMPO!"
        text_w = ui_font.size(msg)[0]
        draw_text(msg, (screen_width - text_w) / 2, screen_height / 2, color=(255,0,0))
    
    if game_state['win']:
        msg = "¡ESCAPASTE!"
        text_w = ui_font.size(msg)[0]
        draw_text(msg, (screen_width - text_w) / 2, screen_height / 2, color=(0,255,0))

#  BUCLE PRINCIPAL DEL JUEGO ---
done = False
Init() # Llama a la función de inicialización UNA SOLA VEZ
clock = pygame.time.Clock() # Inicia el reloj del juego

print("\nJUEGO INICIADO -> Controles: Flechas (mover/girar), Espacio (interactuar)")

while not done:
    # 1. CALCULAR DELTA TIME (dt)
    # dt es el tiempo (en segundos) que pasó desde el último frame.
    # Esencial para que el juego corra a la misma velocidad en todas las PCs.
    dt = clock.tick(60) / 1000.0 
    keys = pygame.key.get_pressed() # Lee todas las teclas presionadas
    is_moving = False # Flag para la animación
    
    # 2. MANEJO DE ESTADO DEL JUEGO
    if game_state['game_over'] or game_state['win']:
        dt = 0.0 # Congela el juego (delta time = 0)
    else:
        # Actualizar timer
        time_remaining -= dt
        if time_remaining <= 0:
            time_remaining = 0
            game_state['game_over'] = True

    
    move_x, move_z = 0.0, 0.0
    
    if keys[pygame.K_UP]: # Moverse ADELANTE
        # Trig: Seno para X, Coseno para Z (depende de cómo esté tu modelo)
        angle_rad = math.radians(personaje.angle_y)
        move_x += math.sin(angle_rad) * move_speed * dt
        move_z += math.cos(angle_rad) * move_speed * dt
        is_moving = True
    if keys[pygame.K_DOWN]: # Moverse ATRÁS
        angle_rad = math.radians(personaje.angle_y)
        move_x -= math.sin(angle_rad) * move_speed * dt
        move_z -= math.cos(angle_rad) * move_speed * dt
        is_moving = True
    if keys[pygame.K_LEFT]: # Girar
        personaje.angle_y += rotate_speed * dt
        is_moving = True 
    if keys[pygame.K_RIGHT]: # Girar
        personaje.angle_y -= rotate_speed * dt
        is_moving = True 
    
    # --- Chequeo de Colisión (Slide) ---   
    # Mover en X
    new_x = personaje.x + move_x
    if not check_collision(new_x, personaje.z, personaje.radius, collision_boxes):
        personaje.x = new_x # Si no choca en X, acepta el movimiento
    
    # Mover en Z
    new_z = personaje.z + move_z
    if not check_collision(personaje.x, new_z, personaje.radius, collision_boxes):
        personaje.z = new_z # Si no choca en Z, acepta el movimiento

    # 2. LÓGICA DEL JUEGO (Interacciones) 
    interaction_message = "" # Reinicia el mensaje cada frame
    
    # A) Checar si esta cerca de una llave
    for llave in llaves_list:
        if llave.is_collected: continue # Ignora llaves recogidas
            
        dist_x = personaje.x - llave.position[0]
        dist_z = personaje.z - llave.position[2]
        distancia = math.sqrt(dist_x**2 + dist_z**2)
        
        if distancia < 2.5: # Rango de interaccion
            if llave.is_hidden:
                interaction_message = "Presiona ESPACIO para buscar..."
            else: # (is_visible)
                interaction_message = "Presiona ESPACIO para recoger la llave"
            break # Solo puede interactuar con una cosa a la vez

    # B) Checar si puede ganar (mostrar mensaje de puerta)
    # Si la puerta está abierta Y no estamos mostrando un mensaje de llave...
    if game_state['puerta_abierta'] and not interaction_message:
        # Comparamos la distancia del jugador con el HUECO original de la puerta
        dist_x = personaje.x - puerta_salida.original_pos[0]
        dist_z = personaje.z - puerta_salida.original_pos[2]
        
        if math.sqrt(dist_x**2 + dist_z**2) < 5.0: # Rango de escape
            interaction_message = "Presiona ESPACIO para escapar"
            
    #  Manejo de Eventos 
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            done = True
        if event.type == pygame.KEYDOWN: 
            if event.key == pygame.K_ESCAPE:
                done = True
            
            # Lógica de INTERACCIÓN (Presionar ESPACIO)
            if event.key == pygame.K_SPACE and not (game_state['game_over'] or game_state['win']):
                
                # ¿Está intentando interactuar con una llave?
                interacted_with_key = False
                for llave in llaves_list:
                    if llave.is_collected: continue
                    
                    dist_x = personaje.x - llave.position[0]
                    dist_z = personaje.z - llave.position[2]
                    
                    if math.sqrt(dist_x**2 + dist_z**2) < 2.5: # Distancia de interaccion
                        if llave.is_hidden:
                            llave.make_visible() # La revela
                        elif llave.is_visible:
                            if llave.collect(): # La recoge
                                game_state['llaves_recogidas'] += 1
                        interacted_with_key = True
                        break # Interactúa solo con la primera llave que encuentra
                
                # ¿Está intentando escapar? (Solo si no acaba de usar la llave)
                if not interacted_with_key and game_state['puerta_abierta']:
                    dist_x = personaje.x - puerta_salida.original_pos[0]
                    dist_z = personaje.z - puerta_salida.original_pos[2]
                    if math.sqrt(dist_x**2 + dist_z**2) < 5.0: # Rango de escape
                        print("!GANASTE!")
                        game_state['win'] = True
    
    personaje.update(dt, is_moving) # Actualiza la animación del personaje
    puerta_salida.update(dt) # Actualiza la puerta
    
    # El fantasma usa su propia lista de colisiones
    ghost.update(dt, ghost_collision_boxes) 
    
    for llave in llaves_list:
        llave.update(dt) # Rota las llaves visibles

    # D) Lógica de la puerta de escape (Revisa si se cumplen las condiciones)
    if game_state['llaves_recogidas'] == game_state['total_llaves'] and not game_state['puerta_abierta']:
        print("Todas las llaves recogidas..- escapa")
        puerta_salida.abrir(offset_x = -4.0) # Abre la puerta
        game_state['puerta_abierta'] = True
        
    # (Opcional) Imprime la posición del jugador para debug de colisiones
    # print(f"Posición: X={personaje.x:.2f}, Z={personaje.z:.2f}")
    
    display(dt, is_moving) 
    pygame.display.flip() 

pygame.quit()
print("Juego terminado.")