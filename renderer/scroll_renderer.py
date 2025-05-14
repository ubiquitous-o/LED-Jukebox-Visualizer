import numpy as np
import ctypes
from OpenGL.GL import *
from OpenGL.GL.shaders import compileShader, compileProgram
import pyglet

from PIL import Image, ImageDraw
from PIL import ImageFont
from enum import Enum

VERTEX_SHADER_SOURCE = """
#version 330 core
layout(location = 0) in vec2 a_Position;
layout(location = 1) in vec2 a_TexCoord;
out vec2 v_TexCoord;
void main() {
    gl_Position = vec4(a_Position, 0.0, 1.0);
    v_TexCoord = a_TexCoord;
}
"""

FRAGMENT_SHADER_SOURCE = """
#version 330 core
in vec2 v_TexCoord;
out vec4 FragColor;
uniform sampler2D u_Texture;
uniform float u_Scroll;
uniform float u_Angle;
uniform int u_Axis;

void main() {
    float face_width = 1.0 / 6.0;
    float u = v_TexCoord.x;
    float v = v_TexCoord.y;
    vec2 uv = vec2(u, v);

    // --- Y軸回転処理 ---
    if (u_Axis == 1) {
        // top
        if(u < face_width) {
            vec2 local = vec2(u / face_width, v);
            vec2 rel = local - vec2(0.5, 0.5);
            float angle = -u_Angle;
            float cosA = cos(angle);
            float sinA = sin(angle);
            vec2 rot = vec2(
                rel.x * cosA - rel.y * sinA,
                rel.x * sinA + rel.y * cosA
            );
            local = rot + vec2(0.5, 0.5);
            uv = vec2(local.x * face_width, local.y) + vec2(0.0, 0.0);
        }
        // bottom
        else if(u >= 5.0 * face_width) {
            vec2 local = vec2((u - 5.0 * face_width) / face_width, v);
            vec2 rel = local - vec2(0.5, 0.5);
            float angle = u_Angle;
            float cosA = cos(angle);
            float sinA = sin(angle);
            vec2 rot = vec2(
                rel.x * cosA - rel.y * sinA,
                rel.x * sinA + rel.y * cosA
            );
            local = rot + vec2(0.5, 0.5);
            uv = vec2(local.x * face_width, local.y) + vec2(5.0 * face_width, 0.0);
        }
        // 側面スクロール
        else if(u >= face_width && u < 5.0 * face_width) {
            float rel = (u - face_width) / (4.0 * face_width);
            rel = mod(rel + u_Scroll / 4.0, 1.0);
            u = face_width + rel * 4.0 * face_width;
            uv = vec2(u, v);
        }
    }

    // --- X軸回転処理 ---
    else if (u_Axis == 0) {
        // right面（その場で回転）
        if(u >= 2.0 * face_width && u < 3.0 * face_width) {
            vec2 local = vec2((u - 2.0 * face_width) / face_width, v);
            vec2 rel = local - vec2(0.5, 0.5);
            float angle = -u_Angle;
            float cosA = cos(angle);
            float sinA = sin(angle);
            vec2 rot = vec2(
                rel.x * cosA - rel.y * sinA,
                rel.x * sinA + rel.y * cosA
            );
            local = rot + vec2(0.5, 0.5);
            uv = vec2(local.x * face_width, local.y) + vec2(2.0 * face_width, 0.0);
        }
        // left面（その場で回転）
        else if(u >= 4.0 * face_width && u < 5.0 * face_width) {
            vec2 local = vec2((u - 4.0 * face_width) / face_width, v);
            vec2 rel = local - vec2(0.5, 0.5);
            float angle = u_Angle;
            float cosA = cos(angle);
            float sinA = sin(angle);
            vec2 rot = vec2(
                rel.x * cosA - rel.y * sinA,
                rel.x * sinA + rel.y * cosA
            );
            local = rot + vec2(0.5, 0.5);
            uv = vec2(local.x * face_width, local.y) + vec2(4.0 * face_width, 0.0);
        }
        // top, front, bottom, back の循環スクロール
        else {
            float fw = face_width;
            float local_u, local_v;
            int face = -1;
            if(u < fw) { face = 0; local_u = u / fw; local_v = v; }           // top
            else if(u < 2.0*fw) { face = 1; local_u = (u-fw)/fw; local_v = v; } // front
            else if(u < 4.0*fw) { face = 3; local_u = (u-3.0*fw)/fw; local_v = v; } // back
            else { face = 5; local_u = (u-5.0*fw)/fw; local_v = v; }                // bottom

            // top, front, bottom, back のみ循環
            int tfbb_face = -1;
            float tfbb_u = local_u, tfbb_v = local_v;
            if(face == 0) tfbb_face = 0;
            else if(face == 1) tfbb_face = 1;
            else if(face == 5) tfbb_face = 2;
            else if(face == 3) tfbb_face = 3;

            if(tfbb_face >= 0) {
                // 0:top, 1:front, 2:bottom, 3:back
                float scroll = u_Scroll; // 0〜4
                float rel;
                int seg = 0;
                float frac = 0.0;
                if (tfbb_face == 0 || tfbb_face == 3) {
                    // top, back: 上から下へ
                    rel = tfbb_v + scroll;
                    seg = int(floor(rel));
                    frac = rel - float(seg);
                } else {
                    // front, bottom: 下から上へ
                    rel = tfbb_v - scroll;
                    seg = -int(floor(rel));
                    frac = rel + float(seg);
                }


                // 面インデックスを循環
                int new_face = (tfbb_face + seg) % 4;
                if(new_face < 0) new_face += 4;

                // 180度回転が必要な面（top→front, bottom→back）
                bool flip = false;
                if (tfbb_face == 0) {
                    if (new_face == 0) {
                        flip = false;
                    }
                    else if (new_face == 1) {
                        flip = true;
                    }
                    else if (new_face == 2) {
                        flip = false;
                    }
                    else if (new_face == 3) {
                        flip = true;
                    }
                } 
                else if (tfbb_face == 1) {
                    if (new_face == 0) {
                        flip = true;
                    }
                    else if (new_face == 1) {
                        flip = false;
                    }
                    else if (new_face == 2) {
                        flip = true;
                    }
                    else if (new_face == 3) {
                        flip = false;
                    }
                }
                else if (tfbb_face == 2) {
                    if (new_face == 0) {
                        flip = false;
                    }
                    else if (new_face == 1) {
                        flip = true;
                    }
                    else if (new_face == 2) {
                        flip = false;
                    }
                    else if (new_face == 3) {
                        flip = true;
                    }
                }
                else if (tfbb_face == 3) {
                    if (new_face == 0) {
                        flip = true;
                    }
                    else if (new_face == 1) {
                        flip = false;
                    }
                    else if (new_face == 2) {
                        flip = true;
                    }
                    else if (new_face == 3) {
                        flip = false;
                    }
                }
                float new_u = flip ? (1.0 - tfbb_u) : tfbb_u;
                float new_v = flip ? (1.0 - frac) : frac;

                // 各面のテクスチャ座標
                float base_u = 0.0;
                if(new_face == 0) base_u = 0.0 * fw;      // top
                else if(new_face == 1) base_u = 1.0 * fw; // front
                else if(new_face == 2) base_u = 5.0 * fw; // bottom
                else if(new_face == 3) base_u = 3.0 * fw; // back

                uv = vec2(new_u * fw, new_v) + vec2(base_u, 0.0);
            }
        }
    }

    FragColor = texture(u_Texture, uv);
}
"""

class RotationAxis(Enum):
    X = 0
    Y = 1
    Z = 2

class ScrollRenderer:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.window = pyglet.window.Window(width, height, "Scroll Renderer", visible=True)
        self.window.switch_to()
        self.window.on_draw = self.on_draw
        self.faces = {}
        
        self.angle = 0
        self.scroll = 0
        self.axis = RotationAxis.X    

        # ここでVAOを生成・バインド
        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)

        vs = compileShader(VERTEX_SHADER_SOURCE, GL_VERTEX_SHADER)
        fs = compileShader(FRAGMENT_SHADER_SOURCE, GL_FRAGMENT_SHADER)
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

    def set_panorama_texture(self, panorama_image: Image.Image):
        if panorama_image.mode != 'RGBA':
            panorama_image = panorama_image.convert('RGBA')
        # 画像を6枚に分割して面名で辞書に格納
        face_names = ["top", "front", "right", "back", "left", "bottom"]
        face_width = panorama_image.width // 6
        face_height = panorama_image.height
        for i, name in enumerate(face_names):
            box = (i * face_width, 0, (i + 1) * face_width, face_height)
            self.faces[name] = panorama_image.crop(box)
        # 例: self.faces["top"] でtop面のPIL.Imageが取得できる

        # OpenGLテクスチャとしてアップロード（全体画像をそのまま使う場合）
        img_data = panorama_image.transpose(Image.FLIP_TOP_BOTTOM).tobytes("raw", "RGBA")
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

    def on_draw(self):
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
