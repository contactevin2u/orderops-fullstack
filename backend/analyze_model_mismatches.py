#!/usr/bin/env python3

"""
Analyze data type mismatches between SQLAlchemy models and Alembic migrations
This script identifies inconsistencies that could cause production issues.
"""

import re
import os
from pathlib import Path

# Key model files and their expected data types
MODEL_ANALYSIS = {
    'user.py': {
        'users': {
            'id': 'Integer (primary key)',
            'username': 'String(50)',
            'password_hash': 'String(128)', 
            'role': 'Enum(Role)',
            'created_at': 'DateTime'
        }
    },
    'driver.py': {
        'drivers': {
            'id': 'BigInteger (primary key)',
            'name': 'String(100) nullable',
            'phone': 'String(20) nullable',
            'firebase_uid': 'String(128) unique',
            'base_warehouse': 'String(20)',
            'priority_lorry_id': 'String(50) nullable',
            'is_active': 'Boolean',
            'created_at': 'DateTime(timezone=True)'
        }
    },
    'lorry_assignment.py': {
        'lorry_assignments': {
            'id': 'BigInteger (primary key)',
            'driver_id': 'ForeignKey(drivers.id)',
            'lorry_id': 'String(50)',
            'assignment_date': 'Date',
            'shift_id': 'ForeignKey(driver_shifts.id) nullable',
            'stock_verified': 'Boolean default=False',
            'status': 'String(20) default=ASSIGNED',
            'assigned_by': 'ForeignKey(users.id)',
            'created_at': 'DateTime(timezone=True)',
            'updated_at': 'DateTime(timezone=True)'
        }
    },
    'lorry.py': {
        'lorries': {
            'id': 'BigInteger (primary key)',
            'lorry_id': 'String(50) unique',
            'plate_number': 'String(20) nullable',
            'model': 'String(100) nullable', 
            'capacity': 'String(50) nullable',
            'is_active': 'Boolean default=True',
            'is_available': 'Boolean default=True',
            'base_warehouse': 'String(20) default=BATU_CAVES',
            'current_location': 'String(100) nullable',
            'notes': 'Text nullable',
            'last_maintenance_date': 'DateTime(timezone=True) nullable',
            'created_at': 'DateTime(timezone=True)',
            'updated_at': 'DateTime(timezone=True)'
        }
    }
}

# Migration analysis patterns
MIGRATION_PATTERNS = {
    'table_creation': r"op\.create_table\('(\w+)'",
    'column_types': r"sa\.Column\('(\w+)',\s*sa\.(\w+)\(([^)]*)\)(?:,\s*([^,\n]*))*",
    'foreign_keys': r"sa\.ForeignKeyConstraint\(\['(\w+)'\],\s*\['([^']+)'\]",
    'primary_keys': r"sa\.PrimaryKeyConstraint\('(\w+)'\)"
}

def analyze_models():
    """Parse model files and extract expected schema"""
    models_dir = Path("app/models")
    analysis = {}
    
    print("📋 ANALYZING MODEL DEFINITIONS...")
    
    for model_file in models_dir.glob("*.py"):
        if model_file.name == "__init__.py" or model_file.name == "base.py":
            continue
            
        try:
            content = model_file.read_text()
            
            # Extract class definitions and their table mappings
            class_matches = re.findall(r'class\s+(\w+)\(Base\):', content)
            table_matches = re.findall(r'__tablename__\s*=\s*"(\w+)"', content)
            
            if class_matches and table_matches:
                class_name = class_matches[0]
                table_name = table_matches[0]
                
                # Extract column mappings
                column_pattern = r'(\w+):\s*Mapped\[([^\]]+)\]\s*=\s*mapped_column\(([^)]+)\)'
                columns = re.findall(column_pattern, content)
                
                analysis[model_file.name] = {
                    'class': class_name,
                    'table': table_name,
                    'columns': columns
                }
                
                print(f"✅ {model_file.name}: {class_name} -> {table_name} ({len(columns)} columns)")
        
        except Exception as e:
            print(f"❌ Error analyzing {model_file.name}: {e}")
    
    return analysis

def analyze_migrations():
    """Parse migration files and extract actual schema"""
    migrations_dir = Path("alembic/versions")
    analysis = {}
    
    print("\n📋 ANALYZING MIGRATION DEFINITIONS...")
    
    for migration_file in migrations_dir.glob("*.py"):
        try:
            content = migration_file.read_text()
            
            # Extract table creations
            table_matches = re.findall(MIGRATION_PATTERNS['table_creation'], content)
            
            if table_matches:
                for table_name in table_matches:
                    # Find the table definition block
                    table_pattern = rf"op\.create_table\('{table_name}',(.*?)sa\.PrimaryKeyConstraint"
                    table_match = re.search(table_pattern, content, re.DOTALL)
                    
                    if table_match:
                        table_def = table_match.group(1)
                        
                        # Extract columns
                        column_matches = re.findall(r"sa\.Column\('(\w+)',\s*sa\.(\w+)(?:\(([^)]*)\))?(?:,\s*([^,\n]*?))?(?=,\s*sa\.Column|\s*sa\.)", table_def)
                        
                        if table_name not in analysis:
                            analysis[table_name] = {}
                        
                        analysis[table_name][migration_file.name] = {
                            'columns': column_matches
                        }
                        
                        print(f"✅ {migration_file.name}: {table_name} ({len(column_matches)} columns)")
        
        except Exception as e:
            print(f"❌ Error analyzing {migration_file.name}: {e}")
    
    return analysis

def find_mismatches(model_analysis, migration_analysis):
    """Compare models vs migrations and identify mismatches"""
    print("\n🔍 IDENTIFYING DATA TYPE MISMATCHES...")
    
    mismatches = []
    
    # Check critical tables from MODEL_ANALYSIS
    for model_file, expected_schema in MODEL_ANALYSIS.items():
        for table_name, expected_columns in expected_schema.items():
            print(f"\n🔍 Checking {table_name} (from {model_file}):")
            
            # Find this table in migrations
            table_found = False
            for migration_file, tables in migration_analysis.items():
                if table_name in tables:
                    table_found = True
                    migration_columns = {col[0]: f"{col[1]}({col[2]})" if col[2] else col[1] 
                                       for col in tables[table_name].get('columns', [])}
                    
                    # Compare each expected column
                    for col_name, expected_type in expected_columns.items():
                        if col_name in migration_columns:
                            migration_type = migration_columns[col_name]
                            
                            # Simple comparison (could be enhanced)
                            if not _types_compatible(expected_type, migration_type):
                                mismatch = {
                                    'table': table_name,
                                    'column': col_name,
                                    'model_file': model_file,
                                    'expected': expected_type,
                                    'migration': migration_type,
                                    'migration_file': migration_file
                                }
                                mismatches.append(mismatch)
                                print(f"  ❌ {col_name}: Expected {expected_type}, Migration has {migration_type}")
                            else:
                                print(f"  ✅ {col_name}: Compatible ({expected_type} ≈ {migration_type})")
                        else:
                            missing = {
                                'table': table_name,
                                'column': col_name,
                                'model_file': model_file,
                                'expected': expected_type,
                                'migration': 'MISSING',
                                'migration_file': migration_file
                            }
                            mismatches.append(missing)
                            print(f"  ❌ {col_name}: MISSING from migration")
            
            if not table_found:
                print(f"  ❌ Table {table_name} not found in any migration!")
    
    return mismatches

def _types_compatible(expected, actual):
    """Check if model type and migration type are compatible"""
    expected = expected.lower()
    actual = actual.lower()
    
    # Handle common compatible cases
    compatibility_map = {
        'integer': ['integer', 'biginteger'],
        'biginteger': ['biginteger', 'integer'],
        'string(50)': ['string(length=50)', 'string(50)', 'varchar(50)'],
        'string(100)': ['string(length=100)', 'string(100)', 'varchar(100)'],
        'string(128)': ['string(length=128)', 'string(128)', 'varchar(128)'],
        'boolean': ['boolean', 'bool'],
        'datetime': ['datetime', 'timestamp'],
        'datetime(timezone=true)': ['datetime(timezone=true)', 'timestamp'],
        'text': ['text', 'string'],
        'date': ['date'],
        'enum': ['string', 'varchar']  # Enums often stored as strings
    }
    
    for expected_type, compatible_types in compatibility_map.items():
        if expected_type in expected:
            return any(compat in actual for compat in compatible_types)
    
    # Fallback: exact match
    return expected == actual

def main():
    print("🔍 ORDEROPS DATA TYPE ANALYSIS")
    print("=" * 50)
    
    # Analyze models
    model_analysis = analyze_models()
    
    # Analyze migrations  
    migration_analysis = analyze_migrations()
    
    # Find mismatches
    mismatches = find_mismatches(model_analysis, migration_analysis)
    
    # Report results
    print(f"\n📊 ANALYSIS RESULTS")
    print("=" * 50)
    
    if mismatches:
        print(f"❌ Found {len(mismatches)} data type mismatches:")
        for mismatch in mismatches:
            print(f"\n🚨 MISMATCH:")
            print(f"   Table: {mismatch['table']}")
            print(f"   Column: {mismatch['column']}")
            print(f"   Model ({mismatch['model_file']}): {mismatch['expected']}")
            print(f"   Migration ({mismatch['migration_file']}): {mismatch['migration']}")
    else:
        print("✅ No critical data type mismatches found!")
    
    print(f"\n🎯 RECOMMENDATIONS:")
    print("   1. Fix data type mismatches before production deployment")
    print("   2. Create a data type alignment migration")
    print("   3. Test all model operations after fixing")
    print("   4. Update model field definitions if needed")

if __name__ == "__main__":
    main()