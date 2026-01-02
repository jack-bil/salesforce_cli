"""
Display Utilities Module

Handles formatting and displaying Salesforce data in a readable way.
"""
from typing import Dict, List, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box


console = Console()


def make_id_clickable(salesforce_id: str) -> str:
    """
    Create a clickable link for a Salesforce ID.
    
    Args:
        salesforce_id: Salesforce record ID
        
    Returns:
        Formatted link string for terminal
    """
    if salesforce_id and len(salesforce_id) in [15, 18]:
        url = f"https://axalta.lightning.force.com/{salesforce_id}"
        # Rich supports clickable links with [link=URL]text[/link] syntax
        return f"[link={url}]{salesforce_id}[/link]"
    return salesforce_id


def make_id_clickable(salesforce_id: str) -> str:
    """
    Create a clickable link for a Salesforce ID.
    
    Args:
        salesforce_id: Salesforce record ID
        
    Returns:
        Formatted link string for terminal
    """
    if salesforce_id and len(salesforce_id) in [15, 18]:
        url = f"https://axalta.lightning.force.com/{salesforce_id}"
        # Rich supports clickable links with [link=URL]text[/link] syntax
        return f"[link={url}]{salesforce_id}[/link]"
    return salesforce_id


def display_search_results(records: List[Dict[str, Any]], object_type: str, total_count: int = None):
    """
    Display search results in a formatted table.
    
    Args:
        records: List of Salesforce records
        object_type: Type of object being displayed
        total_count: Optional total count of matching records (for "showing X of Y")
    """
    if not records:
        console.print("\n[yellow]No results found[/yellow]\n")
        return
    
    # Create table
    table = Table(
        title=f"{object_type} Search Results",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    # Add columns
    table.add_column("#", style="dim", width=4)
    table.add_column("ID", style="blue", width=18)
    
    # Add dynamic columns based on fields in first record
    field_names = [k for k in records[0].keys() if k not in ['attributes', 'Id']]
    for field in field_names:
        table.add_column(field, style="white")
    
    # Add rows
    for idx, record in enumerate(records, 1):
        record_id = record.get('Id', '')
        clickable_id = make_id_clickable(record_id) if record_id else ''
        row_data = [str(idx), clickable_id]
        for field in field_names:
            value = record.get(field, '')
            row_data.append(str(value) if value else '')
        table.add_row(*row_data)
    
    console.print()
    console.print(table)
    if total_count and total_count > len(records):
        console.print(f"\n[dim]Showing {len(records)} of {total_count:,} matching records[/dim]")
        console.print(f"[dim]Use --limit to see more results (e.g., --limit 500)[/dim]\n")
    else:
        console.print(f"\n[dim]Found {len(records)} record(s)[/dim]\n")


def display_record(record: Dict[str, Any], object_type: str):
    """
    Display a single record with all its fields.
    
    Args:
        record: Salesforce record dictionary
        object_type: Type of object being displayed
    """
    # Remove attributes metadata
    record_data = {k: v for k, v in record.items() if k != 'attributes'}
    
    # Create a formatted display
    title = f"{object_type}: {record_data.get('Name', record_data.get('Id', 'Record'))}"
    
    # Build content
    lines = []
    for key, value in sorted(record_data.items()):
        if value is not None and value != '':
            # Format the value
            if isinstance(value, dict):
                value_str = str(value)
            elif isinstance(value, bool):
                value_str = "[green]✓[/green]" if value else "[red]✗[/red]"
            elif key == 'Id' or key.endswith('Id') or 'ID' in key:
                # Make IDs clickable
                value_str = make_id_clickable(str(value))
            else:
                value_str = str(value)
            
            lines.append(f"[cyan]{key:30}[/cyan] {value_str}")
    
    content = "\n".join(lines)
    
    panel = Panel(
        content,
        title=title,
        border_style="green",
        box=box.ROUNDED,
        padding=(1, 2)
    )
    
    console.print()
    console.print(panel)
    console.print()


def display_record_summary(record: Dict[str, Any], object_type: str, fields: List[str] = None):
    """
    Display a summary of a record with selected fields.
    
    Args:
        record: Salesforce record dictionary
        object_type: Type of object being displayed
        fields: List of fields to display (if None, shows common fields)
    """
    if fields is None:
        # Show only key fields
        fields = ['Id', 'Name', 'Type', 'Status', 'Owner.Name', 'CreatedDate']
    
    # Filter record to only show specified fields
    filtered_data = {}
    for field in fields:
        if '.' in field:
            # Handle relationship fields like Owner.Name
            parts = field.split('.')
            value = record
            for part in parts:
                value = value.get(part, {}) if isinstance(value, dict) else None
            if value:
                filtered_data[field] = value
        else:
            if field in record:
                filtered_data[field] = record[field]
    
    display_record(filtered_data, object_type)


def display_related_records(records: List[Dict[str, Any]], 
                           relationship_name: str,
                           parent_info: str):
    """
    Display related records in a table.
    
    Args:
        records: List of related records
        relationship_name: Name of the relationship (e.g., "Contacts")
        parent_info: Information about the parent record
    """
    if not records:
        console.print(f"\n[yellow]No {relationship_name} found for {parent_info}[/yellow]\n")
        return
    
    table = Table(
        title=f"{relationship_name} for {parent_info}",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )
    
    # Add columns
    table.add_column("#", style="dim", width=4)
    table.add_column("ID", style="blue", width=18)
    
    # Add dynamic columns
    field_names = [k for k in records[0].keys() if k not in ['attributes', 'Id']]
    for field in field_names:
        table.add_column(field, style="white")
    
    # Add rows
    for idx, record in enumerate(records, 1):
        record_id = record.get('Id', '')
        clickable_id = make_id_clickable(record_id) if record_id else ''
        row_data = [str(idx), clickable_id]
        for field in field_names:
            value = record.get(field, '')
            row_data.append(str(value) if value else '')
        table.add_row(*row_data)
    
    console.print()
    console.print(table)
    console.print(f"\n[dim]Found {len(records)} {relationship_name}[/dim]\n")


def display_menu(title: str, options: List[str]):
    """
    Display a menu with options.
    
    Args:
        title: Menu title
        options: List of menu options
    """
    console.print(f"\n[bold cyan]{title}[/bold cyan]")
    for idx, option in enumerate(options, 1):
        console.print(f"  [yellow]{idx}.[/yellow] {option}")
    console.print()


def display_error(message: str):
    """Display an error message."""
    console.print(f"\n[bold red]Error:[/bold red] {message}\n")


def display_success(message: str):
    """Display a success message."""
    console.print(f"\n[bold green]✓[/bold green] {message}\n")


def display_info(message: str):
    """Display an info message."""
    console.print(f"\n[cyan]ℹ[/cyan] {message}\n")


def display_warning(message: str):
    """Display a warning message."""
    console.print(f"\n[yellow]⚠[/yellow] {message}\n")
