import re
import os
import random
from io import BytesIO
from PIL import Image
from cairosvg import svg2png
from xml.sax.saxutils import escape as xml_escape


COLORS = [
    ['#9878AD', '#9878AD', '#9878AD'],
    ['#787BAD', '#787BAD', '#787BAD'],
    ['#78A2AD', '#78A2AD', '#78A2AD'],
    ['#78AD8A', '#78AD8A', '#78AD8A'],
]

INITIALS_SVG_TEMPLATE = """
<svg xmlns="http://www.w3.org/2000/svg" 
    pointer-events="none" 
    width="200" height="200">
  <defs>
    <linearGradient id="grad">
    <stop offset="0%" stop-color="{color2}" />
    <stop offset="100%" stop-color="{color2}" />
    </linearGradient>
  </defs>
  <rect width="200" height="200" rx="0" ry="0" fill="url(#grad)"></rect>
  <text text-anchor="middle" y="50%" x="50%" dy="0.35em"
        pointer-events="auto" fill="{text_color}" font-family="sans-serif"
        style="font-weight: 400; font-size: 80px">{text}</text>
</svg>
""".strip()
INITIALS_SVG_TEMPLATE = re.sub('(\s+|\n)', ' ', INITIALS_SVG_TEMPLATE)


def get_png_avatar(text, output_file):

    initials = ':)'

    text = text.strip()
    if text:
        initials = text[-3:]

    random_color = random.choice(COLORS)
    svg_avatar = INITIALS_SVG_TEMPLATE.format(**{
        'color1': random_color[0],
        'color2': random_color[1],
        'text_color': random_color[2],
        'text': xml_escape(initials),
    }).replace('\n', '')

    svg2png(svg_avatar, write_to=output_file)


# generate a .png avatar profile using just profile's address
def generate_avatar_by_address(address):
    rawIO = BytesIO()
    get_png_avatar(address, rawIO)
    byteImg = Image.open(rawIO)

    path = os.path.dirname(os.path.abspath(__file__)) + '/static/avatars/' + address + '.png'
    byteImg.save(path, 'PNG')

    return path

