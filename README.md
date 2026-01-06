# Salesforce CLI

A clean, interactive command-line interface for navigating Salesforce like a file system. Search, navigate, and explore Salesforce data using familiar terminal commands like `cd`, `ls`, and `dir`.

## Features

- 🔍 **Quick Search**: Search for any Salesforce object with simple queries
- 📁 **File System Navigation**: Navigate records using `cd`, `ls`, and `dir` commands
- 🔄 **Smart Sorting**: Sort results by any field with database-level ORDER BY
- 📊 **Interactive Mode**: Navigate through records and relationships interactively
- 🎯 **Drill Down**: View related records (Contacts, Opportunities, Cases, etc.)
- 🎨 **Clean Display**: Beautiful, readable output using Rich formatting
- ⚡ **Fast Navigation**: No clicking through the Salesforce UI
- 🔧 **SOQL Queries**: Execute custom SOQL queries directly

## Installation

1. Clone or download this repository to your local machine

2. Install required packages:
```powershell
pip install -r requirements.txt
```

3. Create a `.env` file with your Salesforce credentials:
```bash
cp .env.example .env
```

4. Edit `.env` with your credentials:
```
SF_USERNAME=your.email@company.com
SF_PASSWORD=your_password
SF_SECURITY_TOKEN=your_security_token
SF_DOMAIN=login  # Use 'test' for sandbox
```

5. (Optional) Add to your PATH for easy access:
```powershell
# The sfcli.bat file allows you to run 'sfcli' from anywhere
# Add the directory to your PATH or copy sfcli.bat to a location already in your PATH
```

## Usage

### Interactive Mode (Recommended)

Start the interactive CLI:
```powershell
python sfcli.py
# Or if added to PATH:
sfcli
```

Once in interactive mode, navigate like a file system:

```
# Search for accounts
sf> search Account Caliber

# Select a record (just type the number)
sf [Account]> 1

# Navigate into Opportunities (like cd into a folder)
sf [Account:Caliber Collision #1516]> cd Opportunities

# List the opportunities (like ls in a directory)
sf [Account:Caliber... / Opportunities]> ls

# Sort by a field
sf [Account:Caliber... / Opportunities]> ls | sort CreatedDate -desc

# Show more results
sf [Account:Caliber... / Opportunities]> ls -n 50

# Show all results
sf [Account:Caliber... / Opportunities]> ls --all

# Select an opportunity
sf [Account:Caliber... / Opportunities]> 2

# Go back (like cd ..)
sf [Opportunity:New Equipment]> cd ..

# Get help
sf> help
```

### Command-Line Mode

Execute one-off commands:

```powershell
# Search for accounts
python sfcli.py search Account "Caliber"

# Get a specific record
python sfcli.py get Account 001xxxxxxxxxxxxxxx

# List available objects
python sfcli.py objects

# Execute SOQL query
python sfcli.py query "SELECT Id, Name FROM Account WHERE Type='Customer' LIMIT 10"
```

## Interactive Commands

### Search & Query
- `search <Object> <query>` - Search for records (e.g., 'search Account Caliber')
- `search <Object> <query> --fields Field1, Field2` - Search with custom fields
- `search <Object> <query> --limit N` - Set max results (default: 200, max: 2000)
- `get <Object> <ID>` - Get a specific record by ID
- `query <SOQL>` - Execute raw SOQL query
- `list objects` - List available Salesforce objects
- `describe [Object]` - Show metadata for object

### File System Navigation
- `cd <relationship>` - Navigate into related records (e.g., 'cd Opportunities')
- `cd ..` - Go back to previous context
- `ls` / `dir` - List contents (shows first 10 by default)
- `ls --all` / `ls -a` - List all records (up to 200)
- `ls -n <number>` - List specific number (e.g., 'ls -n 50')
- `ls | sort <field> -desc` - Sort descending (e.g., 'ls | sort CreatedDate -desc')
- `ls | sort <field> -asc` - Sort ascending (e.g., 'ls | sort Name -asc')
- `<number>` - Quick select (just type a number to select that record)

### Record Actions (when a record is selected)
- `view` - View full record details
- `show all` - View all fields
- `show <field1> <field2>` - Display specific fields
- `fields` - List all available fields for the object
- `relationships` - Show all available related objects
- `update <field> <value>` - Update a field value
- `history [field]` - View field change history
- `parent [fields]` - Jump to parent Account
- `ultimateparent [fields]` - Jump to Ultimate Parent Account
- `children [fields]` - View child Accounts

### General
- `clear` - Clear screen
- `exit` / `quit` - Exit the CLI
- `help` - Show all available commands

## Examples

### Example 1: Navigate Like a File System
```
sf> search Account Caliber
# Results shown in table format

sf [Account]> 1
# Selected: Caliber Collision Indian Trail #1516

sf [Account:Caliber...]> ls
# Shows available relationships (like directories)

sf [Account:Caliber...]> cd Opportunities
# Navigated into Opportunities

sf [Account:Caliber... / Opportunities]> ls | sort CloseDate -desc
# Shows opportunities sorted by close date

sf [Account:Caliber... / Opportunities]> 1
# Selected opportunity

sf [Opportunity:New Equipment]> cd ..
# Back to opportunities list

sf [Account:Caliber... / Opportunities]> cd ..
# Back to account record
```

### Example 2: Search and Sort
```
sf> search Account "Collision" --limit 50
# Search with increased limit

sf [Account]> 1

sf [Account:...]> cd Aggregated_Sales__c
# Navigate to custom object (works with __c or __r)

sf [Account:... / Aggregated_Sales__c]> ls -n 100 | sort CreatedDate -asc
# Show 100 records sorted by creation date
```

### Example 3: Quick Navigation
```
sf> search Contact Smith
sf [Contact]> 2
sf [Contact:John Smith]> cd Cases
sf [Contact:... / Cases]> ls
sf [Contact:... / Cases]> 3
# View case details
```
- `clear` - Clear screen
- `exit` / `quit` - Exit the CLI

## Examples

### Example 1: Search and View Account
```
sf> search Account Amazon
# Results shown in table format

sf [Account]> select 1
# Full account details displayed

sf [Account:Amazon]> related Opportunities
# Related opportunities shown

sf [Account:Amazon]> back
# Return to account view
```

### Example 2: Direct Record Lookup
```
sf> get Contact 003xxxxxxxxxxxxxxx
# Contact details displayed immediately

sf [Contact:John Smith]> related Tasks
# View tasks for this contact
```

### Example 3: Custom Query
```
sf> query SELECT Id, Name, Type FROM Account WHERE AnnualRevenue > 1000000 LIMIT 5
# Query results displayed
```

## Supported Objects

Common objects include:
- Account
- Contact
- Opportunity
- Lead
- Case
- Task
- Event
- Campaign
- User
- Contract
- Custom Objects (e.g., Aggregated_Sales__c)

And many more! Use `list objects` to see all available objects.

## Tips

1. **Navigate Like a File System**: Use `cd` to navigate into relationships and `cd ..` to go back
2. **Use Tab Completion**: The CLI supports tab completion for commands and relationships
3. **Command History**: Use up/down arrows to navigate command history
4. **Quick Select**: Just type a number to select a record (no need to type 'select 1')
5. **Sort Efficiently**: Sorting uses database-level ORDER BY for optimal performance
6. **Custom Objects**: Works with both `__c` and `__r` notation (e.g., `cd Aggregated_Sales__c`)
7. **Display Limits**: Use `ls` for quick view (10 records), `ls -n 50` for more, or `ls --all` for everything
8. **Context Aware**: The prompt shows your current location (e.g., `sf [Account:Name / Opportunities]>`)
9. **Readable Output**: All data is formatted with color and tables for easy reading

## Requirements

- Python 3.7+
- simple-salesforce
- python-dotenv
- rich
- prompt-toolkit

## Security

- Never commit your `.env` file to version control
- Keep your security token secure
- Use environment-specific credentials (production vs sandbox)

## Troubleshooting

### Authentication Failed
- Verify your username, password, and security token
- Check if your IP is whitelisted in Salesforce
- Ensure you're using the correct domain (login vs test)

### Object Not Found
- Use `list objects` to see available objects
- Check object name spelling (case-sensitive)
- Verify you have access to the object in Salesforce

### No Results
- Try broader search terms
- Check if records exist in Salesforce
- Verify field-level security settings

## License

This tool is for internal use only.
