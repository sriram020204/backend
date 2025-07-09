import pdfplumber
import google.generativeai as genai

class PDFSummaryService:
    def __init__(self, api_key):
        self.api_key = api_key
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    def extract_text_from_pdf(self, pdf_path):
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text

    def summarize_text(self, text):
        if not text.strip():
            return "No text found in the PDF."

        if len(text) > 15000:
            text = text[:15000]

        prompt = f"Summarize the following PDF content in concise bullet points:\n\n{text}"
        response = self.model.generate_content(prompt)
        return response.text

    def summarize_pdf(self, pdf_path):
        text = self.extract_text_from_pdf(pdf_path)
        return self.summarize_text(text)
