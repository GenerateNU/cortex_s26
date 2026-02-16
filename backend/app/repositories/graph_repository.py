from neo4j import GraphDatabase, RoutingControl
from neo4j.exceptions import DriverError, Neo4jError

class GraphRepository:
    node_labels = {"Product Specs", "Sales Records", "Customers", "RFQs", "Configurations", "Quotes", "Purchase Orders"}
    relationship_types = {"SOLD_TO", "CONTAINS_ITEM", "CONFIGURED_FOR", "QUOTED_FOR", "ORDERED_BY"}

    def __init__(self, uri, user, password, database=None):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.database = database
        self.driver.verify_connectivity()

    def close(self):        
        self.driver.close()

    def create_node(self, tenant_id, node_label, node_id, extracted_data):
        """
        Creates a node in the graph database with the specified label and data.
        If a node with the same tenant_id and uuid already exists, it updates the properties instead.
        """
        if node_label not in self.node_labels:
            raise ValueError(f"Invalid node label: {node_label}. Allowed labels are: {self.node_labels}")
        
        query = f"""
        MERGE (n:{node_label} {{tenant_id: $tenant_id, uuid: $uuid}})
        SET n += $props
        RETURN n"""

        records, summary, keys = self.driver.execute_query(
            query,
            tenant_id=tenant_id,
            uuid=node_id,
            props=extracted_data,
            database_=self.database
        )

        return records[0]["n"]

    def create_relationship(self, tenant_id, from_node_id, to_node_id, relationship_type):
        """
        Creates a relationship of the specified type between two nodes identified by their IDs if it doesn't already exist.
        """
        if relationship_type not in self.relationship_types:
            raise ValueError(f"Invalid relationship type: {relationship_type}. Allowed types are: {self.relationship_types}")
        # merge checks if the relationship already exists, if not it creates it instead of creating duplicate relationships
        query = f"""
        MATCH (a {{tenant_id: $tenant_id, uuid: $from_uuid}})
        MATCH (b {{tenant_id: $tenant_id, uuid: $to_uuid}})
        MERGE (a)-[r:{relationship_type}]->(b) 
        RETURN r
        """

        records, _, _ = self.driver.execute_query(
            query,
            tenant_id=tenant_id,
            from_uuid=from_node_id,
            to_uuid=to_node_id,
            database_=self.database
        )

        return records[0]["r"]

    def query(self, query, **kwargs):
        """
        Executes a Cypher query with the provided parameters and returns the results.
        """
        records, summary, keys = self.driver.execute_query(
            query,
            **kwargs,
            database_=self.database
        )
        return records
        

    def delete_node(self, tenant_id, node_id):
        query = """
        MATCH (n {tenant_id: $tenant_id, uuid: $node_id})
        DETACH DELETE n
        """
        self.driver.execute_query(
            query,
            tenant_id=tenant_id,
            node_id=node_id,
            database_=self.database
        )

    def delete_relationship(self, tenant_id, from_node_id, to_node_id, relationship_type):
        query = f"""
        MATCH (a {{tenant_id: $tenant_id, uuid: $from_uuid}})
              -[r:{relationship_type}]->
              (b {{tenant_id: $tenant_id, uuid: $to_uuid}})
        DELETE r
        """
        self.driver.execute_query(
            query,
            tenant_id=tenant_id,
            from_uuid=from_node_id,
            to_uuid=to_node_id,
            database_=self.database
        )