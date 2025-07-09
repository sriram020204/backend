# eligibility_extractor.py
import re
import os
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult, AnalyzeDocumentRequest
from dotenv import load_dotenv
load_dotenv()
endpoint = os.getenv("AZURE_DOC_INTEL_ENDPOINT")
key = os.getenv("AZURE_DOC_INTEL_KEY")
if not key or not isinstance(key, str):
    raise ValueError("AZURE_DOC_INTEL_KEY is not set or not a string")
patterns = [  # same as yours
            r"eligibility criteria",
            r"eligibility requirements",
            r"eligibility conditions",
            r"eligibility standards",
            r"eligibility rules",
            r"eligibility qualifications",
            r"eligibility for participation",
            r"eligibility for tender",
            r"eligibility and pre-qualification",
            r"eligibility & prequalification",
            r"eligibility/prequalification",
            r"qualification criteria",
            r"qualification requirements",
            r"qualification standards",
            r"qualification rules",
            r"qualification and experience",
            r"minimum eligibility",
            r"minimum qualification",
            r"minimum eligibility requirements",
            r"minimum qualification criteria",
            r"pre-qualification criteria",
            r"prequalification requirements",
            r"pre-qualification standards",
            r"pre-qualification conditions",
            r"prequalification process",
            r"pre-qualification evaluation",
            r"prequalification of bidders",
            r"prequalification requirements",
            r"prequalification of suppliers",
            r"conditions of participation",
            r"participation criteria",
            r"participation requirements",
            r"tender participation eligibility",
            r"bidder eligibility",
            r"bidder qualification",
            r"bidder pre-qualification",
            r"submission requirements",
            r"bid submission eligibility",
            r"bidder eligibility criteria",
            r"screening criteria",
            r"eligibility and qualification criteria for participation in the tender",
            r"screening of bidders",
            r"evaluation criteria",
            r"evaluation of qualification",
            r"selection criteria",
            r"selection requirements",
            r"selection procedure",
            r"assessment criteria",
            r"compliance requirements",
            r"qualification and compliance",
            r"experience and qualifications",
            r"technical eligibility",
            r"financial eligibility",
            r"legal eligibility",
            r"vendor eligibility",
            r"supplier eligibility",
            r"contractor eligibility",
            r"applicant eligibility",
            r"eligibility of tenderers",
            r"eligibility of bidders",
            r"bidding eligibility",
            r"eligibility & pre-qualification",
            r"eligibility/prequalification",
            r"pre-qual & eligibility",
            r"eligibility & qualification",
            r"eligibility/qualification criteria",
            r"eligibility",
            r"qualification",
            r"pre-qualification",
            r"prequalification",
            r"pre qualification",
            r"pre-qualifications",
            r"prequalifications",
            r"pre qualifications"
        ]

def is_eligibility_heading(text):
    for pat in patterns:
        if re.search(pat, text, re.IGNORECASE):
            return True
    return False

def extract_eligibility_text_from_url(formUrl: str) -> str:
    client = DocumentIntelligenceClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(key)
    )
    poller = client.begin_analyze_document(
        model_id="prebuilt-layout",
        body=AnalyzeDocumentRequest(url_source=formUrl)
    )
    result: AnalyzeResult = poller.result()
    paragraphs = result.paragraphs or []
    headings = [(i, p) for i, p in enumerate(paragraphs) if p.role in ("title", "sectionHeading")]

    for idx, (para_idx, para) in enumerate(headings):
        if is_eligibility_heading(para.content):
            start_idx = para_idx + 1
            end_idx = headings[idx + 1][0] if idx + 1 < len(headings) else len(paragraphs)
            section_text = "\n".join(p.content.strip() for p in paragraphs[start_idx:end_idx])
            return section_text

    for i, p in enumerate(paragraphs):
        if is_eligibility_heading(p.content):
            next_heading = next((h[0] for h in headings if h[0] > i), len(paragraphs))
            section_text = "\n".join(p.content.strip() for p in paragraphs[i + 1:next_heading])
            return section_text

    return ""
