import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import date

from google import genai

GEMINI_TIMEOUT_SECONDS = 45
# Prefer current models; fall back for older API projects (ING010A: Gemini 1.5 Flash family).
MODEL_CANDIDATES = ('gemini-2.0-flash', 'gemini-1.5-flash')


def format_gemini_error(exc):
    """Return a short, user-safe message for UI flashes."""
    msg = str(exc)
    upper = msg.upper()
    if 'CONSUMER_SUSPENDED' in upper or 'PERMISSION_DENIED' in upper or '403' in msg:
        return (
            'Your Gemini API key is invalid or suspended. '
            'Create a new key at Google AI Studio and update GEMINI_API_KEY in .env.'
        )
    if 'API_KEY_INVALID' in upper or 'INVALID API KEY' in upper:
        return 'GEMINI_API_KEY is invalid. Check the value in your .env file.'
    if 'timed out' in msg.lower():
        return 'Gemini API request timed out. Please try again.'
    if 'not configured' in msg.lower():
        return msg
    return 'Letter generation failed. Please try again.'


def generate_complaint_letter(complaint, complainant, agency):
    """Call Google Gemini to generate a formal environmental complaint letter."""
    api_key = os.getenv('GEMINI_API_KEY', '').strip()
    if not api_key or api_key == 'your_gemini_api_key_here':
        raise ValueError('GEMINI_API_KEY is not configured in .env')

    agency_name = agency.agency_name if agency else 'the Concerned Government Agency'
    agency_email = agency.contact_email if agency else 'N/A'
    incident_date = complaint.date_incident.strftime('%B %d, %Y')
    letter_date = date.today().strftime('%B %d, %Y')

    prompt = f"""You are a legal writing assistant for INGAT, a Philippine environmental complaint system.
Write a formal complaint letter that a community member can send to a government agency.

Use clear, professional English suitable for DENR, LLDA, or LGU offices in the Philippines.

COMPLAINANT:
- Full Name: {complainant.full_name}
- Email: {complainant.email}
- Contact Number: {complainant.contact_number}
- Barangay: {complainant.barangay}
- Municipality: {complainant.municipality}

COMPLAINT DETAILS:
- Violation Type: {complaint.violation_type}
- Date of Incident: {incident_date}
- Location (Barangay): {complaint.barangay}
- Location (Municipality): {complaint.municipality}
- Street Address (for reference only, do not exaggerate): {complaint.street_address}
- Description of Violation: {complaint.description}

ROUTED AGENCY:
- Agency Name: {agency_name}
- Agency Email: {agency_email}

FORMAT REQUIREMENTS:
1. Start with today's date on the first line: {letter_date}.
2. Address the letter to {agency_name}.
3. Include a clear RE: subject line mentioning the violation type and barangay.
4. Write a formal body describing the incident based ONLY on the facts provided.
5. End with a respectful closing and the complainant's name and contact details.
6. Do not invent facts, witnesses, or legal citations not implied by the description.
7. Keep the letter between 250 and 450 words.

Output only the letter text, no markdown code fences."""

    client = genai.Client(api_key=api_key)

    def _call_api():
        last_error = None
        for model_name in MODEL_CANDIDATES:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                if response and response.text:
                    return response.text.strip()
                last_error = ValueError('Gemini returned an empty response')
            except Exception as exc:
                last_error = exc
        if last_error:
            raise last_error
        raise ValueError('Gemini returned an empty response')

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_call_api)
        try:
            return future.result(timeout=GEMINI_TIMEOUT_SECONDS)
        except FuturesTimeoutError as exc:
            raise TimeoutError('Gemini API request timed out') from exc
