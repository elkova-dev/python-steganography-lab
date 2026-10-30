# Python Steganography Lab

A university-inspired educational Python experiment showing how to inspect image metadata, append trailing data to PNG files, hide a text message using **least-significant-bit (LSB) steganography**, and test whether the hidden information survives JPEG compression.

## Features

- Read and display EXIF/GPS metadata when available.
- Append raw bytes after the PNG end marker as a basic file-format demonstration.
- Embed and extract UTF-8 messages in PNG RGB channel bits.
- Compare changed pixels and least-significant-bit distributions.
- Demonstrate why lossy JPEG recompression typically destroys simple LSB payloads.
- Save the generated images and a text report in `output/`.

## Requirements

Python 3.10+ and Pillow.

## Setup and run

```bash
python -m pip install -r requirements.txt
python steganography.py
python -m unittest discover -s tests -v
```

`assets/sample_photo.jpg` is the included example input. The script writes results to `output/`, which is intentionally excluded from Git. You can replace the sample with a photograph you have permission to use.

## How LSB embedding works

Each byte of a UTF-8 message is converted into 8 bits. The script stores those bits in the last bit of successive RGB channel values, producing at most a one-unit change per affected channel.

The educational format uses a four-byte `STEG` signature and three null bytes as an end-of-message marker, with an extraction limit of 10,000 bytes including framing. It is **not** encryption, authentication, or a secure covert messaging system. Treat this as a demonstration of a file manipulation technique, not as a security product.

## Suggested learning exercises

- Compare file sizes before and after hiding text.
- Experiment with short and long payloads.
- Examine what changes when converting the image to JPEG.
- Inspect the `output/results.txt` report.

## Project history

Originally a course exercise named `Steganografia`, reorganized with English names, isolated generated results, basic error handling and automated tests.

## License

MIT. See [LICENSE](LICENSE). Confirm you have the rights to redistribute any image you add to `assets/`.
