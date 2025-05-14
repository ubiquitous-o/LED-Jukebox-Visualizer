PANORAMA_VERTEX_SHADER = """
#version 330 core
layout(location = 0) in vec2 a_Position;
layout(location = 1) in vec2 a_TexCoord;
out vec2 v_TexCoord;
void main() {
    gl_Position = vec4(a_Position, 0.0, 1.0);
    v_TexCoord = a_TexCoord;
}
"""

PANORAMA_FRAGMENT_SHADER = """
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
            float angle = u_Angle;
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
            float angle = -u_Angle;
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
            float angle = u_Angle;
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
            float angle = -u_Angle;
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
                if (tfbb_face == 0) {// top
                    if (new_face == 0) {
                        flip = false;
                    }
                    else if (new_face == 1) {
                        flip = true;
                    }
                    else if (new_face == 2) {
                        flip = true;
                    }
                    else if (new_face == 3) {
                        flip = false;
                    }
                } 
                else if (tfbb_face == 1) {// front
                    if (new_face == 0) {
                        flip = true;
                    }
                    else if (new_face == 1) {
                        flip = false;
                    }
                    else if (new_face == 2) {
                        flip = false;
                    }
                    else if (new_face == 3) {
                        flip = true;
                    }
                }
                else if (tfbb_face == 2) { // bottom
                    if (new_face == 0) {
                        flip = true;
                    }
                    else if (new_face == 1) {
                        flip = false;
                    }
                    else if (new_face == 2) {
                        flip = false;
                    }
                    else if (new_face == 3) {
                        flip = true;
                    }
                }
                else if (tfbb_face == 3) { // back
                    if (new_face == 0) {
                        flip = false;
                    }
                    else if (new_face == 1) {
                        flip = true;
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
    // --- Z軸回転処理 ---
    else if (u_Axis == 2) {
        // front面（その場で回転）
        if(u >= face_width && u < 2.0 * face_width) {
            vec2 local = vec2((u - face_width) / face_width, v);
            vec2 rel = local - vec2(0.5, 0.5);
            float angle = u_Angle;
            float cosA = cos(angle);
            float sinA = sin(angle);
            vec2 rot = vec2(
                rel.x * cosA - rel.y * sinA,
                rel.x * sinA + rel.y * cosA
            );
            local = rot + vec2(0.5, 0.5);
            uv = vec2(local.x * face_width, local.y) + vec2(face_width, 0.0);
        }
        // back面（その場で回転）
        else if(u >= 3.0 * face_width && u < 4.0 * face_width) {
            vec2 local = vec2((u - 3.0 * face_width) / face_width, v);
            vec2 rel = local - vec2(0.5, 0.5);
            float angle = -u_Angle;
            float cosA = cos(angle);
            float sinA = sin(angle);
            vec2 rot = vec2(
                rel.x * cosA - rel.y * sinA,
                rel.x * sinA + rel.y * cosA
            );
            local = rot + vec2(0.5, 0.5);
            uv = vec2(local.x * face_width, local.y) + vec2(3.0 * face_width, 0.0);
        }
        // top, right, bottom, left の循環スクロール
        else {
            float fw = face_width;
            float local_u, local_v;
            int face = -1;
            if(u < fw) { face = 0; local_u = u / fw; local_v = v; }           // top
            else if(u >= 2.0*fw && u < 3.0*fw) { face = 2; local_u = (u-2.0*fw)/fw; local_v = v; } // right
            else if(u >= 4.0*fw && u < 5.0*fw) { face = 4; local_u = (u-4.0*fw)/fw; local_v = v; } // left
            else if(u >= 5.0*fw) { face = 5; local_u = (u-5.0*fw)/fw; local_v = v; }               // bottom

            // top, right, bottom, left のみ循環
            int trbl_face = -1;
            float trbl_u = local_u, trbl_v = local_v;
            if(face == 0) trbl_face = 0; // top
            else if(face == 2) trbl_face = 1; // right
            else if(face == 5) trbl_face = 2; // bottom
            else if(face == 4) trbl_face = 3; // left

            if(trbl_face >= 0) {
                // 0:top, 1:right, 2:bottom, 3:left
                float scroll = u_Scroll; // 0〜4
                float rel;
                int seg = 0;
                float frac = 0.0;
                if(trbl_face == 0) {
                    // top: 右から左へ
                    rel = trbl_u + scroll;
                    seg =  - int(floor(rel));
                    frac = rel + float(seg);
                } else if(trbl_face == 1) {
                    // right: 上から下へ
                    rel = trbl_v + scroll;
                    seg = - int(floor(rel));
                    frac = rel + float(seg);
                } else if(trbl_face == 2) {
                    // bottom: 右から左へ
                    rel = trbl_u + scroll;
                    seg = - int(floor(rel));
                    frac = rel + float(seg);
                } else if(trbl_face == 3) {
                    // left: 下から上へ
                    rel = 1.0 - trbl_v + scroll;
                    seg = -int(floor(rel));
                    frac = rel + float(seg);
                }

                // 面インデックスを循環
                int new_face = (trbl_face + seg) % 4;
                if(new_face < 0) new_face += 4;

                float new_u = trbl_u;
                float new_v = trbl_v;
                float base_u = 0.0;
                bool rotate90 = false;
                bool inv_rotate90 = false;
                bool flip = false;

                // 各面遷移ごとに90度回転やflipを考慮
                if(trbl_face == 0) { // top
                    if(new_face == 0) {
                        new_u = frac;
                        new_v = trbl_v;
                        base_u = 0.0 * fw;
                    }
                    else if(new_face == 1) {
                        new_u = 1.0 - trbl_v;
                        new_v = frac;
                        base_u = 2.0 * fw;
                    }
                    else if(new_face == 2) {
                        new_u = 1.0 - frac;
                        new_v = 1.0 - trbl_v;
                        base_u = 5.0 * fw; flip = true; }
                    else if(new_face == 3) {
                        new_u = trbl_v;
                        new_v = 1.0 - frac;
                        base_u = 4.0 * fw;
                    }
                }
                else if(trbl_face == 1) { // right
                    if(new_face == 0) {
                        new_u = 1.0 - frac;
                        new_v = trbl_u;
                        base_u = 0.0 * fw;
                        flip = true;
                    }
                    else if(new_face == 1) {
                        new_u = trbl_u;
                        new_v = frac;
                        base_u = 2.0 * fw;
                    }
                    else if(new_face == 2) {
                        new_u = frac;
                        new_v = 1.0 - trbl_u;
                        base_u = 5.0 * fw;
                    }
                    else if(new_face == 3) {
                        new_u = trbl_u;
                        new_v = 1.0 - frac;
                        base_u = 4.0 * fw;
                    }
                }
                else if(trbl_face == 2) { // bottom
                    if(new_face == 0) {
                        new_u = 1.0 - frac;
                        new_v = 1.0 - trbl_v;
                        base_u = 0.0 * fw;
                        flip = true;
                    }
                    else if(new_face == 1) {
                        new_u = trbl_v;
                        new_v = 1.0 - frac;
                        base_u = 2.0 * fw;
                        flip = true;
                    }
                    else if(new_face == 2) {
                        new_u = frac;
                        new_v = trbl_v;
                        base_u = 5.0 * fw;
                    }
                    else if(new_face == 3) {
                        new_u = 1.0 - trbl_v;
                        new_v = frac;
                        base_u = 4.0 * fw;
                        flip = true;
                    }
                }
                else if(trbl_face == 3) { // left
                    if(new_face == 0) {
                        new_u = 1.0 - frac;
                        new_v = 1.0 - trbl_u;
                        base_u = 0.0 * fw;
                        flip = true;
                    }
                    else if(new_face == 1) {
                        new_u = trbl_u;
                        new_v = 1.0 - frac;
                        base_u = 2.0 * fw;
                        flip = true;
                    }
                    else if(new_face == 2) {
                        new_u = frac;
                        new_v = trbl_u;
                        base_u = 5.0 * fw;
                    }
                    else if(new_face == 3) {
                        new_u = 1.0 - trbl_u;
                        new_v = frac;
                        base_u = 4.0 * fw;
                        flip = true;
                        
                    }
                }

                // 90度回転
                if(rotate90) {
                    float tmp = new_u;
                    new_u = new_v;
                    new_v = tmp;
                }
                if(inv_rotate90) {
                    float tmp = new_u;
                    new_u = 1.0 - new_v;
                    new_v = 1.0 - tmp;
                }
                // 上下反転
                if(flip) {
                    new_u = 1.0 - new_u;
                    new_v = 1.0 - new_v;
                }
                uv = vec2(new_u * fw, new_v) + vec2(base_u, 0.0);
            }
        }
    }
    FragColor = texture(u_Texture, uv);
}
"""

CUBE_VERTEX_SHADER = """
#version 330 core
layout(location = 0) in vec3 a_Position;
layout(location = 1) in vec2 a_TexCoord;
uniform mat4 u_MVP;
out vec2 v_TexCoord;
void main() {
    gl_Position = u_MVP * vec4(a_Position, 1.0);
    v_TexCoord = a_TexCoord;
}
"""

CUBE_FRAGMENT_SHADER = """
#version 330 core
in vec2 v_TexCoord;
out vec4 FragColor;
uniform sampler2D u_Texture;
void main() {
    FragColor = texture(u_Texture, v_TexCoord);
}
"""