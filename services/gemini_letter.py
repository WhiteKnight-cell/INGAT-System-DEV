import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import date

GEMINI_TIMEOUT_SECONDS = 45
# Order matters: try working models first (1.5-flash is retired on many keys).
MODEL_CANDIDATES = ('gemini-2.5-flash', 'gemini-flash-latest', 'gemini-2.0-flash-lite')


def format_gemini_error(exc):
    """Return a short, user-safe message for UI flashes."""
    msg = str(exc)
    upper = msg.upper()
    if 'cannot import name' in msg.lower() or 'no module named' in msg.lower():
        return (
            'Gemini library is not installed. Run: pip install google-genai '
            '(or: pip install google-generativeai)'
        )
    if 'CONSUMER_SUSPENDED' in upper or 'PERMISSION_DENIED' in upper or '403' in msg:
        return (
            'Your Gemini API key is invalid or suspended. '
            'Create a new key at Google AI Studio and update GEMINI_API_KEY in .env.'
        )
    if 'API_KEY_INVALID' in upper or 'INVALID API KEY' in upper:
        return 'GEMINI_API_KEY is invalid. Check the value in your .env file.'
    if 'timed out' in msg.lower():
        return 'Gemini API request timed out. Please try again.'
    if '429' in msg or 'quota' in msg.lower() or 'rate limit' in msg.lower():
        return (
            'Gemini rate limit reached. Wait a minute and click Try Generate Letter Again.'
        )
    if '404' in msg or 'not found' in msg.lower():
        return 'Gemini model unavailable. Restart the app and try again.'
    if 'not configured' in msg.lower():
        return msg
    return 'Letter generation failed. Please try again.'


def build_fallback_complaint_letter(complaint, complainant, agency):
    """Build a formal letter locally when Gemini is not available."""
    from datetime import date

    agency_name = agency.agency_name if agency else 'the Concerned Government Agency'
    incident_date = complaint.date_incident.strftime('%B %d, %Y')
    letter_date = date.today().strftime('%B %d, %Y')

    return f"""{letter_date}

{agency_name}

RE: Environmental Complaint Regarding {complaint.violation_type} in {complaint.barangay}

Dear Sir/Madam:

I am writing to formally report an environmental concern involving {complaint.violation_type} in {complaint.barangay}, {complaint.municipality}. The incident was observed on {incident_date} at {complaint.street_address}.

Based on my report, the following details describe the concern:

{complaint.description}

I respectfully request your office to review this complaint and take the appropriate action according to your agency's procedures. This report is submitted in good faith to help protect the community and support proper handling of environmental violations.

Thank you for your attention to this matter.

Respectfully yours,

{complainant.full_name}
{complainant.email}
{complainant.contact_number}"""


def _build_prompt(complaint, complainant, agency):
    agency_name = agency.agency_name if agency else 'the Concerned Government Agency'
    agency_email = agency.contact_email if agency else 'N/A'
    incident_date = complaint.date_incident.strftime('%B %d, %Y')
    letter_date = date.today().strftime('%B %d, %Y')

    return f"""You are a legal writing assistant for INGAT, a Philippine environmental complaint system.
=======

import google.generativeai as genai

GEMINI_TIMEOUT_SECONDS = 45


def generate_complaint_letter(complaint, complainant, agency):

    api_key = os.getenv('GEMINI_API_KEY', '').strip()
    if not api_key or api_key == 'your_gemini_api_key_here':
        raise ValueError('GEMINI_API_KEY is not configured in .env')

    agency_name = agency.agency_name if agency else 'the Concerned Government Agency'
    agency_email = agency.contact_email if agency else 'N/A'
    incident_date = complaint.date_incident.strftime('%B %d, %Y')

    

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
=======
1. Start with today's date on the first line (use: {incident_date} as reference; letter date may be today).
>>>>>>> main
2. Address the letter to {agency_name}.
3. Include a clear RE: subject line mentioning the violation type and barangay.
4. Write a formal body describing the incident based ONLY on the facts provided.
5. End with a respectful closing and the complainant's name and contact details.
6. Do not invent facts, witnesses, or legal citations not implied by the description.
7. Keep the letter between 250 and 450 words.

Output only the letter text, no markdown code fences."""


def _call_gemini_new_sdk(api_key, prompt):
    from google import genai

    client = genai.Client(api_key=api_key)
    last_error = None
    for model_name in MODEL_CANDIDATES:
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            if response and response.text:
                return response.text.strip()
            last_error = ValueError('Gemini returned an empty response')
        except Exception as exc:
            last_error = exc
    if last_error:
        raise last_error
    raise ValueError('Gemini returned an empty response')


def _call_gemini_legacy_sdk(api_key, prompt):
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    last_error = None
    for model_name in MODEL_CANDIDATES:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text.strip()
            last_error = ValueError('Gemini returned an empty response')
        except Exception as exc:
            last_error = exc
    if last_error:
        raise last_error
    raise ValueError('Gemini returned an empty response')


def generate_complaint_letter(complaint, complainant, agency):
    """Call Google Gemini to generate a formal environmental complaint letter."""
    api_key = os.getenv('GEMINI_API_KEY', '').strip()
    if not api_key or api_key == 'your_gemini_api_key_here':
        raise ValueError(
            'GEMINI_API_KEY is not set. Open .env in the project folder, paste your key '
            'from Google AI Studio, save the file (Ctrl+S), then restart python app.py.'
        )

    prompt = _build_prompt(complaint, complainant, agency)

    def _call_api():
        try:
            from google import genai as _  # noqa: F401
            return _call_gemini_new_sdk(api_key, prompt)
        except ImportError:
            return _call_gemini_legacy_sdk(api_key, prompt)

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    def _call_api():
        return model.generate_content(prompt)

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_call_api)
        try:
            return future.result(timeout=GEMINI_TIMEOUT_SECONDS)
        except FuturesTimeoutError as exc:
            raise TimeoutError('Gemini API request timed out') from exc
            response = future.result(timeout=GEMINI_TIMEOUT_SECONDS)
        except FuturesTimeoutError as exc:
            raise TimeoutError('Gemini API request timed out') from exc

    if not response or not response.text:
        raise ValueError('Gemini returned an empty response')

    return response.text.strip()
