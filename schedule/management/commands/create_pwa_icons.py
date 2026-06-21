import os
import struct
import zlib
from django.core.management.base import BaseCommand
from django.conf import settings


def make_png(size, bg=(26, 26, 46), accent=(255, 193, 7)):
    """유도관 앱 아이콘 PNG 생성 (순수 Python, 외부 라이브러리 불필요)"""
    w = h = size

    def chunk(tag, data):
        buf = tag + data
        return struct.pack('>I', len(data)) + buf + struct.pack('>I', zlib.crc32(buf) & 0xffffffff)

    rows = b''
    for y in range(h):
        row = b'\x00'
        for x in range(w):
            # 배경: 다크 네이비
            # 중앙 원형 노란 영역 (아이콘처럼 보이게)
            cx, cy = w / 2, h / 2
            radius = w * 0.38
            inner = w * 0.18
            dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5

            if dist < inner:
                # 중앙 작은 원 (다크)
                row += bytes(bg)
            elif dist < radius:
                # 외곽 원 (노란색)
                row += bytes(accent)
            else:
                row += bytes(bg)
        rows += row

    ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
    idat = chunk(b'IDAT', zlib.compress(rows, 9))
    iend = chunk(b'IEND', b'')
    return b'\x89PNG\r\n\x1a\n' + ihdr + idat + iend


class Command(BaseCommand):
    help = 'PWA 아이콘 PNG 파일 생성'

    def handle(self, *args, **options):
        icons_dir = os.path.join(settings.BASE_DIR, 'schedule', 'static', 'icons')
        os.makedirs(icons_dir, exist_ok=True)

        for size in [192, 512]:
            path = os.path.join(icons_dir, f'icon-{size}.png')
            with open(path, 'wb') as f:
                f.write(make_png(size))
            self.stdout.write(f'생성: {path}')

        self.stdout.write(self.style.SUCCESS('아이콘 생성 완료'))
