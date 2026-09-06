import hashlib
import sys


def hash_file(file_path):
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        while chunk := file.read(8192):
            sha256.update(chunk)

    return sha256.hexdigest()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python hash_image.py <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]

    file_hash = hash_file(image_path)

    print("SHA-256:")
    print(file_hash)