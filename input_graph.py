from neo4j import GraphDatabase
import json
import os
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
                        years=get_safe_value(exp.get('years'))
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

def main():
    # Get the output folder path
    output_folder = Path("output")
    
    if not output_folder.exists():
        logger.error("Output folder not found!")
        return

    # Create graph
    creator = GraphCreator()
    try:
        # Process all JSON files in the output folder
        json_files = list(output_folder.glob("*.json"))
        
        if not json_files:
            logger.warning("No JSON files found in output folder!")
            return

        logger.info(f"Found {len(json_files)} JSON files to process")
        
        for json_file in json_files:
            logger.info(f"Processing {json_file}")
            creator.create_graph(json_file)
            
        logger.info("All files processed successfully!")
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
    finally:
        creator.close()

if __name__ == "__main__":
    main() 