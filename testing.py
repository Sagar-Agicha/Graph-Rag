from neo4j import GraphDatabase

# Neo4j connection details
NEO4J_URI = "bolt://192.168.10.159:7687"  # Update if needed
USERNAME = "neo4j"  # Replace with your Neo4j username
PASSWORD = "Sagar1601"  # Replace with your Neo4j password

class Neo4jQuery:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def find_person_by_name_and_dob(self, name, dob):
        # First check if name exists
        name_query = """
        MATCH (p:Person)
        WHERE toLower(p.name) = toLower($name)
        RETURN p.DOB AS dob
        """
        with self.driver.session() as session:
            result = session.run(name_query, name=name)
            record = result.single()
            
            if record is None:
                return False
                
            # If name found, verify DOB matches
            stored_dob = record["dob"]
            return stored_dob == dob

# Instantiate the Neo4jQuery class
db = Neo4jQuery(NEO4J_URI, USERNAME, PASSWORD)

# Input details
input_name = "Kalim Nabban khan"  # Replace with the name to search
input_dob = "10/12/1997"  # Replace with the DOB to search

# Check if the person exists
person_found = db.find_person_by_name_and_dob(input_name, input_dob)
if person_found:
    print(f"Person with name '{input_name}' and DOB '{input_dob}' found.")
    # # Retrieve all names if the person is found
    # all_names = db.get_all_person_names()
    # print("All names in the database:")
    # print(all_names)
else:
    print(f"Person with name '{input_name}' and DOB '{input_dob}' not found.")

# Close the connection
db.close()
