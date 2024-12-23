from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
from werkzeug.utils import secure_filename
from pathlib import Path
import json
import os
from typing import Dict, Any
import easyocr
import re
import time
import openai
import pytesseract
from pdf2image import convert_from_path
import numpy as np
from PyPDF2 import PdfReader
from datetime import datetime, timedelta
import shutil
from neo4j import GraphDatabase
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configure Neo4j connection
uri = "bolt://localhost:7687"
username = "neo4j"
password = "Sagar1601"

# Configure upload settings
UPLOAD_FOLDER = Path("uploads")
ALLOWED_EXTENSIONS = {'pdf'}

DUPLICATES_FOLDER = Path("duplicates")
DUPLICATES_FOLDER.mkdir(exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
UPLOAD_FOLDER.mkdir(exist_ok=True)

pytesseract.pytesseract.tesseract_cmd = r"C:\Users\Sagar\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"

if os.name == 'nt':  # Windows
    POPPLER_PATH = r"C:\Users\Sagar\Downloads\poppler-24.07.0\Library\bin"
    os.environ["PATH"] += os.pathsep + POPPLER_PATH

STATUS_FOLDER = Path("status")
STATUS_FOLDER.mkdir(exist_ok=True)

# Add a secret key for session management
app.secret_key = 'Sagar'  # Change this to a secure secret key

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_users():
    with open('users.json', 'r') as f:
        return json.load(f)

def count_user_duplicates(username):
    """Count number of duplicate files for a user"""
    try:
        duplicate_folder = get_user_folder(username) / 'duplicates'
        if not duplicate_folder.exists():
            return 0
        return len([f for f in duplicate_folder.glob('*.pdf')])
    except Exception as e:
        print(f"Error counting duplicates: {str(e)}")
        return 0

@app.route('/') 
def home():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    users = load_users()
    
    user = next((user for user in users['users'] 
                 if user['username'] == username 
                 and user['password'] == password), None)
    
    if user:
        session['username'] = username  # Store username in session
        return jsonify({'success': True, 'message': 'Login successful'})
    else:
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@app.route('/logout')
def logout():
    session.pop('username', None)  # Remove username from session
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('home'))
        
    duplicate_count = count_user_duplicates(session['username'])
    return render_template('index.html', 
                         username=session['username'],
                         duplicate_count=duplicate_count)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    if 'files' not in request.files:
        return jsonify({'error': 'No files in request'}), 400
    
    files = request.files.getlist('files')
    user_folder = get_user_folder(session['username'])
    
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Read the unique number from uniq_num.txt
            try:
                with open('uniq_num.txt', 'r') as f:
                    unq_num = int(f.read().strip())
                # Add leading zeros to make it 7 digits
                padded_num = str(unq_num)
                # Add the padded number to start of filename
                filename = f"{padded_num}_{filename}"
                # Increment the unique number for next time
                unq_num += 1
                with open('uniq_num.txt', 'w') as f:
                    f.write(str(unq_num))
            except Exception as e:
                print(f"Error adding unique number to filename: {str(e)}")
            file.save(user_folder / filename)
    
    return jsonify({'message': 'Files uploaded successfully'})

@app.route('/delete', methods=['POST'])
def delete_file():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    data = request.get_json()
    filename = data.get('filename')
    if not filename:
        return jsonify({'error': 'No filename provided'}), 400

    user_folder = get_user_folder(session['username'])
    file_path = user_folder / secure_filename(filename)
    
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return jsonify({'message': 'File deleted successfully'})
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': f'Error deleting file: {str(e)}'}), 500

@app.route('/files')
def get_user_files_and_duplicates():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    try:
        files = []
        user_folder = get_user_folder(session['username'])
        duplicate_folder = user_folder / 'duplicates'
        duplicate_count = len(list(duplicate_folder.glob('*.pdf'))) if duplicate_folder.exists() else 0
        
        for filename in os.listdir(user_folder):
            if filename.lower().endswith('.pdf'):
                file_path = user_folder / filename
                files.append({
                    'name': filename,
                    'size': os.path.getsize(file_path)
                })
                
        return jsonify({
            'files': files,
            'duplicate_count': duplicate_count
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_uploaded_files():
    files = []
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        if allowed_file(filename):
            files.append(filename)
    return files

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')

        
    
    response = f"Received: {user_message}"
    return jsonify({'response': response})

def get_user_status_file(username):
    """Get the path to user's status file"""
    return STATUS_FOLDER / f"{username}_status.json"

def update_processing_status(filename: str, status: str, file_link: str = None, duplicate_count: int = None):
    if 'username' not in session:
        return
        
    username = session['username']
    status_file = get_user_status_file(username)
    
    try:
        if status_file.exists():
            with open(status_file, 'r') as f:
                status_data = json.load(f)
        else:
            status_data = []
        
        # Update existing entry or add new one
        entry = next((item for item in status_data if item["filename"] == filename), None)
        if entry:
            entry.update({
                "status": status,
                "file_link": file_link,
                "last_updated": datetime.now().isoformat()
            })
        else:
            status_data.append({
                "filename": filename,
                "status": status,
                "file_link": file_link,
                "last_updated": datetime.now().isoformat()
            })
        
        if duplicate_count is not None:
            status_data[-1]["duplicate_count"] = duplicate_count
        
        with open(status_file, 'w') as f:
            json.dump(status_data, f, indent=4)
            
    except Exception as e:
        print(f"Error updating status: {str(e)}")

def cleanup_old_status_files():
    """Remove status files older than 24 hours"""
    current_time = datetime.now()
    
    for status_file in STATUS_FOLDER.glob("*_status.json"):
        try:
            file_modified_time = datetime.fromtimestamp(os.path.getmtime(status_file))
            if current_time - file_modified_time > timedelta(hours=24):
                os.remove(status_file)
                print(f"Removed old status file: {status_file}")
        except Exception as e:
            print(f"Error cleaning up status file {status_file}: {str(e)}")

@app.route('/process', methods=['POST'])
def process_files():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401

    username = session['username']
    
    # Add user to queue
    add_to_queue(username)
    
    # Check queue position
    position = check_queue_position(username)
    
    if position > 0:
        return jsonify({
            'status': 'queued',
            'position': position,
            'message': f'Your request is queued. Position: {position}'
        })

    try:
        # Process files only if first in queue
        if is_first_in_queue(username):
            print(f"Starting to process files for {username}...")
        
            user_folder = get_user_folder(session['username'])
            
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
                    api_key="e4f88cdc-e437-4545-b92b-5aaed8866b27",
                    base_url="https://api.sambanova.ai/v1"
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

            def create_prompt(text: str, token_count: int, unq_num: int) -> str:
                return f"""
                    You are a precise JSON resume parser. Parse the following resume text into a structured JSON format optimized for Neo4j graph database.
                    
                    CRITICAL RULES:
                    1. Return ONLY valid JSON - no explanations or other text
                    2. All arrays must be properly formatted with NO extra commas or braces
                    3. Use "Not specified" for missing values instead of null or empty strings
                    4. Never include trailing commas in arrays or objects
                    5. All strings must use double quotes, not single quotes
                    6. Each skill, certification, and achievement must be a separate entry in its array
                    7. Check for skills synonyms eg Competencies, Skills, Technologies, Tools, etc. and consolidate them into a single skill entry.
                    8. Dont take skills from experience section, take them from skills section
                    9. Change the DOB format to YYYY-MM-DD from any other format
                    10. Dont change the json structure keys, only add or remove values

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
                        "unique_number": {unq_num},
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
                            "Individual Skill n"
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
                            "Individual Language n"
                        ],
                        "projects": [
                            {{
                                "name": "Project name",
                                "skills_used": "Technologies used"
                            }}
                        ],
                        "achievements": [
                            "Individual Achievement 1",
                            "Individual Achievement n"
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

            class GraphCreator:
                def __init__(self):
                    # Neo4j connection settings
                    self.uri = "bolt://localhost:7687"
                    self.username = "neo4j"
                    self.password = "Sagar1601"
                    
                    try:
                        self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
                        # Test the connection
                        self.driver.verify_connectivity()
                        logger.info("Successfully connected to Neo4j database")
                    except Exception as e:
                        logger.error(f"Failed to connect to Neo4j: {e}")
                        raise

                def close(self):
                    if hasattr(self, 'driver'):
                        self.driver.close()
                        logger.info("Neo4j connection closed")

                def create_graph(self, json_file_path):
                    logger.info(f"Processing file: {json_file_path}")
                    try:
                        with open(json_file_path, 'r', encoding='utf-8') as file:
                            data = json.load(file)
                        
                        with self.driver.session() as session2:
                            # Helper function to ensure primitive types
                            def get_safe_value(value):
                                if isinstance(value, (str, int, float, bool)):
                                    return value
                                elif isinstance(value, dict) and 'name' in value:
                                    return value['name']
                                elif isinstance(value, dict):
                                    return str(value)
                                elif value is None:
                                    return ''
                                return str(value)

                            # Create person node with extended properties
                            session2.run("""
                                MERGE (p:Person {
                                    name: $name,
                                    email: $email,
                                    unique_number: $unique_number,
                                    DOB: $dob,
                                    gender: $gender,
                                    marital_status: $marital_status,
                                    nationality: $nationality,
                                    current_position: $current_position,
                                    current_employer: $current_employer,
                                    number_of_years_of_experience: $number_of_years_of_experience
                                })
                            """, 
                                name=get_safe_value(data.get('name')),
                                email=get_safe_value(data.get('email')),
                                unique_number=get_safe_value(data.get('unique_number')),
                                dob=get_safe_value(data.get('DOB')),
                                gender=get_safe_value(data.get('gender')),
                                marital_status=get_safe_value(data.get('marital_status')),
                                nationality=get_safe_value(data.get('nationality')),
                                current_position=get_safe_value(data.get('current_position')),
                                current_employer=get_safe_value(data.get('current_employer')),
                                number_of_years_of_experience=get_safe_value(data.get('number_of_years_of_experience'))
                            )
                            logger.info(f"Created Person node for {data.get('name')}")

                            # Create education nodes
                            for edu in data.get('education', []):
                                session2.run("""
                                    MATCH (p:Person {name: $name})
                                    MERGE (i:Institution {name: $institution})
                                    MERGE (p)-[:STUDIED_AT {
                                        degree: $degree,
                                        field: $field,
                                        year: $year
                                    }]->(i)
                                """,
                                    name=get_safe_value(data.get('name')),
                                    institution=get_safe_value(edu.get('institution')),
                                    degree=get_safe_value(edu.get('degree')),
                                    field=get_safe_value(edu.get('field')),
                                    year=get_safe_value(edu.get('year'))
                                )

                            # Create skills
                            for skill in data.get('professional_skills', []):
                                skill_name = get_safe_value(skill)
                                session2.run("""
                                    MATCH (p:Person {name: $name})
                                    MERGE (s:Skill {name: $skill})
                                    MERGE (p)-[:HAS_SKILL]->(s)
                                """, name=get_safe_value(data.get('name')), skill=skill_name)

                            # Create certifications
                            for cert in data.get('certifications', []):
                                session2.run("""
                                    MATCH (p:Person {name: $name})
                                    MERGE (c:Certification {
                                        name: $cert_name,
                                        year: $cert_year,
                                        id: $cert_id
                                    })
                                    MERGE (p)-[:HAS_CERTIFICATION]->(c)
                                """,
                                    name=get_safe_value(data.get('name')),
                                    cert_name=get_safe_value(cert.get('name')),
                                    cert_year=get_safe_value(cert.get('year')),
                                    cert_id=get_safe_value(cert.get('id'))
                                )

                            # Create languages
                            for lang in data.get('languages', []):
                                lang_name = get_safe_value(lang)
                                session2.run("""
                                    MATCH (p:Person {name: $name})
                                    MERGE (l:Language {name: $lang})
                                    MERGE (p)-[:SPEAKS]->(l)
                                """, name=get_safe_value(data.get('name')), lang=lang_name)

                            # Create projects
                            for project in data.get('projects', []):
                                session2.run("""
                                    MATCH (p:Person {name: $name})
                                    MERGE (pr:Project {
                                        name: $project_name
                                    })
                                    MERGE (p)-[:WORKED_ON]->(pr)
                                    SET pr.skills_used = $skills_used
                                """,
                                    name=get_safe_value(data.get('name')),
                                    project_name=get_safe_value(project.get('name')),
                                    skills_used=get_safe_value(project.get('skills_used'))
                                )

                            # Create achievements
                            for achievement in data.get('achievements', []):
                                achievement_desc = get_safe_value(achievement)
                                session2.run("""
                                    MATCH (p:Person {name: $name})
                                    MERGE (a:Achievement {description: $achievement})
                                    MERGE (p)-[:ACHIEVED]->(a)
                                """, name=get_safe_value(data.get('name')), achievement=achievement_desc)

                            # Create work experience
                            for exp in data.get('experience', []):
                                # First create the basic work experience relationship
                                session2.run("""
                                    MATCH (p:Person {name: $name})
                                    MERGE (c:Company {name: $company})
                                    MERGE (p)-[:WORKED_AT {
                                        designation: $designation,
                                        years: $years
                                    }]->(c)
                                """, 
                                    name=get_safe_value(data.get('name')),
                                    company=get_safe_value(exp.get('work_at')),
                                    designation=get_safe_value(exp.get('designation')),
                                    years=get_safe_value(exp.get('years')),
                                    unique_number=get_safe_value(data.get('unique_number'))
                                )

                                # Now process work_on field to create Technology nodes
                                work_on = get_safe_value(exp.get('work_on'))
                                if work_on:
                                    # Split the work_on string into individual technologies
                                    technologies = [tech.strip() for tech in work_on.split(',')]
                                    for tech in technologies:
                                        if tech:  # Skip empty strings
                                            session2.run("""
                                                MATCH (p:Person {name: $name})
                                                MATCH (p)-[w:WORKED_AT]->(c:Company {name: $company})
                                                MERGE (t:Technology {name: $tech})
                                                MERGE (p)-[:USED_TECHNOLOGY {during: $years}]->(t)
                                            """,
                                                name=get_safe_value(data.get('name')),
                                                company=get_safe_value(exp.get('work_at')),
                                                tech=tech,
                                                years=get_safe_value(exp.get('years'))
                                            )

                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON in file {json_file_path}: {e}")
                    except KeyError as e:
                        logger.error(f"Missing required field in JSON {json_file_path}: {e}")
                    except Exception as e:
                        logger.error(f"Error processing file {json_file_path}: {e}")

            def extract_text_from_resumes(folder_path):
                def process_resume(file_path):
                    extracted_text = {}
                    total_tokens = 0
                    reader = easyocr.Reader(['en'], gpu=True)
                    
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

                    # Extract first 7 digits from filename as unique number
                    unq_num = ''.join(filter(str.isdigit, filename))[:7]
                    if not unq_num:
                        unq_num = "0000000"  # Default if no digits found
                    unq_num = int(unq_num)
                    
                    return extracted_text, unq_num, text_tokens
                
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

                for filename in os.listdir(folder_path):
                    if filename.lower().endswith(".pdf"):
                        pdf_path = os.path.join(folder_path, filename)
                        print(f"\nProcessing {filename}...")
                        extracted_text, unq_num, text_tokens = process_resume(pdf_path)
                        # Generate appropriate prompt based on token count
                        prompt = create_prompt(str(extracted_text), text_tokens, unq_num)
                        prompt_tokens = count_tokens(prompt)
                        print(f"Prompt tokens: {prompt_tokens}")
                        print(f"Using {'simplified' if text_tokens > 1000 else 'detailed'} prompt format")
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
                            
                        # Check if structured output is valid JSON
                        try:
                            # Attempt to serialize the output to validate JSON structure
                            json.dumps(structured_output)
                            json_is_valid = True
                        except (TypeError, ValueError) as e:
                            print(f"Invalid JSON structure for {filename}: {str(e)}")
                            json_is_valid = False
                            
                        if not json_is_valid:
                            print(f"Retrying with JSON fix for {filename}...")
                            retry_output = retry_llm_with_json_fix(str(structured_output))
                            
                            if isinstance(retry_output, dict):
                                structured_output = retry_output
                                json_is_valid = True
                            else:
                                print(f"Failed to fix JSON for {filename} after retry")
                                continue
                        
                        if not json_is_valid:
                            print(f"Retrying with JSON fix for {filename}...")
                            retry_output = retry_llm_with_json_fix(str(structured_output))
                            
                            if isinstance(retry_output, dict):
                                structured_output = retry_output
                                json_is_valid = True
                            else:
                                print(f"Failed to fix JSON for {filename} after retry")
                                continue

                        # Create output directory if it doesn't exist
                        output_dir = "output"
                        os.makedirs(output_dir, exist_ok=True)
                        
                        # Save JSON file using the PDF name or candidate's name
                        if isinstance(structured_output, dict):
                            if "name" in structured_output:
                                # Use candidate's name if available
                                json_filename = str(unq_num) + "_" + structured_output["name"].lower().replace(" ", "_") + ".json"
                            else:
                                # Use PDF filename if name not found
                                json_filename = os.path.splitext(filename)[0] + ".json"
                            output_path = os.path.join(output_dir, json_filename)
                            
                            try:
                                uri = "bolt://localhost:7687"
                                username = "neo4j"
                                password = "Sagar1601"
                                driver = GraphDatabase.driver(uri, auth=(username, password))
                                driver.verify_connectivity()
                                logger.info("Connected to Neo4j successfully")

                                def find_pdf_by_unique_number(unique_number):
                                    """Find PDF file in processed folder by unique number"""
                                    processed_folder = Path("processed")
                                    for pdf in processed_folder.glob("*.pdf"):
                                        if pdf.name.startswith(str(unique_number)):
                                            return pdf
                                    return None
                                
                                def find_json_by_unique_number(unique_number):
                                    """Find JSON file in output folder by unique number"""
                                    output_folder = Path("output")
                                    for json_file in output_folder.glob("*.json"):
                                        if json_file.name.startswith(str(unique_number).zfill(7)):
                                            return json_file

                                def find_person_by_name_and_dob(name, dob):
                                    """
                                    Find all potential duplicates using Levenshtein distance and DOB
                                    Returns status and duplicate status JSON
                                    """
                                    try:
                                        matches = []
                                        with GraphDatabase.driver(uri, auth=(username, password)) as driver:
                                            with driver.session() as session1:
                                                # Use apoc.text.levenshteinSimilarity for name comparison
                                                result = session1.run("""
                                                    MATCH (p:Person)
                                                    WHERE toLower(p.name) = toLower($name)
                                                        OR apoc.text.levenshteinSimilarity(toLower(p.name), toLower($name)) > 0.8
                                                    RETURN p.name as matched_name,
                                                            p.DOB as dob,
                                                            p.current_position as current_position,
                                                            p.current_employer as current_employer,
                                                            p.unique_number as unique_number,
                                                            apoc.text.levenshteinSimilarity(toLower(p.name), toLower($name)) as similarity
                                                    ORDER BY similarity DESC
                                                """, name=name)
                                                
                                                records = list(result)
                                                if not records:
                                                    return "False", None
                                                    # Create duplicate status structure
                                                duplicate_status = {
                                                    "uploaded_file": {
                                                        "name": name,
                                                        "dob": dob,
                                                        "current_position": "Not specified",  # Will be filled from structured_output
                                                        "unique_number": None  # Will be filled from structured_output
                                                    },
                                                    "duplicates": [],
                                                    "timestamp": datetime.now().isoformat(),
                                                    "status": "pending_review"
                                                }
                                                
                                                for record in records:
                                                    # Find corresponding files
                                                    pdf_path = find_pdf_by_unique_number(record['unique_number'])
                                                    json_path = find_json_by_unique_number(record['unique_number'])
                                                    
                                                    duplicate_entry = {
                                                        "name": record['matched_name'],
                                                        "unique_number": record['unique_number'],
                                                        "similarity": round(record['similarity'] * 100, 2),
                                                        "details": {
                                                            "dob": record['dob'] if record['dob'] else "Not specified",
                                                            "current_position": record['current_position'] if record['current_position'] else "Not specified",
                                                            "current_employer": record['current_employer'] if record['current_employer'] else "Not specified",
                                                            "pdf_path": str(pdf_path) if pdf_path else None,
                                                            "json_path": str(json_path) if json_path else None
                                                        }
                                                    }
                                                    duplicate_status["duplicates"].append(duplicate_entry)
                                                    # Save duplicate status JSON
                                                    if 'username' in session:  # Use flask.session instead of session
                                                        status_path = STATUS_FOLDER / f"{session['username']}_duplicate_status.json"
                                                        with open(status_path, 'w') as f:
                                                            json.dump(duplicate_status, f, indent=2)
                                                
                                                return "True", duplicate_status
                                                
                                    except Exception as e:
                                        logger.error(f"Error in duplicate check: {str(e)}")
                                        return "Error", str(e)
                                    # Update the section where duplicates are handled

                                status, duplicate_status = find_person_by_name_and_dob(structured_output["name"], structured_output.get("DOB"))
                                if status == "True":
                                    print(f"Found {len(duplicate_status['duplicates'])} potential duplicates:")
                                
                                    # Update the uploaded file details
                                    duplicate_status["uploaded_file"].update({
                                        "path": str(get_user_folder(session['username']) / filename),
                                        "current_position": structured_output.get("current_position", "Not specified"),
                                        "unique_number": structured_output.get("unique_number")
                                    })
                                    
                                    # Save updated status
                                    status_path = STATUS_FOLDER / f"{session['username']}_duplicate_status.json"
                                    with open(status_path, 'w') as f:
                                        json.dump(duplicate_status, f, indent=2)
                                    
                                    # Create duplicates folder and move file
                                    user_duplicates = get_user_folder(session['username']) / 'duplicates'
                                    user_duplicates.mkdir(exist_ok=True)
                                    
                                    try:
                                        # Move PDF to user's duplicates folder
                                        source_path = get_user_folder(session['username']) / filename
                                        dest_path = user_duplicates / filename
                                        shutil.move(str(source_path), str(dest_path))
                                        
                                        # Save JSON in duplicates folder
                                        json_path = user_duplicates / json_filename
                                        with open(json_path, 'w', encoding='utf-8') as f:
                                            json.dump(structured_output, f, indent=2, ensure_ascii=False)
                                            
                                        duplicate_count = count_user_duplicates(session['username'])
                                        
                                        update_processing_status(
                                            filename=filename,
                                            status="duplicate",
                                            file_link=f"/uploads/{session['username']}/{filename}",
                                            duplicate_count=duplicate_count
                                        )
                                        
                                        print(f"Moved duplicate {filename} and saved JSON to user's duplicates folder")
                                        return "duplicate", None
                                        
                                    except Exception as e:
                                        print(f"Error handling duplicate file: {str(e)}")
                                        return "error", str(e)

                                else:
                                    def move_to_processed(username: str, filename: str):
                                        """Move a processed file to the processed folder while maintaining user structure"""
                                        try:
                                            # Create user folder in processed directory
                                            PROCESSED_FOLDER = Path("processed")
                                            PROCESSED_FOLDER.mkdir(exist_ok=True)
                                            
                                            # Source and destination paths
                                            source_path = get_user_folder(username) / filename
                                            dest_path = PROCESSED_FOLDER / filename
                                            
                                            # Move the file
                                            shutil.move(str(source_path), str(dest_path))
                                            print(f"Moved {filename} to processed folder")
                                            return True
                                        except Exception as e:
                                            print(f"Error moving file to processed folder: {str(e)}")
                                            return False

                                    if move_to_processed(session['username'], filename):
                                        print(f"Successfully processed and moved: {filename}")
                                        with open(output_path, 'w', encoding='utf-8') as f:
                                            json.dump(structured_output, f, indent=2, ensure_ascii=False)
                                        print(f"Saved JSON output to: {output_path}")
                                        return "completed", output_path
                                    else:
                                        print(f"File processed but move failed: {filename}")
                                        break
                    
                            except Exception as e:
                                print(f"Failed to save JSON for {filename}, attempting reparse...")
                                # Simply send it back to LLM for reparsing
                                structured_output = retry_llm_with_json_fix(json.dumps(structured_output))
                        else:
                            print(f"Error: Could not save JSON for {filename} - invalid format")
                            return "failed", None

            for filename in os.listdir(user_folder):
                if filename.lower().endswith(".pdf"):
                    try:
                        # Update status to "processing"
                        update_processing_status(
                            filename=filename,
                            status="processing",
                            file_link=f"/uploads/{session['username']}/{filename}"
                        )
                        
                        # Pass the folder path instead of the file path
                        output_path = None
                        status, output_path = extract_text_from_resumes(str(user_folder))

                        # Update status to "completed"
                        if status == "completed":
                            creator = GraphCreator()
                            creator.create_graph(output_path)
                            update_processing_status(
                                filename=filename,
                                status=status,
                                file_link=f"/uploads/{session['username']}/{filename}"
                            )

                        if status == "duplicate":
                            # Get updated duplicate count
                            duplicate_count = count_user_duplicates(session['username'])
                            update_processing_status(
                                filename=filename,
                                status=status,
                                file_link=f"/uploads/{session['username']}/{filename}",
                                duplicate_count=duplicate_count  # Add duplicate count to status
                            )

                        time.sleep(20)
                        
                    except Exception as e:
                        # Update status to "failed"
                        update_processing_status(
                            filename=filename,
                            status=status,
                            file_link=f"/uploads/{session['username']}/{filename}"
                        )
                        print(f"Error processing {filename}: {str(e)}")
                        continue

            remove_from_queue(session['username'])

            return jsonify({'message': 'All documents processed successfully'})
        else:
            return jsonify({
                'status': 'queued',
                'position': position,
                'message': f'Your request is queued. Position: {position}'
            })

    except Exception as e:
        # Update status to "failed"
        print(f"Error in processing: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/processing-status', methods=['GET'])
def get_processing_status():

    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    status_file = get_user_status_file(session['username'])
    duplicate_count = count_user_duplicates(session['username'])
    
    try:
        if status_file.exists():
            with open(status_file, 'r') as f:
                status_data = json.load(f)
            return jsonify({
                'status_data': status_data,
                'duplicate_count': duplicate_count
            })
        return jsonify({
            'status_data': [],
            'duplicate_count': duplicate_count
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_user_folder(username):
    """Get the path to user's upload folder"""
    user_folder = UPLOAD_FOLDER / username
    user_folder.mkdir(exist_ok=True)
    return user_folder

@app.before_request
def check_session():
    """Check if user is logged in for protected routes"""
    protected_routes = ['/dashboard', '/files', '/upload', '/delete', '/process']
    if request.path in protected_routes and 'username' not in session:
        if request.is_json:
            return jsonify({'error': 'Not logged in'}), 401
        return redirect(url_for('home'))

def init_app():
    """Initialize the application"""
    # Schedule cleanup every hour
    def run_cleanup():
        while True:
            cleanup_old_status_files()
            time.sleep(3600)

    # Start cleanup thread
    from threading import Thread
    cleanup_thread = Thread(target=run_cleanup, daemon=True)
    cleanup_thread.start()

try:
    import fcntl  # For Unix systems
    def lock_file(f):
        fcntl.flock(f, fcntl.LOCK_EX)
        
    def unlock_file(f):
        fcntl.flock(f, fcntl.LOCK_UN)
        
except ImportError:  # For Windows systems
    import msvcrt
    def lock_file(f):
        while True:
            try:
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                break
            except IOError:
                time.sleep(0.1)
                
    def unlock_file(f):
        try:
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
        except IOError:
            pass

def add_to_queue(username):
    """Add a user to the processing queue"""
    queue_file = Path("queue.txt")
    
    try:
        with open(queue_file, 'a+') as f:
            lock_file(f)
            
            # Read existing queue
            f.seek(0)
            queue = f.readlines()
            
            # Check if user is already in queue
            if f"{username}\n" not in queue:
                timestamp = datetime.now().isoformat()
                f.write(f"{username},{timestamp}\n")
            
            unlock_file(f)
            
        return True
    except Exception as e:
        print(f"Error adding to queue: {str(e)}")
        return False

def remove_from_queue(username):
    """Remove a user from the processing queue"""
    queue_file = Path("queue.txt")
    temp_file = Path("queue_temp.txt")
    
    try:
        # Read current queue
        with open(queue_file, 'r') as f:
            lock_file(f)
            lines = f.readlines()
            unlock_file(f)
        
        # Write to temp file excluding the user
        with open(temp_file, 'w') as f:
            lock_file(f)
            for line in lines:
                if not line.startswith(f"{username},"):
                    f.write(line)
            unlock_file(f)
            
        # Replace original file with temp file
        os.replace(temp_file, queue_file)
            
    except Exception as e:
        print(f"Error removing from queue: {str(e)}")

def check_queue_position(username):
    """Check user's position in the queue"""
    queue_file = Path("queue.txt")
    
    try:
        if not queue_file.exists():
            return 0
            
        with open(queue_file, 'r') as f:
            lock_file(f)
            lines = f.readlines()
            unlock_file(f)
            
        # Sort by timestamp
        queue = [line.strip().split(',') for line in lines]
        queue.sort(key=lambda x: x[1])  # Sort by timestamp
        
        # Find position
        for i, (queued_username, _) in enumerate(queue):
            if queued_username == username:
                return i
                
        return -1  # Not in queue
        
    except Exception as e:
        print(f"Error checking queue: {str(e)}")
        return -1

def is_first_in_queue(username):
    """Check if user is first in queue"""
    position = check_queue_position(username)
    return position == 0

@app.route('/queue-status', methods=['GET'])
def get_queue_status():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    username = session['username']
    position = check_queue_position(username)
    
    if position == -1:
        return jsonify({
            'status': 'not_queued',
            'message': 'Not in queue'
        })
    elif position == 0:
        return jsonify({
            'status': 'processing',
            'message': 'Processing your files'
        })
    else:
        return jsonify({
            'status': 'queued',
            'position': position,
            'message': f'Your request is queued. Position: {position}'
        })

@app.route('/duplicates')
def duplicates():
    if 'username' not in session:
        return redirect(url_for('login'))
        
    # Get user's duplicates folder
    duplicates_folder = get_user_folder(session['username']) / 'duplicates'
    duplicates_folder.mkdir(exist_ok=True)
    
    # Get list of duplicate files
    files = []
    for file in duplicates_folder.glob('*.pdf'):
        # Get corresponding status file
        status_file = STATUS_FOLDER / f"{session['username']}_duplicate_status.json"
        if status_file.exists():
            with open(status_file, 'r') as f:
                status_data = json.load(f)
                files.append({
                    'name': file.name,
                    'uploaded_file': status_data.get('uploaded_file', {}),
                    'duplicates': status_data.get('duplicates', [])
                })
    
    return render_template('duplicates.html', 
                         username=session['username'],
                         files=files)

@app.route('/view_duplicate/<filename>')
def view_duplicate(filename):
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    try:
        # Get the file path from the duplicates folder
        file_path = get_user_folder(session['username']) / 'duplicates' / filename
        
        # Set the response headers for PDF display
        response = send_file(
            file_path,
            mimetype='application/pdf',
            as_attachment=False,
            download_name=filename
        )
        
        # Add headers to prevent caching
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        
        return response
        
    except Exception as e:
        logger.error(f"Error viewing duplicate: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/overwrite_duplicate', methods=['POST'])
def overwrite_duplicate():

    class GraphCreator:
        def __init__(self):
            # Neo4j connection settings
            self.uri = "bolt://localhost:7687"
            self.username = "neo4j"
            self.password = "Sagar1601"
            
            try:
                self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
                # Test the connection
                self.driver.verify_connectivity()
                logger.info("Successfully connected to Neo4j database")
            except Exception as e:
                logger.error(f"Failed to connect to Neo4j: {e}")
                raise

        def close(self):
            if hasattr(self, 'driver'):
                self.driver.close()
                logger.info("Neo4j connection closed")

        def create_graph(self, json_file_path):
            logger.info(f"Processing file: {json_file_path}")
            try:
                with open(json_file_path, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                
                with self.driver.session() as session:
                    # Helper function to ensure primitive types
                    def get_safe_value(value):
                        if isinstance(value, (str, int, float, bool)):
                            return value
                        elif isinstance(value, dict) and 'name' in value:
                            return value['name']
                        elif isinstance(value, dict):
                            return str(value)
                        elif value is None:
                            return ''
                        return str(value)

                    # Create person node with extended properties
                    session.run("""
                        MERGE (p:Person {
                            name: $name,
                            email: $email,
                            unique_number: $unique_number,
                            DOB: $dob,
                            gender: $gender,
                            marital_status: $marital_status,
                            nationality: $nationality,
                            current_position: $current_position,
                            current_employer: $current_employer,
                            number_of_years_of_experience: $number_of_years_of_experience
                        })
                    """, 
                        name=get_safe_value(data.get('name')),
                        email=get_safe_value(data.get('email')),
                        unique_number=get_safe_value(data.get('unique_number')),
                        dob=get_safe_value(data.get('DOB')),
                        gender=get_safe_value(data.get('gender')),
                        marital_status=get_safe_value(data.get('marital_status')),
                        nationality=get_safe_value(data.get('nationality')),
                        current_position=get_safe_value(data.get('current_position')),
                        current_employer=get_safe_value(data.get('current_employer')),
                        number_of_years_of_experience=get_safe_value(data.get('number_of_years_of_experience'))
                    )
                    logger.info(f"Created Person node for {data.get('name')}")

                    # Create education nodes
                    for edu in data.get('education', []):
                        session.run("""
                            MATCH (p:Person {name: $name})
                            MERGE (i:Institution {name: $institution})
                            MERGE (p)-[:STUDIED_AT {
                                degree: $degree,
                                field: $field,
                                year: $year
                            }]->(i)
                        """,
                            name=get_safe_value(data.get('name')),
                            institution=get_safe_value(edu.get('institution')),
                            degree=get_safe_value(edu.get('degree')),
                            field=get_safe_value(edu.get('field')),
                            year=get_safe_value(edu.get('year'))
                        )

                    # Create skills
                    for skill in data.get('professional_skills', []):
                        skill_name = get_safe_value(skill)
                        session.run("""
                            MATCH (p:Person {name: $name})
                            MERGE (s:Skill {name: $skill})
                            MERGE (p)-[:HAS_SKILL]->(s)
                        """, name=get_safe_value(data.get('name')), skill=skill_name)

                    # Create certifications
                    for cert in data.get('certifications', []):
                        session.run("""
                            MATCH (p:Person {name: $name})
                            MERGE (c:Certification {
                                name: $cert_name,
                                year: $cert_year,
                                id: $cert_id
                            })
                            MERGE (p)-[:HAS_CERTIFICATION]->(c)
                        """,
                            name=get_safe_value(data.get('name')),
                            cert_name=get_safe_value(cert.get('name')),
                            cert_year=get_safe_value(cert.get('year')),
                            cert_id=get_safe_value(cert.get('id'))
                        )

                    # Create languages
                    for lang in data.get('languages', []):
                        lang_name = get_safe_value(lang)
                        session.run("""
                            MATCH (p:Person {name: $name})
                            MERGE (l:Language {name: $lang})
                            MERGE (p)-[:SPEAKS]->(l)
                        """, name=get_safe_value(data.get('name')), lang=lang_name)

                    # Create projects
                    for project in data.get('projects', []):
                        session.run("""
                            MATCH (p:Person {name: $name})
                            MERGE (pr:Project {
                                name: $project_name
                            })
                            MERGE (p)-[:WORKED_ON]->(pr)
                            SET pr.skills_used = $skills_used
                        """,
                            name=get_safe_value(data.get('name')),
                            project_name=get_safe_value(project.get('name')),
                            skills_used=get_safe_value(project.get('skills_used'))
                        )

                    # Create achievements
                    for achievement in data.get('achievements', []):
                        achievement_desc = get_safe_value(achievement)
                        session.run("""
                            MATCH (p:Person {name: $name})
                            MERGE (a:Achievement {description: $achievement})
                            MERGE (p)-[:ACHIEVED]->(a)
                        """, name=get_safe_value(data.get('name')), achievement=achievement_desc)

                    # Create work experience
                    for exp in data.get('experience', []):
                        # First create the basic work experience relationship
                        session.run("""
                            MATCH (p:Person {name: $name})
                            MERGE (c:Company {name: $company})
                            MERGE (p)-[:WORKED_AT {
                                designation: $designation,
                                years: $years
                            }]->(c)
                        """, 
                            name=get_safe_value(data.get('name')),
                            company=get_safe_value(exp.get('work_at')),
                            designation=get_safe_value(exp.get('designation')),
                            years=get_safe_value(exp.get('years')),
                            unique_number=get_safe_value(data.get('unique_number'))
                        )

                        # Now process work_on field to create Technology nodes
                        work_on = get_safe_value(exp.get('work_on'))
                        if work_on:
                            # Split the work_on string into individual technologies
                            technologies = [tech.strip() for tech in work_on.split(',')]
                            for tech in technologies:
                                if tech:  # Skip empty strings
                                    session.run("""
                                        MATCH (p:Person {name: $name})
                                        MATCH (p)-[w:WORKED_AT]->(c:Company {name: $company})
                                        MERGE (t:Technology {name: $tech})
                                        MERGE (p)-[:USED_TECHNOLOGY {during: $years}]->(t)
                                    """,
                                        name=get_safe_value(data.get('name')),
                                        company=get_safe_value(exp.get('work_at')),
                                        tech=tech,
                                        years=get_safe_value(exp.get('years'))
                                    )

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in file {json_file_path}: {e}")
            except KeyError as e:
                logger.error(f"Missing required field in JSON {json_file_path}: {e}")
            except Exception as e:
                logger.error(f"Error processing file {json_file_path}: {e}")

    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    data = request.get_json()
    filename = data.get('filename')
    if not filename:
        return jsonify({'error': 'No filename provided'}), 400
        
    try:
        # Source paths in duplicates folder
        source_pdf = get_user_folder(session['username']) / 'duplicates' / filename
        source_json = get_user_folder(session['username']) / 'duplicates' / (filename.rsplit('.', 1)[0] + '.json')

        PROCESSED_FOLDER = Path("processed")
        PROCESSED_FOLDER.mkdir(exist_ok=True)

        list_of_json_files = []
        for file in os.listdir(get_user_folder(session['username']) / 'duplicates'):
            if file.endswith('.json'):
                list_of_json_files.append(file)

        def get_matching_json(pdf_file, json_files):
            unique_number = int(os.path.basename(pdf_file).split("_")[0].lstrip("0"))
            for json_file in json_files:
                json_number = int(os.path.basename(json_file).split("_")[0].lstrip("0"))
                if json_number == unique_number:
                    return json_file
            return None

        # Get the matching JSON file
        matching_json = get_matching_json(source_pdf, list_of_json_files)

        creator = GraphCreator()
        creator.create_graph(str(get_user_folder(session['username']) / 'duplicates' / matching_json))
        creator.close()

        # Remove the files from duplicates folder
        if source_pdf.exists():
            os.remove(source_pdf)
        if source_json.exists():
            os.remove(str(get_user_folder(session['username']) / 'duplicates' / matching_json))
            
        # Get updated list of duplicate files
        duplicate_files = []
        duplicates_folder = get_user_folder(session['username']) / 'duplicates'
        for file in os.listdir(duplicates_folder):
            if file.endswith('.pdf'):
                duplicate_files.append(file)
        
        # Update the session with new list
        session['duplicate_files'] = duplicate_files

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': True})

@app.route('/get_duplicates/<filename>')
def get_duplicates(filename):
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    try:
        # Connect to Neo4j and fetch duplicates
        driver = GraphDatabase.driver(uri, auth=(username, password))
        with driver.session() as session:
            # Query to find potential duplicates based on name and DOB
            result = session.run("""
                MATCH (p:Person)
                WHERE p.name = $name OR p.DOB = $dob
                RETURN p.name as name, p.DOB as dob, p.current_position as role
            """, name=filename_to_name(filename))
            
            duplicates = [dict(record) for record in result]
            return jsonify(duplicates)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/handle_duplicate_action', methods=['POST'])
def handle_duplicate_action():
    data = request.get_json()
    action = data.get('action')
    selected_id = data.get('selected_id')
    filename = data.get('filename')
    
    if action == 'doNotUpload':
        # Delete the file
        return delete_duplicate(filename)
    elif action == 'overwrite':
        # Overwrite the selected entry
        return overwrite_duplicate(filename, selected_id)
    elif action == 'differentPerson':
        # Process as new person
        return process_as_new_person(filename)

def filename_to_name(filename):
    """Extract name from filename by removing unique number prefix and extension"""
    # Remove unique number prefix (7 digits + underscore) and .pdf extension
    return filename[8:].rsplit('.', 1)[0].replace('_', ' ')

def process_as_new_person(filename):
    """Process file as a new person, ignoring potential duplicates"""
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    try:
        # Move file from duplicates to main upload folder
        source = get_user_folder(session['username']) / 'duplicates' / filename
        dest = get_user_folder(session['username']) / filename
        shutil.move(str(source), str(dest))
        
        # Add to processing queue
        add_to_queue(session['username'])
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/process_as_new', methods=['POST'])
def process_as_new():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    data = request.get_json()
    filename = data.get('filename')
    
    try:
        # Move file from duplicates to main upload folder
        source = get_user_folder(session['username']) / 'duplicates' / filename
        destination = get_user_folder(session['username']) / filename
        
        shutil.move(str(source), str(destination))
        
        # Also move the JSON file if it exists
        json_filename = filename.rsplit('.', 1)[0] + '.json'
        json_source = get_user_folder(session['username']) / 'duplicates' / json_filename
        if json_source.exists():
            os.remove(json_source)
            
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error processing as new: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/delete_duplicate', methods=['POST'])
def delete_duplicate():
    if 'username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    data = request.get_json()
    filename = data.get('filename')
    
    try:
        # Delete both PDF and JSON files
        duplicate_folder = get_user_folder(session['username']) / 'duplicates'
        pdf_path = duplicate_folder / filename
        json_filename = filename.rsplit('.', 1)[0] + '.json'
        json_path = duplicate_folder / json_filename
        
        if pdf_path.exists():
            os.remove(pdf_path)
        if json_path.exists():
            os.remove(json_path)
            
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error deleting duplicate: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    init_app()
    app.run(debug=True, port=6001, host='0.0.0.0')