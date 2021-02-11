#!/usr/bin/env python3
import json
import pathlib
import os
from barcode import EAN8
from barcode.writer import ImageWriter
from fpdf import FPDF
from collections import defaultdict

# BASE_FP = "/home/pi/Dropbox/Music"
BASE_FP = "/home/bsaund/Dropbox/Music/"
CONFIG_FILENAME = ".barcode_config"
MUSIC_EXTENSIONS = [".mp3", ".m4a"]
ART_EXTENSIONS = [".jpg", ".png"]
START_ID = 100


def load_config_file():
    fp = pathlib.Path(BASE_FP) / CONFIG_FILENAME
    if not fp.exists():
        return {}
    with fp.open() as f:
        cfg = json.load(f)
    return {int(k): v for k, v in cfg.items()}


def save_config_file(config: dict):
    with (pathlib.Path(BASE_FP) / CONFIG_FILENAME).open('w') as f:
        json.dump(config, f)


def glob_music_files(path):
    return [f for f in pathlib.Path(path).glob('*') if f.suffix in MUSIC_EXTENSIONS]


def generate_config_file():
    cf = load_config_file()
    existing_dirs = set(cf.values())
    new_id = START_ID
    dirs = sorted([f[0] for f in os.walk(BASE_FP)])
    added_configs = 0
    for d in dirs:
        rel_dir = pathlib.Path(d).relative_to(BASE_FP).as_posix()
        if rel_dir in existing_dirs:
            continue
        if not glob_music_files(d):
            continue
        while new_id in cf.keys():
            new_id += 1
        cf[new_id] = rel_dir
        added_configs += 1

    print(f"Added {added_configs} more folders")
    save_config_file(cf)


def generate_barcodes():
    cf = load_config_file()
    fp = pathlib.Path(BASE_FP) / 'Barcodes'
    if not fp.exists():
        fp.mkdir()
    for k, v in sorted(cf.items()):
        rel_fp = pathlib.Path(v)
        image_fp = (fp / rel_fp)
        if not image_fp.exists():
            image_fp.mkdir(parents=True)
        image_fp = image_fp.as_posix()
        EAN8(f'{int(k):07}', writer=ImageWriter()).save(image_fp)


class PDF(FPDF):
    def __init__(self):
        super().__init__()
        self.section_name = ""

    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        # Arial italic 8
        self.set_font('Arial', 'I', 8)
        self.set_text_color(90)
        self.cell(0, 10, f'Page {self.page_no()}: {self.section_name}', 0, 0, 'C')

    def header(self):
        # self.text()
        # pass
        prev_y = self.get_y()
        self.set_y(5)
        self.set_font('Arial', 'B', 16)
        alignment = 'R' if self.page_no() % 2 else 'L'

        self.cell(0, 10, self.section_name, border=0, ln=0, align=alignment)
        self.set_y(20)



    def add_section_title(self, title):
        self.section_name = ""
        self.add_page()
        if self.page_no() % 2 == 0:
            self.add_page()
        self.set_font('Arial', 'B', 60)
        # Background color
        # self.set_fill_color(200, 220, 255)
        # Title
        self.ln(50)
        self.cell(0, 6, title, 0, 1, 'C')
        # Line break
        self.ln(50)
        self.section_name = title

    def add_section_barcodes(self, folders):
        fp = pathlib.Path(BASE_FP) / 'Barcodes'
        self.set_font('Arial', '', 12)
        for folder in folders:
            if self.get_y() > 250:
                self.add_page()
                
            rel_fp = pathlib.Path(folder)
            barcode = (fp / rel_fp).as_posix()
            clean_rel_fp = pathlib.Path(*rel_fp.parts[1:-1]).as_posix().encode('ascii', errors='ignore').decode()
            clean_name = rel_fp.parts[-1].encode('ascii', errors='ignore').decode()
            self.set_font('Arial', '', 12)
            self.cell(30, 5, clean_rel_fp.replace('/', '  /  '))
            self.ln()
            self.set_font('Arial', 'B', 12)
            self.cell(60, 5, clean_name)
            self.ln()
            img_y = self.get_y()
            self.image(barcode + '.png', w=60, h=15)

            album_cover_fps = [fp.as_posix() for fp in (pathlib.Path(BASE_FP) / folder).glob('[!._]*') if
                               fp.suffix in ART_EXTENSIONS]
            if album_cover_fps:
                selected_fp = sorted(album_cover_fps)[0]
                self.image(selected_fp, x=100, y=img_y - 5, h=25)
                cover_size = pathlib.Path(selected_fp).stat().st_size
                # print(f"Adding album cover for {folder}: size: {cover_size/100000} MB")
                if cover_size/1000000 > 0.3:
                    print(f"Cover size for {selected_fp} is over 300KB")

            self.ln(8)


    def add_section(self, folders):
        self.add_section_title(pathlib.Path(list(folders)[0]).parts[0])
        self.add_section_barcodes(folders)

    def add_all_playlists(self, folders):
        def separate_into_categories(folders_):
            c = defaultdict(lambda: [])
            for f in folders_:
                path = pathlib.Path(f)
                c[path.parts[0]].append(f)
            return c

        for cat, folders_ in sorted(separate_into_categories(folders).items()):
            self.add_section(sorted(folders_))


def generate_pdf():
    cf = load_config_file()
    fp = pathlib.Path(BASE_FP) / 'Barcodes'
    if not fp.exists():
        fp.mkdir()

    pdf = PDF()
    pdf.add_all_playlists(cf.values())
    print('Writing to file')
    pdf.output((pathlib.Path(BASE_FP) / 'directory.pdf').as_posix(), "F")


if __name__ == "__main__":
    generate_config_file()
    generate_barcodes()
    generate_pdf()
