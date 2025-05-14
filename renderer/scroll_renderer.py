import numpy as np
import ctypes
from OpenGL.GL import *
from OpenGL.GL.shaders import compileShader, compileProgram
import pyglet
import glm
from PIL import Image, ImageDraw
from PIL import ImageFont
from enum import Enum
from .shaders import PANORAMA_VERTEX_SHADER, PANORAMA_FRAGMENT_SHADER, CUBE_VERTEX_SHADER, CUBE_FRAGMENT_SHADER

class RotationAxis(Enum):
    X = 0
    Y = 1
    Z = 2

class ScrollRenderer:
    def __init__(self, width, height, show_cube=False):
        self.width = width * 6
        self.height = height
        self.window = pyglet.window.Window(self.width, self.height, "Scroll Renderer (Panorama)", visible=True)
        self.window.switch_to()
        self.window.on_draw = self.on_draw
        
        self.angle = 0
        self.scroll = 0
        self.axis = RotationAxis.X

        # ここでVAOを生成・バインド
        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)

        vs = compileShader(PANORAMA_VERTEX_SHADER, GL_VERTEX_SHADER)
        fs = compileShader(PANORAMA_FRAGMENT_SHADER, GL_FRAGMENT_SHADER)
        self.shader_program = compileProgram(vs, fs)
        glUseProgram(self.shader_program)

        # フルスクリーン矩形
        vertices = np.array([
            -1, -1,  0, 0,
             1, -1,  1, 0,
             1,  1,  1, 1,
            -1,  1,  0, 1,
        ], dtype=np.float32)
        indices = np.array([0,1,2, 2,3,0], dtype=np.uint32)

        self.vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        self.ebo = glGenBuffers(1)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 4 * 4, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 4 * 4, ctypes.c_void_p(2 * 4))
        glEnableVertexAttribArray(1)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindVertexArray(0)

        self.texture_id = glGenTextures(1)
        self.show_cube = show_cube

        if self.show_cube:
            self.init_cube_window()

    def init_cube_window(self):
            # 立方体のスクロール用
            self.cube_window = None
            self.cube_rot_x = 20.0
            self.cube_rot_y = -30.0
            self.cube_drag = False
            self.cube_last_mouse = (0, 0)

            self.cube_window = pyglet.window.Window(self.height * 5, self.height * 5, "Scroll Renderer (Cube)", visible=True)
            self.cube_window.switch_to()
            self.cube_texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self.cube_texture_id)
            # 1x1ピクセルのダミー画像で初期化
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 1, 1, 0, GL_RGBA, GL_UNSIGNED_BYTE, b'\x00\x00\x00\x00')
            glBindTexture(GL_TEXTURE_2D, 0)
            self.cube_window.on_draw = self.cube_on_draw
            self.cube_window.on_mouse_drag = self.cube_on_mouse_drag
            self.cube_window.on_mouse_press = self.cube_on_mouse_press
            self.cube_window.on_mouse_release = self.cube_on_mouse_release

            # 立方体用VAO/VBO/EBO
            self.cube_vertices = np.array([
                # x, y, z, u, v
                # Front face
                -1, -1,  1, 1/6, 0, #左下
                1, -1,  1, 2/6, 0, #右下
                1,  1,  1, 2/6, 1, #右上
                -1,  1,  1, 1/6, 1, #左上
                # Back face
                -1, -1, -1, 4/6, 0,
                1, -1, -1, 3/6, 0,
                1,  1, -1, 3/6, 1,
                -1,  1, -1, 4/6, 1,
                # Top face
                1,  1, -1, 0/6, 0,
                -1,  1, -1, 1/6, 0,
                -1,  1,  1, 1/6, 1,
                1,  1, 1, 0/6, 1,
                # Bottom face 裏表逆
                -1, -1, -1, 5/6, 0,
                1, -1, -1, 6/6, 0,
                1, -1,  1, 6/6, 1,
                -1, -1,  1, 5/6, 1,
                # Right face
                1, -1, 1, 2/6, 0,
                1,  -1, -1, 3/6, 0,
                1,  1, -1, 3/6, 1,
                1, 1, 1, 2/6, 1,
                # Left face
                -1, -1, -1, 4/6, 0,
                -1,  -1, 1, 5/6, 0,
                -1,  1,  1, 5/6, 1,
                -1,  1, -1, 4/6, 1,
            ], dtype=np.float32)

            self.cube_indices = np.array([
                0, 1, 2, 2, 3, 0,       # Front
                4, 5, 6, 6, 7, 4,       # Back
                8, 9,10,10,11, 8,       # Top
                12,13,14,14,15,12,       # Bottom
                16,17,18,18,19,16,       # Right
                20,21,22,22,23,20        # Left
            ], dtype=np.uint32)

            self.cube_vao = glGenVertexArrays(1)
            glBindVertexArray(self.cube_vao)
            self.cube_vbo = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, self.cube_vbo)
            glBufferData(GL_ARRAY_BUFFER, self.cube_vertices.nbytes, self.cube_vertices, GL_STATIC_DRAW)
            self.cube_ebo = glGenBuffers(1)
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.cube_ebo)
            glBufferData(GL_ELEMENT_ARRAY_BUFFER, self.cube_indices.nbytes, self.cube_indices, GL_STATIC_DRAW)
            glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 5 * 4, ctypes.c_void_p(0))
            glEnableVertexAttribArray(0)
            glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 5 * 4, ctypes.c_void_p(3 * 4))
            glEnableVertexAttribArray(1)
            glBindBuffer(GL_ARRAY_BUFFER, 0)
            glBindVertexArray(0)

            # 立方体用シェーダ
            cube_vs = compileShader(CUBE_VERTEX_SHADER, GL_VERTEX_SHADER)
            cube_fs = compileShader(CUBE_FRAGMENT_SHADER, GL_FRAGMENT_SHADER)
            glBindVertexArray(self.cube_vao)  # 追加
            self.cube_shader_program = compileProgram(cube_vs, cube_fs)
            glBindVertexArray(0)  # 終わったら解除

    def set_panorama_texture(self, panorama_image: Image.Image):
        if panorama_image.mode != 'RGBA':
            panorama_image = panorama_image.convert('RGBA')

        # OpenGLテクスチャとしてアップロード（全体画像をそのまま使う場合）
        img_data = panorama_image.transpose(Image.FLIP_TOP_BOTTOM).tobytes("raw", "RGBA")
        self.window.switch_to()
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, panorama_image.width, panorama_image.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glBindTexture(GL_TEXTURE_2D, 0)


    def rotate(self, axis: RotationAxis, degree: float):
        self.axis = axis
        self.angle = np.radians(degree)
        self.scroll = (degree / 90.0) % 4.0
        rotated_image = self.get_current_frame_panorama_image()

        if self.show_cube:
            self.set_cube_texture_from_image(rotated_image)
            self.cube_window.dispatch_event('on_draw')
        return rotated_image
    
    def get_current_frame_panorama_image(self):
        width, height = self.window.width, self.window.height
        glPixelStorei(GL_PACK_ALIGNMENT, 1)
        data = glReadPixels(0, 0, width, height, GL_RGBA, GL_UNSIGNED_BYTE)
        image = Image.frombytes("RGBA", (width, height), data)
        image = image.transpose(Image.FLIP_TOP_BOTTOM)  # OpenGLは上下逆
        return image

    def set_cube_texture_from_image(self, pil_image):
        """cube用テクスチャをPIL.Imageから更新"""
        if pil_image.mode != 'RGBA':
            pil_image = pil_image.convert('RGBA')
        img_data = pil_image.transpose(Image.FLIP_TOP_BOTTOM).tobytes("raw", "RGBA")
        self.cube_window.switch_to()
        glBindTexture(GL_TEXTURE_2D, self.cube_texture_id)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, pil_image.width, pil_image.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glBindTexture(GL_TEXTURE_2D, 0)
        glFinish()  # ← 追加
    
    def on_draw(self):
        self.window.switch_to()
        glClearColor(0.1, 0.1, 0.1, 1.0)
        glClear(GL_COLOR_BUFFER_BIT)
        glUseProgram(self.shader_program)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        glUniform1i(glGetUniformLocation(self.shader_program, "u_Texture"), 0)
        glUniform1f(glGetUniformLocation(self.shader_program, "u_Scroll"), self.scroll)
        glUniform1f(glGetUniformLocation(self.shader_program, "u_Angle"), self.angle)
        glUniform1i(glGetUniformLocation(self.shader_program, "u_Axis"), self.axis.value)
        glBindVertexArray(self.vao)
        glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, None)
        glBindVertexArray(0)
        glBindTexture(GL_TEXTURE_2D, 0)
    
    def cube_on_draw(self):
        self.cube_window.switch_to()
        glClearColor(0.2, 0.2, 0.2, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glEnable(GL_DEPTH_TEST)
        glUseProgram(self.cube_shader_program)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.cube_texture_id)
        glUniform1i(glGetUniformLocation(self.cube_shader_program, "u_Texture"), 0)

        # MVP行列を計算して渡す
        aspect = self.cube_window.width / self.cube_window.height
        proj = glm.perspective(glm.radians(45.0), aspect, 0.1, 100.0)
        view = glm.lookAt(glm.vec3(0,0,5), glm.vec3(0,0,0), glm.vec3(0,1,0))
        model = glm.rotate(glm.mat4(1), glm.radians(self.cube_rot_x), glm.vec3(1,0,0))
        model = glm.rotate(model, glm.radians(self.cube_rot_y), glm.vec3(0,1,0))
        mvp = proj * view * model
        loc = glGetUniformLocation(self.cube_shader_program, "u_MVP")
        glUniformMatrix4fv(loc, 1, GL_FALSE, np.array(mvp.to_list(), dtype=np.float32))

        glBindVertexArray(self.cube_vao)
        glDrawElements(GL_TRIANGLES, 36, GL_UNSIGNED_INT, None)
        glBindVertexArray(0)
        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_DEPTH_TEST)

    def cube_on_mouse_press(self, x, y, button, modifiers):
        self.cube_drag = True
        self.cube_last_mouse = (x, y)

    def cube_on_mouse_release(self, x, y, button, modifiers):
        self.cube_drag = False

    def cube_on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        if self.cube_drag:
            self.cube_rot_x += dy
            self.cube_rot_y += dx

    def cleanup(self):
        if self.shader_program:
            glDeleteProgram(self.shader_program)
        if self.vao:
            glDeleteVertexArrays(1, [self.vao])
        if self.vbo:
            glDeleteBuffers(1, [self.vbo])
        if self.ebo:
            glDeleteBuffers(1, [self.ebo])
        if self.texture_id:
            glDeleteTextures(1, [self.texture_id])
        if hasattr(self, "cube_vao"):
            glDeleteVertexArrays(1, [self.cube_vao])
        if hasattr(self, "cube_vbo"):
            glDeleteBuffers(1, [self.cube_vbo])
        if hasattr(self, "cube_ebo"):
            glDeleteBuffers(1, [self.cube_ebo])
