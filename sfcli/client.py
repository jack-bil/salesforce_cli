"""
Salesforce Client Wrapper

Handles authentication and provides methods for querying Salesforce.
"""
import os
from typing import Dict, List, Any, Optional
from simple_salesforce import Salesforce, SalesforceAuthenticationFailed
from dotenv import load_dotenv


class SalesforceClient:
    """Wrapper around SimpleSalesforce for easier interaction."""
    
    def __init__(self):
        """Initialize Salesforce connection using environment variables."""
        load_dotenv()
        
        username = os.getenv('SF_USERNAME')
        password = os.getenv('SF_PASSWORD')
        security_token = os.getenv('SF_SECURITY_TOKEN')
        domain = os.getenv('SF_DOMAIN', 'login')
        
        if not all([username, password, security_token]):
            raise ValueError(
                "Missing Salesforce credentials. Please create a .env file with:\n"
                "SF_USERNAME, SF_PASSWORD, SF_SECURITY_TOKEN, and SF_DOMAIN"
            )
        
        try:
            self.sf = Salesforce(
                username=username,
                password=password,
                security_token=security_token,
                domain=domain
            )
            self._object_cache = {}
        except SalesforceAuthenticationFailed as e:
            raise ValueError(f"Salesforce authentication failed: {e}")
    
    def search_with_stats(self, object_type: str, query: str, limit: int = 200, fields: Optional[List[str]] = None) -> tuple[List[Dict[str, Any]], int]:
        """
        Search for records in Salesforce and return results with total count.
        
        Args:
            object_type: Salesforce object type (e.g., 'Account', 'Contact')
            query: Search query string
            limit: Maximum number of results (default: 200, max: 2000)
            fields: Optional list of fields to return (e.g., ['Name', 'Type', 'Phone'])
            
        Returns:
            Tuple of (List of matching records, total count of matches)
        """
        # First get the limited results
        results = self.search(object_type, query, limit, fields)
        
        # Then get total count without limit
        try:
            name_field = self._get_name_field(object_type)
            count_soql = f"""
                SELECT COUNT()
                FROM {object_type}
                WHERE {name_field} LIKE '%{query}%'
            """
            count_result = self.sf.query(count_soql)
            total_count = count_result.get('totalSize', len(results))
        except:
            # If count query fails, just use the result count
            total_count = len(results)
        
        return results, total_count
    
    def search(self, object_type: str, query: str, limit: int = 200, fields: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Search for records in Salesforce using SOSL (Salesforce Object Search Language).
        This matches the global search behavior in the Salesforce UI.
        
        Args:
            object_type: Salesforce object type (e.g., 'Account', 'Contact')
            query: Search query string
            limit: Maximum number of results (default: 200, max: 2000)
            fields: Optional list of fields to return (e.g., ['Name', 'Type', 'Phone'])
            
        Returns:
            List of matching records
        """
        # Use SOSL (Salesforce Object Search Language) for more comprehensive search
        # This searches across multiple fields, similar to Salesforce UI search
        try:
            # Determine fields to return
            if fields:
                # Use custom fields if provided
                fields_str = ', '.join(fields)
            elif object_type == 'Account':
                fields_str = 'Id, Name, ParentId, Ultimate_Parent__c, ShippingStreet, ShippingCity, ShippingState, ShippingPostalCode'
            else:
                fields_str = 'Id, Name'
            
            # Build SOSL query - searches all text fields in the object
            # If query already has quotes, use it as-is; otherwise wrap in quotes for exact phrase matching
            if query.startswith('"') and query.endswith('"'):
                search_term = query
            else:
                # For multi-word searches without quotes, wrap in quotes for phrase matching
                search_term = f'"{query}"' if ' ' in query else query
            
            sosl = f"FIND {{{search_term}}} IN ALL FIELDS RETURNING {object_type}({fields_str} ORDER BY Name LIMIT {limit})"
            
            result = self.sf.search(sosl)
            
            # SOSL returns results grouped by object type
            search_records = result.get('searchRecords', [])
            
            # If SOSL returns results, return them
            if search_records:
                return search_records
            
            # Fallback to SOQL if SOSL returns nothing
            # This handles cases where the search term might be too short or special
            name_field = self._get_name_field(object_type)
            
            if fields:
                soql_fields = ', '.join(fields)
            elif object_type == 'Account':
                soql_fields = f"Id, {name_field}, ParentId, Ultimate_Parent__c, ShippingStreet, ShippingCity, ShippingState, ShippingPostalCode"
            else:
                soql_fields = f"Id, {name_field}"
            
            soql = f"""
                SELECT {soql_fields}
                FROM {object_type}
                WHERE {name_field} LIKE '%{query}%'
                ORDER BY {name_field}
                LIMIT {limit}
            """
            
            result = self.sf.query(soql)
            return result['records']
            result = self.sf.query(soql)
            return result['records']
            
        except Exception as e:
            # If SOSL fails, fall back to SOQL
            name_field = self._get_name_field(object_type)
            
            if fields:
                soql_fields = ', '.join(fields)
            elif object_type == 'Account':
                soql_fields = f"Id, {name_field}, ParentId, Ultimate_Parent__c, ShippingStreet, ShippingCity, ShippingState, ShippingPostalCode"
            else:
                soql_fields = f"Id, {name_field}"
            
            soql = f"""
                SELECT {fields}
                FROM {object_type}
                WHERE {name_field} LIKE '%{query}%'
                ORDER BY {name_field}
                LIMIT {limit}
            """
            
            result = self.sf.query(soql)
            return result['records']
    
    def query(self, soql: str) -> Dict[str, Any]:
        """
        Execute a SOQL query and return the full result.
        
        Args:
            soql: SOQL query string
            
        Returns:
            Query result dictionary with 'records' and 'totalSize'
        """
        return self.sf.query(soql)
    
    def get_record(self, object_type: str, record_id: str) -> Dict[str, Any]:
        """
        Get a specific record by ID.
        
        Args:
            object_type: Salesforce object type
            record_id: Record ID (18-character Salesforce ID)
            
        Returns:
            Record data as dictionary
        """
        obj = getattr(self.sf, object_type)
        return obj.get(record_id)
    
    def update_record(self, object_type: str, record_id: str, data: Dict[str, Any]) -> bool:
        """
        Update a record with new field values.
        
        Args:
            object_type: Salesforce object type
            record_id: Record ID to update
            data: Dictionary of field names and new values
            
        Returns:
            True if successful, False otherwise
        """
        try:
            obj = getattr(self.sf, object_type)
            result = obj.update(record_id, data)
            # SimpleSalesforce returns HTTP status code
            return result in [200, 204]
        except Exception as e:
            raise ValueError(f"Failed to update record: {e}")
    
    def get_record_with_fields(self, object_type: str, record_id: str, fields: List[str]) -> Dict[str, Any]:
        """
        Get a specific record with selected fields.
        
        Args:
            object_type: Salesforce object type
            record_id: Record ID
            fields: List of fields to retrieve
            
        Returns:
            Record data as dictionary
        """
        fields_str = ', '.join(fields)
        soql = f"SELECT {fields_str} FROM {object_type} WHERE Id = '{record_id}'"
        result = self.sf.query(soql)
        
        if result['totalSize'] == 0:
            raise ValueError(f"Record {record_id} not found")
        
        return result['records'][0]
    
    def get_related_records(self, object_type: str, record_id: str, 
                          relationship_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get related records (e.g., Contacts for an Account).
        
        Args:
            object_type: Parent object type
            record_id: Parent record ID
            relationship_name: Relationship name (e.g., 'Contacts', 'Opportunities')
            limit: Maximum number of results
            
        Returns:
            List of related records
        """
        # First, try to find the relationship in child relationships
        relationships = self.get_child_relationships(object_type)
        relationship_field = None
        actual_object = None
        
        for rel in relationships:
            if rel['name'] == relationship_name:
                actual_object = rel['object']
                relationship_field = rel['field']
                break
        
        # If not found, try legacy mapping for backwards compatibility
        if not actual_object:
            object_mapping = {
                'Contacts': 'Contact',
                'Opportunities': 'Opportunity',
                'OpportunityLineItems': 'OpportunityLineItem',
                'Cases': 'Case',
                'Tasks': 'Task',
                'Events': 'Event',
                'Leads': 'Lead',
                'Contracts': 'Contract',
                'Orders': 'Order',
                'Assets': 'Asset',
                'Invoices': 'Invoice',
                'Quotes': 'SBQQ__Quote__c',
                'Accounts': 'Account',
                'Products': 'Product2',
            }
            actual_object = object_mapping.get(relationship_name, relationship_name)
            relationship_field = self._get_relationship_field(object_type, actual_object, record_id)
        
        if not relationship_field:
            raise ValueError(f"Could not determine relationship field for {relationship_name} to {object_type}")
        
        # Get appropriate fields for this object type
        fields = self._get_query_fields(actual_object)
        fields_str = ', '.join(fields)
        
        soql = f"""
            SELECT {fields_str}
            FROM {actual_object}
            WHERE {relationship_field} = '{record_id}'
            LIMIT {limit}
        """
        
        result = self.sf.query(soql)
        return result['records']
    
    def execute_query(self, soql: str) -> List[Dict[str, Any]]:
        """
        Execute a raw SOQL query.
        
        Args:
            soql: SOQL query string
            
        Returns:
            List of records
        """
        result = self.sf.query(soql)
        return result['records']
    
    def describe_object(self, object_type: str) -> Dict[str, Any]:
        """
        Get metadata about a Salesforce object.
        
        Args:
            object_type: Salesforce object type
            
        Returns:
            Object metadata
        """
        if object_type not in self._object_cache:
            obj = getattr(self.sf, object_type)
            self._object_cache[object_type] = obj.describe()
        
        return self._object_cache[object_type]
    
    def get_child_relationships(self, object_type: str) -> List[Dict[str, str]]:
        """
        Get all child relationships for an object.
        
        Args:
            object_type: Salesforce object type
            
        Returns:
            List of dictionaries with relationship info: 
            [{'name': 'Contacts', 'object': 'Contact', 'field': 'AccountId'}, ...]
        """
        metadata = self.describe_object(object_type)
        relationships = []
        
        # Get child relationships from the object metadata
        for child_rel in metadata.get('childRelationships', []):
            if child_rel.get('relationshipName'):  # Has a queryable relationship name
                relationships.append({
                    'name': child_rel['relationshipName'],
                    'object': child_rel['childSObject'],
                    'field': child_rel['field'],
                    'cascadeDelete': child_rel.get('cascadeDelete', False)
                })
        
        return relationships
    
    def get_field_names(self, object_type: str) -> List[str]:
        """
        Get all field names for an object.
        
        Args:
            object_type: Salesforce object type
            
        Returns:
            List of field names
        """
        metadata = self.describe_object(object_type)
        return [field['name'] for field in metadata['fields']]
    
    def describe_detailed(self, object_type: str) -> Dict[str, Any]:
        """
        Get detailed metadata about an object including fields, relationships, and properties.
        
        Args:
            object_type: Salesforce object type
            
        Returns:
            Dictionary with organized metadata:
            - object_info: Basic object properties
            - fields: Field metadata organized by category
            - relationships: Parent and child relationships
            - permissions: CRUD permissions
        """
        metadata = self.describe_object(object_type)
        
        # Organize fields by category
        standard_fields = []
        custom_fields = []
        system_fields = []
        formula_fields = []
        lookup_fields = []
        
        for field in metadata['fields']:
            field_info = {
                'name': field['name'],
                'label': field['label'],
                'type': field['type'],
                'length': field.get('length'),
                'precision': field.get('precision'),
                'scale': field.get('scale'),
                'required': not field['nillable'] and not field['defaultedOnCreate'],
                'unique': field.get('unique', False),
                'externalId': field.get('externalId', False),
                'calculated': field.get('calculated', False),
                'picklistValues': [v['value'] for v in field.get('picklistValues', [])] if field.get('picklistValues') else None,
                'referenceTo': field.get('referenceTo', []),
                'relationshipName': field.get('relationshipName'),
                'helpText': field.get('inlineHelpText'),
            }
            
            # Categorize fields
            if field['calculated']:
                formula_fields.append(field_info)
            elif field.get('referenceTo'):
                lookup_fields.append(field_info)
            elif field['custom']:
                custom_fields.append(field_info)
            elif field['name'] in ['Id', 'CreatedDate', 'CreatedById', 'LastModifiedDate', 'LastModifiedById', 'SystemModstamp']:
                system_fields.append(field_info)
            else:
                standard_fields.append(field_info)
        
        # Get relationships
        parent_relationships = []
        child_relationships = []
        
        for field in metadata['fields']:
            if field.get('referenceTo') and field.get('relationshipName'):
                parent_relationships.append({
                    'field': field['name'],
                    'relationshipName': field['relationshipName'],
                    'referenceTo': field['referenceTo']
                })
        
        for rel in metadata.get('childRelationships', []):
            if rel.get('relationshipName'):
                child_relationships.append({
                    'name': rel['relationshipName'],
                    'object': rel['childSObject'],
                    'field': rel['field']
                })
        
        return {
            'object_info': {
                'name': metadata['name'],
                'label': metadata['label'],
                'labelPlural': metadata['labelPlural'],
                'custom': metadata['custom'],
                'queryable': metadata['queryable'],
                'searchable': metadata['searchable'],
                'createable': metadata['createable'],
                'updateable': metadata['updateable'],
                'deletable': metadata['deletable'],
                'undeletable': metadata.get('undeletable', False),
                'triggerable': metadata.get('triggerable', False),
                'recordTypeInfos': len(metadata.get('recordTypeInfos', [])),
            },
            'fields': {
                'standard': standard_fields,
                'custom': custom_fields,
                'system': system_fields,
                'formula': formula_fields,
                'lookup': lookup_fields,
            },
            'relationships': {
                'parent': parent_relationships,
                'child': child_relationships,
            },
            'counts': {
                'total_fields': len(metadata['fields']),
                'standard_fields': len(standard_fields),
                'custom_fields': len(custom_fields),
                'formula_fields': len(formula_fields),
                'lookup_fields': len(lookup_fields),
                'child_relationships': len(child_relationships),
            }
        }
    
    def get_field_history(self, object_type: str, record_id: str, field_name: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get field history for a record. If field_name is provided, returns history for that field only.
        If field_name is None, returns all field changes for the record.
        
        Args:
            object_type: Salesforce object type (e.g., 'Account', 'Opportunity')
            record_id: Record ID
            field_name: Optional field name to filter history (if None, returns all fields)
            limit: Maximum number of history records to return
            
        Returns:
            List of history records with CreatedDate, CreatedBy, Field, OldValue, NewValue
        """
        # Salesforce stores field history in {Object}History tables
        history_object = f"{object_type}History"
        
        # The parent field name varies by object
        # Most use {Object}Id, but some use ParentId
        parent_field = f"{object_type}Id"
        
        try:
            if field_name:
                # Get history for specific field
                soql = f"""
                    SELECT Id, Field, OldValue, NewValue, CreatedDate, CreatedBy.Name
                    FROM {history_object}
                    WHERE {parent_field} = '{record_id}' AND Field = '{field_name}'
                    ORDER BY CreatedDate DESC
                    LIMIT {limit}
                """
            else:
                # Get all field history for the record
                soql = f"""
                    SELECT Id, Field, OldValue, NewValue, CreatedDate, CreatedBy.Name
                    FROM {history_object}
                    WHERE {parent_field} = '{record_id}'
                    ORDER BY CreatedDate DESC
                    LIMIT {limit}
                """
            
            result = self.sf.query(soql)
            return result['records']
        except Exception as e:
            # If history tracking isn't enabled for this object/field, return empty
            return []
    
    def list_objects(self, show_all: bool = False) -> List[str]:
        """
        List available Salesforce objects.
        
        Args:
            show_all: If True, show all objects including system objects
            
        Returns:
            List of object names
        """
        describe = self.sf.describe()
        objects = []
        
        for obj in describe['sobjects']:
            if show_all or obj['customSetting'] is False:
                # Filter out system objects unless show_all is True
                if show_all or (obj['queryable'] and obj['createable']):
                    objects.append(obj['name'])
        
        return objects
    
    def get_common_fields(self, object_type: str) -> List[str]:
        """
        Get commonly used fields for an object type.
        
        Args:
            object_type: Salesforce object type
            
        Returns:
            List of field names
        """
        metadata = self.describe_object(object_type)
        
        # Common field patterns to look for
        common_patterns = ['Name', 'Id', 'Email', 'Phone', 'Type', 'Status', 
                          'Owner', 'CreatedDate', 'LastModifiedDate', 'Description']
        
        fields = []
        for field in metadata['fields']:
            field_name = field['name']
            # Include ID and Name by default
            if field_name in ['Id', 'Name']:
                fields.append(field_name)
            # Include other common fields
            elif any(pattern in field_name for pattern in common_patterns):
                fields.append(field_name)
        
        return fields[:20]  # Limit to 20 fields for readability
    
    def _get_name_field(self, object_type: str) -> str:
        """Get the primary name field for an object."""
        metadata = self.describe_object(object_type)
        
        # Look for Name field
        for field in metadata['fields']:
            if field['name'] == 'Name' and field['type'] == 'string':
                return 'Name'
        
        # Fallback to first string field
        for field in metadata['fields']:
            if field['type'] == 'string' and field['name'] != 'Id':
                return field['name']
        
        return 'Id'  # Fallback to Id if no string fields
    
    def _get_query_fields(self, object_type: str, max_fields: int = 5) -> List[str]:
        """Get appropriate fields for querying an object."""
        metadata = self.describe_object(object_type)
        fields = ['Id']  # Always include Id
        
        # Preferred field names in order of priority
        preferred_fields = [
            'Name', 'Subject', 'Title', 'Status', 'Type', 
            'Priority', 'Description', 'ActivityDate', 'DueDate',
            'Email', 'Phone', 'Company', 'Amount', 'StageName',
            'CloseDate', 'CreatedDate'
        ]
        
        field_names = {f['name']: f for f in metadata['fields']}
        
        # Add preferred fields that exist
        for pref in preferred_fields:
            if pref in field_names and len(fields) < max_fields:
                fields.append(pref)
        
        # If we don't have enough fields, add some more
        if len(fields) < max_fields:
            for field in metadata['fields']:
                if field['name'] not in fields and field['type'] in ['string', 'picklist', 'boolean']:
                    fields.append(field['name'])
                    if len(fields) >= max_fields:
                        break
        
        return fields
    
    def _get_relationship_field(self, parent_object: str, child_object: str, parent_id: str) -> Optional[str]:
        """
        Dynamically determine the relationship field by inspecting the child object's fields.
        
        Args:
            parent_object: The parent object type (e.g., 'Account', 'Opportunity')
            child_object: The child object type (e.g., 'Contact', 'SBQQ__Quote__c')
            parent_id: The parent record ID
            
        Returns:
            The field name that links child to parent (e.g., 'AccountId', 'OpportunityId')
        """
        # First, try common patterns
        common_patterns = {
            'Account': 'AccountId',
            'Opportunity': 'OpportunityId',
            'Contact': 'ContactId',
            'Case': 'CaseId',
            'Lead': 'LeadId',
            'Campaign': 'CampaignId',
        }
        
        if parent_object in common_patterns:
            # Check if this field exists on the child object
            try:
                metadata = self.describe_object(child_object)
                field_names = [f['name'] for f in metadata['fields']]
                
                if common_patterns[parent_object] in field_names:
                    return common_patterns[parent_object]
            except:
                pass
        
        # If common pattern doesn't work, look for reference fields pointing to parent
        try:
            metadata = self.describe_object(child_object)
            
            for field in metadata['fields']:
                # Check if this is a reference field pointing to the parent object
                if field['type'] == 'reference':
                    # Check if this field references the parent object
                    reference_to = field.get('referenceTo', [])
                    if parent_object in reference_to:
                        return field['name']
                    
                    # Special case: WhoId and WhatId can reference multiple objects
                    if field['name'] in ['WhoId', 'WhatId']:
                        if parent_object in reference_to:
                            return field['name']
            
            # If still not found, try the standard pattern: ParentObjectId
            standard_field = f"{parent_object}Id"
            field_names = [f['name'] for f in metadata['fields']]
            if standard_field in field_names:
                return standard_field
                
        except Exception as e:
            pass
        
        # Last resort: return None and let caller handle
        return None
