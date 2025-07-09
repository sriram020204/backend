from sentence_transformers import SentenceTransformer, util
import numpy as np

# Load lightweight model for field mapping
model = SentenceTransformer('all-MiniLM-L6-v2')

def map_fields_by_embedding(gemini_fields: list, backend_fields: list, backend_data: dict, threshold: float = 0.5):
    """
    Maps template fields to backend data fields using embedding similarity.

    Parameters:
    - gemini_fields: List of field dicts from template schema
    - backend_fields: List of backend keys (from tender data)
    - backend_data: Full backend dict (tender document)
    - threshold: Minimum similarity required to map

    Returns: dict with mapped values
    """
    mapped_data = {}

    if not backend_fields:
        print("⚠️ No backend fields available for mapping")
        return mapped_data

    # Embed backend fields
    try:
        backend_embeddings = model.encode(backend_fields, convert_to_tensor=True)
    except Exception as e:
        print(f"❌ Error encoding backend fields: {e}")
        return mapped_data

    for field in gemini_fields:
        field_id = field['id']
        label = field.get('label', field_id)

        try:
            # Embed template field label/id
            query_embedding = model.encode(label, convert_to_tensor=True)

            # Compute cosine similarities
            cosine_scores = util.cos_sim(query_embedding, backend_embeddings)[0].cpu().numpy()
            max_score_idx = np.argmax(cosine_scores)
            max_score = cosine_scores[max_score_idx]

            if max_score >= threshold:
                matched_backend_field = backend_fields[max_score_idx]
                mapped_value = backend_data.get(matched_backend_field, "")
                
                # Convert value to string if it's not already
                if mapped_value is not None:
                    mapped_data[field_id] = str(mapped_value)
                    print(f"✅ {label} -> {matched_backend_field} (score: {max_score:.2f}) = '{mapped_value}'")
                else:
                    mapped_data[field_id] = ""
                    print(f"⚠️ {label} -> {matched_backend_field} (score: {max_score:.2f}) = NULL")
            else:
                mapped_data[field_id] = ""  # leave empty if no good match
                print(f"❌ No good match for {label} (max score: {max_score:.2f})")

        except Exception as e:
            print(f"❌ Error processing field {label}: {e}")
            mapped_data[field_id] = ""

    return mapped_data


def get_mapping_confidence(similarity_score: float) -> str:
    """
    Convert similarity score to confidence level
    """
    if similarity_score >= 0.8:
        return "high"
    elif similarity_score >= 0.6:
        return "medium"
    elif similarity_score >= 0.4:
        return "low"
    else:
        return "very_low"


def map_fields_with_confidence(gemini_fields: list, backend_fields: list, backend_data: dict, threshold: float = 0.5):
    """
    Enhanced mapping function that returns confidence levels
    """
    mapped_data = {}
    mapping_details = {}

    if not backend_fields:
        return mapped_data, mapping_details

    try:
        backend_embeddings = model.encode(backend_fields, convert_to_tensor=True)
    except Exception as e:
        print(f"❌ Error encoding backend fields: {e}")
        return mapped_data, mapping_details

    for field in gemini_fields:
        field_id = field['id']
        label = field.get('label', field_id)

        try:
            query_embedding = model.encode(label, convert_to_tensor=True)
            cosine_scores = util.cos_sim(query_embedding, backend_embeddings)[0].cpu().numpy()
            max_score_idx = np.argmax(cosine_scores)
            max_score = cosine_scores[max_score_idx]

            if max_score >= threshold:
                matched_backend_field = backend_fields[max_score_idx]
                mapped_value = backend_data.get(matched_backend_field, "")
                
                mapped_data[field_id] = str(mapped_value) if mapped_value is not None else ""
                mapping_details[field_id] = {
                    'matched_field': matched_backend_field,
                    'similarity_score': float(max_score),
                    'confidence': get_mapping_confidence(max_score),
                    'value': mapped_data[field_id]
                }
            else:
                mapped_data[field_id] = ""
                mapping_details[field_id] = {
                    'matched_field': None,
                    'similarity_score': float(max_score),
                    'confidence': 'none',
                    'value': ""
                }

        except Exception as e:
            print(f"❌ Error processing field {label}: {e}")
            mapped_data[field_id] = ""
            mapping_details[field_id] = {
                'matched_field': None,
                'similarity_score': 0.0,
                'confidence': 'error',
                'value': ""
            }

    return mapped_data, mapping_details