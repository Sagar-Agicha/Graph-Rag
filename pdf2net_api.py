import json
import os
from typing import Dict, Any
import easyocr
import re
import time
import dotenv
import openai
import pytesseract
from pdf2image import convert_from_path
import numpy as np
from PyPDF2 import PdfReader

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

dotenv.load_dotenv()

# Add at the top of your file, before any PDF processing
if os.name == 'nt':  # Windows
    POPPLER_PATH = r"C:\Users\DELL\Downloads\Release-24.08.0-0\poppler-24.08.0\Library\bin"
    os.environ["PATH"] += os.pathsep + POPPLER_PATH

def clean_and_parse_json(json_string):
    try:
        # First attempt: direct JSON parsing
        return json.loads(json_string)
    except json.JSONDecodeError:
        print("Initial JSON parsing failed, attempting fixes...")
        
        try:
            # Try the new fix_and_parse_json function
            fixed_json = fix_and_parse_json(json_string)
            if fixed_json:
                return fixed_json
                
            # If fix_and_parse_json fails, continue with existing cleanup methods
            # Remove escaped quotes
            json_string = json_string.replace('\\"', '"')
            json_string = json_string.replace('\"', '"')
            
            # Fix the DOB field
            json_string = re.sub(r'"DOB": "([^"]+),\s*"', r'"DOB": "\1", "', json_string)
            
            # Try parsing again
            return json.loads(json_string)
            
        except Exception as e:
            print(f"All parsing attempts failed: {str(e)}")
            return {
                "error": "Failed to parse LLM response as JSON",
                "details": str(e),
                "raw_response": json_string
            }

def fix_and_parse_json(malformed_json):
    try:
        # Try parsing the JSON directly first
        return json.loads(malformed_json)
    except json.JSONDecodeError:
        # Existing cleanup steps...
        cleaned_json = malformed_json.strip("`").strip("{}")
        cleaned_json = re.sub(r",\s*([\]}])", r"\1", cleaned_json)
        cleaned_json = re.sub(r'":\s*[,]', r'": ""', cleaned_json)
        cleaned_json = re.sub(r'("\w+":\s*".*?",\s*)("\w+":)', r'\2', cleaned_json)
        cleaned_json = cleaned_json.replace("'", '"')
        
        # New: Remove stray quotation marks that aren't part of key-value pairs
        cleaned_json = re.sub(r'"\s*}', '}', cleaned_json)
        cleaned_json = re.sub(r'"\s*,', ',', cleaned_json)

        try:
            return json.loads("{" + cleaned_json + "}")
        except json.JSONDecodeError as e:
            print("Final JSON parsing failed:", e)
            return None

def validate_json_structure(json_data):
    """Validate and clean the JSON structure"""
    required_fields = ['name', 'email', 'skills', 'experience', 'education']
    cleaned_data = {}
    
    for field in required_fields:
        if field not in json_data:
            json_data[field] = "" if field in ['name', 'email'] else []
    
    # Ensure all string fields are actually strings
    string_fields = ['name', 'email', 'DOB', 'gender', 'nationality', 'marital_status']
    for field in string_fields:
        if field in json_data:
            json_data[field] = str(json_data[field])
    
    # Ensure list fields are actually lists
    list_fields = ['skills', 'experience', 'education', 'certifications', 'languages', 'projects']
    for field in list_fields:
        if field in json_data and not isinstance(json_data[field], list):
            if json_data[field]:  # If there's a value but it's not a list
                json_data[field] = [json_data[field]]
            else:
                json_data[field] = []
    
    return json_data

def query_sambanova_llm(prompt: str) -> Dict[str, Any]:
    """Query SambaNova's API endpoint for text generation and return JSON"""
    client = openai.OpenAI(
        api_key=os.getenv("SAMBANOVA_API_KEY"),
        base_url=os.getenv("SAMBANOVA_BASE_URL")
    )

    response = client.chat.completions.create(
        model='Meta-Llama-3.1-8B-Instruct',
        messages=[
            {"role": "system", "content": "You are a helpful assistant. Always return valid JSON."},
            {"role": "user", "content": "Return the response as a single, valid JSON object. " + prompt}
        ],
        temperature=0.1,  # Reduced temperature for more consistent output
        top_p=0.1
    )

    result = response.choices[0].message.content.strip()
    
    try:
        # Clean and parse the response
        structured_output = clean_and_parse_json(result)
        
        if "error" in structured_output:
            print(f"Warning: {structured_output['error']}")
            print("Raw response:", structured_output['raw_response'])
            return structured_output
        
        # Validate and clean the structure
        validated_output = validate_json_structure(structured_output)
        
        return validated_output
        
    except Exception as e:
        print(f"Error in LLM query: {str(e)}")
        return {"error": str(e)}

def count_tokens(text: str) -> int:
    """
    Count the approximate number of tokens in a text string.
    This is a simple approximation based on word count and punctuation.
    """
    # Split on whitespace and punctuation
    words = re.findall(r'\w+|[^\w\s]', text)
    return len(words)

def extract_text_from_resumes(folder_path):
    reader = easyocr.Reader(['en'], gpu=True)
    
    def process_resume(file_path):
        extracted_text = {}
        total_tokens = 0
        
        try:
            # Add PyPDF2 text extraction
            pdf_reader = PdfReader(file_path)
            text_pypdf = ""
            for page in pdf_reader.pages:
                text_pypdf += page.extract_text() + "\n"
            
            # Convert PDF to images with explicit poppler path
            images = convert_from_path(
                file_path,
                poppler_path=POPPLER_PATH if os.name == 'nt' else None
            )
            
            for page_num, image in enumerate(images):
                try:
                    # Convert PIL Image to numpy array for EasyOCR
                    image_np = np.array(image)
                    
                    # Get text using pytesseract (works with PIL Image)
                    text_pytesseract = pytesseract.image_to_string(image)
                    
                    # Get text using EasyOCR (works with numpy array)
                    text_easyocr = reader.readtext(image_np, detail=0)
                    text_easyocr_combined = ' '.join(text_easyocr)
                    
                    # Combine texts from all three OCR engines
                    combined_text = combine_texts_multiple(
                        text_pytesseract, 
                        text_easyocr_combined,
                        text_pypdf
                    )
                    
                    # Count tokens for this page
                    page_tokens = count_tokens(combined_text)
                    total_tokens += page_tokens
                    print(f"Page {page_num+1} tokens: {page_tokens}")
                    
                    # Process sections as before
                    sections = re.split(r'\n(?=\b(Experience|Education|Skills|Projects|Certifications|Summary|Objective|Contact Information)\b)', combined_text)
                    
                    current_section = "General"
                    for section in sections:
                        header_match = re.match(r'^(Experience|Education|Skills|Projects|Certifications|Summary|Objective|Contact Information)\b', section)
                        if header_match:
                            current_section = header_match.group(0)
                            extracted_text[current_section] = section
                            print(f"Section '{current_section}' tokens: {count_tokens(section)}")
                        else:
                            extracted_text.setdefault(current_section, "")
                            extracted_text[current_section] += section
                    
                except Exception as e:
                    print(f"Error processing page {page_num+1} of {file_path}: {str(e)}")
                    continue
            
        except Exception as e:
            print(f"Error processing PDF: {str(e)}")
            return {}, 0
        
        print(f"\nTotal tokens for {os.path.basename(file_path)}: {total_tokens}")

        text_tokens = count_tokens(str(extracted_text))
        print(f"\nExtracted text tokens: {text_tokens}")
        
        # Generate appropriate prompt based on token count
        prompt = create_prompt(str(extracted_text), text_tokens)
        prompt_tokens = count_tokens(prompt)
        print(f"Prompt tokens: {prompt_tokens}")
        print(f"Using {'simplified' if text_tokens > 1000 else 'detailed'} prompt format")
        
        # Continue with existing processing...
        initial_output = query_sambanova_llm(prompt)
        
        if "error" in initial_output or not isinstance(initial_output, dict):
            print(f"Initial parsing failed for {filename}, attempting fixes...")
            structured_output = retry_llm_with_json_fix(
                json.dumps(initial_output) if isinstance(initial_output, dict) else str(initial_output)
            )
        else:
            structured_output = initial_output
        
        if "error" in structured_output:
            print(f"Error processing {filename}: {structured_output['error']}")
            
        # Create output directory if it doesn't exist
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        
        # Save JSON file using the PDF name or candidate's name
        if isinstance(structured_output, dict):
            if "name" in structured_output:
                # Use candidate's name if available
                json_filename = structured_output["name"].lower().replace(" ", "_") + ".json"
            else:
                # Use PDF filename if name not found
                json_filename = os.path.splitext(filename)[0] + ".json"
                
            output_path = os.path.join(output_dir, json_filename)
            
            try:
                # Try to save JSON file
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(structured_output, f, indent=2, ensure_ascii=False)
                print(f"Saved JSON output to: {output_path}")
            except Exception as e:
                print(f"Failed to save JSON for {filename}, attempting reparse...")
                # Simply send it back to LLM for reparsing
                structured_output = retry_llm_with_json_fix(json.dumps(structured_output))
                
                # Try saving again
                try:
                    with open(output_path, 'w', encoding='utf-8') as f:
                        json.dump(structured_output, f, indent=2, ensure_ascii=False)
                    print(f"Saved reparsed JSON to: {output_path}")
                except Exception as e:
                    print(f"Error: Could not save JSON for {filename} after reparsing - {str(e)}")
        else:
            print(f"Error: Could not save JSON for {filename} - invalid format")
                    
        if total_tokens > 4000:
            print("⚠️ WARNING: Token count exceeds recommended limit!")
            print("Consider summarizing or truncating the text")
        
        return extracted_text, total_tokens

    # Updated combine_texts function to handle multiple sources
    def combine_texts_multiple(*texts):
        # Split all texts into words
        word_lists = [text.split() for text in texts]
        
        # Find the maximum length among all word lists
        max_length = max(len(words) for words in word_lists)
        
        # Pad shorter lists with empty strings
        padded_lists = [words + [''] * (max_length - len(words)) for words in word_lists]
        
        combined = []
        # Iterate through words from all sources
        for words in zip(*padded_lists):
            # Take the first non-empty word found
            for word in words:
                if word.strip():
                    combined.append(word)
                    break
            else:
                # If no non-empty word found, skip
                continue
                
        return ' '.join(combined)

    all_extracted_resumes = {}
    total_tokens_all_resumes = 0
    
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".pdf"):
            pdf_path = os.path.join(folder_path, filename)
            print(f"\nProcessing {filename}...")
            extracted_text, tokens = process_resume(pdf_path)
            all_extracted_resumes[filename] = extracted_text
            total_tokens_all_resumes += tokens
    
    print(f"\n=== Token Statistics ===")
    print(f"Total tokens across all resumes: {total_tokens_all_resumes}")
    print(f"Average tokens per resume: {total_tokens_all_resumes // len(all_extracted_resumes)}")
    
    return all_extracted_resumes

def create_prompt(text: str, token_count: int) -> str:
    """Creates a detailed prompt for structured resume parsing based on token count"""
    
    if token_count <= 1000:
        # Original detailed prompt for shorter texts
        return f"""
        You are a precise JSON resume parser. Parse the following resume text into a structured JSON format optimized for Neo4j graph database.
        
        CRITICAL RULES:
        1. Return ONLY valid JSON - no explanations or other text
        2. All arrays must be properly formatted with NO extra commas or braces
        3. Use "Not specified" for missing values instead of null or empty strings
        4. Never include trailing commas in arrays or objects
        5. All strings must use double quotes, not single quotes
        6. Each skill, certification, and achievement must be a separate entry in its array
        7. Check for skills synonyms eg Competencies, Skills, Technologies, Tools, etc. and consolidate them into a single skill entry
        8. Dont take skills from experience section, take them from skills section

        VALIDATION CHECKLIST:
        - Each array must start with [ and end with ]
        - Each object must start with {{ and end with }}
        - No trailing commas after the last item in arrays or objects
        - All string values must be in double quotes
        - Dates should be in specified format or "Not specified"
        - Each entry in skills, certifications, and achievements must be a separate object or string as specified
        - Projects should have a name and skills_used, as individual entries

        IMPORTANT FOR NEO4J:
        - Skills must be individual entries for proper node creation
        - Certifications and projects should be separate objects for proper relationships
        - Achievements should be individual strings for node creation
        - Experience entries should be in reverse chronological order
        
        Expected Structure:
        {{
            "name": "Candidate full name",
            "education": [
                {{
                    "degree": "Exact degree name",
                    "field": "Field of study",
                    "institution": "Institution name",
                    "year": "YYYY or YYYY-YYYY format"
                }}
            ],
            "experience": [
                {{
                    "designation": "Exact job title",
                    "work_at": "Company name",
                    "years": "YYYY-YYYY or YYYY-Present",
                    "worked_on": "Technologies worked on"
                }}
            ],
            "number_of_years_of_experience": <integer>,
            "professional_skills": [
                "Individual Skill 1",
                "Individual Skill 2"
            ],
            "certifications": [
                {{
                    "name": "Individual certification name",
                    "year": "YYYY or Not specified",
                    "id": "ID or Not specified"
                }}
            ],
            "languages": [
                "Individual Language 1",
                "Individual Language 2"
            ],
            "projects": [
                {{
                    "name": "Project name",
                    "skills_used": "Technologies used"
                }}
            ],
            "achievements": [
                "Individual Achievement 1",
                "Individual Achievement 2"
            ],
            "DOB": "YYYY-MM-DD or Not specified",
            "gender": "Gender or Not specified",
            "marital_status": "Status or Not specified",
            "nationality": "Nationality or Not specified",
            "current_position": "Current job title",
            "current_employer": "Current employer name"
        }}

        Resume text to parse:
        {text}
        """
    else:
        # Simplified prompt for longer texts, focusing on essential information
        return f"""
        Parse this resume into a focused JSON format. Extract only the most important information.
        
        CRITICAL RULES:
        1. Return ONLY valid JSON - no explanations or other text
        2. All arrays must be properly formatted with NO extra commas or braces
        3. Use "Not specified" for missing values instead of null or empty strings
        4. Never include trailing commas in arrays or objects
        5. All strings must use double quotes, not single quotes
        6. Each skill, certification, and achievement must be a separate entry in its array
        7. Check for skills synonyms eg Competencies, Skills, Technologies, Tools, etc. and consolidate them into a single skill entry
        8. Dont take skills from experience section, take them from skills section
        9. Skills must be individual entries for proper node creation 
        10. Dont take skills from experience section, take them from skills section
        11. If its a big line of text, take keywords from it.

        Expected Structure:
        {{
            "name": "Candidate full name",
            "education": [
                {{
                    "degree": "Exact degree name",
                    "field": "Field of study",
                    "institution": "Institution name",
                    "year": "YYYY or YYYY-YYYY format"
                }}
            ],
            "experience": [
                {{
                    "designation": "Exact job title",
                    "work_at": "Company name",
                    "years": "YYYY-YYYY or YYYY-Present",
                    "worked_on": "Technologies worked on"
                }}
            ],
            "number_of_years_of_experience": <integer>,
            "professional_skills": [
                "Individual Skill 1",
                "Individual Skill 2"
            ],
            "certifications": [
                {{
                    "name": "Individual certification name",
                    "year": "YYYY or Not specified",
                    "id": "ID or Not specified"
                }}
            ],
            "languages": [
                "Individual Language 1",
                "Individual Language 2"
            ],
            "projects": [
                {{
                    "name": "Project name",
                    "skills_used": "Technologies used"
                }}
            ],
            "achievements": [
                "Individual Achievement 1",
                "Individual Achievement 2"
            ],
            "DOB": "YYYY-MM-DD or Not specified",
            "gender": "Gender or Not specified",
            "marital_status": "Status or Not specified",
            "nationality": "Nationality or Not specified",
            "current_position": "Current job title",
            "current_employer": "Current employer name"
        }}

        Resume text:
        {text}
        """

def retry_llm_with_json_fix(json_string: str, attempt: int = 1) -> Dict[str, Any]:
    """
    Sends the failed JSON back to LLM for reparsing, with up to 2 attempts
    """
    if attempt > 2:
        return {"error": "Failed to parse JSON after 2 attempts"}
        
    fix_prompt = f"""
    You are a JSON repair specialist. The following JSON needs to be reparsed into a valid format.
    
    REQUIREMENTS:
    1. Return ONLY the corrected JSON - no explanations or additional text
    2. Maintain all existing data but consolidate redundant skills:
       - Combine similar skills into single entries
       - Remove duplicate skills
       - Limit to most important/unique skills (max 30)
       - For technologies like VMware, list main components only
    3. Ensure proper formatting:
       - Use double quotes for all strings
       - No trailing commas
       - Properly closed arrays and objects
       - Valid date formats (YYYY-MM-DD)
    4. Required fields:
       - name (string)
       - education (array of objects)
       - experience (array of objects)
       - skills (array of strings)
    5. Data cleaning rules:
       - Remove any fields with empty or "Not specified" values
       - Remove any empty arrays
       - Remove any optional fields that lack meaningful data
       - Keep only fields with actual content
    
    JSON TO FIX (Attempt {attempt} of 2):
    {json_string}
    """
    
    result = query_sambanova_llm(fix_prompt)
    
    if "error" in result or not isinstance(result, dict):
        print(f"Attempt {attempt} failed, trying again..." if attempt < 2 else "All attempts failed")
        return retry_llm_with_json_fix(
            json.dumps(result) if isinstance(result, dict) else str(result),
            attempt + 1
        )
    
    return result

def convert_pdf_to_structured_json(pdf_folder):
    i = 1
    for filename in os.listdir(pdf_folder):
        if filename.lower().endswith(".pdf"):
            single_pdf_path = os.path.join(pdf_folder, filename)
            time.sleep(20)

            # Extract text and get token count
            extract_text_from_resumes(os.path.dirname(single_pdf_path))

            if i == 1:
                break
# Usage
pdf_folder = "test_cvs"
convert_pdf_to_structured_json(pdf_folder)
 