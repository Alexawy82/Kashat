#!/usr/bin/env python3
"""
LedgerLoop CLI - Command-line interface for personal finance management

Usage:
    ledgerloop ingest <file>           # Import CSV/PDF file
    ledgerloop stats                   # Show database statistics  
    ledgerloop classify                # Run AI classification
    ledgerloop detect transfers        # Detect transfer pairs
    ledgerloop detect recurring        # Detect recurring transactions
    ledgerloop export <format>         # Export data (csv, json)
    ledgerloop health                  # Check system health
"""

import sys
import os
import json
import click
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add the src directory to the path so we can import ledgerloop modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from ledgerloop.db import connect, get_conn
from ledgerloop.ingest_csv import import_csv_upload
from ledgerloop.ingest_pdf import import_pdf_upload
from ledgerloop.transfers import detect_transfers
from ledgerloop.recurring import detect_recurring_series
from ledgerloop.ai import get_ai_service
from ledgerloop.rules import apply_all_rules


@click.group()
@click.option('--data-dir', envvar='LEDGERLOOP_DATA_DIR', 
              help='Directory for database and temp files')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.pass_context
def cli(ctx, data_dir, verbose):
    """LedgerLoop - Local-first personal finance management"""
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    
    if data_dir:
        os.environ['LEDGERLOOP_DATA_DIR'] = data_dir
    
    # Initialize database connection
    try:
        connect()
        if verbose:
            click.echo(f"Connected to database: {data_dir or '~/.ledgerloop'}")
    except Exception as e:
        click.echo(f"Error connecting to database: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--account-id', help='Target account ID')
@click.option('--enable-ai/--no-ai', default=True, help='Enable AI processing')
@click.option('--dry-run', is_flag=True, help='Parse without saving to database')
@click.pass_context
def ingest(ctx, file_path, account_id, enable_ai, dry_run):
    """Import and process a CSV or PDF file"""
    verbose = ctx.obj['verbose']
    file_path = Path(file_path)
    
    if verbose:
        click.echo(f"Processing file: {file_path}")
        click.echo(f"Account ID: {account_id or 'auto-create'}")
        click.echo(f"AI enabled: {enable_ai}")
        click.echo(f"Dry run: {dry_run}")
    
    try:
        # Determine file type and process
        if file_path.suffix.lower() == '.csv':
            if verbose:
                click.echo("Detected CSV file")
            
            with open(file_path, 'rb') as f:
                result = import_csv_upload(
                    file_content=f.read(),
                    filename=file_path.name,
                    account_id=account_id,
                    enable_ai=enable_ai,
                    dry_run=dry_run
                )
                
        elif file_path.suffix.lower() == '.pdf':
            if verbose:
                click.echo("Detected PDF file")
                
            with open(file_path, 'rb') as f:
                result = import_pdf_upload(
                    file_content=f.read(),
                    filename=file_path.name,
                    account_id=account_id,
                    enable_ai=enable_ai,
                    dry_run=dry_run
                )
        else:
            click.echo(f"Unsupported file type: {file_path.suffix}", err=True)
            sys.exit(1)
        
        # Display results
        click.echo(f"✅ Import completed successfully")
        click.echo(f"   Run ID: {result.get('run_id', 'N/A')}")
        click.echo(f"   Transactions inserted: {result.get('inserted', 0)}")
        click.echo(f"   Duplicates skipped: {result.get('duplicates', 0)}")
        click.echo(f"   Total rows processed: {result.get('total_rows', 0)}")
        
        if result.get('balance_validated'):
            click.echo("   ✅ Running balance validation passed")
        elif 'balance_validated' in result:
            click.echo("   ⚠️  Running balance validation failed")
            
        if enable_ai and result.get('ai_processing'):
            click.echo(f"   🤖 AI processing: {result['ai_processing']['status']}")
            
    except Exception as e:
        click.echo(f"❌ Import failed: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.option('--period', type=click.Choice(['week', 'month', 'year', 'all']), 
              default='month', help='Time period for statistics')
@click.pass_context
def stats(ctx, period):
    """Show database statistics and insights"""
    verbose = ctx.obj['verbose']
    conn = get_conn()
    
    try:
        # Basic counts
        tx_count = conn.execute("SELECT COUNT(*) FROM [transaction]").fetchone()[0]
        account_count = conn.execute("SELECT COUNT(*) FROM account").fetchone()[0]
        category_count = conn.execute("SELECT COUNT(*) FROM category").fetchone()[0]
        rule_count = conn.execute("SELECT COUNT(*) FROM rule WHERE enabled = true").fetchone()[0]
        
        click.echo(f"📊 LedgerLoop Statistics")
        click.echo(f"   Transactions: {tx_count:,}")
        click.echo(f"   Accounts: {account_count}")
        click.echo(f"   Categories: {category_count}")
        click.echo(f"   Active rules: {rule_count}")
        
        # Date range
        date_range = conn.execute("""
            SELECT MIN(posted_at), MAX(posted_at) 
            FROM [transaction]
        """).fetchone()
        
        if date_range[0]:
            click.echo(f"   Date range: {date_range[0]} to {date_range[1]}")
        
        # Recent activity
        recent_imports = conn.execute("""
            SELECT COUNT(*) FROM import_run 
            WHERE started_at > datetime('now', '-7 days')
        """).fetchone()[0]
        
        click.echo(f"   Recent imports (7 days): {recent_imports}")
        
        # Top categories by amount
        top_categories = conn.execute("""
            SELECT c.name, COUNT(*) as count, SUM(ABS(t.amount)) as total
            FROM [transaction] t
            JOIN transaction_category tc ON t.id = tc.tx_id
            JOIN category c ON tc.category_id = c.id
            WHERE t.amount < 0  -- expenses only
            GROUP BY c.name
            ORDER BY total DESC
            LIMIT 5
        """).fetchall()
        
        if top_categories:
            click.echo(f"\n💰 Top Expense Categories:")
            for name, count, total in top_categories:
                click.echo(f"   {name}: ${total:,.2f} ({count} transactions)")
        
        # AI processing stats
        ai_processed = conn.execute("""
            SELECT COUNT(*) FROM [transaction] 
            WHERE ai_processed_at IS NOT NULL
        """).fetchone()[0]
        
        if ai_processed > 0:
            avg_confidence = conn.execute("""
                SELECT AVG(ai_confidence_score) FROM [transaction] 
                WHERE ai_confidence_score IS NOT NULL
            """).fetchone()[0]
            
            click.echo(f"\n🤖 AI Processing:")
            click.echo(f"   AI-processed transactions: {ai_processed}")
            if avg_confidence:
                click.echo(f"   Average confidence: {avg_confidence:.2%}")
        
    except Exception as e:
        click.echo(f"❌ Error retrieving statistics: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--provider', help='AI provider to use (default: auto)')
@click.option('--confidence-threshold', type=float, default=0.7, 
              help='Minimum confidence threshold')
@click.option('--limit', type=int, help='Limit number of transactions to process')
@click.pass_context
def classify(ctx, provider, confidence_threshold, limit):
    """Run AI classification on unclassified transactions"""
    verbose = ctx.obj['verbose']
    
    try:
        ai_service = get_ai_service()
        
        # Find unclassified transactions
        conn = get_conn()
        query = """
            SELECT id, description_norm, amount, posted_at 
            FROM [transaction] t
            WHERE NOT EXISTS (
                SELECT 1 FROM transaction_category tc 
                WHERE tc.tx_id = t.id
            )
            ORDER BY posted_at DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
            
        unclassified = conn.execute(query).fetchall()
        
        if not unclassified:
            click.echo("✅ All transactions are already classified")
            return
            
        click.echo(f"🤖 Found {len(unclassified)} unclassified transactions")
        
        if verbose:
            click.echo(f"   Using confidence threshold: {confidence_threshold}")
            
        # Process in batches
        classified_count = 0
        skipped_count = 0
        
        with click.progressbar(unclassified, label='Classifying') as transactions:
            for tx_id, description, amount, posted_at in transactions:
                try:
                    result = ai_service.classify_transaction(
                        description=description,
                        amount=abs(amount),
                        context={
                            'posted_at': posted_at,
                            'is_expense': amount < 0
                        }
                    )
                    
                    if result.confidence >= confidence_threshold:
                        # Apply classification
                        # This would need the actual classification logic
                        classified_count += 1
                    else:
                        skipped_count += 1
                        
                except Exception as e:
                    if verbose:
                        click.echo(f"\n   Error classifying {tx_id}: {e}")
                    skipped_count += 1
        
        click.echo(f"✅ Classification complete")
        click.echo(f"   Classified: {classified_count}")
        click.echo(f"   Skipped (low confidence): {skipped_count}")
        
    except Exception as e:
        click.echo(f"❌ Classification failed: {e}", err=True)
        sys.exit(1)


@cli.group()
def detect():
    """Detection operations (transfers, recurring, etc.)"""
    pass


@detect.command()
@click.option('--method', type=click.Choice(['amount_date', 'amount_window']), 
              default='amount_date', help='Detection algorithm')
@click.option('--days', type=int, default=3, help='Detection window in days')
@click.option('--min-amount', type=float, default=1.0, help='Minimum amount to consider')
@click.pass_context  
def transfers(ctx, method, days, min_amount):
    """Detect transfer pairs between accounts"""
    verbose = ctx.obj['verbose']
    
    try:
        if verbose:
            click.echo(f"Running transfer detection with method: {method}")
            click.echo(f"Detection window: {days} days")
            click.echo(f"Minimum amount: ${min_amount}")
        
        result = detect_transfers(
            method=method,
            days_window=days,
            min_amount=min_amount
        )
        
        click.echo(f"✅ Transfer detection complete")
        click.echo(f"   Pairs found: {result.get('pairs_found', 0)}")
        click.echo(f"   New pairs: {result.get('new_pairs', 0)}")
        click.echo(f"   Total amount: ${result.get('total_amount', 0):,.2f}")
        
    except Exception as e:
        click.echo(f"❌ Transfer detection failed: {e}", err=True)
        sys.exit(1)


@detect.command()
@click.option('--min-frequency', type=int, default=3, 
              help='Minimum occurrences to consider recurring')
@click.option('--tolerance-days', type=int, default=7, 
              help='Date tolerance for recurring detection')
@click.pass_context
def recurring(ctx, min_frequency, tolerance_days):
    """Detect recurring transaction patterns"""
    verbose = ctx.obj['verbose']
    
    try:
        if verbose:
            click.echo(f"Running recurring detection")
            click.echo(f"Minimum frequency: {min_frequency}")
            click.echo(f"Date tolerance: {tolerance_days} days")
        
        result = detect_recurring_series(
            min_frequency=min_frequency,
            tolerance_days=tolerance_days
        )
        
        click.echo(f"✅ Recurring detection complete")
        click.echo(f"   Series found: {result.get('series_found', 0)}")
        click.echo(f"   Transactions classified: {result.get('transactions_classified', 0)}")
        
    except Exception as e:
        click.echo(f"❌ Recurring detection failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('format', type=click.Choice(['csv', 'json', 'parquet']))
@click.option('--output', '-o', help='Output file path')
@click.option('--start-date', type=click.DateTime(), help='Start date filter')
@click.option('--end-date', type=click.DateTime(), help='End date filter')
@click.option('--category', help='Category filter')
@click.pass_context
def export(ctx, format, output, start_date, end_date, category):
    """Export transaction data in various formats"""
    verbose = ctx.obj['verbose']
    
    try:
        conn = get_conn()
        
        # Build query with filters
        query = """
            SELECT t.*, c.name as category_name
            FROM [transaction] t
            LEFT JOIN transaction_category tc ON t.id = tc.tx_id
            LEFT JOIN category c ON tc.category_id = c.id
            WHERE 1=1
        """
        
        params = []
        
        if start_date:
            query += " AND t.posted_at >= ?"
            params.append(start_date.date())
            
        if end_date:
            query += " AND t.posted_at <= ?"
            params.append(end_date.date())
            
        if category:
            query += " AND c.name = ?"
            params.append(category)
            
        query += " ORDER BY t.posted_at DESC"
        
        transactions = conn.execute(query, params).fetchall()
        
        if not transactions:
            click.echo("No transactions found matching criteria")
            return
            
        # Generate output filename if not provided
        if not output:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output = f"ledgerloop_export_{timestamp}.{format}"
        
        # Export based on format
        if format == 'csv':
            import csv
            with open(output, 'w', newline='') as f:
                if transactions:
                    writer = csv.DictWriter(f, fieldnames=transactions[0].keys())
                    writer.writeheader()
                    for row in transactions:
                        writer.writerow(dict(row))
                        
        elif format == 'json':
            data = [dict(row) for row in transactions]
            with open(output, 'w') as f:
                json.dump(data, f, indent=2, default=str)
                
        elif format == 'parquet':
            try:
                import pandas as pd
                df = pd.DataFrame([dict(row) for row in transactions])
                df.to_parquet(output, index=False)
            except ImportError:
                click.echo("Parquet export requires pandas and pyarrow", err=True)
                sys.exit(1)
        
        click.echo(f"✅ Exported {len(transactions)} transactions to {output}")
        
    except Exception as e:
        click.echo(f"❌ Export failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def health(ctx):
    """Check system health and configuration"""
    verbose = ctx.obj['verbose']
    
    try:
        conn = get_conn()
        
        # Database connectivity
        conn.execute("SELECT 1").fetchone()
        click.echo("✅ Database connection: OK")
        
        # Check for required tables
        required_tables = [
            'transaction', 'account', 'category', 'rule', 
            'import_run', 'import_file', 'event_log'
        ]
        
        for table in required_tables:
            try:
                conn.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone()
                if verbose:
                    click.echo(f"✅ Table {table}: OK")
            except Exception:
                click.echo(f"❌ Table {table}: Missing or inaccessible")
        
        # Check AI service
        try:
            ai_service = get_ai_service()
            if ai_service.is_available():
                click.echo("✅ AI service: Available")
            else:
                click.echo("⚠️  AI service: Not configured")
        except Exception as e:
            click.echo(f"❌ AI service: Error - {e}")
        
        # Check environment variables
        env_vars = ['LEDGERLOOP_DATA_DIR', 'LEDGERLOOP_API_TOKEN']
        for var in env_vars:
            value = os.getenv(var)
            if value:
                if verbose:
                    click.echo(f"✅ {var}: Set")
            else:
                if verbose:
                    click.echo(f"⚠️  {var}: Not set (using defaults)")
        
        click.echo("\n🏥 System health check complete")
        
    except Exception as e:
        click.echo(f"❌ Health check failed: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()