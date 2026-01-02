# Quick Start Guide

## Setup (One-Time)

1. **Create your `.env` file**:
   ```powershell
   cd "c:\Python312\Projects\Salesforce CLI"
   Copy-Item .env.example .env
   notepad .env
   ```

2. **Add your Salesforce credentials** to `.env`:
   ```
   SF_USERNAME=your.email@axalta.com
   SF_PASSWORD=your_password
   SF_SECURITY_TOKEN=your_security_token
   SF_DOMAIN=login
   ```

   To get your security token:
   - Log into Salesforce
   - Click your profile icon → Settings
   - Search for "Reset My Security Token"
   - Click "Reset Security Token"
   - Check your email for the token

3. **Test the connection**:
   ```powershell
   python sfcli.py objects
   ```

## Quick Examples

### Interactive Mode (Best for exploring)
```powershell
python sfcli.py

# Then try these commands:
search Account Axalta
select 1
related Contacts
fields
back
help
exit
```

### Command Mode (Best for quick lookups)
```powershell
# Search for an account
python sfcli.py search Account "Advance Auto Parts"

# Get specific record
python sfcli.py get Account 001xxxxxxxxxxxxxxx

# Run a query
python sfcli.py query "SELECT Id, Name, Type FROM Account WHERE Type='Customer' LIMIT 10"
```

## Common Use Cases

### Find an account and view its contacts
```
sf> search Account "PPG"
sf [Account]> select 1
sf [Account:PPG Industries]> related Contacts
```

### View all fields on a record
```
sf> get Account 001xxxxxxxxxxxxxxx
sf [Account:...]> fields
```

### Find opportunities for an account
```
sf> search Account "Sherwin"
sf [Account]> select 1
sf [Account:Sherwin Williams]> related Opportunities
```

## Tips

- Use **Tab** for command completion
- Use **↑/↓** for command history
- Type `help` anytime for available commands
- Type `back` to navigate up one level
- The prompt shows your current context

## Troubleshooting

**"Missing Salesforce credentials"**
→ Make sure your `.env` file exists and has all required fields

**"Authentication failed"**
→ Check your password and security token are correct
→ Make sure you're using the right domain (login vs test)

**"No results found"**
→ Try broader search terms
→ Make sure the records exist in Salesforce

## Need More Help?

See the full README.md for detailed documentation.
