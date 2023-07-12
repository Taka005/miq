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
BASE_FLIPPED_IMAGE = Image.open("images/base-gd-flipped.png")
BASE_IMAGE = Image.open("images/base.png")
MPLUS_FONT = ImageFont.truetype("fonts/MPLUSRounded1c-Regular.ttf", size=16)
branding = "TakasumiBOT"

 def draw_text(im, ofs, string, font="fonts/MPLUSRounded1c-Regular.ttf", size=16, color=(0, 0, 0, 255), split_len=None, padding=4, auto_expand=False, disable_dot_wrap=False):
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

    tsize_t = draw_text(img, (890, 270), content, size=45, color=(255, 255, 255, 255), split_len=16, auto_expand=True)

    name_y = tsize_t[2] + 40
    tsize_name = draw_text(img, (890, name_y), f"{name}#{tag}", size=25, color=(255, 255, 255, 255), split_len=25, disable_dot_wrap=True)

    id_y = name_y + tsize_name[1] + 4
    tsize_id = draw_text(img, (890, id_y), id, size=18, color=(180, 180, 180, 255), split_len=45, disable_dot_wrap=True)

    tx.text((1125, 694), branding,
            font=MPLUS_FONT, fill=(120, 120, 120, 255))

    file = io.BytesIO()
    img.save(file, format="PNG", quality=95)
    file.seek(0)
    return file

def colourmake(name, tag, id, content, icon):
    img = BASE_IMAGE.copy()

    icon = Image.open(io.BytesIO(requests.get(icon).content))
    icon = icon.resize((720, 720), Image.LANCZOS)
    icon_filtered = ImageEnhance.Brightness(icon)

    img.paste(icon_filtered.enhance(0.7), (0, 0))
    img.paste(BASE_GD_IMAGE, (0, 0), BASE_GD_IMAGE)

    tx = ImageDraw.Draw(img)

    tsize_t = draw_text(img, (890, 270), content, size=45, color=(
        255, 255, 255, 255), split_len=16, auto_expand=True)

    name_y = tsize_t[2] + 40
    tsize_name = draw_text(img, (890, name_y), f"{name}#{tag}", size=25, color=(
        255, 255, 255, 255), split_len=25, disable_dot_wrap=True)

    id_y = name_y + tsize_name[1] + 4
    tsize_id = draw_text(img, (890, id_y), id, size=18, color=(
        180, 180, 180, 255), split_len=45, disable_dot_wrap=True)

    tx.text((1125, 694), branding,
            font=MPLUS_FONT, fill=(120, 120, 120, 255))

    file = io.BytesIO()
    img.save(file, format="PNG", quality=95)
    file.seek(0)
    return file

def reversemake(name, tag, id, content, icon):
    img = BASE_IMAGE.copy()

    icon = Image.open(io.BytesIO(requests.get(icon).content))
    icon = icon.resize((720, 720), Image.LANCZOS)
    icon = icon.convert("L")
    icon_filtered = ImageEnhance.Brightness(icon)

    img.paste(icon_filtered.enhance(0.7), (570, 0))
    img.paste(BASE_FLIPPED_IMAGE, (0, 0), BASE_FLIPPED_IMAGE)

    tx = ImageDraw.Draw(img)

    tsize_t = draw_text(img, (390, 270), content, size=45, color=(
        255, 255, 255, 255), split_len=16, auto_expand=True)

    name_y = tsize_t[2] + 40
    tsize_name = draw_text(img, (390, name_y), f"{name}#{tag}", size=25, color=(
        255, 255, 255, 255), split_len=25, disable_dot_wrap=True)

    id_y = name_y + tsize_name[1] + 4
    tsize_id = draw_text(img, (390, id_y), id, size=18, color=(
        180, 180, 180, 255), split_len=45, disable_dot_wrap=True)

    tx.text((15, 694), branding,
            font=MPLUS_FONT, fill=(120, 120, 120, 255))

    file = io.BytesIO()
    img.save(file, format="PNG", quality=95)
    file.seek(0)
    return file

app = Flask(__name__)

@app.route("/", methods=["GET"])
def original():
    res = make(
        request.args.get("name") or "SAMPLE",
        request.args.get("tag") or "1234",
        request.args.get("id") or "0000000000000000000",
        request.args.get("content") or "This isn't a very good quote unless you say something",
        request.args.get(
            "icon") or "https://cdn.mikn.dev/MikanBot.png"
    )
    return send_file(res, mimetype="image/png")

@app.route("/color", methods=["GET"])
def colour():
    res = colourmake(
        request.args.get("name") or "SAMPLE",
        request.args.get("tag") or "1234",
        request.args.get("id") or "0000000000000000000",
        request.args.get("content") or "This isn't a very good quote unless you say something",
        request.args.get(
            "icon") or "https://cdn.mikn.dev/MikanBot.png"
    )
    return send_file(res, mimetype="image/png")

@app.route("/reverse", methods=["GET"])
def reverse():
    res = reversemake(
        request.args.get("name") or "SAMPLE",
        request.args.get("tag") or "1234",
        request.args.get("id") or "0000000000000000000",
        request.args.get("content") or "This isn't a very good quote unless you say something",
        request.args.get(
            "icon") or "https://cdn.mikn.dev/MikanBot.png"
    )
    return send_file(res, mimetype="image/png")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
