from neo4j import GraphDatabase, RoutingControl
from neo4j.exceptions import DriverError, Neo4jError

class GraphRepository:
    def __init__(self, uri, user, password, database=None):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.database = database
        self.driver.verify_connectivity()

    def close(self):        
        self.driver.close()

    def create_node(self, node_label, extracted_data):
        """
        Creates a node in the graph database with the specified label and data.
        """
        query = f"""
        CREATE (n: {node_label}) 
        SET n += $props
        SET n.uuid = randomUUID()
        RETURN n"""

        records, summary, keys = self.driver.execute_query(
            query,
            props=extracted_data,
            database_=self.database
        )

        return records[0]["n"]

    def create_relationship(self, from_node_id, to_node_id, relationship_type):
        """
        Creates a relationship of the specified type between two nodes identified by their IDs if it doesn't already exist.
        """
        # merge checks if the relationship already exists, if not it creates it instead of creating duplicate relationships
        query = f"""
        MATCH (a {{uuid: $from_uuid}})
        MATCH (b {{uuid: $to_uuid}})
        MERGE (a)-[r:{relationship_type}]->(b) 
        RETURN r
        """

        records, _, _ = self.driver.execute_query(
            query,
            from_uuid=from_node_id,
            to_uuid=to_node_id,
            database_=self.database
        )

        return records[0]["r"]

    def query(self):
        pass

    def delete_node(self):
        pass