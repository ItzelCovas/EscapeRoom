import pygame
from pygame.locals import *

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

import math
import random
import objloader 

# CLASE PERSONAJE
class Personaje:
    def __init__(self, model_paths):
        """Carga todos los modelos del personaje"""
        
        # Carga los modelos
        self.body = objloader.OBJ(model_paths['body'])
        self.arm_l = objloader.OBJ(model_paths['arm_l'])
        self.arm_r = objloader.OBJ(model_paths['arm_r'])
        self.leg_l = objloader.OBJ(model_paths['leg_l'])
        self.leg_r = objloader.OBJ(model_paths['leg_r'])
        
        # Genera las listas de OpenGL para cada parte
        self.body.generate()
        self.arm_l.generate()
        self.arm_r.generate()
        self.leg_l.generate()
        self.leg_r.generate()

        # Posición y rotación del personaje
        self.x = 0.0
        self.y = 5.0  # Elevamos al personaje para que esté sobre el piso
        self.z = 0.0
        self.angle_y = 0.0 # Rotación sobre el eje Y

        # Variables de animación de caminata
        self.walk_time = 0.0
        self.leg_amplitude = 25.0   # Grados de rotación de la PIERNA
        self.arm_amplitude = 5.0   # Grados de rotación del BRAZO 
        self.walk_speed = 10.0      # Qué tan rápido mueve las piernas

    def update(self, dt, is_moving):
        """Actualiza el tiempo de animación si el personaje se está moviendo"""
        if is_moving:
            self.walk_time += dt

    def draw(self):
        """Dibuja el personaje completo con animación"""
        try:
            glPushMatrix()
            
            # 1. Transformaciones globales del personaje (posición y rotación)
            glTranslatef(self.x, self.y, self.z)
            glRotatef(self.angle_y, 0.0, 1.0, 0.0)
            glScalef(5.0, 5.0, 5.0)

            # 2. Dibujar cuerpo (estático)
            self.body.render()

        
            # 3. Calcular ángulos de caminata (separados)
            base_angle = math.sin(self.walk_time * self.walk_speed)
            leg_angle = self.leg_amplitude * base_angle
            arm_angle = self.arm_amplitude * base_angle

            # 4. Dibujar Brazo Izquierdo 
            glPushMatrix()
            glRotatef(-arm_angle, 1.0, 0.0, 0.0) 
            self.arm_l.render()
            glPopMatrix()

            # 5. Dibujar Brazo Derecho 
            glPushMatrix()
            glRotatef(arm_angle, 1.0, 0.0, 0.0) 
            self.arm_r.render()
            glPopMatrix()
            
            # 6. Dibujar Pierna Izquierda 
            glPushMatrix()
            glRotatef(leg_angle, 1.0, 0.0, 0.0) 
            self.leg_l.render()
            glPopMatrix()

            # 7. Dibujar Pierna Derecha 
            glPushMatrix()
            glRotatef(-leg_angle, 1.0, 0.0, 0.0) 
            self.leg_r.render()
            glPopMatrix()
            

        finally:
            glPopMatrix() # Restaura la matriz de transformación



# CONFIGURACION GLOBAL
screen_width = 1050
screen_height = 800

FOVY = 75.0
ZNEAR = 0.1 
ZFAR = 500.0
DimBoard = 50      

X_MIN = -50
X_MAX = 50
Y_MIN = -50
Y_MAX = 50
Z_MIN = -50
Z_MAX = 50

# Variable global para el personaje
personaje = None

# Variables para el control
move_speed = 25.0
rotate_speed = 100.0 # Grados por segundo

pygame.init()
glutInit() # Necesario para el objloader


def Axis():
    """ Dibuja los ejes X, Y, Z (opcional) """
    glDisable(GL_LIGHTING)
    glLineWidth(1.0)
    glColor3f(1.0,0.0,0.0)
    glBegin(GL_LINES)
    glVertex3f(X_MIN,0.0,0.0)
    glVertex3f(X_MAX,0.0,0.0)
    glEnd()
    glColor3f(0.0,1.0,0.0)
    glBegin(GL_LINES)
    glVertex3f(0.0,Y_MIN,0.0)
    glVertex3f(0.0,Y_MAX,0.0)
    glEnd()
    glColor3f(0.0,0.0,1.0)
    glBegin(GL_LINES)
    glVertex3f(0.0,0.0,Z_MIN)
    glVertex3f(0.0,0.0,Z_MAX)
    glEnd()
    glEnable(GL_LIGHTING)

def Init():
    """ Inicializa pygame y OpenGL """
    global personaje
    
    screen = pygame.display.set_mode(
        (screen_width, screen_height), DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Test Personaje Caminando (con PyGame)")

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(FOVY, screen_width/screen_height, ZNEAR, ZFAR)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    
    glClearColor(0.0, 0.0, 0.0, 1.0); # Fondo negro
    glEnable(GL_DEPTH_TEST)
    glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
    
    # Luces (igual que en fantasma.py)
    glLightfv(GL_LIGHT0, GL_POSITION,  (0, 200, 0, 0.0))
    glLightfv(GL_LIGHT0, GL_AMBIENT, (0.5, 0.5, 0.5, 1.0))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.5, 0.5, 0.5, 1.0))
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_COLOR_MATERIAL)
    glShadeModel(GL_SMOOTH)
    
    # Rutas a los modelos
    model_paths = {
        'body': 'body_head.obj',
        'arm_l': 'arm_left.obj',
        'arm_r': 'arm_right.obj',
        'leg_l': 'leg_left.obj',
        'leg_r': 'leg_right.obj'
    }
    
    # Creamos el personaje
    personaje = Personaje(model_paths)


def lookat():
    """ Configura la cámara en una vista inclinada fija """
    glLoadIdentity()
    # Vista inclinada: (x=0, y=40, z=50) mirando al origen (0,0,0)
    gluLookAt(0, 40, 50, 0, 0, 0, 0, 1, 0)
    
def draw_floor():
    """ Dibuja el piso gris """
    glColor3f(0.3, 0.3, 0.3) # Gris
    glBegin(GL_QUADS)
    glNormal3f(0.0, 1.0, 0.0)
    glVertex3d(-DimBoard, 0, -DimBoard)
    glVertex3d(-DimBoard, 0, DimBoard)
    glVertex3d(DimBoard, 0, DimBoard)
    glVertex3d(DimBoard, 0, -DimBoard)
    glEnd()
    
def display(dt, is_moving):
    """ Funcion principal de dibujado """
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    
    # 1. Actualizamos la camara
    lookat()
    
    # 2. Dibujamos los elementos
    Axis() 
    draw_floor()
        
    # 3. Actualizamos y dibujamos el personaje
    personaje.update(dt, is_moving) # Le pasamos el deltatime y si se mueve
    personaje.draw()
    

# BUCLE PRINCIPAL 
done = False
Init()
clock = pygame.time.Clock()

while not done:
    
    dt = clock.tick(60) / 1000.0 
    
    keys = pygame.key.get_pressed()
    
    is_moving = False # Reseteamos el flag en cada frame

    # Controles de personaje (movimiento y rotación)
    if keys[pygame.K_UP]:
        # Moverse hacia adelante (en la dirección de la rotación)
        angle_rad = math.radians(personaje.angle_y)
        personaje.x += math.sin(angle_rad) * move_speed * dt
        personaje.z += math.cos(angle_rad) * move_speed * dt
        is_moving = True
        
    if keys[pygame.K_DOWN]:
        # Moverse hacia atrás
        angle_rad = math.radians(personaje.angle_y)
        personaje.x -= math.sin(angle_rad) * move_speed * dt
        personaje.z -= math.cos(angle_rad) * move_speed * dt
        is_moving = True

    if keys[pygame.K_LEFT]:
        # Rotar a la izquierda
        personaje.angle_y += rotate_speed * dt
        is_moving = True # Las piernas se mueven al rotar
        
    if keys[pygame.K_RIGHT]:
        # Rotar a la derecha
        personaje.angle_y -= rotate_speed * dt
        is_moving = True # Las piernas se mueven al rotar
        
    
    personaje.x = max(-DimBoard +6, min(personaje.x, DimBoard -5))
    personaje.z = max(-DimBoard +9, min(personaje.z, DimBoard -5))
    
    
    # Eventos 
    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                done = True

    display(dt, is_moving)

    # Actualizamos la pantalla
    pygame.display.flip()

pygame.quit()