#!/usr/bin/env python3
import json
import pathlib
import os
from barcode import EAN8
from barcode.writer import ImageWriter
from fpdf import FPDF

# BASE_FP = "/home/pi/Music"
BASE_FP = "/home/bsaund/Music/Sorted Music"
CONFIG_FILENAME = ".barcode_config"
START_ID = 100


def load_config_file():
    fp = pathlib.Path(BASE_FP) / CONFIG_FILENAME
    if not fp.exists():
        return {}
    with fp.open() as f:
        return json.load(f)


def save_config_file(config: dict):
    with (pathlib.Path(BASE_FP) / CONFIG_FILENAME).open('w') as f:
        json.dump(config, f)


def generate_config_file():
    cf = load_config_file()
    existing_dirs = set(cf.values())
    new_id = START_ID
    dirs = sorted([f[0] for f in os.walk(BASE_FP)])
    for d in dirs:
        rel_dir = pathlib.Path(d).relative_to(BASE_FP).as_posix()
        if rel_dir in existing_dirs:
            continue
        if not list(pathlib.Path(d).glob('*.mp3')):
            continue
        while new_id in cf.keys():
            new_id += 1
        cf[new_id] = rel_dir

    save_config_file(cf)


def generate_barcodes():
    cf = load_config_file()
    fp = pathlib.Path(BASE_FP) / 'Barcodes'
    if not fp.exists():
        fp.mkdir()

    pdf = FPDF()
    pdf.set_font('Arial', '', 12)
    pdf.add_page()
    for k, v in sorted(cf.items()):
        rel_fp = pathlib.Path(v)
        image_fp = (fp / rel_fp)
        if not image_fp.exists():
            image_fp.mkdir(parents=True)
        image_fp = image_fp.as_posix()
        EAN8(f'{int(k):07}', writer=ImageWriter()).save(image_fp)
        img = EAN8(f'{int(k):07}')
        # pdf.add_page()
        clean_rel_fp = rel_fp.as_posix().encode('ascii', errors='ignore').decode()
        pdf.cell(30, 5, clean_rel_fp)
        pdf.ln()
        pdf.cell(60, 5, pathlib.Path(clean_rel_fp).parts[-1])
        pdf.ln()
        pdf.image(image_fp + '.png', w=60, h=20)
    pdf.output((fp / 'directory.pdf').as_posix(), "F")




if __name__ == "__main__":
    generate_config_file()
    generate_barcodes()

