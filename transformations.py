# transformations.py
# (Copiado de proyecto 'Carro 3D Movimiento')

import numpy as np
from OpenGL.GL import *

class OpMat:
    def __init__(self):
        self.matrix = np.identity(4, dtype=np.float32)

    def getMatrix(self):
        return self.matrix.flatten('F')

    def translate(self, tx, ty, tz):
        trans_mat = np.array([
            [1, 0, 0, tx],
            [0, 1, 0, ty],
            [0, 0, 1, tz],
            [0, 0, 0, 1]
        ], dtype=np.float32)
        self.matrix = np.dot(trans_mat, self.matrix)

    def rotateX(self, angle_deg):
        rad = np.radians(angle_deg)
        cos_a = np.cos(rad)
        sin_a = np.sin(rad)
        rot_mat = np.array([
            [1, 0, 0, 0],
            [0, cos_a, -sin_a, 0],
            [0, sin_a, cos_a, 0],
            [0, 0, 0, 1]
        ], dtype=np.float32)
        self.matrix = np.dot(rot_mat, self.matrix)

    def rotateY(self, angle_deg):
        rad = np.radians(angle_deg)
        cos_a = np.cos(rad)
        sin_a = np.sin(rad)
        rot_mat = np.array([
            [cos_a, 0, sin_a, 0],
            [0, 1, 0, 0],
            [-sin_a, 0, cos_a, 0],
            [0, 0, 0, 1]
        ], dtype=np.float32)
        self.matrix = np.dot(rot_mat, self.matrix)

    def rotateZ(self, angle_deg):
        rad = np.radians(angle_deg)
        cos_a = np.cos(rad)
        sin_a = np.sin(rad)
        rot_mat = np.array([
            [cos_a, -sin_a, 0, 0],
            [sin_a, cos_a, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ], dtype=np.float32)
        self.matrix = np.dot(rot_mat, self.matrix)

    def scale(self, sx, sy, sz):
        scale_mat = np.array([
            [sx, 0, 0, 0],
            [0, sy, 0, 0],
            [0, 0, sz, 0],
            [0, 0, 0, 1]
        ], dtype=np.float32)
        self.matrix = np.dot(scale_mat, self.matrix)