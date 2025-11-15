import cv2
import mediapipe as mp
import numpy as np

mp_face_mesh = mp.solutions.face_mesh

# points for face alignment
LEFT_EYE_IDX = 33
RIGHT_EYE_IDX = 263
NOSE_TIP_IDX = 1

def get_face_mesh(image):
    with mp_face_mesh.FaceMesh(static_image_mode=True) as face_mesh:
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)
        if not results.multi_face_landmarks:
            return None
        return results.multi_face_landmarks[0]

def get_point(landmarks, idx, image_shape):
    h, w = image_shape[:2]
    lm = landmarks.landmark[idx]
    return np.array([int(lm.x * w), int(lm.y * h)], dtype=np.int32)

def merge_faces(source_path, target_path, result_path):
    src = cv2.imread(source_path)
    tgt = cv2.imread(target_path)

    src_lm = get_face_mesh(src)
    tgt_lm = get_face_mesh(tgt)

    if src_lm is None or tgt_lm is None:
        raise ValueError("لم يتم العثور على وجه في إحدى الصورتين.")

    # alignment points
    src_pts = np.array([
        get_point(src_lm, LEFT_EYE_IDX, src.shape),
        get_point(src_lm, RIGHT_EYE_IDX, src.shape),
        get_point(src_lm, NOSE_TIP_IDX, src.shape)
    ], dtype=np.float32)

    tgt_pts = np.array([
        get_point(tgt_lm, LEFT_EYE_IDX, tgt.shape),
        get_point(tgt_lm, RIGHT_EYE_IDX, tgt.shape),
        get_point(tgt_lm, NOSE_TIP_IDX, tgt.shape)
    ], dtype=np.float32)

    # affine transform
    M = cv2.getAffineTransform(src_pts, tgt_pts)
    warped_src = cv2.warpAffine(src, M, (tgt.shape[1], tgt.shape[0]))

    # create mask using face mesh convex hull
    mask_points = []
    for lm in tgt_lm.landmark:
        x = int(lm.x * tgt.shape[1])
        y = int(lm.y * tgt.shape[0])
        mask_points.append([x, y])

    mask_points = np.array(mask_points, dtype=np.int32)
    hull = cv2.convexHull(mask_points)

    mask = np.zeros(tgt.shape[:2], dtype=np.uint8)
    cv2.fillConvexPoly(mask, hull, 255)

    # color correction (simple)
    warped_src = cv2.blur(warped_src, (15, 15))

    # final seamless cloning
    output = cv2.seamlessClone(
        warped_src,
        tgt,
        mask,
        tuple(np.mean(hull, axis=0).astype(int)),
        cv2.NORMAL_CLONE
    )

    cv2.imwrite(result_path, output)
    return result_path
