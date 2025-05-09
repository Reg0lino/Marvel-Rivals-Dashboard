# File: ai_processor.py
import json
import re
import os # For API_PROMPT_ constants if needed directly, though better to pass paths
import sys # For traceback
import requests # For requests.exceptions.RequestException

# Attempt to import Google AI library and handle if not available
try:
    import google.generativeai as genai
    from google.api_core import exceptions as google_exceptions
    AI_GOOGLE_AI_AVAILABLE = True
except ImportError:
    print("AIP ERROR: google-generativeai library not found. AI features will be disabled.")
    AI_GOOGLE_AI_AVAILABLE = False
    # Define dummy exceptions if library is missing for type hinting and graceful failure
    class google_exceptions:
        class GoogleAPIError(Exception): pass
        class InvalidArgument(GoogleAPIError): pass
        class PermissionDenied(GoogleAPIError): pass
        class ResourceExhausted(GoogleAPIError): pass
        class FailedPrecondition(GoogleAPIError): pass
        class InternalServerError(GoogleAPIError): pass
    # Dummy genai object if needed for type hints, or ensure functions check AI_GOOGLE_AI_AVAILABLE
    class GenAIPlaceholder:
        def configure(self, *args, **kwargs): pass
        def list_models(self, *args, **kwargs): return []
        class GenerativeModel:
            def __init__(self, *args, **kwargs): pass
            def generate_content(self, *args, **kwargs):
                # Simulate a blocked/error response
                class MockResponse:
                    parts = []
                    text = ""
                    prompt_feedback = type('Feedback', (), {'block_reason': 'LIBRARY_MISSING'})()
                    candidates = [type('Candidate', (), {'finish_reason': type('FinishReason', (), {'name': 'OTHER'})()})()]
                return MockResponse()

    genai = GenAIPlaceholder() # Use placeholder if library not found


# --- Constants (consider passing these as arguments for more flexibility) ---
# These paths are relative to where this script (ai_processor.py) is located.
# If updater_v3.py calls this, SCRIPT_DIR from updater_v3.py should be used to form absolute paths.
# For now, assuming they are in the same directory as this module for simplicity.
AIP_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AIP_API_PROMPT_TEMPLATE_FILE = os.path.join(AIP_SCRIPT_DIR, 'api_prompt_v3_template.txt')
AIP_DEFAULT_PROMPT_FILE = os.path.join(AIP_SCRIPT_DIR, 'api_prompt_v3_default.txt')
AIP_PATCH_PROMPT_FILE = os.path.join(AIP_SCRIPT_DIR, 'api_prompt_v3_patch_apply.txt')
AIP_TUNING_PROMPT_FILE = os.path.join(AIP_SCRIPT_DIR, 'api_prompt_v3_tuning.txt')

# --- Core AI Call Wrapper (Private Helper) ---
def _call_generative_model(api_key, model_name, prompt_text, generation_config_override=None, safety_settings_override=None, timeout=180):
    """
    Internal helper to make a call to a generative model and process the response for JSON.
    Returns a dictionary (parsed JSON or error dict).
    """
    if not AI_GOOGLE_AI_AVAILABLE:
        return {"error": "Google AI library not installed.", "details": "Cannot make API calls."}
    if not api_key:
        return {"error": "API Key missing for AI call."}
    if not model_name:
        return {"error": "No AI model name provided."}
    if not prompt_text:
        return {"error": "Prompt text is empty."}

    try:
        genai.configure(api_key=api_key)
        
        default_generation_config = {
            "temperature": 0.1, "top_p": 1, "top_k": 1, "max_output_tokens": 8192,
        }
        final_generation_config = generation_config_override if generation_config_override else default_generation_config

        default_safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]
        final_safety_settings = safety_settings_override if safety_settings_override else default_safety_settings

        print(f"AIP: Creating GenerativeModel for '{model_name}'...")
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=final_generation_config,
            safety_settings=final_safety_settings
        )
        print(f"AIP: Sending request to AI [{model_name}] (expecting text)... Prompt length: {len(prompt_text)}")
        response = model.generate_content(prompt_text, request_options={"timeout": timeout})
        print("AIP: AI call completed.")

        extracted_json_string = None
        raw_ai_output = ""

        if not response: # Should not happen if API call succeeds, but defensively check
            print("AIP DEBUG: Response object is None after API call!")
            return {"error": "API response was unexpectedly null.", "details": "Null Response"}

        if not response.parts:
            block_reason = "?"
            finish_reason = "?"
            if response.prompt_feedback: block_reason = response.prompt_feedback.block_reason or "?"
            if response.candidates and response.candidates[0]: finish_reason = response.candidates[0].finish_reason.name if response.candidates[0].finish_reason else "?"
            error_detail = f"API Error (Blocked/No Parts). BlockReason:{block_reason}, FinishReason:{finish_reason}"
            print(f"AIP DEBUG: API response blocked or empty. Details: {error_detail}")
            return {"error": "API response was blocked or empty.", "details": error_detail, "raw_response": getattr(response, 'text', '')}

        raw_ai_output = response.text
        print(f"AIP DEBUG: Received raw text response (length {len(raw_ai_output)}). Snippet: '{raw_ai_output[:100]}...'")

        # Robust JSON Extraction
        match = re.search(r'```json\s*(\{.*?\})\s*```', raw_ai_output, re.DOTALL)
        if match: extracted_json_string = match.group(1)
        else:
            match = re.search(r'^\s*(\{.*?\})\s*$', raw_ai_output, re.DOTALL | re.MULTILINE)
            if match: extracted_json_string = match.group(1)
            else:
                start_brace = raw_ai_output.find('{'); end_brace = raw_ai_output.rfind('}')
                if start_brace != -1 and end_brace != -1 and end_brace > start_brace:
                    extracted_json_string = raw_ai_output[start_brace : end_brace + 1]
                else:
                    return {"error": "JSON block delimiters not found.", "details": "Could not find {...} or ```json in AI response.", "raw_response": raw_ai_output}
        
        if not extracted_json_string: # Should be caught above, but as a safeguard
            return {"error": "JSON extraction failed, empty result.", "raw_response": raw_ai_output}

        try:
            parsed_data = json.loads(extracted_json_string)
            print("AIP DEBUG: SUCCESS: Parsed extracted JSON string.")
            return parsed_data # Successfully parsed Python dictionary
        except json.JSONDecodeError as e:
            return {"error": "Invalid JSON syntax in AI response.", "details": str(e), "raw_response": extracted_json_string}

    except google_exceptions.InvalidArgument as e: return {"error": "Google API Error: Invalid Argument", "details": str(e)}
    except google_exceptions.PermissionDenied as e: return {"error": "Google API Error: Permission Denied", "details": str(e)}
    except google_exceptions.ResourceExhausted as e: return {"error": "Google API Error: Resource Exhausted (Quota?)", "details": str(e)}
    except google_exceptions.FailedPrecondition as e: return {"error": "Google API Error: Failed Precondition", "details": str(e)}
    except google_exceptions.InternalServerError as e: return {"error": "Google API Error: Internal Server Error", "details": str(e)}
    except google_exceptions.GoogleAPIError as e: return {"error": "Google API General Error", "details": str(e)}
    except requests.exceptions.RequestException as e: # Though less likely here, for completeness
        return {"error": "Network Error during API call (requests lib)", "details": str(e)}
    except Exception as e:
        print(f"AIP DEBUG: Unexpected API call error: {e}")
        import traceback; traceback.print_exc(file=sys.stderr)
        return {"error": "Unexpected API call error", "details": str(e)}

# --- Public Functions for Specific AI Tasks ---

def generate_json_from_raw(api_key, raw_text, character_name, selected_model_name, json_schema_str,
                           prompt_template_file=AIP_API_PROMPT_TEMPLATE_FILE,
                           default_prompt_file=AIP_DEFAULT_PROMPT_FILE):
    """Generates character JSON from raw text using the AI."""
    prompt_template_content = None
    prompt_source = "Unknown (AIP)"
    try:
        if os.path.exists(prompt_template_file):
            with open(prompt_template_file, 'r', encoding='utf-8') as f: loaded_template = f.read()
            if loaded_template and loaded_template.strip():
                prompt_template_content = loaded_template
                prompt_source = f"custom ({os.path.basename(prompt_template_file)})"
        if prompt_template_content is None and os.path.exists(default_prompt_file):
             with open(default_prompt_file, 'r', encoding='utf-8') as f: loaded_default = f.read()
             if loaded_default and loaded_default.strip():
                 prompt_template_content = loaded_default
                 prompt_source = f"default ({os.path.basename(default_prompt_file)})"
        if prompt_template_content is None:
            return {"error": "API prompt template file not found or empty.", "details": f"Checked: {prompt_template_file}, {default_prompt_file}"}
        print(f"AIP: Using prompt from {prompt_source} for base JSON generation.")
    except Exception as e:
        return {"error": "Error loading prompt template for base JSON.", "details": str(e)}

    try:
        required_placeholders = ["{json_schema_target}", "{character_name}", "{raw_text}"]
        for ph in required_placeholders:
            if ph not in prompt_template_content:
                return {"error": f"Placeholder {ph} missing in prompt template.", "details": f"Source: {prompt_source}"}
        prompt = prompt_template_content.format(
            character_name=character_name,
            raw_text=raw_text,
            json_schema_target=json_schema_str
        )
    except Exception as e:
        return {"error": "Error formatting prompt for base JSON.", "details": str(e)}

    return _call_generative_model(api_key, selected_model_name, prompt)

def interpret_patch_with_ai(api_key, base_json_str, patch_section_text, character_name, model_name,
                            patch_prompt_file=AIP_PATCH_PROMPT_FILE):
    """Interprets a patch section against a base JSON using AI."""
    patch_prompt_template = None
    try:
        if os.path.exists(patch_prompt_file):
            with open(patch_prompt_file, 'r', encoding='utf-8') as f:
                patch_prompt_template = f.read()
        if not patch_prompt_template or not patch_prompt_template.strip():
            return {"error": "Patch interpretation prompt template not found or empty.", "details": f"File: {patch_prompt_file}"}
        print(f"AIP: Using patch prompt from {os.path.basename(patch_prompt_file)}.")
    except Exception as e:
        return {"error": "Error loading patch prompt template.", "details": str(e)}

    try:
        prompt = patch_prompt_template
        prompt = prompt.replace("{character_name}", str(character_name))
        prompt = prompt.replace("{base_json_str}", str(base_json_str))
        prompt = prompt.replace("{patch_section_text}", str(patch_section_text))
        # Add more placeholder checks if your patch prompt has them
    except Exception as e:
        return {"error": "Error formatting patch interpretation prompt.", "details": str(e)}
    
    # Patch interpretation might benefit from slightly different generation config
    patch_gen_config = {"temperature": 0.1, "top_p": 1, "top_k": 1, "max_output_tokens": 4096}
    return _call_generative_model(api_key, model_name, prompt, generation_config_override=patch_gen_config, timeout=120)

def tune_json_with_ai(api_key, current_json_str, raw_source_text, user_instruction, tune_model_name, json_schema_str,
                      tuning_prompt_file=AIP_TUNING_PROMPT_FILE):
    """Tunes JSON based on user instruction using AI."""
    tuning_prompt_template = None
    try:
        if os.path.exists(tuning_prompt_file):
            with open(tuning_prompt_file, 'r', encoding='utf-8') as f:
                tuning_prompt_template = f.read()
        if not tuning_prompt_template or not tuning_prompt_template.strip():
            return {"error": "Tuning prompt template not found or empty.", "details": f"File: {tuning_prompt_file}"}
        print(f"AIP: Using tuning prompt from {os.path.basename(tuning_prompt_file)}.")
    except Exception as e:
        return {"error": "Error loading tuning prompt template.", "details": str(e)}

    try:
        required_placeholders = ["{json_schema_target}", "{raw_source_text}", "{current_json_str}", "{user_instruction}"]
        for ph in required_placeholders:
            if ph not in tuning_prompt_template:
                return {"error": f"Placeholder {ph} missing in tuning prompt.", "details": f"File: {tuning_prompt_file}"}
        prompt = tuning_prompt_template.format(
            json_schema_target=json_schema_str,
            raw_source_text=raw_source_text,
            current_json_str=current_json_str,
            user_instruction=user_instruction
        )
    except Exception as e:
        return {"error": "Error formatting tuning prompt.", "details": str(e)}
        
    tune_gen_config = {"temperature": 0.2, "max_output_tokens": 8192} # As per your original
    return _call_generative_model(api_key, tune_model_name, prompt, generation_config_override=tune_gen_config)

def list_available_models_from_ai(api_key):
    """Lists available Gemini models from the AI provider."""
    if not AI_GOOGLE_AI_AVAILABLE:
        print("AIP WARN: Google AI lib not available, cannot list models from API.")
        return [] # Return empty list or predefined fallbacks
    if not api_key:
        print("AIP WARN: API Key not provided, cannot list models.")
        return []

    try:
        genai.configure(api_key=api_key)
        model_list = [m.name.split('/')[-1] for m in genai.list_models()
                      if 'generateContent' in m.supported_generation_methods and 'gemini' in m.name]
        if model_list:
            print(f"AIP: Found {len(model_list)} models via API.")
        else:
            print("AIP WARN: No Gemini models found via API.")
        return sorted(list(set(model_list)), reverse=True)
    except Exception as e:
        print(f"AIP ERROR listing models via API: {e}.")
        return [] # Return empty on error


if __name__ == '__main__':
    print("Testing ai_processor.py...")
    # This requires a valid GOOGLE_API_KEY in your environment or .env in this directory
    # and the prompt files to exist.
    if AI_GOOGLE_AI_AVAILABLE:
        print("Attempting to load .env for local testing of ai_processor...")
        try:
            from dotenv import load_dotenv as aip_load_dotenv # Local import for test
            if os.path.exists(os.path.join(AIP_SCRIPT_DIR, '.env')):
                aip_load_dotenv(dotenv_path=os.path.join(AIP_SCRIPT_DIR, '.env'))
                print("AIP TEST: .env loaded.")
            else:
                print("AIP TEST: .env file not found in ai_processor's directory, ensure GOOGLE_API_KEY is in environment for tests.")
        except ImportError:
            print("AIP TEST: python-dotenv not installed, ensure GOOGLE_API_KEY is in environment for tests.")

        test_api_key = os.environ.get("GOOGLE_API_KEY")
        if test_api_key:
            print("\n--- Testing list_available_models_from_ai ---")
            models = list_available_models_from_ai(test_api_key)
            print(f"Available models: {models}")

            if models:
                test_model = models[0] # Use the first available model
                print(f"\n--- Testing generate_json_from_raw with model: {test_model} ---")
                # Provide dummy schema and raw text for a simple test
                dummy_schema = '{"name": "string", "description": "string"}'
                dummy_raw = "Character: TestBot. Description: A friendly testing bot."
                dummy_char_name = "TestBot"
                result = generate_json_from_raw(test_api_key, dummy_raw, dummy_char_name, test_model, dummy_schema)
                print(f"Result of generate_json_from_raw: {json.dumps(result, indent=2)}")
            else:
                print("AIP TEST: No models available to run further tests.")
        else:
            print("AIP TEST: GOOGLE_API_KEY not found. Skipping API call tests.")
    else:
        print("AIP TEST: Google AI library not available. Skipping API call tests.")
    print("ai_processor.py testing placeholders complete.")