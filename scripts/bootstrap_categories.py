#!/usr/bin/env python3
"""
Bootstrap Standard Categories Script

This script creates standard financial categories that AI commonly suggests.
Run this after clearing the database to ensure proper categorization.

Usage:
    python bootstrap_categories.py
"""

import sys
import os
from pathlib import Path

# Add the backend src directory to the path
backend_src = Path(__file__).parent / "apps" / "backend" / "src"
sys.path.insert(0, str(backend_src))

def bootstrap_categories():
    """Bootstrap standard financial categories"""
    try:
        from kashat.ai_smart_categorization import bootstrap_missing_categories
        from kashat.db import get_conn
        
        print("🏗️  Bootstrapping standard financial categories...")
        
        # Bootstrap standard categories
        created_count = bootstrap_missing_categories()
        print(f"✅ Created {created_count} standard categories")
        
        # Show current categories
        conn = get_conn()
        categories = conn.execute('SELECT id, name, parent_id FROM category ORDER BY name').fetchall()
        print(f"📊 Total categories: {len(categories)}")
        
        print("\n📋 Category Hierarchy:")
        
        # Group by parent for better display
        parent_groups = {}
        for cat_id, name, parent_id in categories:
            if parent_id is None:
                parent_groups[cat_id] = {'name': name, 'children': []}
            else:
                if parent_id not in parent_groups:
                    parent_groups[parent_id] = {'name': 'Unknown Parent', 'children': []}
                parent_groups[parent_id]['children'].append(name)
        
        # Display hierarchy
        for parent_id, group in parent_groups.items():
            print(f"  🗂️  {group['name']}")
            for child in group['children']:
                print(f"    └── {child}")
        
        print("\n🎉 Categories bootstrapped successfully!")
        print("📈 Your AI categorization should now work much better!")
        
    except ImportError as e:
        print(f"❌ Error: Could not import required modules: {e}")
        print("💡 Make sure you're in the project root directory and dependencies are installed")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error bootstrapping categories: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    bootstrap_categories()