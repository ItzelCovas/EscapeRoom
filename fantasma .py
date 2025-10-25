import pygame
from pygame.locals import *

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *

import math
import random
import objloader 

# CLASE GHOST 
class Ghost:
    def __init__(self, model_path, plane_size=250):
        
        self.model = objloader.OBJ(model_path)
        self.model.generate()
        
        self.min_val = -plane_size / 2
        self.max_val = plane_size / 2
        
        self.x = random.uniform(self.min_val, self.max_val)
        self.y = 5.0
        self.z = random.uniform(self.min_val, self.max_val)
        
        self.speed = 25.0
        self.target_x = 0
        self.target_z = 0
        self.get_new_random_target() 

        self.float_time = 0.0
        self.float_amplitude = 6.0 # controla qué tanto sube y baja
        self.float_speed = 3.0
        self.base_y = self.y

    def get_new_random_target(self):
        self.target_x = random.uniform(self.min_val, self.max_val)
        self.target_z = random.uniform(self.min_val, self.max_val)

    def update(self, dt):
        """Actualiza la posicion (requiere dt)"""
        dir_x = self.target_x - self.x
        dir_z = self.target_z - self.z
        distance = math.sqrt(dir_x**2 + dir_z**2)
        
        if distance < 5.0:
            self.get_new_random_target()
        else:
            norm_x = dir_x / distance
            norm_z = dir_z / distance
            self.x += norm_x * self.speed * dt
            self.z += norm_z * self.speed * dt

        self.float_time += dt
        self.y = self.base_y + math.sin(self.float_time * self.float_speed) * self.float_amplitude

    def draw(self):
        """Dibuja el fantasma"""
        try:
            glPushMatrix()
            glTranslatef(self.x, self.y, self.z)
            glScalef(10.0, 10.0, 10.0)
            self.model.render()
        finally:
            glPopMatrix()
            
# FIN DE LA CLASE GHOST 


# CONFIGURACION GLOBAL 
screen_width = 1050
screen_height = 800

FOVY = 75.0         # Lente gran angular
ZNEAR = 0.1
ZFAR = 500.0       # Distancia de dibujado larga
DimBoard = 200      # El plano es 500x500 (de -250 a 250)

# Variables para la camara rotativa
theta = 40.0
radius = 300.0      # Alejamos la camara
eye_y = 50.0       # Subimos la camara
CENTER_X = 0
CENTER_Y = 0
CENTER_Z = 0
UP_X = 0
UP_Y = 1
UP_Z = 0

# Variables para los ejes
X_MIN = -400
X_MAX = 400
Y_MIN = -400
Y_MAX = 400
Z_MIN = -400
Z_MAX = 400

# Variable global para el fantasma
ghost = None

pygame.init()
glutInit() # Necesario para el objloader

# FUNCIONES DE OPENGL 

def Axis():
    """ Dibuja los ejes X, Y, Z """
    glDisable(GL_LIGHTING)
    glLineWidth(1.0)
    #X axis in red
    glColor3f(1.0,0.0,0.0)
    glBegin(GL_LINES)
    glVertex3f(X_MIN,0.0,0.0)
    glVertex3f(X_MAX,0.0,0.0)
    glEnd()
    #Y axis in green
    glColor3f(0.0,1.0,0.0)
    glBegin(GL_LINES)
    glVertex3f(0.0,Y_MIN,0.0)
    glVertex3f(0.0,Y_MAX,0.0)
    glEnd()
    #Z axis in blue
    glColor3f(0.0,0.0,1.0)
    glBegin(GL_LINES)
    glVertex3f(0.0,0.0,Z_MIN)
    glVertex3f(0.0,0.0,Z_MAX)
    glEnd()
    glLineWidth(1.0)
    glEnable(GL_LIGHTING)


def Init():
    """ Inicializa pygame y OpenGL """
    global ghost
    
    screen = pygame.display.set_mode(
        (screen_width, screen_height), DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Escape Room - Test Fantasma (con PyGame)")

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(FOVY, screen_width/screen_height, ZNEAR, ZFAR)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    # (Quitamos el gluLookAt de aqui, se hara en cada frame)
    
    glClearColor(0.1, 0.1, 0.1, 1.0); # Fondo oscuro
    glEnable(GL_DEPTH_TEST)
    glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
    
    # Luces 
    glLightfv(GL_LIGHT0, GL_POSITION,  (0, 200, 0, 0.0))
    glLightfv(GL_LIGHT0, GL_AMBIENT, (0.5, 0.5, 0.5, 1.0))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.5, 0.5, 0.5, 1.0))
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_COLOR_MATERIAL)
    glShadeModel(GL_SMOOTH)
    
    #Creamos el fantasma
    ghost = Ghost('ghost.obj', plane_size=250)


def lookat():
    """ Actualiza la camara en cada frame """
    global theta, radius, eye_y, CENTER_X, CENTER_Y, CENTER_Z, UP_X, UP_Y, UP_Z
    
    # Calculamos la posicion de la camara
    eye_x = radius * math.sin(math.radians(theta))
    eye_z = radius * math.cos(math.radians(theta))
    
    glLoadIdentity()
    gluLookAt(eye_x, eye_y, eye_z, CENTER_X, CENTER_Y, CENTER_Z, UP_X, UP_Y, UP_Z)
    
def draw_floor():
    """ Dibuja el piso gris """
    glColor3f(0.3, 0.3, 0.3)
    glBegin(GL_QUADS)
    glNormal3f(0.0, 1.0, 0.0) # Normal para la luz
    glVertex3d(-DimBoard, 0, -DimBoard)
    glVertex3d(-DimBoard, 0, DimBoard)
    glVertex3d(DimBoard, 0, DimBoard)
    glVertex3d(DimBoard, 0, -DimBoard)
    glEnd()
    
def display(dt):
    """ Funcion principal de dibujado """
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    
    # 1. Actualizamos la camara
    lookat()
    
    # 2. Dibujamos los elementos
    Axis()
    draw_floor()
        
    # 3. Actualizamos y dibujamos el fantasma
    ghost.update(dt) # Le pasamos el deltatime
    ghost.draw()
    

# BUCLE PRINCIPAL 
done = False
Init()
clock = pygame.time.Clock() # Reloj para calcular deltatime

while not done:
    
    # Calculamos deltatime (tiempo desde el ultimo frame)
    # Lo dividimos por 1000 para pasarlo a segundos
    dt = clock.tick(60) / 1000.0 
    
    keys = pygame.key.get_pressed()
    
    # Controles de camara
    if keys[pygame.K_RIGHT]:
        theta += 1.0
        if theta > 360.0:
            theta = 0.0
    if keys[pygame.K_LEFT]:
        theta -= 1.0
        if theta < 0.0:
            theta = 360.0
    
    # Eventos (como Salir)
    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                done = True

    # Llamamos a la funcion de dibujado
    display(dt)

    # Actualizamos la pantalla
    pygame.display.flip()

pygame.quit()