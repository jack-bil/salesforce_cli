#!/usr/bin/env python
"""
Salesforce CLI - Main Entry Point

A clean, interactive CLI for navigating Salesforce without the standard UI.
Search for accounts, contacts, opportunities, and other objects with ease.

Usage:
    python sfcli.py                          # Interactive mode
    python sfcli.py search Account "Axalta"  # Quick search
    python sfcli.py get Account 001...       # Get specific record
    
For detailed help:
    python sfcli.py --help
"""
import sys
from sfcli.cli import main

if __name__ == "__main__":
    sys.exit(main())
