import sys
import os
import time
from PIL import Image, ImageDraw
from PIL import ImageFont
import pyglet

from renderer.scroll_renderer import ScrollRenderer

if __name__ == "__main__":
    renderer = ScrollRenderer(64*6, 64)

    img = Image.new("RGBA", (64, 64))
    imgs = []
    background_colors = ["red", "green", "blue", "yellow", "purple", "orange"]
    for i in range(6):
        tmp = img.copy()
        tmp.paste(background_colors[i], [0, 0, tmp.width, tmp.height])
        draw = ImageDraw.Draw(tmp)
        text = str(i+1)
        font_size = 20
        font = ImageFont.truetype("test/Courier.ttc", font_size)
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_size = (text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1])
        text_position = ((tmp.width - text_size[0]) // 2, (tmp.height - text_size[1]) // 2)
        draw.text(text_position, text, fill="black", font=font)
        imgs.append(tmp)

    concat_img = Image.new("RGBA", (img.width * 6, img.height))
    for i in range(6):
        concat_img.paste(imgs[i], (i * img.width, 0))

    renderer.set_panorama_texture(concat_img)

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