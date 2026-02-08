import os

from PIL import Image, ImageDraw, ImageFont
from qrcode.constants import ERROR_CORRECT_L
from qrcode.main import QRCode

from src.models import User

TEMPLATE_IMAGE = 'assets/images/referral_stats_template.png'
FONTS = {
    'gems': ('assets/fonts/outfit-extrabold.ttf', 100),
    'spins': ('assets/fonts/outfit-extrabold.ttf', 80),
    'anon_name': ('assets/fonts/outfit-bold.ttf', 50),
    'referral_link': ('assets/fonts/arial.ttf', 30)
}

GENERATED_DIRECTORY = 'generated'
os.makedirs(GENERATED_DIRECTORY, exist_ok=True)

TEXT_POSITIONS = {
    'gems': (120, 95),
    'spins': (120, 245),
    'anon_name': (120, 416),
    'referral_link': (120, 640)
}

COLORS = {
    'gems': '#00ffa6',
    'spins': '#00ffa6',
    'anon_name': '#ffffff',
    'referral_link': '#000000'
}

QR_COORDS = ((692, 463), (898, 669))


def draw_text(draw, text, font_path, size, position, color):
    font = ImageFont.truetype(font_path, size)
    draw.text(position, text, font=font, fill=color)


def add_qr_code(image: Image, referral_link: str, coords: tuple):
    qr_code = QRCode(version=1, border=1, error_correction=ERROR_CORRECT_L)
    qr_code.add_data(referral_link)

    qr_width = coords[1][0] - coords[0][0]
    qr_height = coords[1][1] - coords[0][1]

    qr_image = qr_code.make_image().convert('RGBA')
    qr_image = qr_image.resize((qr_width, qr_height))

    image.paste(qr_image, coords[0], qr_image)


def create_referral_image(gems: int, spins: int, anon_name: str, referral_link: str, output_path: str):
    image = Image.open(TEMPLATE_IMAGE)
    draw = ImageDraw.Draw(image)

    draw_text(draw, str(gems), *FONTS['gems'], TEXT_POSITIONS['gems'], COLORS['gems'])
    draw_text(draw, str(spins), *FONTS['spins'], TEXT_POSITIONS['spins'], COLORS['spins'])
    draw_text(draw, anon_name, *FONTS['anon_name'], TEXT_POSITIONS['anon_name'], COLORS['anon_name'])
    draw_text(draw, referral_link, *FONTS['referral_link'], TEXT_POSITIONS['referral_link'], COLORS['referral_link'])

    add_qr_code(image, referral_link, QR_COORDS)
    image.save(output_path)


def get_referral_image(user: User) -> str:
    image_filename = f"referral_stats_{user.id}.png"
    image_path = os.path.join(GENERATED_DIRECTORY, image_filename)

    create_referral_image(
        user.gems_total,
        user.spins_total,
        user.anon_name,
        user.create_referral_link(),
        image_path
    )

    return image_path
