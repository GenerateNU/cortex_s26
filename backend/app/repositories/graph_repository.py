from neo4j import GraphDatabase, RoutingControl
from neo4j.exceptions import DriverError, Neo4jError
class GraphRepository:

    def __init__(self, uri, user, password, database=None):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.database = database
        self.driver.verify_connectivity()
        self._valid_labels: set[str] = set()
        self._valid_relationship_types: set[str] = set()

    def set_valid_labels(self, labels: set[str]):
        """Set the allowed node labels for validation. Called by GraphService before syncing."""
        self._valid_labels = labels

    def set_valid_relationship_types(self, types: set[str]):
        """Set the allowed relationship types for validation. Called by GraphService before syncing."""
        self._valid_relationship_types = types

    def close(self):        
        self.driver.close()

    def create_node(self, tenant_id, node_label, node_id, extracted_data):
        """
        Creates a node in the graph database with the specified label and data.
        If a node with the same tenant_id and uuid already exists, it updates the properties instead.
        """
        if self._valid_labels and node_label not in self._valid_labels:
            raise ValueError(f"Invalid node label: {node_label}. Allowed labels are: {self._valid_labels}")
        
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
        if self._valid_relationship_types and relationship_type not in self._valid_relationship_types:
            raise ValueError(f"Invalid relationship type: {relationship_type}. Allowed types are: {self._valid_relationship_types}")

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

    def cleanup_orphaned_nodes(self, tenant_id, current_ids):
        """
        Remove nodes for a tenant that are no longer present in Supabase.
        Returns count of nodes removed.
        """
        query = """
        MATCH (n {tenant_id: $tenant_id})
        WHERE NOT n.uuid IN $current_ids
        DETACH DELETE n
        RETURN count(n) as removed
        """

        records, _, _ = self.driver.execute_query(
            query,
            tenant_id=tenant_id,
            current_ids=list(current_ids),
            database_=self.database
        )

        return records[0]["removed"] if records else 0

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














