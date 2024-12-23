import os
import openai
from neo4j import GraphDatabase
import logging
from typing import Dict, List, Any
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GraphSearcher:
    def __init__(self):
        # Neo4j connection
        self.uri = "bolt://localhost:7687"
        self.username = "neo4j"
        self.password = "Sagar1601"
        
        # Sambanova settings
        self.client = openai.OpenAI(
            api_key=os.environ.get("SAMBANOVA_API_KEY"),
            base_url=os.environ.get("SAMBANOVA_BASE_URL")
        )

        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
            self.driver.verify_connectivity()
            logger.info("Connected to Neo4j successfully")
            
        except Exception as e:
            logger.error(f"Connection error: {e}")
            raise

    def close(self):
        self.driver.close()

    def query_to_cypher(self, query: str) -> str:
        """Convert natural language query to Cypher using Sambanova"""
        try:
            response = self.client.chat.completions.create(
                model='Meta-Llama-3.1-8B-Instruct',
                messages=[
                    {"role": "system", "content": """
                        You are an expert in Neo4j and Cypher query language. Your task is to convert natural language queries into precise Cypher statements using the given database schema.
                        Return only the Cypher query with no additional responses.
                        If asked for skills or certifications, return only `p.name AS Name`.
                        If specifically asked for email, return only `p.email AS Email`.
                        For numeric comparisons, ensure to convert string fields to integers using toInteger().
                        Use `CONTAINS` or `STARTS WITH` for partial matches in skill names.
                        For exact word matches within a sentence, use regular expressions to ensure the word is matched as a standalone word.

                        ### Database Schema
                        Nodes:
                        - (:Person {name, email, DOB, gender, marital_status, nationality, current_position, current_employer, number_of_years_of_experience})
                        - (:Language {name})
                        - (:Skill {name})
                        - (:Certification {name, year, id})
                        - (:Company {name, domain})
                        - (:Institution {name, domain})
                        - (:Achievement {description})
                        - (:Project {name, skills_used})
                        - (:Experience {company, role, duration})
                        - (:Technology {name})

                        Relationships:
                        - [:HAS_SKILL] between `Person` and `Skill`
                        - [:SPEAKS] between `Person` and `Language`
                        - [:HAS_CERTIFICATION] between `Person` and `Certification`
                        - [:WORKED_AT] between `Person` and `Experience`
                        - [:STUDIED_AT] between `Person` and `Institution`
                        - [:ACHIEVED] between `Person` and `Achievement`
                        - [:WORKED_ON] between `Person` and `Project`
                        - [:USED_TECHNOLOGY] between `Person` and `Technology`

                        ### Instructions:
                        1. Use OPTIONAL MATCH to include partial matches.
                        2. Combine results from multiple relationships when necessary.
                        3. Ensure the query adheres to the schema.
                        4. Return DISTINCT results to avoid duplicates.

                        ### Examples:
                        #### Example 1:
                        **Natural Language Query**: Find all people skilled in Python with a certification in data science.
                        **Cypher Query**:
                        OPTIONAL MATCH (p:Person)-[:HAS_SKILL]->(s:Skill {name: "Python"})
                        OPTIONAL MATCH (p)-[:HAS_CERTIFICATION]->(c:Certification {name: "Data Science"})
                        RETURN DISTINCT p.name AS Name

                        #### Example 2:
                        **Natural Language Query**: Show me all people who who have more then 3 years of experience 
                        **Cypher Query**:
                        MATCH (p:Person)
                        WHERE toInteger(p.number_of_years_of_experience) > 3
                        RETURN p.name as Name   
                     
                        #### Example 3:
                        **Natural Language Query**: Show me all the people who are skilled in Nutanix.
                        **Cypher Query**:
                        MATCH (p:Person)-[:HAS_SKILL]->(s:Skill)
                        WHERE toLower(s.name) CONTAINS toLower('nutanix')
                        RETURN DISTINCT p.name AS Name

                        Return only cypher query no addiational responses.
                        Validate the response again, only cypher query nothing else.
                        """},
                    {"role": "user", "content": query}
                ],
                temperature=0.0,
                top_p=0.1
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error in query conversion: {e}")
            return None

    def format_results(self, results: List[Dict[str, Any]]) -> str:
        """Format results into a natural language response using Sambanova"""
        if not results:
            return "No results found."
            
        try:
            response = self.client.chat.completions.create(
                model='Meta-Llama-3.1-8B-Instruct',
                messages=[
                    {"role": "system", "content": "Convert database results into natural language response. Be concise and clear."},
                    {"role": "user", "content": f"Convert these results to natural language just names nothing else and if any fields are empty delete it from the response and give each name in a new line: {json.dumps(results)}"}
                ],
                temperature=0.0,
                top_p=0.0
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error in result formatting: {e}")
            return str(results)  # Fallback to raw results


    def search(self, user_query: str) -> str:
        try:
            # Convert natural language to Cypher
            cypher_query = self.query_to_cypher(user_query)
            cypher_query = cypher_query.replace("\n", " ")
            print("cypher_query = ", cypher_query)
            if not cypher_query:
                return "Sorry, I couldn't understand the query."

            # Add debug query to list all certifications
            with self.driver.session() as session:
                results = list(session.run(cypher_query))
                results_list = [record.data() for record in results]

            print("results_list = ", results_list)

            return self.format_results(results_list)

        except Exception as e:
            logger.error(f"Search error: {e}")
            return f"An error occurred: {str(e)}"

def main():
    searcher = GraphSearcher()
    
    try:
        print("Graph Search System (type 'exit' to quit)")
        print("\nExample queries:")
        print("- Show me all people with Python skills")
        print("- Find people who worked at Google")
        print("- Show certifications for John Doe")
        
        while True:
            query = input("\nEnter your query (or 'exit' to quit): ").strip()
            
            if query.lower() == 'exit':
                break
            
            result = searcher.search(query)
            print("\nResult:", result)
            
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        searcher.close()

if __name__ == "__main__":
    main() 