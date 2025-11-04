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
    def __init__(self, plane_size=100):
        self.model = objloader.OBJ('ghost.obj')
        self.model.generate()
        self.min_val = -plane_size / 2
        self.max_val = plane_size / 2
        
        self.angle_y = 0.0
        
        self.x = random.uniform(self.min_val, self.max_val)
        self.y = 5.0
        self.z = random.uniform(self.min_val, self.max_val)
        
        self.speed = 8.0         
        self.target_x = 0
        self.target_z = 0
        self.get_new_random_target()

        self.float_time = 0.0
        self.float_amplitude = 2.0  
        self.float_speed = 3.0
        self.base_y = self.y

        self.bound_margin = 8.0

    def get_new_random_target(self):
        self.target_x = random.uniform(self.min_val, self.max_val)
        self.target_z = random.uniform(self.min_val, self.max_val)

    def update(self, dt):
        dir_x = self.target_x - self.x
        dir_z = self.target_z - self.z
        distance = math.sqrt(dir_x**2 + dir_z**2)
        
        if distance < 5.0:
            self.get_new_random_target()
        else:
            norm_x = dir_x / max(distance, 1e-6)
            norm_z = dir_z / max(distance, 1e-6)
            self.x += norm_x * self.speed * dt
            self.z += norm_z * self.speed * dt
            target_angle = math.degrees(math.atan2(norm_x, norm_z))
            self.angle_y += (target_angle - self.angle_y) * 0.4  # 0.1 = suavidad (ajusta entre 0.05 y 0.2)


        # movimiento vertical (flotación)
        self.float_time += dt
        self.y = self.base_y + math.sin(self.float_time * self.float_speed) * self.float_amplitude

        # confinamiento dentro del plano
        prev_x, prev_z = self.x, self.z
        self.x = max(self.min_val + self.bound_margin, min(self.x, self.max_val - self.bound_margin))
        self.z = max(self.min_val + self.bound_margin, min(self.z, self.max_val - self.bound_margin))
        if (self.x != prev_x) or (self.z != prev_z):
            self.get_new_random_target()

    def draw(self):
        try:
            glPushMatrix()
            glTranslatef(self.x, self.y, self.z)
            glRotatef(self.angle_y, 0.0, 1.0, 0.0)
            glScalef(1.5, 1.5, 1.5)  
            self.model.render()
        finally:
            glPopMatrix()


# CLASE PERSONAJE
class Personaje:
    def __init__(self, model_paths):
        """Carga todos los modelos del personaje"""
        self.body = objloader.OBJ(model_paths['body'])
        self.arm_l = objloader.OBJ(model_paths['arm_l'])
        self.arm_r = objloader.OBJ(model_paths['arm_r'])
        self.leg_l = objloader.OBJ(model_paths['leg_l'])
        self.leg_r = objloader.OBJ(model_paths['leg_r'])
        
        self.body.generate()
        self.arm_l.generate()
        self.arm_r.generate()
        self.leg_l.generate()
        self.leg_r.generate()

        self.x = 0.0
        self.y = 5.0
        self.z = 0.0
        self.angle_y = 0.0

        self.walk_time = 0.0
        self.leg_amplitude = 25.0
        self.arm_amplitude = 5.0
        self.walk_speed = 10.0

    def update(self, dt, is_moving):
        if is_moving:
            self.walk_time += dt

    def draw(self):
        try:
            glPushMatrix()
            glTranslatef(self.x, self.y, self.z)
            glRotatef(self.angle_y, 0.0, 1.0, 0.0)
            glScalef(5.0, 5.0, 5.0)

            self.body.render()

            base_angle = math.sin(self.walk_time * self.walk_speed)
            leg_angle = self.leg_amplitude * base_angle
            arm_angle = self.arm_amplitude * base_angle

            glPushMatrix()
            glRotatef(-arm_angle, 1.0, 0.0, 0.0)
            self.arm_l.render()
            glPopMatrix()

            glPushMatrix()
            glRotatef(arm_angle, 1.0, 0.0, 0.0)
            self.arm_r.render()
            glPopMatrix()
            
            glPushMatrix()
            glRotatef(leg_angle, 1.0, 0.0, 0.0)
            self.leg_l.render()
            glPopMatrix()

            glPushMatrix()
            glRotatef(-leg_angle, 1.0, 0.0, 0.0)
            self.leg_r.render()
            glPopMatrix()
        finally:
            glPopMatrix()


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

personaje = None
ghost = None

move_speed = 25.0
rotate_speed = 100.0

pygame.init()


def Axis():
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
    global personaje, ghost
    screen = pygame.display.set_mode(
        (screen_width, screen_height), DOUBLEBUF | OPENGL)
    pygame.display.set_caption("Personaje + Fantasma")

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(FOVY, screen_width/screen_height, ZNEAR, ZFAR)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    
    glClearColor(0.0, 0.0, 0.0, 1.0)
    glEnable(GL_DEPTH_TEST)
    glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
    
    glLightfv(GL_LIGHT0, GL_POSITION,  (0, 200, 0, 0.0))
    glLightfv(GL_LIGHT0, GL_AMBIENT, (0.5, 0.5, 0.5, 1.0))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.5, 0.5, 0.5, 1.0))
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_COLOR_MATERIAL)
    glShadeModel(GL_SMOOTH)
    
    model_paths = {
        'body': 'body_head.obj',
        'arm_l': 'arm_left.obj',
        'arm_r': 'arm_right.obj',
        'leg_l': 'leg_left.obj',
        'leg_r': 'leg_right.obj'
    }
    personaje = Personaje(model_paths)
    ghost = Ghost(plane_size=DimBoard * 2)

def lookat():
    glLoadIdentity()
    gluLookAt(0, 30, 50, 0, 0, 0, 0, 1, 0)
    
def draw_floor():
    glColor3f(0.3, 0.3, 0.3)
    glBegin(GL_QUADS)
    glNormal3f(0.0, 1.0, 0.0)
    glVertex3d(-DimBoard, 0, -DimBoard)
    glVertex3d(-DimBoard, 0, DimBoard)
    glVertex3d(DimBoard, 0, DimBoard)
    glVertex3d(DimBoard, 0, -DimBoard)
    glEnd()
    
def display(dt, is_moving):
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    lookat()
    Axis()
    draw_floor()
    personaje.update(dt, is_moving)
    ghost.update(dt)
    ghost.draw()
    personaje.draw()

# BUCLE PRINCIPAL
done = False
Init()
clock = pygame.time.Clock()

while not done:
    dt = clock.tick(60) / 1000.0 
    keys = pygame.key.get_pressed()
    is_moving = False

    if keys[pygame.K_UP]:
        angle_rad = math.radians(personaje.angle_y)
        personaje.x += math.sin(angle_rad) * move_speed * dt
        personaje.z += math.cos(angle_rad) * move_speed * dt
        is_moving = True
        
    if keys[pygame.K_DOWN]:
        angle_rad = math.radians(personaje.angle_y)
        personaje.x -= math.sin(angle_rad) * move_speed * dt
        personaje.z -= math.cos(angle_rad) * move_speed * dt
        is_moving = True

    if keys[pygame.K_LEFT]:
        personaje.angle_y += rotate_speed * dt
        is_moving = True 
        
    if keys[pygame.K_RIGHT]:
        personaje.angle_y -= rotate_speed * dt
        is_moving = True 
        
    personaje.x = max(-DimBoard +6, min(personaje.x, DimBoard -5))
    personaje.z = max(-DimBoard +9, min(personaje.z, DimBoard -5))

    for event in pygame.event.get():
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                done = True

    display(dt, is_moving)
    pygame.display.flip()

pygame.quit()
