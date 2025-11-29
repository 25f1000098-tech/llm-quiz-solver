# data_handler.py
import requests
import pandas as pd
import pdfplumber
import io

def download_and_read_data(url):
    """Downloads content from a URL and extracts text/data based on file type."""
    print(f"Downloading data from: {url}")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        content_type = response.headers.get('Content-Type', '').lower()
        content = response.content

        if 'application/pdf' in content_type or url.lower().endswith('.pdf'):
            return _read_pdf(content)
        elif 'text/csv' in content_type or url.lower().endswith('.csv'):
            return _read_csv(content)
        else:
            # Treat everything else as plain text
            return content.decode('utf-8', errors='ignore')

    except requests.exceptions.RequestException as e:
        return f"Error downloading data: {e}"

def _read_pdf(content):
    """Extracts text from all pages of a PDF."""
    try:
        text = ""
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                text += f"\n--- PAGE {page.page_number} ---\n"
                # Use extract_text to get page content
                text += page.extract_text() or ""
        return text
    except Exception as e:
        return f"Error reading PDF: {e}"

def _read_csv(content):
    """Reads a CSV into a markdown string representation for the LLM."""
    try:
        df = pd.read_csv(io.StringIO(content.decode('utf-8')))
        # Markdown is a clear, readable format for LLMs
        return df.to_markdown(index=False)
    except Exception as e:
        return f"Error reading CSV: {e}"