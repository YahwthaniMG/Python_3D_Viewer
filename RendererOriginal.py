import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np

"""
    Esta clase se encarga de renderizar el modelo original leido del archivo obj.
    
    Se utiliza OpenGL, para rendeizar en tiempo real el modelo, tambien posee una luz ambiental, 
    la camara se posiciona a una distancia siempre alejada del objeto, a pesar de su tamaño. 
"""

class Renderer:
    def __init__(self):
        self.initialize_normal_scene()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    self.rotation_y -= 5
                elif event.key == pygame.K_RIGHT:
                    self.rotation_y += 5
                elif event.key == pygame.K_UP:
                    self.rotation_x -= 5
                elif event.key == pygame.K_DOWN:
                    self.rotation_x += 5
                elif event.key == pygame.K_KP_PLUS:
                    self.scaling += 0.1
                elif event.key == pygame.K_KP_MINUS:
                    self.scaling -= 0.1
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 4:  # Rueda del ratón hacia arriba
                    self.scaling += 0.1
                elif event.button == 5:  # Rueda del ratón hacia abajo
                    self.scaling -= 0.1
            elif event.type == pygame.MOUSEMOTION:
                if event.buttons[0]:  # Botón izquierdo del ratón presionado 
                    self.rotation_y += event.rel[0]  # Rotar en el eje Y
                    self.rotation_x += event.rel[1]  # Rotar en el eje X
        self.handle_vertical_movement()

    def handle_vertical_movement(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE]:
            glTranslatef(0, -0.1, 0)  # Mover la cámara hacia arriba
        elif keys[pygame.K_LCTRL]:
            glTranslatef(0, 0.1, 0)  # Mover la cámara hacia abajo
        
    def calculate_model_size(self, vertices):
        # Calcula el tamaño máximo del modelo en la dimensión Z
        z_coordinates = [vertex[2] for vertex in vertices]
        return np.max(z_coordinates) 

    def initialize_normal_scene(self):
        pygame.init()
        display = (600, 500)
        self.normal_window = pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
        pygame.display.set_caption("Visualizador 3D - Objeto Normal")

        gluPerspective(45, (display[0] / display[1]), 0.1, 50.0)
        glTranslatef(0, 0, -5)

        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_POSITION, (0, -100, -200, 0.0))
        glLightfv(GL_LIGHT0, GL_AMBIENT, (1.0, 1.0, 1.0, 0.1))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.5, 0.5, 0.5, 0.1))
        glEnable(GL_DEPTH_TEST)

        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        glMaterialfv(GL_FRONT, GL_SPECULAR, (1, 1, 1, 1))
        glMaterialfv(GL_FRONT, GL_SHININESS, 50)

        self.rotation_x = 0
        self.rotation_y = 0
        self.scaling = 1.0
        
    def render_normal_scene(self, vertices, faces, edges, tam):
        while True:
            self.handle_events()

            glClearColor(0.8, 0.8, 0.8, 1.0)
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

            glPushMatrix()

            # Ajustes de cámara y rotaciones
            glTranslatef(0, 0, -tam*2)
            glRotatef(self.rotation_x, 1, 0, 0)
            glRotatef(self.rotation_y, 0, 1, 0)
            glScalef(self.scaling, self.scaling, self.scaling)

            # Configuración de luz ambiental
            glEnable(GL_LIGHTING)
            glDisable(GL_LIGHT0)  # Desactivar otras luces para mostrar solo la ambiental
            ambient_color = [1.0, 1.0, 1.0, 1.0]  # Luz blanca
            glLightModelfv(GL_LIGHT_MODEL_AMBIENT, ambient_color)  # Luz ambiental global

            # Dibuja vértices
            glPointSize(5.0)
            glBegin(GL_POINTS)
            glColor3f(1.0, 0.0, 0.0)
            for vertex in vertices:
                glVertex3f(*vertex)
            glEnd()

            # Dibuja aristas
            glBegin(GL_LINES)
            glColor3f(0.0, 1.0, 0.0)
            for edge in edges:
                glVertex3f(*vertices[edge[0]])
                glVertex3f(*vertices[edge[1]])
            glEnd()

            # Dibuja triángulos
            glBegin(GL_TRIANGLES)
            glColor3f(0.2, 0.4, 1.0)
            for face in faces:
                for vertex_index in face:
                    glVertex3f(*vertices[vertex_index])
            glEnd()

            glPopMatrix()

            pygame.display.flip()