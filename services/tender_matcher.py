from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer("all-MiniLM-L6-v2")

def compute_embedding_similarity_list(required_list, provided_list, threshold=0.75):
    matched, missing = [], []
    for req in required_list:
        emb_req = model.encode(req, convert_to_tensor=True)
        found = False
        for prov in provided_list:
            emb_prov = model.encode(prov, convert_to_tensor=True)
            if util.cos_sim(emb_req, emb_prov).item() >= threshold:
                matched.append(req)
                found = True
                break
        if not found:
            missing.append(req)
    score = len(matched) / len(required_list) if required_list else 1.0
    return round(score, 2), matched, missing

def compute_tender_match_score(eligibility: dict, company: dict):
    score, total_weight = 0, 0
    field_scores, missing_fields = {}, {}

    # PAN check
    if eligibility.get("pan", {}).get("required"):
        s = 1 if company.get("pan") else 0
        field_scores["pan"] = s
        if s == 0:
            missing_fields["pan"] = "Missing PAN"
        score += s * 0.1
        total_weight += 0.1

    # GSTIN check
    if eligibility.get("gstin", {}).get("required"):
        s = 1 if company.get("gstin") else 0
        field_scores["gstin"] = s
        if s == 0:
            missing_fields["gstin"] = "Missing GSTIN"
        score += s * 0.1
        total_weight += 0.1

    # Experience check (safe null fallback)
    required_exp = eligibility.get("experience", {}).get("minimum_years") or 0
    try:
        company_exp = int(company.get("prior_experience", "0").split()[0])
    except Exception:
        company_exp = 0
    s = 1 if company_exp >= required_exp else round(company_exp / required_exp, 2) if required_exp > 0 else 1
    field_scores["experience"] = s
    if s < 1:
        missing_fields["experience"] = f"Required {required_exp}, has {company_exp}"
    score += s * 0.2
    total_weight += 0.2

    # Documents similarity
    docs_score, _, miss = compute_embedding_similarity_list(
        eligibility.get("required_documents", []),
        company.get("documents_provided", [])
    )
    field_scores["documents"] = docs_score
    if miss:
        missing_fields["documents"] = miss
    score += docs_score * 0.2
    total_weight += 0.2

    # Certifications similarity
    certs_score, _, miss = compute_embedding_similarity_list(
        eligibility.get("certifications", []),
        company.get("certifications_provided", [])
    )
    field_scores["certifications"] = certs_score
    if miss:
        missing_fields["certifications"] = miss
    score += certs_score * 0.2
    total_weight += 0.2

    # Other criteria (if present)
    other_text = " ".join(str(v) for v in eligibility.get("other_criteria", {}).values() if v)
    company_text = company.get("product_service_description", "")
    if other_text and company_text:
        sim = util.cos_sim(
            model.encode(other_text, convert_to_tensor=True),
            model.encode(company_text, convert_to_tensor=True)
        ).item()
        s = round(min(max(sim, 0), 1), 2)
        field_scores["other_criteria"] = s
        if s < 0.7:
            missing_fields["other_criteria"] = "Service description may not match"
        score += s * 0.2
        total_weight += 0.2

    # Final score calculation
    final_score = round((score / total_weight) * 100, 2) if total_weight else 0
    eligible = final_score >= 70 and not missing_fields
    print(final_score)
    return {
        "matching_score": final_score,
        "eligible": eligible,
        "field_scores": field_scores,
        "missing_fields": missing_fields
    }
