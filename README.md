# Salesforce CLI

A clean, interactive command-line interface for navigating Salesforce without the standard UI. Search for accounts, contacts, opportunities, and other objects with ease.

## Features

- 🔍 **Quick Search**: Search for any Salesforce object with simple queries
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

## Usage

### Interactive Mode (Recommended)

Start the interactive CLI:
```powershell
python sfcli.py
```

Once in interactive mode, you can use these commands:

```
# Search for accounts
sf> search Account Amazon

# Select a record from results
sf [Account]> select 1

# View related contacts
sf [Account:Amazon]> related Contacts

# View all available fields
sf [Account:Amazon]> fields

# Go back
sf [Account:Amazon]> back

# Get help
sf> help
```

### Command-Line Mode

Execute one-off commands:

```powershell
# Search for accounts
python sfcli.py search Account "Amazon"

# Get a specific record
python sfcli.py get Account 001xxxxxxxxxxxxxxx

# List available objects
python sfcli.py objects

# Execute SOQL query
python sfcli.py query "SELECT Id, Name FROM Account WHERE Type='Customer' LIMIT 10"
```

## Interactive Commands

### Search & Query
- `search <Object> <query>` - Search for records (e.g., 'search Account Amazon')
- `get <Object> <ID>` - Get a specific record by ID
- `query <SOQL>` - Execute raw SOQL query
- `list objects` - List available Salesforce objects

### Record Actions (when a record is selected)
- `view` - View full record details
- `fields` - List all available fields for the object
- `related <type>` - View related records (e.g., 'related Contacts')

### Navigation
- `select <number>` - Select a record from search results
- `back` - Go back to previous context
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

And many more! Use `list objects` to see all available objects.

## Common Relationships

The CLI understands common Salesforce relationships:
- Account → Contacts, Opportunities, Cases, Tasks
- Contact → Opportunities, Cases, Tasks
- Opportunity → OpportunityLineItems, Tasks
- Lead → Tasks
- Case → Tasks

## Tips

1. **Use Tab Completion**: The CLI supports tab completion for commands
2. **Command History**: Use up/down arrows to navigate command history
3. **Context Aware**: The CLI shows your current context in the prompt
4. **Quick Navigation**: Use numbers to select records instead of copying IDs
5. **Readable Output**: All data is formatted with color and tables for easy reading

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
