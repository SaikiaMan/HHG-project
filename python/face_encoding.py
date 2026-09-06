import cv2
from insightface.app import FaceAnalysis
from face_match import cosine_similarity


def load_face_model():
    app = FaceAnalysis(
        name="buffalo_l",
        providers=["CPUExecutionProvider"]
    )

    app.prepare(
        ctx_id=0,
        det_size=(640, 640)
    )

    return app


def encode_faces(image_path, app):
    image = cv2.imread(image_path)

    if image is None:
        raise ValueError(f"Could not load image: {image_path}")

    return app.get(image)


def get_first_embedding(image_path, app):
    faces = encode_faces(image_path, app)

    if len(faces) == 0:
        raise ValueError(f"No face found in {image_path}")

    return faces[0].embedding


if __name__ == "__main__":

    image1 = "python/test.jpg"
    image2 = "python/test2.jpg"

    print("Loading face recognition model...")

    app = load_face_model()

    print(f"Encoding: {image1}")
    embedding1 = get_first_embedding(image1, app)

    print(f"Encoding: {image2}")
    embedding2 = get_first_embedding(image2, app)

    similarity = cosine_similarity(
        embedding1,
        embedding2
    )

    print("\n--- Comparison ---")
    print(f"Image 1: {image1}")
    print(f"Image 2: {image2}")
    print(f"Cosine similarity: {similarity:.4f}")