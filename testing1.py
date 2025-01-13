from neo4j import GraphDatabase


uri = "bolt://localhost:7687"
username = "neo4j"
password = "neo4j"
driver = GraphDatabase.driver(uri, auth=(username, password))
driver.verify_connectivity()

