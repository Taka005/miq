from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from pilmoji import Pilmoji
from flask import Flask, request, send_file
import textwrap
import requests
import warnings
import base64
import io
import os

warnings.simplefilter("ignore")

BASE_GD_IMAGE = Image.open("images/base-gd.png")
BASE_RV_IMAGE = Image.open("images/base-gd-rv.png")

BASE_GD_W_IMAGE = Image.open("images/base-gd-w.png")
BASE_RV_W_IMAGE = Image.open("images/base-gd-w-rv.png")

BASE_IMAGE = Image.open("images/base.png")
MPLUS_FONT = ImageFont.truetype("fonts/MPLUSRounded1c-Regular.ttf", size=16)
BRAND = "TakasumiBOT#7189"

def drawText(im, ofs, string, font="fonts/MPLUSRounded1c-Regular.ttf", size=16, color=(0, 0, 0, 255), split_len=None, padding=4, auto_expand=False, disable_dot_wrap=False):
    draw = ImageDraw.Draw(im)
    fontObj = ImageFont.truetype(font, size=size)

    pure_lines = []
    pos = 0
    l = ""

    if not disable_dot_wrap:
        for char in string:
            if char == "\n":
                pure_lines.append(l)
                l = ""
                pos += 1
            elif char == "、" or char == ",":
                pure_lines.append(l + ("、" if char == "、" else ","))
                l = ""
                pos += 1
            elif char == "。" or char == ".":
                pure_lines.append(l + ("。" if char == "。" else "."))
                l = ""
                pos += 1
            else:
                l += char
                pos += 1

        if l:
            pure_lines.append(l)
    else:
        pure_lines = string.split("\n")

    lines = []

    for line in pure_lines:
        lines.extend(textwrap.wrap(line, width=split_len))

    dy = 0

    draw_lines = []

    for line in lines:
        tsize = fontObj.getsize(line)

        ofs_y = ofs[1] + dy
        t_height = tsize[1]

        x = int(ofs[0] - (tsize[0]/2))
        draw_lines.append((x, ofs_y, line))
        ofs_y += t_height + padding
        dy += t_height + padding

    adj_y = -30 * (len(draw_lines)-1)
    for dl in draw_lines:
        with Pilmoji(im) as p:
            p.text((dl[0], (adj_y + dl[1])), dl[2], font=fontObj, fill=color)

    real_y = ofs[1] + adj_y + dy

    return (0, dy, real_y)

def make(name, tag, id, content, icon):
    img = BASE_IMAGE.copy()

    icon = Image.open(io.BytesIO(requests.get(icon).content))
    icon = icon.resize((720, 720), Image.LANCZOS)
    icon = icon.convert("L")
    icon_filtered = ImageEnhance.Brightness(icon)

    img.paste(icon_filtered.enhance(0.7), (0, 0))
    img.paste(BASE_GD_IMAGE, (0, 0), BASE_GD_IMAGE)

    tx = ImageDraw.Draw(img)

    tsize_t = drawText(img, (890, 270), content, size=45, color=(255, 255, 255, 255), split_len=16, auto_expand=True)

    name_y = tsize_t[2] + 40
    tsize_name = drawText(img, (890, name_y), f"{name}#{tag}", size=25, color=(255, 255, 255, 255), split_len=25, disable_dot_wrap=True)

    id_y = name_y + tsize_name[1] + 4
    tsize_id = drawText(img, (890, id_y), id, size=18, color=(180, 180, 180, 255), split_len=45, disable_dot_wrap=True)

    tx.text((1122, 694), BRAND, font=MPLUS_FONT, fill=(120, 120, 120, 255))

    file = io.BytesIO()
    img.save(file, format="PNG", quality=95)
    file.seek(0)
    return file

def colorMake(name, tag, id, content, icon):
    img = BASE_IMAGE.copy()

    icon = Image.open(io.BytesIO(requests.get(icon).content))
    icon = icon.resize((720, 720), Image.LANCZOS)

    img.paste(icon, (0, 0))
    img.paste(BASE_GD_IMAGE, (0, 0), BASE_GD_IMAGE)

    tx = ImageDraw.Draw(img)

    tsize_t = drawText(img, (890, 270), content, size=45, color=(255, 255, 255, 255), split_len=16, auto_expand=True)

    name_y = tsize_t[2] + 40
    tsize_name = drawText(img, (890, name_y), f"{name}#{tag}", size=25, color=(255, 255, 255, 255), split_len=25, disable_dot_wrap=True)

    id_y = name_y + tsize_name[1] + 4
    tsize_id = drawText(img, (890, id_y), id, size=18, color=(180, 180, 180, 255), split_len=45, disable_dot_wrap=True)

    tx.text((1122, 694), BRAND,font=MPLUS_FONT, fill=(120, 120, 120, 255))

    file = io.BytesIO()
    img.save(file, format="PNG", quality=95)
    file.seek(0)
    return file

def reverseMake(name, tag, id, content, icon):
    img = BASE_IMAGE.copy()

    icon = Image.open(io.BytesIO(requests.get(icon).content))
    icon = icon.resize((720, 720), Image.LANCZOS)
    icon = icon.convert("L")
    icon_filtered = ImageEnhance.Brightness(icon)

    img.paste(icon_filtered.enhance(0.7), (570, 0))
    img.paste(BASE_RV_IMAGE, (0, 0), BASE_RV_IMAGE)

    tx = ImageDraw.Draw(img)

    tsize_t = drawText(img, (390, 270), content, size=45, color=(255, 255, 255, 255), split_len=16, auto_expand=True)

    name_y = tsize_t[2] + 40
    tsize_name = drawText(img, (390, name_y), f"{name}#{tag}", size=25, color=(255, 255, 255, 255), split_len=25, disable_dot_wrap=True)

    id_y = name_y + tsize_name[1] + 4
    tsize_id = drawText(img, (390, id_y), id, size=18, color=(90, 90, 90, 255), split_len=45, disable_dot_wrap=True)

    tx.text((6, 694), BRAND, font=MPLUS_FONT, fill=(110, 110, 110, 255))

    file = io.BytesIO()
    img.save(file, format="PNG", quality=95)
    file.seek(0)
    return file

def whiteMake(name, tag, id, content, icon):
    img = BASE_IMAGE.copy()

    icon = Image.open(io.BytesIO(requests.get(icon).content))
    icon = icon.resize((720, 720), Image.LANCZOS)

    img.paste(icon, (0, 0), icon)
    img.paste(BASE_GD_W_IMAGE, (0, 0), BASE_GD_W_IMAGE)
   
    tx = ImageDraw.Draw(img)

    tsize_t = drawText(img, (890, 270), content, size=45, color=(0, 0, 0, 0), split_len=16, auto_expand=True)

    name_y = tsize_t[2] + 40
    tsize_name = drawText(img, (890, name_y), f"{name}#{tag}", size=25, color=(0, 0, 0, 0), split_len=25, disable_dot_wrap=True)

    id_y = name_y + tsize_name[1] + 4
    tsize_id = drawText(img, (890, id_y), id, size=18, color=(180, 180, 180, 255), split_len=45, disable_dot_wrap=True)

    tx.text((1122, 694), BRAND, font=MPLUS_FONT, fill=(120, 120, 120, 255))

    file = io.BytesIO()
    img.save(file, format="PNG", quality=95)
    file.seek(0)
    return file

app = Flask(__name__)

@app.route("/", methods=["GET"])
def main():
    res = make(
        request.args.get("name") or "SAMPLE",
        request.args.get("tag") or "1234",
        request.args.get("id") or "0000000000000000000",
        request.args.get("content") or "Make it a Quote",
        request.args.get("icon") or "https://cdn.discordapp.com/embed/avatars/0.png"
    )
    return send_file(res, mimetype="image/png")

@app.route("/color", methods=["GET"])
def color():
    res = colorMake(
        request.args.get("name") or "SAMPLE",
        request.args.get("tag") or "1234",
        request.args.get("id") or "0000000000000000000",
        request.args.get("content") or "Make it a Quote",
        request.args.get("icon") or "https://cdn.discordapp.com/embed/avatars/0.png"
    )
    return send_file(res, mimetype="image/png")

@app.route("/reverse", methods=["GET"])
def reverse():
    res = reverseMake(
        request.args.get("name") or "SAMPLE",
        request.args.get("tag") or "1234",
        request.args.get("id") or "0000000000000000000",
        request.args.get("content") or "Make it a Quote",
        request.args.get("icon") or "https://cdn.discordapp.com/embed/avatars/0.png"
    )
    return send_file(res, mimetype="image/png")

@app.route("/white", methods=["GET"])
def white():
    res = whiteMake(
        request.args.get("name") or "SAMPLE",
        request.args.get("tag") or "1234",
        request.args.get("id") or "0000000000000000000",
        request.args.get("content") or "Make it a Quote",
        request.args.get("icon") or "https://cdn.discordapp.com/embed/avatars/0.png"
    )
    return send_file(res, mimetype="image/png")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
