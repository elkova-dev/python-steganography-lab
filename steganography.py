"""Educational experiments with EXIF, trailing bytes, and LSB steganography.

Run `python steganography.py` to generate a report in output/.
"""

from pathlib import Path

from PIL import ExifTags, Image

PROJECT_DIR = Path(__file__).resolve().parent
SAMPLE_PHOTO = PROJECT_DIR / "assets" / "sample_photo.jpg"
OUTPUT_DIR = PROJECT_DIR / "output"
SECRET_MESSAGE = "Meeting at 18:00 by the main gate"
APPENDED_MESSAGE = b"SECRET MESSAGE: meeting at 18:00"
MAGIC_PREFIX = b"STEG"
END_MARKER = b"\x00\x00\x00"
MAX_EXTRACTED_BYTES = 10_000


def file_size(path: Path) -> int:
    return path.stat().st_size


def describe_exif(path: Path) -> list[str]:
    """Return a human-readable summary of the file's available EXIF metadata."""
    lines = [f"EXIF metadata for {path.name}:"]
    with Image.open(path) as image:
        exif = image.getexif()
        tags = dict(exif.items())
        tags.update(exif.get_ifd(0x8769))
        if not tags:
            lines.append("  No EXIF tags found.")
        for tag_id, value in sorted(tags.items()):
            name = ExifTags.TAGS.get(tag_id, str(tag_id))
            if name not in ("GPSInfo", "ExifOffset", "ExifIFDPointer"):
                lines.append(f"  {name}: {str(value)[:150]}")

        gps = exif.get_ifd(0x8825)
        if gps:
            lines.append("  GPS data:")
            for tag_id, value in sorted(gps.items()):
                name = ExifTags.GPSTAGS.get(tag_id, str(tag_id))
                lines.append(f"    {name}: {value}")
        else:
            lines.append("  No GPS data found.")
    return lines


def hide_message(source: Path, destination: Path, message: str) -> None:
    """Embed UTF-8 text in the least-significant bit of successive RGB bytes.

    This simple teaching format uses three null bytes as a terminator, so the
    message may not contain that delimiter. It does not encrypt the data.
    """
    raw_message = message.encode("utf-8")
    if END_MARKER in raw_message:
        raise ValueError("Message contains the reserved end marker.")

    with Image.open(source) as image:
        rgb = image.convert("RGB")
        pixels = bytearray(rgb.tobytes())
        dimensions = rgb.size

    payload = MAGIC_PREFIX + raw_message + END_MARKER
    if len(payload) > MAX_EXTRACTED_BYTES:
        raise ValueError("Message exceeds the educational extraction limit.")
    if len(payload) * 8 > len(pixels):
        raise ValueError("Message is too long for the selected image.")

    position = 0
    for byte in payload:
        for shift in range(7, -1, -1):
            pixels[position] = (pixels[position] & 0xFE) | ((byte >> shift) & 1)
            position += 1

    destination.parent.mkdir(parents=True, exist_ok=True)
    Image.frombytes("RGB", dimensions, bytes(pixels)).save(destination, format="PNG")


def extract_message(path: Path) -> str | None:
    """Return the embedded message, or None if it cannot be recovered."""
    with Image.open(path) as image:
        pixels = image.convert("RGB").tobytes()

    limit = min(len(pixels), MAX_EXTRACTED_BYTES * 8)
    recovered = bytearray()
    byte = 0
    bit_count = 0
    for value in pixels[:limit]:
        byte = (byte << 1) | (value & 1)
        bit_count += 1
        if bit_count == 8:
            recovered.append(byte)
            if len(recovered) == len(MAGIC_PREFIX) and recovered != MAGIC_PREFIX:
                return None
            if len(recovered) > len(MAGIC_PREFIX) and recovered.endswith(END_MARKER):
                try:
                    return recovered[len(MAGIC_PREFIX):-len(END_MARKER)].decode("utf-8")
                except UnicodeDecodeError:
                    return None
            byte = 0
            bit_count = 0
    return None


def lsb_one_ratio(path: Path) -> float:
    with Image.open(path) as image:
        data = image.convert("RGB").tobytes()[:600_000]
    return sum(value & 1 for value in data) / len(data)


def compare_images(first: Path, second: Path) -> tuple[int, int, int]:
    with Image.open(first) as image:
        a = image.convert("RGB")
        size_a = a.size
        first_bytes = a.tobytes()
    with Image.open(second) as image:
        b = image.convert("RGB")
        size_b = b.size
        second_bytes = b.tobytes()

    if size_a != size_b:
        raise ValueError("Images must have the same dimensions.")

    changed = sum(
        first_bytes[index:index + 3] != second_bytes[index:index + 3]
        for index in range(0, len(first_bytes), 3)
    )
    largest_difference = max(
        abs(first_value - second_value)
        for first_value, second_value in zip(first_bytes, second_bytes)
    )
    return changed, largest_difference, len(first_bytes) // 3


def main() -> None:
    if not SAMPLE_PHOTO.is_file():
        raise FileNotFoundError(f"Missing example image: {SAMPLE_PHOTO}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report: list[str] = []

    def log(text: str = "") -> None:
        print(text)
        report.append(text)

    log("1. Prepare a lossless PNG carrier")
    carrier = OUTPUT_DIR / "carrier.png"
    with Image.open(SAMPLE_PHOTO) as image:
        image.convert("RGB").save(carrier)
    log(f"Created {carrier.name}")
    log()

    log("2. Inspect image metadata")
    for line in describe_exif(SAMPLE_PHOTO):
        log(line)
    resized_photo = OUTPUT_DIR / "sample_photo_small.jpg"
    with Image.open(SAMPLE_PHOTO) as image:
        smaller = image.copy()
    smaller.thumbnail((800, 800))
    smaller.convert("RGB").save(resized_photo, quality=90)
    for line in describe_exif(resized_photo):
        log(line)
    log()

    log("3. Append a message after the PNG end marker")
    appended = OUTPUT_DIR / "appended_bytes.png"
    appended.write_bytes(carrier.read_bytes() + APPENDED_MESSAGE)
    log(f"{carrier.name}: {file_size(carrier)} bytes")
    log(f"{appended.name}: {file_size(appended)} bytes")
    log(f"Difference: {file_size(appended) - file_size(carrier)} bytes")
    log(f"Trailing bytes: {appended.read_bytes()[-60:]!r}")
    log()

    log("4. Hide and recover a message using LSB")
    stego = OUTPUT_DIR / "stego.png"
    hide_message(carrier, stego, SECRET_MESSAGE)
    extracted = extract_message(stego)
    log(f"Recovered message: {extracted!r}")
    log(f"Matches original: {extracted == SECRET_MESSAGE}")
    with Image.open(carrier) as image:
        width, height = image.size
    log(f"Dimensions: {width} x {height} pixels")
    log(f"Physical byte capacity (including 7-byte framing): {(width * height * 3) // 8} bytes")
    log(f"{carrier.name}: {file_size(carrier)} bytes")
    log(f"{stego.name}: {file_size(stego)} bytes")
    log()

    log("5. Compare changed pixels and LSB ratios")
    changed, maximum_delta, total = compare_images(carrier, stego)
    log(f"Changed pixels: {changed} of {total}")
    log(f"Maximum channel difference: {maximum_delta}")
    long_message = OUTPUT_DIR / "stego_long.png"
    hide_message(carrier, long_message, SECRET_MESSAGE * 100)
    log(f"LSB one ratio, original: {lsb_one_ratio(carrier):.4f}")
    log(f"LSB one ratio, short message: {lsb_one_ratio(stego):.4f}")
    log(f"LSB one ratio, long message: {lsb_one_ratio(long_message):.4f}")
    log()

    log("6. Test JPEG compression")
    jpeg = OUTPUT_DIR / "stego.jpg"
    roundtrip = OUTPUT_DIR / "stego_roundtrip.png"
    with Image.open(stego) as image:
        image.save(jpeg, quality=90)
    with Image.open(jpeg) as image:
        image.save(roundtrip)
    extracted_after_jpeg = extract_message(roundtrip)
    log(f"Recovered after JPEG: {extracted_after_jpeg!r}")
    log(f"Message survived: {extracted_after_jpeg == SECRET_MESSAGE}")

    (OUTPUT_DIR / "results.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\nDone. See output/results.txt for the experiment report.")


if __name__ == "__main__":
    main()
