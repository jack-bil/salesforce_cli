"""
CLI Interface Module

Handles command-line argument parsing and interactive mode.
"""
import argparse
import sys
from .interactive import InteractiveSession
from .client import SalesforceClient
from .display import display_record, display_search_results


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Salesforce CLI - Navigate Salesforce from the command line",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Interactive mode:
    python sfcli.py
  
  Search for accounts:
    python sfcli.py search Account "Axalta"
    python sfcli.py search Contact "John Smith"
  
  Get specific record:
    python sfcli.py get Account 001xxxxxxxxxxxxxxx
    
  List available objects:
    python sfcli.py objects
        """
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 0.1.0'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search for records')
    search_parser.add_argument('object_type', help='Object type (e.g., Account, Contact)')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--limit', type=int, default=10, help='Maximum results (default: 10)')
    
    # Get command
    get_parser = subparsers.add_parser('get', help='Get a specific record by ID')
    get_parser.add_argument('object_type', help='Object type (e.g., Account, Contact)')
    get_parser.add_argument('record_id', help='Record ID')
    
    # Objects command
    objects_parser = subparsers.add_parser('objects', help='List available Salesforce objects')
    objects_parser.add_argument('--all', action='store_true', help='Show all objects including system objects')
    
    # Query command
    query_parser = subparsers.add_parser('query', help='Execute raw SOQL query')
    query_parser.add_argument('soql', help='SOQL query string')
    
    args = parser.parse_args()
    
    try:
        # Initialize Salesforce client
        client = SalesforceClient()
        
        # No command = interactive mode
        if not args.command:
            session = InteractiveSession(client)
            return session.run()
        
        # Handle specific commands
        if args.command == 'search':
            results = client.search(args.object_type, args.query, limit=args.limit)
            display_search_results(results, args.object_type)
            return 0
            
        elif args.command == 'get':
            record = client.get_record(args.object_type, args.record_id)
            display_record(record, args.object_type)
            return 0
            
        elif args.command == 'objects':
            objects = client.list_objects(show_all=args.all)
            print("\nAvailable Salesforce Objects:")
            print("=" * 50)
            for obj in sorted(objects):
                print(f"  {obj}")
            print()
            return 0
            
        elif args.command == 'query':
            results = client.execute_query(args.soql)
            print(f"\nQuery returned {len(results)} records\n")
            for record in results:
                print(record)
                print("-" * 50)
            return 0
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\nExiting...")
        return 0
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
