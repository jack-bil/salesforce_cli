"""
Interactive Session Module

Handles the interactive CLI mode with search and navigation.
"""
from typing import Optional, List, Dict, Any
from difflib import get_close_matches
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import InMemoryHistory
from .client import SalesforceClient
from .display import (
    display_search_results, display_record, display_related_records,
    display_menu, display_error, display_success, display_info,
    console
)


class InteractiveSession:
    """Interactive Salesforce CLI session."""
    
    # Common Salesforce objects
    COMMON_OBJECTS = [
        'Account', 'Contact', 'Opportunity', 'Lead', 'Case',
        'Task', 'Event', 'Campaign', 'User', 'Contract',
        'Order', 'Product2', 'Pricebook2', 'Quote', 'Asset',
        'OpportunityLineItem', 'OrderItem', 'ContentDocument'
    ]
    
    # Common relationships
    RELATIONSHIPS = {
        'Account': ['Contacts', 'Opportunities', 'Cases', 'Tasks', 'Orders', 'Contracts'],
        'Contact': ['Opportunities', 'Cases', 'Tasks', 'Events'],
        'Opportunity': ['OpportunityLineItems', 'Tasks', 'Quotes', 'Contracts'],
        'Lead': ['Tasks', 'Events'],
        'Case': ['Tasks', 'Events'],
        'Campaign': ['Opportunities', 'Leads']
    }
    
    def __init__(self, client: SalesforceClient):
        """Initialize interactive session."""
        self.client = client
        self.history = InMemoryHistory()
        self.current_object: Optional[str] = None
        self.current_records: List[Dict[str, Any]] = []
        self.current_record: Optional[Dict[str, Any]] = None
        self.related_records: List[Dict[str, Any]] = []
        self.related_type: Optional[str] = None
        # Navigation stack for browser-like back button
        self.navigation_stack: List[Dict[str, Any]] = []
        # Navigation path for prompt display (e.g., ['Account:Caliber 1516', 'Opportunities'])
        self.navigation_path: List[str] = []
    
    def _show_banner(self):
        """Display startup banner."""
        from rich.text import Text
        
        try:
            from pyfiglet import figlet_format
            banner = figlet_format("SF CLI", font="alligator2")
            
            # Apply gradient color to banner
            lines = banner.split('\n')
            colored_banner = Text()
            
            # Define gradient colors (cyan to blue to magenta)
            colors = ["cyan", "bright_cyan", "blue", "bright_blue", "magenta", "bright_magenta"]
            
            for i, line in enumerate(lines):
                # Calculate color index based on line position
                color_idx = int((i / len(lines)) * (len(colors) - 1))
                colored_banner.append(line + '\n', style=colors[color_idx])
            
        except ImportError:
            # Fallback if pyfiglet not installed
            colored_banner = Text("\n  Salesforce CLI\n", style="bold cyan")
        
        # Create panel with info
        info_lines = [
            Text("🚀 Interactive Salesforce Navigation", style="bold green"),
            Text(""),
            Text("Quick Start:", style="bold yellow"),
            Text("  • search Account <name>  - Find records", style="dim"),
            Text("  • Type number to select   - Quick navigation", style="dim"),
            Text("  • cd Opportunities        - Navigate folders", style="dim"),
            Text("  • ls / dir                - Show current list", style="dim"),
            Text("  • cd .. / back            - Go back", style="dim"),
            Text("  • help                    - See all commands", style="dim"),
            Text(""),
            Text("Type 'exit' to quit", style="dim italic")
        ]
        
        console.print()
        console.print(colored_banner)
        
        for line in info_lines:
            console.print(line)
        
        console.print()
    
    def run(self):
        """Run the interactive session."""
        self._show_banner()
        
        while True:
            try:
                # Build prompt with navigation path
                if self.navigation_path:
                    path_str = ' / '.join(self.navigation_path)
                    prompt_text = f"sf [{path_str}]> "
                elif self.current_record:
                    prompt_text = f"sf [{self.current_object}:{self.current_record.get('Name', 'Record')}]> "
                elif self.current_object:
                    prompt_text = f"sf [{self.current_object}]> "
                else:
                    prompt_text = "sf> "
                
                # Get user input
                user_input = prompt(
                    prompt_text,
                    history=self.history,
                    completer=self._get_completer()
                ).strip()
                
                if not user_input:
                    continue
                
                # Parse and execute command
                self._execute_command(user_input)
                
            except KeyboardInterrupt:
                continue
            except EOFError:
                break
        
        console.print("\n[dim]Goodbye![/dim]\n")
        return 0
    
    def _get_completer(self) -> WordCompleter:
        """Get command completer based on current context."""
        base_commands = ['search', 'get', 'list', 'query', 'help', 'exit', 'back', 'clear', 'update', 'describe', 'cd', 'ls', 'dir', '--fields', '--limit']
        
        if self.related_records:
            commands = base_commands + ['select', 'view']
        elif self.current_record:
            # Get relationship names dynamically from Salesforce metadata
            relationship_names = []
            try:
                relationships = self.client.get_child_relationships(self.current_object)
                relationship_names = [rel['name'] for rel in relationships]
                # For custom objects (relationships ending in __r), also add the __c version
                # to make it more intuitive for users
                for rel_name in list(relationship_names):
                    if rel_name.endswith('__r'):
                        object_name = rel_name[:-1] + 'c'  # Convert __r to __c
                        relationship_names.append(object_name)
            except:
                # Fallback to static relationships if API call fails
                if self.current_object in self.RELATIONSHIPS:
                    relationship_names = self.RELATIONSHIPS[self.current_object]
            
            # Add field names from current record for show command tab completion
            field_names = list(self.current_record.keys())
            commands = base_commands + ['view', 'related', 'relationships', 'fields', 'show', 'history', 'parent', 'ultimateparent', 'children', 'all'] + relationship_names + field_names
        elif self.current_records:
            commands = base_commands + ['select']
        elif self.current_object:
            # If we have a current object but no record (e.g., in search mode), add field names
            try:
                object_field_names = self.client.get_field_names(self.current_object)
                commands = base_commands + self.COMMON_OBJECTS + object_field_names
            except:
                commands = base_commands + self.COMMON_OBJECTS
        else:
            commands = base_commands + self.COMMON_OBJECTS
        
        return WordCompleter(commands, ignore_case=True, match_middle=True)
    
    def _execute_command(self, user_input: str):
        """Execute a command."""
        # Check if input is just a number (shortcut for select)
        if user_input.strip().isdigit():
            if self.related_records:
                self._handle_select_related(user_input.strip())
            elif self.current_records:
                self._handle_select(user_input.strip())
            else:
                display_error("No records to select from. Use 'search' first.")
            return
        
        parts = user_input.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        # Navigation commands
        if command == 'exit' or command == 'quit':
            raise EOFError
        
        elif command == 'help':
            self._show_help()
        
        elif command == 'back':
            self._go_back()
        
        elif command == 'cd':
            if args == '..':
                self._go_back()
            elif args and self.current_record:
                # cd <relationship> changes context without displaying
                self._handle_cd(args)
            elif args:
                display_error("No current record. Use 'search' or 'get' first.")
            else:
                display_error("Usage: cd .. (go back) or cd <relationship> (navigate to related records)")
        
        elif command == 'ls' or command == 'dir':
            # Check if there's a pipe for sorting
            if '|' in user_input:
                self._handle_ls_with_pipe(user_input)
            else:
                self._handle_ls()
        
        elif command == 'clear':
            console.clear()
        
        # Search and query commands
        elif command == 'search':
            self._handle_search(args)
        
        elif command == 'get':
            self._handle_get(args)
        
        elif command == 'query':
            self._handle_query(args)
        
        elif command == 'list':
            self._handle_list(args)
        
        # Context-specific commands
        elif command == 'select' and self.related_records:
            self._handle_select_related(args)
        
        elif command == 'select' and self.current_records:
            self._handle_select(args)
        
        elif command == 'view' and self.current_record:
            self._handle_view()
        
        elif command == 'related' and self.current_record:
            self._handle_related(args)
        
        elif command == 'fields' and self.current_record:
            self._handle_fields()
        
        elif command == 'relationships' and self.current_record:
            self._handle_relationships()
        
        elif command == 'show' and self.current_record:
            self._handle_show(args)
        
        elif command == 'update' and self.current_record:
            self._handle_update(args)
        
        elif command == 'history' and self.current_record:
            self._handle_history(args)
        
        elif command == 'parent' and self.current_record:
            self._handle_parent(args)
        
        elif command == 'ultimateparent' and self.current_record:
            self._handle_ultimate_parent(args)
        
        elif command == 'children' and self.current_record:
            self._handle_children(args)
        
        elif command == 'describe':
            self._handle_describe(args)
        
        else:
            display_error(f"Unknown command: {command}. Type 'help' for available commands.")
    
    def _show_help(self):
        """Show help message."""
        console.print("\n[bold cyan]Available Commands:[/bold cyan]\n")
        
        console.print("[yellow]Search & Query:[/yellow]")
        console.print("  search <Object> <query>  - Search for records (e.g., 'search Account Axalta')")
        console.print("  search <Object> <query> --fields F1, F2  - Search with custom fields")
        console.print("  search <Object> <query> --limit N  - Set max results (default: 200, max: 2000)")
        console.print("  get <Object> <ID>        - Get a specific record by ID")
        console.print("  query <SOQL>             - Execute raw SOQL query")
        console.print("  list objects             - List available Salesforce objects")
        console.print("  describe [Object]        - Show detailed metadata for object (uses current if not specified)")
        
        if self.current_records and not self.current_record:
            console.print("\n[yellow]Result Navigation:[/yellow]")
            console.print("  <number>                 - Select a record (e.g., just type '1')")
            console.print("  select <number>          - Select a record from search results")
            console.print("  list                     - Re-display the current search results")
            console.print("  list                     - Re-display the current search results")
        
        if self.related_records:
            console.print("\n[yellow]Related Record Navigation:[/yellow]")
            console.print("  <number>                 - Select a related record (e.g., just type '1')")
            console.print("  select <number>          - Select a related record to view details")
        
        if self.current_record:
            console.print("\n[yellow]Record Actions:[/yellow]")
            console.print("  view                     - View full record details")
            console.print("  show all                 - View all fields")
            console.print("  show <field1> <field2>...   - Display specific fields (e.g., 'show Name Phone')")
            console.print("  update <field> <value>   - Update a field (e.g., 'update Phone 555-1234')")
            console.print("  history [field]          - View all field changes or specific field (e.g., 'history')")
            console.print("  fields                   - List all available fields")
            console.print("  relationships            - Show all available related objects")
            console.print("  related <type>           - View related records immediately (e.g., 'related Contacts')")
            console.print("  parent [field1 field2]   - Jump to parent Account (e.g., 'parent' or 'parent Name Phone')")
            console.print("  ultimateparent [field1 field2] - Jump to Ultimate Parent Account")
            console.print("  children [field1 field2] - View child Accounts (e.g., 'children' or 'children Name City')")
        
        console.print("\n[yellow]Navigation:[/yellow]")
        console.print("  cd <relationship>        - Navigate to related records (e.g., 'cd Opportunities')")
        console.print("  cd ..                    - Go back to previous context")
        console.print("  back                     - Go back to previous context")
        console.print("  ls / dir                 - List current context (show table)")
        console.print("  ls | sort <field> [-desc|-asc] - List and sort by field (e.g., 'ls | sort CreatedDate -desc')")
        console.print("  clear                    - Clear screen")
        console.print("  exit / quit              - Exit the CLI")
        console.print()
    
    def _go_back(self):
        """Go back to previous context."""
        if not self.navigation_stack:
            # We're at the root or at search results - clear everything to go to root
            if self.current_records or self.current_record or self.related_records:
                # Clear all state to go back to root
                self.current_object = None
                self.current_records = []
                self.current_record = None
                self.related_records = []
                self.related_type = None
                self.navigation_path = []
                display_info("Returned to root")
            else:
                display_info("Already at root level")
            return
        
        # Pop the previous context from stack
        previous_context = self.navigation_stack.pop()
        context_type = previous_context['type']
        
        # Restore navigation path if it exists
        if 'navigation_path' in previous_context:
            self.navigation_path = previous_context['navigation_path']
        else:
            self.navigation_path = []
        
        # Restore the previous context
        if context_type == 'search':
            self.current_object = previous_context['object']
            self.current_records = previous_context['records']
            self.current_record = None
            self.related_records = []
            self.related_type = None
            display_search_results(self.current_records, self.current_object)
            display_info("Returned to search results")
            
        elif context_type == 'record':
            self.current_object = previous_context['object']
            self.current_record = previous_context['record']
            self.current_records = []
            self.related_records = []
            self.related_type = None
            
        elif context_type == 'related':
            self.current_object = previous_context['object']
            self.current_record = previous_context['parent_record']
            self.related_records = previous_context['records']
            self.related_type = previous_context['related_type']
    
    def _handle_search(self, args: str):
        """Handle search command."""
        if not args:
            display_error("Usage: search <Object> <query> [--fields Field1, Field2, ...] [--limit N]")
            return
        
        # Parse --limit flag
        limit = 200  # Default limit
        if '--limit' in args:
            try:
                limit_parts = args.split('--limit')
                args = limit_parts[0].strip()
                limit_value = limit_parts[1].strip().split()[0]
                limit = int(limit_value)
                # Remove the limit value from args for further parsing
                args = args + ' ' + ' '.join(limit_parts[1].strip().split()[1:])
            except (ValueError, IndexError):
                display_error("Invalid --limit value. Usage: --limit <number>")
                return
        
        # Parse --fields flag
        custom_fields = None
        if '--fields' in args:
            parts = args.split('--fields')
            if len(parts) != 2:
                display_error("Usage: search <Object> <query> --fields Field1, Field2, ...")
                return
            
            search_part = parts[0].strip()
            fields_part = parts[1].strip()
            
            # Parse fields (comma-separated)
            custom_fields = [f.strip() for f in fields_part.split(',')]
            
            # Parse object and query from search part
            search_parts = search_part.split(maxsplit=1)
            if len(search_parts) != 2:
                display_error("Usage: search <Object> <query> --fields Field1, Field2, ...")
                return
            object_type, query = search_parts
        else:
            # No custom fields, use default behavior
            parts = args.split(maxsplit=1)
            if len(parts) != 2:
                display_error("Usage: search <Object> <query> [--fields Field1, Field2, ...] [--limit N]")
                return
            object_type, query = parts
        
        try:
            self.current_object = object_type
            self.current_records, total_count = self.client.search_with_stats(object_type, query, limit=limit, fields=custom_fields)
            # Clear navigation stack and current state when starting new search
            self.navigation_stack = []
            self.current_record = None
            self.related_records = []
            self.related_type = None
            self.navigation_path = []
            display_search_results(self.current_records, object_type, total_count)
            
            if self.current_records:
                display_info("Type a number to view a record (e.g., '1') or 'select <number>'")
            else:
                # If no results, try to suggest a corrected query
                self._suggest_query_correction(query)
        except Exception as e:
            display_error(f"Search failed: {e}")
            self.current_object = None
            self.current_records = []
    
    def _suggest_query_correction(self, query: str):
        """Suggest a corrected query if the search found no results."""
        # Split the query into words and check for common typos
        words = query.split()
        corrections = []
        
        # Common Salesforce/business terms to check against
        common_terms = [
            'collision', 'caliber', 'service', 'center', 'automotive',
            'account', 'contact', 'opportunity', 'customer', 'dealer',
            'distributor', 'paint', 'refinish', 'coating', 'industrial',
            'transportation', 'commercial', 'vehicle', 'body', 'shop'
        ]
        
        for word in words:
            # Find close matches for each word (cutoff=0.6 is fairly lenient)
            matches = get_close_matches(word.lower(), common_terms, n=1, cutoff=0.6)
            if matches and matches[0] != word.lower():
                corrections.append((word, matches[0]))
        
        if corrections:
            # Build a suggested query
            suggested_query = query
            for original, correction in corrections:
                suggested_query = suggested_query.replace(original, correction)
            
            display_info(f"Did you mean: [cyan]{suggested_query}[/cyan]?")
            display_info(f"Try: search {self.current_object} {suggested_query}")
    
    def _handle_get(self, args: str):
        """Handle get command."""
        if not args:
            display_error("Usage: get <Object> <ID>")
            return
        
        parts = args.split()
        if len(parts) != 2:
            display_error("Usage: get <Object> <ID>")
            return
        
        object_type, record_id = parts
        
        try:
            self.current_object = object_type
            self.current_record = self.client.get_record(object_type, record_id)
            display_record(self.current_record, object_type)
        except Exception as e:
            display_error(f"Failed to get record: {e}")
    
    def _handle_query(self, args: str):
        """Handle SOQL query command."""
        if not args:
            display_error("Usage: query <SOQL>")
            return
        
        try:
            results = self.client.execute_query(args)
            console.print(f"\n[green]Query returned {len(results)} record(s)[/green]\n")
            
            if results:
                # Try to display as table if possible
                display_search_results(results, "Query Results")
        except Exception as e:
            display_error(f"Query failed: {e}")
    
    def _handle_list(self, args: str):
        """Handle list command."""
        if not args:
            # Show records based on current context
            if self.related_records:
                # Currently viewing related records list
                parent_name = self.current_record.get('Name', self.current_record['Id'])
                display_related_records(self.related_records, self.related_type, parent_name)
                if self.related_records:
                    display_info("Type a number to view a record (e.g., '1') or 'select <number>'")
            elif self.current_records:
                # Currently at search results
                display_search_results(self.current_records, self.current_object)
                if self.current_records:
                    display_info("Type a number to view a record (e.g., '1') or 'select <number>'")
            elif self.current_record:
                # Currently viewing a single record
                display_record(self.current_record, self.current_object)
            else:
                display_info("No records to display. Use 'search' to find records.")
            return
        
        if args.lower() == 'objects':
            try:
                objects = self.client.list_objects(show_all=False)
                console.print("\n[bold cyan]Available Salesforce Objects:[/bold cyan]")
                console.print("[dim]Common objects:[/dim]")
                
                # Group objects
                common = [o for o in objects if o in self.COMMON_OBJECTS]
                other = [o for o in objects if o not in self.COMMON_OBJECTS]
                
                for obj in sorted(common):
                    console.print(f"  [green]{obj}[/green]")
                
                console.print(f"\n[dim]Other objects ({len(other)} total):[/dim]")
                for obj in sorted(other)[:20]:  # Show first 20
                    console.print(f"  {obj}")
                
                if len(other) > 20:
                    console.print(f"  [dim]... and {len(other) - 20} more[/dim]")
                console.print()
            except Exception as e:
                display_error(f"Failed to list objects: {e}")
        else:
            display_error("Usage: list objects")
    
    def _handle_select(self, args: str):
        """Handle select command to choose a record from results."""
        try:
            index = int(args) - 1
            if 0 <= index < len(self.current_records):
                record = self.current_records[index]
                record_id = record['Id']
                
                # Push current search results to stack
                self.navigation_stack.append({
                    'type': 'search',
                    'object': self.current_object,
                    'records': self.current_records,
                    'navigation_path': self.navigation_path.copy()
                })
                
                # Fetch full record details
                self.current_record = self.client.get_record(self.current_object, record_id)
                self.current_records = []  # Clear search results
                self.navigation_path = []  # Clear navigation path when selecting new record
                
                # Show compact confirmation instead of full record
                record_name = self.current_record.get('Name', self.current_record.get('Id', 'Record'))
                display_success(f"Selected: {record_name}")
                console.print("[dim]Use 'view' or 'show all' to see all fields[/dim]")
                
                # Show available actions
                if self.current_object in self.RELATIONSHIPS:
                    related = self.RELATIONSHIPS[self.current_object]
                    console.print(f"[dim]Available related objects: {', '.join(related)}[/dim]")
                    console.print("[dim]Use 'cd <type>' or 'related <type>' to view related records[/dim]\n")
            else:
                display_error(f"Invalid selection. Choose a number between 1 and {len(self.current_records)}")
        except ValueError:
            display_error("Please enter a valid number")
    
    def _handle_view(self):
        """Handle view command to show full record."""
        if self.current_record:
            display_record(self.current_record, self.current_object)
        else:
            display_error("No record selected")
    
    def _handle_related(self, args: str):
        """Handle related command to show related records."""
        if not self.current_record:
            display_error("No record selected")
            return
        
        if not args:
            # Show available relationships dynamically
            try:
                relationships = self.client.get_child_relationships(self.current_object)
                
                if not relationships:
                    display_info("No child relationships found for this object")
                    return
                
                console.print("\n[cyan]Available related objects:[/cyan]")
                
                # Show up to 20 most common relationships
                for rel in sorted(relationships, key=lambda x: x['name'])[:20]:
                    console.print(f"  [yellow]{rel['name']:30}[/yellow] ({rel['object']})")
                
                if len(relationships) > 20:
                    console.print(f"  [dim]... and {len(relationships) - 20} more (use 'relationships' to see all)[/dim]")
                
                console.print(f"\n[dim]Use 'related <name>' to view records[/dim]")
                console.print()
            except Exception as e:
                display_error(f"Failed to get relationships: {e}")
            return
        
        relationship_name = args.strip()
        
        try:
            related_records = self.client.get_related_records(
                self.current_object,
                self.current_record['Id'],
                relationship_name
            )
            
            # Push current record context to stack
            self.navigation_stack.append({
                'type': 'record',
                'object': self.current_object,
                'record': self.current_record
            })
            
            parent_name = self.current_record.get('Name', self.current_record['Id'])
            display_related_records(related_records, relationship_name, parent_name)
            
            # Store related records for potential selection
            self.related_records = related_records
            self.related_type = relationship_name
            
            if related_records:
                display_info("Use 'select <number>' to view a related record")
        except Exception as e:
            display_error(f"Failed to get related records: {e}")
    
    def _handle_cd(self, args: str):
        """Handle cd command to navigate to related records without displaying."""
        if not self.current_record:
            display_error("No record selected")
            return
        
        relationship_name = args.strip()
        
        # If user provides a custom object name (__c), try to convert to relationship name (__r)
        # This makes it more intuitive for users
        if relationship_name.endswith('__c'):
            relationship_name_r = relationship_name[:-1] + 'r'  # Replace __c with __r
            # Try with __r first
            try:
                related_records = self.client.get_related_records(
                    self.current_object,
                    self.current_record['Id'],
                    relationship_name_r
                )
                relationship_name = relationship_name_r  # Use the __r version
            except:
                # If __r doesn't work, try the original __c version
                try:
                    related_records = self.client.get_related_records(
                        self.current_object,
                        self.current_record['Id'],
                        relationship_name
                    )
                except Exception as e:
                    display_error(f"Failed to navigate to related records: {e}")
                    return
        else:
            try:
                # Query for related records
                related_records = self.client.get_related_records(
                    self.current_object,
                    self.current_record['Id'],
                    relationship_name
                )
            except Exception as e:
                display_error(f"Failed to navigate to related records: {e}")
                return
        
        try:
            
            # Push current record context to stack
            self.navigation_stack.append({
                'type': 'record',
                'object': self.current_object,
                'record': self.current_record,
                'navigation_path': self.navigation_path.copy()
            })
            
            # Store related records for potential selection
            self.related_records = related_records
            self.related_type = relationship_name
            
            # Update navigation path
            if not self.navigation_path:
                # Starting from a record
                record_name = self.current_record.get('Name', self.current_record.get('Id', 'Record'))
                self.navigation_path = [f"{self.current_object}:{record_name}", relationship_name]
            else:
                # Already in a path, append the relationship
                self.navigation_path.append(relationship_name)
            
        except Exception as e:
            display_error(f"Failed to navigate to related records: {e}")
    
    def _handle_ls(self):
        """Handle ls/dir command to display current context."""
        if self.related_records:
            # Display related records
            parent_name = self.navigation_path[0] if self.navigation_path else "Record"
            display_related_records(self.related_records, self.related_type, parent_name)
            if self.related_records:
                display_info("Type a number to select a record")
        elif self.current_records:
            # Display search results
            display_search_results(self.current_records, self.current_object)
            if self.current_records:
                display_info("Type a number to select a record")
        elif self.current_record:
            # Display available relationships like a directory listing
            try:
                relationships = self.client.get_child_relationships(self.current_object)
                
                if not relationships:
                    display_info("No related objects found for this record")
                    return
                
                # Filter and group relationships
                common_rel_names = ['Contacts', 'Opportunities', 'Cases', 'Tasks', 'Events', 
                                   'Orders', 'Contracts', 'Assets', 'Quotes', 'OpportunityLineItems']
                common_rels = []
                other_rels = []
                
                for rel in relationships:
                    if rel['name'] in common_rel_names:
                        common_rels.append(rel)
                    else:
                        other_rels.append(rel)
                
                console.print(f"\n[bold cyan]Available relationships for {self.current_object}:[/bold cyan]\n")
                
                # Display common relationships first
                if common_rels:
                    console.print("[green]Common relationships:[/green]")
                    for rel in sorted(common_rels, key=lambda x: x['name']):
                        console.print(f"  [cyan]{rel['name']:30}[/cyan] → {rel['object']}")
                
                # Display other relationships
                if other_rels:
                    if common_rels:
                        console.print(f"\n[dim]Other relationships ({len(other_rels)} total):[/dim]")
                    # Show first 20
                    for rel in sorted(other_rels, key=lambda x: x['name'])[:20]:
                        console.print(f"  [cyan]{rel['name']:30}[/cyan] → {rel['object']}")
                    
                    if len(other_rels) > 20:
                        console.print(f"  [dim]... and {len(other_rels) - 20} more[/dim]")
                
                console.print(f"\n[dim]Use 'cd <name>' to navigate (e.g., 'cd Contacts')[/dim]")
                console.print()
                
            except Exception as e:
                display_error(f"Failed to get relationships: {e}")
        else:
            display_info("No records to display. Use 'search' to find records.")
    
    def _handle_ls_with_pipe(self, full_command: str):
        """Handle ls/dir command with pipe for sorting."""
        # Parse the pipe command: ls | sort FieldName -desc
        parts = full_command.split('|')
        if len(parts) != 2:
            display_error("Invalid pipe syntax. Usage: ls | sort <FieldName> [-desc|-asc]")
            return
        
        pipe_command = parts[1].strip()
        
        # Parse sort command
        if not pipe_command.startswith('sort'):
            display_error("Only 'sort' is supported after pipe. Usage: ls | sort <FieldName> [-desc|-asc]")
            return
        
        sort_parts = pipe_command.split()
        if len(sort_parts) < 2:
            display_error("Usage: ls | sort <FieldName> [-desc|-asc]")
            return
        
        field_name = sort_parts[1]
        descending = False
        
        # Check for -desc or -asc flag
        if len(sort_parts) > 2:
            if sort_parts[2] == '-desc':
                descending = True
            elif sort_parts[2] == '-asc':
                descending = False
            else:
                display_error("Invalid sort order. Use -desc or -asc")
                return
        
        # Sort and display
        if self.related_records:
            sorted_records = self._sort_records(self.related_records, field_name, descending)
            if sorted_records is not None:
                parent_name = self.navigation_path[0] if self.navigation_path else "Record"
                display_related_records(sorted_records, self.related_type, parent_name)
                if sorted_records:
                    display_info("Type a number to select a record")
        elif self.current_records:
            sorted_records = self._sort_records(self.current_records, field_name, descending)
            if sorted_records is not None:
                display_search_results(sorted_records, self.current_object)
                if sorted_records:
                    display_info("Type a number to select a record")
        elif self.current_record:
            display_info("Cannot sort a single record. Use 'ls' without sort.")
        else:
            display_info("No records to display. Use 'search' to find records.")
    
    def _sort_records(self, records: List[Dict[str, Any]], field_name: str, descending: bool) -> Optional[List[Dict[str, Any]]]:
        """Sort records by a field name."""
        if not records:
            return records
        
        # Check if field exists in records
        if field_name not in records[0]:
            available_fields = [k for k in records[0].keys() if not k.startswith('attributes')]
            display_error(f"Field '{field_name}' not found in records.")
            console.print(f"[dim]Available fields: {', '.join(available_fields)}[/dim]")
            return None
        
        try:
            # Sort records, handling None values
            sorted_records = sorted(
                records,
                key=lambda x: (x.get(field_name) is None, x.get(field_name) or ''),
                reverse=descending
            )
            return sorted_records
        except Exception as e:
            display_error(f"Failed to sort records: {e}")
            return None
    
    def _handle_fields(self):
        """Handle fields command to show all available fields."""
        if not self.current_record:
            display_error("No record selected")
            return
        
        try:
            metadata = self.client.describe_object(self.current_object)
            console.print(f"\n[bold cyan]Available fields for {self.current_object}:[/bold cyan]\n")
            
            for field in sorted(metadata['fields'], key=lambda x: x['name']):
                field_name = field['name']
                field_type = field['type']
                field_label = field['label']
                
                # Check if field has a value in current record
                has_value = field_name in self.current_record and self.current_record[field_name]
                value_indicator = "[green]✓[/green]" if has_value else "[dim]○[/dim]"
                
                console.print(f"  {value_indicator} [cyan]{field_name:30}[/cyan] [{field_type:15}] {field_label}")
            
            console.print()
        except Exception as e:
            display_error(f"Failed to get field information: {e}")
    
    def _handle_show(self, args: str):
        """Handle show command to display specific fields."""
        if not self.current_record:
            display_error("No record selected")
            return
        
        if not args:
            display_error("Usage: show <field1> <field2> ... or 'show all' (e.g., 'show Name Phone AnnualRevenue')")
            return
        
        # Check for 'show all' command
        if args.strip().lower() == 'all':
            display_record(self.current_record, self.current_object)
            return
        
        # Parse field names from args (comma or space separated)
        field_names = [f.strip() for f in args.replace(',', ' ').split()]
        
        if not field_names:
            display_error("Please specify at least one field name")
            return
        
        # Build a table to display the requested fields
        from rich.table import Table
        from rich.panel import Panel
        
        record_name = self.current_record.get('Name', self.current_record.get('Id', 'Record'))
        table = Table(title=f"{self.current_object}: {record_name}", show_header=True, header_style="bold cyan")
        table.add_column("Field", style="cyan", width=40)
        table.add_column("Value", style="white")
        
        found_fields = []
        missing_fields = []
        
        for field_name in field_names:
            # Try exact match first
            if field_name in self.current_record:
                value = self.current_record[field_name]
                # Format value nicely
                if value is None:
                    value_str = "[dim]null[/dim]"
                elif isinstance(value, bool):
                    value_str = "[green]✓[/green]" if value else "[red]✗[/red]"
                elif isinstance(value, dict):
                    value_str = str(value)
                else:
                    value_str = str(value)
                
                table.add_row(field_name, value_str)
                found_fields.append(field_name)
            else:
                # Try case-insensitive match
                matched = False
                for key in self.current_record.keys():
                    if key.lower() == field_name.lower():
                        value = self.current_record[key]
                        if value is None:
                            value_str = "[dim]null[/dim]"
                        elif isinstance(value, bool):
                            value_str = "[green]✓[/green]" if value else "[red]✗[/red]"
                        elif isinstance(value, dict):
                            value_str = str(value)
                        else:
                            value_str = str(value)
                        
                        table.add_row(key, value_str)
                        found_fields.append(key)
                        matched = True
                        break
                
                if not matched:
                    missing_fields.append(field_name)
        
        if found_fields:
            console.print()
            console.print(table)
            console.print()
        
        if missing_fields:
            display_error(f"Fields not found: {', '.join(missing_fields)}")
            console.print("[dim]Use 'fields' to see all available fields[/dim]\n")
    
    def _handle_update(self, args: str):
        """Handle update command to modify a field value."""
        if not self.current_record:
            display_error("No record selected")
            return
        
        if not args:
            display_error("Usage: update <field> <value> (e.g., 'update Phone 555-1234')")
            return
        
        # Parse field name and value (split on first space)
        parts = args.split(maxsplit=1)
        if len(parts) != 2:
            display_error("Usage: update <field> <value>")
            return
        
        field_name, new_value = parts
        
        # Check if field exists in current record
        actual_field = None
        for key in self.current_record.keys():
            if key.lower() == field_name.lower():
                actual_field = key
                break
        
        if not actual_field:
            display_error(f"Field '{field_name}' not found in current record")
            console.print("[dim]Use 'fields' to see all available fields[/dim]\n")
            return
        
        # Get old value for display
        old_value = self.current_record.get(actual_field)
        
        # Convert value to appropriate type based on old value
        try:
            if isinstance(old_value, bool):
                # Handle boolean conversion
                new_value_typed = new_value.lower() in ['true', '1', 'yes', 't', 'y']
            elif isinstance(old_value, int):
                new_value_typed = int(new_value)
            elif isinstance(old_value, float):
                new_value_typed = float(new_value)
            else:
                new_value_typed = new_value
        except ValueError:
            new_value_typed = new_value  # Keep as string if conversion fails
        
        # Confirm the update
        console.print(f"\n[yellow]Update Confirmation:[/yellow]")
        console.print(f"  Record: [cyan]{self.current_record.get('Name', self.current_record['Id'])}[/cyan]")
        console.print(f"  Field:  [cyan]{actual_field}[/cyan]")
        console.print(f"  From:   [dim]{old_value}[/dim]")
        console.print(f"  To:     [green]{new_value_typed}[/green]")
        
        from prompt_toolkit import prompt as pt_prompt
        confirmation = pt_prompt("\nProceed with update? (yes/no): ").strip().lower()
        
        if confirmation not in ['yes', 'y']:
            display_info("Update cancelled")
            return
        
        # Perform the update
        try:
            success = self.client.update_record(
                self.current_object,
                self.current_record['Id'],
                {actual_field: new_value_typed}
            )
            
            if success:
                # Update the local record cache
                self.current_record[actual_field] = new_value_typed
                display_success(f"Successfully updated {actual_field}")
                
                # Show the updated field
                console.print(f"\n[cyan]{actual_field}:[/cyan] {new_value_typed}\n")
            else:
                display_error("Update failed")
        except Exception as e:
            display_error(f"Update failed: {e}")
    
    def _handle_parent(self, args: str):
        """Handle parent command to navigate to parent Account."""
        if not self.current_record:
            display_error("No record selected")
            return
        
        # Check if current object is Account and has ParentId
        if self.current_object != 'Account':
            display_error("Parent navigation only works for Account objects")
            return
        
        parent_id = self.current_record.get('ParentId')
        if not parent_id:
            display_info("This account has no parent account")
            return
        
        try:
            # Parse field names if provided (similar to show command)
            field_names = []
            if args:
                field_names = [f.strip() for f in args.replace(',', ' ').split()]
            
            # Fetch parent record
            if field_names:
                # Custom fields requested
                fields_str = ', '.join(['Id', 'ParentId'] + field_names)
                soql = f"SELECT {fields_str} FROM Account WHERE Id = '{parent_id}'"
                result = self.client.query(soql)
                if result['records']:
                    parent_record = result['records'][0]
                else:
                    display_error("Parent account not found")
                    return
            else:
                # Get full record
                parent_record = self.client.get_record('Account', parent_id)
            
            # Save current context to navigation stack
            self.navigation_stack.append({
                'type': 'record',
                'object': self.current_object,
                'record': self.current_record,
                'records': self.current_records
            })
            
            # Navigate to parent
            self.current_record = parent_record
            self.related_records = []
            self.related_type = None
            
            # Display parent record
            if field_names:
                # Show only requested fields
                self._handle_show(args)
            else:
                # Show default view
                default_fields = 'Id Name ShippingStreet ShippingCity ShippingState'
                self._handle_show(default_fields)
            
            display_success(f"Navigated to parent account")
            
        except Exception as e:
            display_error(f"Failed to navigate to parent: {e}")
    
    def _handle_ultimate_parent(self, args: str):
        """Handle ultimateparent command to navigate to Ultimate Parent Account."""
        if not self.current_record:
            display_error("No record selected")
            return
        
        # Check if current object is Account and has Ultimate_Parent__c
        if self.current_object != 'Account':
            display_error("Ultimate parent navigation only works for Account objects")
            return
        
        ultimate_parent_id = self.current_record.get('Ultimate_Parent__c')
        if not ultimate_parent_id:
            display_info("This account has no ultimate parent account")
            return
        
        try:
            # Parse field names if provided (similar to show command)
            field_names = []
            if args:
                field_names = [f.strip() for f in args.replace(',', ' ').split()]
            
            # Fetch ultimate parent record
            if field_names:
                # Custom fields requested
                fields_str = ', '.join(['Id', 'ParentId', 'Ultimate_Parent__c'] + field_names)
                soql = f"SELECT {fields_str} FROM Account WHERE Id = '{ultimate_parent_id}'"
                result = self.client.query(soql)
                if result['records']:
                    ultimate_parent_record = result['records'][0]
                else:
                    display_error("Ultimate parent account not found")
                    return
            else:
                # Get full record
                ultimate_parent_record = self.client.get_record('Account', ultimate_parent_id)
            
            # Save current context to navigation stack
            self.navigation_stack.append({
                'type': 'record',
                'object': self.current_object,
                'record': self.current_record,
                'records': self.current_records
            })
            
            # Navigate to ultimate parent
            self.current_record = ultimate_parent_record
            self.related_records = []
            self.related_type = None
            
            # Display ultimate parent record
            if field_names:
                # Show only requested fields
                self._handle_show(args)
            else:
                # Show default view
                default_fields = 'Id Name ShippingStreet ShippingCity ShippingState'
                self._handle_show(default_fields)
            
            display_success(f"Navigated to ultimate parent account")
            
        except Exception as e:
            display_error(f"Failed to navigate to ultimate parent: {e}")
    
    def _handle_children(self, args: str):
        """Handle children command to view child Accounts."""
        if not self.current_record:
            display_error("No record selected")
            return
        
        # Check if current object is Account
        if self.current_object != 'Account':
            display_error("Children navigation only works for Account objects")
            return
        
        account_id = self.current_record.get('Id')
        if not account_id:
            display_error("Current record has no ID")
            return
        
        try:
            # Parse field names if provided
            field_names = []
            if args:
                field_names = [f.strip() for f in args.replace(',', ' ').split()]
            
            # Build query for child accounts
            if field_names:
                fields_str = ', '.join(['Id', 'ParentId', 'Name'] + [f for f in field_names if f not in ['Id', 'ParentId', 'Name']])
            else:
                fields_str = 'Id, ParentId, Name, ShippingStreet, ShippingCity, ShippingState'
            
            # First get total count
            count_soql = f"SELECT COUNT() FROM Account WHERE ParentId = '{account_id}'"
            count_result = self.client.query(count_soql)
            total_count = count_result.get('totalSize', 0)
            
            if total_count == 0:
                display_info("This account has no child accounts")
                return
            
            # Then get the records (limited to reasonable display)
            limit = 50  # Default limit for children display
            soql = f"SELECT {fields_str} FROM Account WHERE ParentId = '{account_id}' ORDER BY Name LIMIT {limit}"
            result = self.client.query(soql)
            
            children = result['records']
            
            # Save current context to navigation stack
            self.navigation_stack.append({
                'type': 'record',
                'object': self.current_object,
                'record': self.current_record,
                'records': self.current_records
            })
            
            # Set children as related records so user can select them
            self.related_records = children
            self.related_type = 'Account'
            
            # Display children with count context
            parent_name = self.current_record.get('Name', 'Unknown')
            display_related_records(children, 'Child Accounts', parent_name)
            
            if total_count > len(children):
                display_info(f"Showing {len(children)} of {total_count:,} total child accounts")
            else:
                display_info(f"Found {len(children)} child account(s)")
            
            display_info("Type a number to view a child account (e.g., '1') or 'select <number>'")
            
        except Exception as e:
            display_error(f"Failed to fetch child accounts: {e}")
    
    def _handle_describe(self, args: str):
        """Handle describe command to show object metadata."""
        # Determine object type
        object_type = args.strip() if args else self.current_object
        
        if not object_type:
            display_error("Usage: describe <Object> or use describe when viewing a record")
            return
        
        try:
            from rich.table import Table
            from rich.panel import Panel
            
            # Get detailed metadata
            metadata = self.client.describe_detailed(object_type)
            
            # Display object info
            obj_info = metadata['object_info']
            console.print(f"\n[bold cyan]Object: {obj_info['label']} ({obj_info['name']})[/bold cyan]")
            console.print(f"[dim]{obj_info['labelPlural']}[/dim]")
            
            # Properties table
            props_table = Table(show_header=False, box=None, padding=(0, 2))
            props_table.add_column("Property", style="cyan")
            props_table.add_column("Value", style="white")
            
            props_table.add_row("Type", "[yellow]Custom[/yellow]" if obj_info['custom'] else "Standard")
            props_table.add_row("Queryable", "[green]✓[/green]" if obj_info['queryable'] else "[red]✗[/red]")
            props_table.add_row("Searchable", "[green]✓[/green]" if obj_info['searchable'] else "[red]✗[/red]")
            props_table.add_row("Createable", "[green]✓[/green]" if obj_info['createable'] else "[red]✗[/red]")
            props_table.add_row("Updateable", "[green]✓[/green]" if obj_info['updateable'] else "[red]✗[/red]")
            props_table.add_row("Deletable", "[green]✓[/green]" if obj_info['deletable'] else "[red]✗[/red]")
            if obj_info['recordTypeInfos'] > 0:
                props_table.add_row("Record Types", str(obj_info['recordTypeInfos']))
            
            console.print(props_table)
            
            # Field counts
            counts = metadata['counts']
            console.print(f"\n[bold yellow]Fields Summary:[/bold yellow]")
            console.print(f"  Total: {counts['total_fields']} | Standard: {counts['standard_fields']} | Custom: {counts['custom_fields']} | Formula: {counts['formula_fields']} | Lookup: {counts['lookup_fields']}")
            
            # Display fields by category
            fields = metadata['fields']
            
            if fields['custom']:
                console.print(f"\n[bold yellow]Custom Fields ({len(fields['custom'])}):[/bold yellow]")
                self._display_field_table(fields['custom'][:20])  # Show first 20
                if len(fields['custom']) > 20:
                    console.print(f"[dim]... and {len(fields['custom']) - 20} more custom fields[/dim]")
            
            if fields['lookup']:
                console.print(f"\n[bold yellow]Lookup/Master-Detail Fields ({len(fields['lookup'])}):[/bold yellow]")
                self._display_lookup_table(fields['lookup'][:15])  # Show first 15
                if len(fields['lookup']) > 15:
                    console.print(f"[dim]... and {len(fields['lookup']) - 15} more lookup fields[/dim]")
            
            if fields['formula']:
                console.print(f"\n[bold yellow]Formula Fields ({len(fields['formula'])}):[/bold yellow]")
                self._display_field_table(fields['formula'][:10])  # Show first 10
                if len(fields['formula']) > 10:
                    console.print(f"[dim]... and {len(fields['formula']) - 10} more formula fields[/dim]")
            
            # Display relationships
            relationships = metadata['relationships']
            if relationships['child']:
                console.print(f"\n[bold yellow]Child Relationships ({len(relationships['child'])}):[/bold yellow]")
                rel_table = Table(show_header=True, header_style="bold cyan", box=None)
                rel_table.add_column("Name", style="cyan")
                rel_table.add_column("Object", style="white")
                rel_table.add_column("Field", style="dim")
                
                for rel in relationships['child'][:20]:  # Show first 20
                    rel_table.add_row(rel['name'], rel['object'], rel['field'])
                
                console.print(rel_table)
                if len(relationships['child']) > 20:
                    console.print(f"[dim]... and {len(relationships['child']) - 20} more child relationships[/dim]")
            
            console.print()
            
        except Exception as e:
            display_error(f"Failed to describe object: {e}")
    
    def _display_field_table(self, fields: List[Dict[str, Any]]):
        """Display a table of field metadata."""
        from rich.table import Table
        
        table = Table(show_header=True, header_style="bold cyan", box=None)
        table.add_column("Field", style="cyan", width=30)
        table.add_column("Label", style="white", width=30)
        table.add_column("Type", style="yellow", width=15)
        table.add_column("Properties", style="dim")
        
        for field in fields:
            props = []
            if field['required']:
                props.append('[red]Required[/red]')
            if field['unique']:
                props.append('[blue]Unique[/blue]')
            if field['externalId']:
                props.append('[green]ExtID[/green]')
            
            props_str = ' '.join(props) if props else ''
            
            # Add length/precision info
            type_info = field['type']
            if field.get('length'):
                type_info += f"({field['length']})"
            elif field.get('precision') and field.get('scale'):
                type_info += f"({field['precision']},{field['scale']})"
            
            table.add_row(field['name'], field['label'], type_info, props_str)
        
        console.print(table)
    
    def _display_lookup_table(self, fields: List[Dict[str, Any]]):
        """Display a table of lookup/reference fields."""
        from rich.table import Table
        
        table = Table(show_header=True, header_style="bold cyan", box=None)
        table.add_column("Field", style="cyan", width=30)
        table.add_column("Label", style="white", width=30)
        table.add_column("References", style="yellow")
        
        for field in fields:
            refs = ', '.join(field['referenceTo']) if field['referenceTo'] else ''
            table.add_row(field['name'], field['label'], refs)
        
        console.print(table)
    
    def _handle_history(self, args: str):
        """Handle history command to show field change history."""
        if not self.current_record:
            display_error("No record selected")
            return
        
        # Parse field name (optional) and limit
        field_name = None
        actual_field = None
        limit = 100  # Default limit
        
        if args:
            parts = args.split()
            # Check if first arg is --limit
            if parts[0] == '--limit':
                # Just limit, no field name
                try:
                    if len(parts) > 1:
                        limit = int(parts[1])
                except (ValueError, IndexError):
                    display_error("Invalid --limit value")
                    return
            else:
                # First arg is field name
                field_name = parts[0]
                
                # Check for --limit flag after field name
                if len(parts) > 1 and '--limit' in args:
                    try:
                        limit_idx = parts.index('--limit')
                        if limit_idx + 1 < len(parts):
                            limit = int(parts[limit_idx + 1])
                    except (ValueError, IndexError):
                        display_error("Invalid --limit value")
                        return
        
        # If field name provided, find the actual field name (case-insensitive)
        if field_name:
            for key in self.current_record.keys():
                if key.lower() == field_name.lower():
                    actual_field = key
                    break
            
            if not actual_field:
                display_error(f"Field '{field_name}' not found in current record")
                console.print("[dim]Use 'fields' to see all available fields[/dim]\n")
                return
        
        # Get field history
        try:
            history = self.client.get_field_history(
                self.current_object,
                self.current_record['Id'],
                actual_field,
                limit=limit
            )
            
            if not history:
                if actual_field:
                    display_info(f"No history found for field '{actual_field}'")
                else:
                    display_info("No history found for this record")
                console.print("[dim]Note: Field history tracking may not be enabled[/dim]\n")
                return
            
            # Display history in a table
            from rich.table import Table
            
            title = f"Field History: {actual_field}" if actual_field else "All Field Changes"
            table = Table(title=title, show_header=True, header_style="bold cyan")
            table.add_column("Date", style="yellow", width=20)
            table.add_column("Field", style="magenta", width=25) if not actual_field else None
            table.add_column("Changed By", style="cyan", width=25)
            table.add_column("Old Value", style="dim", width=30)
            table.add_column("New Value", style="green", width=30)
            
            # Add Field column if showing all fields
            if not actual_field:
                table = Table(title=title, show_header=True, header_style="bold cyan")
                table.add_column("Date", style="yellow", width=20)
                table.add_column("Field", style="magenta", width=25)
                table.add_column("Changed By", style="cyan", width=20)
                table.add_column("Old Value", style="dim", width=25)
                table.add_column("New Value", style="green", width=25)
            
            for record in history:
                created_date = record.get('CreatedDate', '')
                # Format date nicely
                if created_date:
                    from datetime import datetime
                    try:
                        dt = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                        created_date = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass
                
                field = record.get('Field', '')
                
                created_by = record.get('CreatedBy', {})
                if isinstance(created_by, dict):
                    created_by_name = created_by.get('Name', 'Unknown')
                else:
                    created_by_name = str(created_by)
                
                old_value = str(record.get('OldValue', '')) if record.get('OldValue') is not None else '[dim]null[/dim]'
                new_value = str(record.get('NewValue', '')) if record.get('NewValue') is not None else '[dim]null[/dim]'
                
                # Truncate long values based on whether we're showing field column
                max_len = 25 if not actual_field else 30
                if len(old_value) > max_len:
                    old_value = old_value[:max_len-3] + '...'
                if len(new_value) > max_len:
                    new_value = new_value[:max_len-3] + '...'
                
                if actual_field:
                    table.add_row(created_date, created_by_name, old_value, new_value)
                else:
                    table.add_row(created_date, field, created_by_name, old_value, new_value)
            
            console.print()
            console.print(table)
            console.print(f"\n[dim]Showing {len(history)} history record(s)[/dim]\n")
            
        except Exception as e:
            display_error(f"Failed to retrieve field history: {e}")
    
    def _handle_relationships(self):
        """Handle relationships command to show all available related objects."""
        if not self.current_record:
            display_error("No record selected")
            return
        
        try:
            relationships = self.client.get_child_relationships(self.current_object)
            
            if not relationships:
                display_info(f"No child relationships found for {self.current_object}")
                return
            
            console.print(f"\n[bold cyan]Available relationships for {self.current_object}:[/bold cyan]\n")
            
            # Group by common vs uncommon
            common_objects = ['Contact', 'Opportunity', 'Case', 'Task', 'Event', 
                            'Lead', 'Contract', 'Order', 'Asset', 'Note', 'Attachment']
            
            common_rels = []
            other_rels = []
            
            for rel in relationships:
                if rel['object'] in common_objects:
                    common_rels.append(rel)
                else:
                    other_rels.append(rel)
            
            # Display common relationships first
            if common_rels:
                console.print("[green]Common relationships:[/green]")
                for rel in sorted(common_rels, key=lambda x: x['name']):
                    console.print(f"  [cyan]{rel['name']:30}[/cyan] → {rel['object']:30} (via {rel['field']})")
            
            # Display other relationships
            if other_rels:
                console.print(f"\n[dim]Other relationships ({len(other_rels)} total):[/dim]")
                # Show first 15
                for rel in sorted(other_rels, key=lambda x: x['name'])[:15]:
                    console.print(f"  [cyan]{rel['name']:30}[/cyan] → {rel['object']:30} (via {rel['field']})")
                
                if len(other_rels) > 15:
                    console.print(f"  [dim]... and {len(other_rels) - 15} more[/dim]")
            
            console.print(f"\n[dim]Use 'related <name>' to view records (e.g., 'related Contacts')[/dim]")
            console.print()
            
        except Exception as e:
            display_error(f"Failed to get relationships: {e}")
    
    def _handle_select_related(self, args: str):
        """Handle selecting a record from related records list."""
        try:
            index = int(args) - 1
            if 0 <= index < len(self.related_records):
                record = self.related_records[index]
                record_id = record['Id']
                
                # Map plural relationship name to singular object name
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
                    'Quotes': 'SBQQ__Quote__c',
                    'Accounts': 'Account',
                    'Products': 'Product2',
                }
                
                # Get the actual object type
                actual_object = object_mapping.get(self.related_type, self.related_type)
                
                # Fetch full record details
                full_record = self.client.get_record(actual_object, record_id)
                
                # Push related records list to stack
                self.navigation_stack.append({
                    'type': 'related',
                    'object': self.current_object,
                    'parent_record': self.current_record,
                    'related_type': self.related_type,
                    'records': self.related_records,
                    'navigation_path': self.navigation_path.copy()
                })
                
                # Update context - we're now viewing a different object type
                self.current_object = actual_object
                self.current_record = full_record
                self.related_records = []
                self.related_type = None
                self.navigation_path = []  # Clear navigation path when selecting new record
                
                display_record(full_record, actual_object)
                
                # Show available related objects for this record type
                if actual_object in self.RELATIONSHIPS:
                    related = self.RELATIONSHIPS[actual_object]
                    console.print(f"[dim]Available related objects: {', '.join(related)}[/dim]")
                    console.print("[dim]Use 'cd <type>' or 'related <type>' to view related records[/dim]\n")
            else:
                display_error(f"Invalid selection. Choose a number between 1 and {len(self.related_records)}")
        except ValueError:
            display_error("Please enter a valid number")
        except Exception as e:
            display_error(f"Failed to select related record: {e}")
