import numpy as np
from PIL import Image
import ctypes
from OpenGL.GL import *
import pyglet
from PIL import Image, ImageDraw
from PIL import ImageFont

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
uniform float u_YScroll;
uniform float u_YAngle;
uniform float u_XScroll;
uniform float u_XAngle;

void main() {
    float face_width = 1.0 / 6.0;
    float u = v_TexCoord.x;
    float v = v_TexCoord.y;
    vec2 uv = vec2(u, v);

    // --- Y軸回転処理 ---
    if (abs(u_YAngle) > 0.0001 || abs(u_YScroll) > 0.0001) {
        // top
        if(u < face_width) {
            vec2 local = vec2(u / face_width, v);
            vec2 rel = local - vec2(0.5, 0.5);
            float angle = -u_YAngle;
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
            float angle = u_YAngle;
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
            rel = mod(rel + u_YScroll / 4.0, 1.0);
            u = face_width + rel * 4.0 * face_width;
            uv = vec2(u, v);
        }
    }

    // --- X軸回転処理 ---
    else if (abs(u_XAngle) > 0.0001 || abs(u_XScroll) > 0.0001) {
        // right面（その場で回転）
        if(u >= 2.0 * face_width && u < 3.0 * face_width) {
            vec2 local = vec2((u - 2.0 * face_width) / face_width, v);
            vec2 rel = local - vec2(0.5, 0.5);
            float angle = -u_XAngle;
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
            float angle = u_XAngle;
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
            //else if(u < 3.0*fw) { face = 2; local_u = (u-2.0*fw)/fw; local_v = v; } // right
            else if(u < 4.0*fw) { face = 3; local_u = (u-3.0*fw)/fw; local_v = v; } // back
            //else if(u < 5.0*fw) { face = 4; local_u = (u-4.0*fw)/fw; local_v = v; } // left
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
                float scroll = u_XScroll; // 0〜4
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
                        flip = false; // 二重にかかるのでfalse
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
            // right/left/back以外はそのまま
        }
    }

    FragColor = texture(u_Texture, uv);
}
"""
class ScrollRenderer:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.window = pyglet.window.Window(width, height, "Panorama", visible=True)
        self.window.switch_to()
        self.window.on_draw = self.on_draw
        self.faces = {}
        # 軸ごとの回転状態
        self.rotation = {"x": 0.0, "y": 0.0}
        self.y_scroll = 0.0
        self.y_angle = 0.0
        self.x_angle = 0.0


        # ここでVAOを生成・バインド
        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)

        from OpenGL.GL.shaders import compileShader, compileProgram
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
        glBindVertexArray(0)  # ここで解除

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


    def rotate(self, axis: str, degree: float):
        axis = axis.lower()
        if axis == "y":
            self.rotation["y"] = degree
            # 側面スクロール値
            self.y_scroll = (degree / 90.0) % 4.0
            # top/bottom用ラジアン
            self.y_angle = np.radians(degree)
        elif axis == "x":
            self.rotation["x"] = degree
            # x軸回転用の値をここで計算してself.x_angleなどに格納
            self.x_angle = np.radians(degree)
            self.x_scroll = (degree / 90.0) % 4.0 # ←追加

        # 他の軸も拡張可能

    def on_draw(self):
        glClearColor(0.1, 0.1, 0.1, 1.0)
        glClear(GL_COLOR_BUFFER_BIT)
        glUseProgram(self.shader_program)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        glUniform1i(glGetUniformLocation(self.shader_program, "u_Texture"), 0)
        glUniform1f(glGetUniformLocation(self.shader_program, "u_YScroll"), self.y_scroll)
        glUniform1f(glGetUniformLocation(self.shader_program, "u_YAngle"), self.y_angle)
        glUniform1f(glGetUniformLocation(self.shader_program, "u_XScroll"), getattr(self, "x_scroll", 0.0))  # ←追加
        glUniform1f(glGetUniformLocation(self.shader_program, "u_XAngle"), getattr(self, "x_angle", 0.0))
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

if __name__ == "__main__":
    renderer = PanoramaRenderer(64*6, 64)

    img = Image.new("RGBA", (64, 64))  # テスト用に黒い画像を作成
    imgs = []
    background_colors = ["red", "green", "blue", "yellow", "purple", "orange"]
    for i in range(6):
        tmp = img.copy()
        tmp.paste(background_colors[i], [0, 0, tmp.width, tmp.height])
        draw = ImageDraw.Draw(tmp)
        text = str(i+1)
        font_size = 20  # 文字サイズを指定
        font = ImageFont.truetype("test/Courier.ttc", font_size)  # フォントを指定
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_size = (text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1])
        text_position = ((tmp.width - text_size[0]) // 2, (tmp.height - text_size[1]) // 2)
        draw.text(text_position, text, fill="black", font=font)
        imgs.append(tmp)

    concat_img = Image.new("RGBA", (img.width * 6, img.height))
    for i in range(6):
        concat_img.paste(imgs[i], (i * img.width, 0))

    renderer.set_panorama_texture(concat_img)  # panorama_imageはPIL.Image(384x64)

    # アニメーション的に回転させる例
    import time

    def update(dt):
        # 0〜359度で回転
        current_deg = (update.deg + 2) % 360
        renderer.rotate("x", current_deg)
        renderer.window.dispatch_event('on_draw')
        update.deg = current_deg

    update.deg = 0

    pyglet.clock.schedule_interval(update, 1/30)  # 30FPSで回転
    pyglet.app.run()