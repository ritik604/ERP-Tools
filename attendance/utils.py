import math

FACE_MATCH_THRESHOLD = 0.55  # Standard threshold for @vladmandic/face-api 128-D descriptors

def calculate_face_distance(live_vector, stored_vector):
    """
    Calculates the Euclidean distance between two 128-dimensional facial vectors.
    A lower distance indicates higher facial similarity.
    """
    if not live_vector or not stored_vector:
        return 1.0
    
    if len(live_vector) != len(stored_vector):
        return 1.0
        
    try:
        sum_sq = sum((float(a) - float(b)) ** 2 for a, b in zip(live_vector, stored_vector))
        return math.sqrt(sum_sq)
    except (ValueError, TypeError):
        return 1.0

def verify_face_match(live_vector, stored_vector, threshold=FACE_MATCH_THRESHOLD):
    """
    Compares live embedding against stored profile.
    Returns (is_match: bool, distance: float, message: str)
    """
    if not stored_vector:
        return False, 1.0, "Worker has not enrolled a face profile yet."
        
    if not live_vector:
        return False, 1.0, "No face embedding received from scanner."

    dist = calculate_face_distance(live_vector, stored_vector)
    
    if dist <= 0.45:
        return True, dist, "Face verified with high confidence."
    elif dist <= threshold:
        return True, dist, "Face verified successfully."
    else:
        return False, dist, f"Face mismatch. Similarity score {dist:.2f} exceeds threshold {threshold}."

def average_embeddings(embeddings_list):
    """
    Averages multiple 128-D vectors captured during enrollment to improve accuracy.
    """
    if not embeddings_list:
        return None
        
    valid_embeddings = [e for e in embeddings_list if e and len(e) == 128]
    if not valid_embeddings:
        return None
        
    n = len(valid_embeddings)
    dim = 128
    avg = [0.0] * dim
    
    for emb in valid_embeddings:
        for i in range(dim):
            avg[i] += float(emb[i])
            
    avg = [round(val / n, 6) for val in avg]
    return avg
