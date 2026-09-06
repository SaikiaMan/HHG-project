import cv2
import sys


def detect_face(image_path):

    print("Loading image...")

    image = cv2.imread(image_path)

    if image is None:
        print("ERROR: Could not load image.")
        return

    print("Image loaded successfully.")

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades +
        "haarcascade_frontalface_default.xml"
    )

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(30, 30)
    )

    print(f"Faces detected: {len(faces)}")

    for (x, y, w, h) in faces:
        cv2.rectangle(
            image,
            (x, y),
            (x + w, y + h),
            (0, 255, 0),
            2
        )

    cv2.imshow("Face Detection", image)

    print("Press any key on the image window to close.")

    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":

    if len(sys.argv) != 2:
        print("Usage: python face_detection.py <image>")
        sys.exit(1)

    detect_face(sys.argv[1])