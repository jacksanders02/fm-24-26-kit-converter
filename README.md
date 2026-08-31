# FM24-26 Kit Converter

A small desktop tool that converts Football Manager 2024 3D kit textures to
the UV layout used by Football Manager 2026, using a precomputed UV lookup
map.

Original conversion approach provided by roundel0 on the Sortitoutsi forums:
[Transferring 3D outfits from FM24 to FM26 in Photoshop](https://sortitoutsi.net/content/74713/transferring-3d-outfits-from-fm24-to-fm26-in-photoshop?page=3#comment_854826).

## How it works

FM24 and FM26 use different UV layouts for 3D kit textures. This tool remaps
each pixel of an FM24 kit texture to its corresponding position in the FM26
layout, using a lookup EXR image (`src/resources/fm24_to_fm26_lookup.exr`)
where the red and green channels encode the source U/V coordinates for each
destination pixel.

For each FM24 kit image:
1. The image is resized to match the resolution of the lookup map, if needed.
2. Each output pixel is sampled from the source image using the U/V
   coordinates stored in the lookup map.
3. The remapped image is saved as an FM26-compatible kit texture.

## Usage

### Windows executable

Download the latest `convert.exe` from the [Releases](../../releases) page
and run it. A window will prompt you to select a folder containing your FM24
3D kits — the tool scans it recursively for `.png` files. Converted kits are
written to an `output` folder created next to the executable, preserving the
original folder structure.

### Running from source

Requires Python (see [`.python-version`](.python-version) for the version
used in CI).

```bash
pip install -r requirements.txt
python src/convert.py
```

Command-line flags:

| Flag | Description |
| --- | --- |
| `-v`, `--verbose` | Enable info-level logging |
| `-d`, `--debug` | Enable debug-level logging |

## Building the executable

The Windows executable is built with [PyInstaller](https://pyinstaller.org/)
using the provided spec file:

```bash
pip install -r requirements.txt pyinstaller
pyinstaller convert.spec
```

The built executable is output to `dist/convert.exe`.

## Development

Linting is done with `pylint`:

```bash
pip install -r requirements.txt
pylint src
```

CI runs linting and a Windows build on every pull request and push to
`main`. Releases are published via a manually triggered workflow that
builds the executable and tags a new version.

## Project structure

```
src/
├── convert.py                       # Main entrypoint / conversion logic
└── resources/
    └── fm24_to_fm26_lookup.exr      # FM24 -> FM26 UV lookup map
convert.spec                         # PyInstaller build spec
```
