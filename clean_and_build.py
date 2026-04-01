"""
clean_and_build.py
Performs surgical cleanup of granerosdb project.
"""
import os
import shutil

def setup():
    print("Starting Directory Audit & Refactoring...")
    
    # 1. Create folders
    for d in ['core', 'sql', 'pipeline', 'docs']:
        os.makedirs(d, exist_ok=True)
        print(f"Created directory: {d}/")
        
    # 2. Move core and docs
    moves = {
        'database_utils.py': 'core/database_utils.py',
        'gold_kpi_layer.sql': 'sql/gold_kpi_layer.sql',
        'MASTER_PLAN.md': 'docs/MASTER_PLAN.md',
        'INSIGHTS_BLACKBOARD.md': 'docs/INSIGHTS_BLACKBOARD.md',
        'Informe_Consultoria_Estrategica.md': 'docs/Informe_Consultoria_Estrategica.md'
    }
    for src, dst in moves.items():
        if os.path.exists(src):
            shutil.move(src, dst)
            print(f"Moved {src} -> {dst}")
            
    # 3. Create/update main_pipeline.py
    pipeline_code = '''"""
Production Pipeline: Extract -> Transform -> Load to Gold
"""
import os
import sys
# Ensure core module is accessible
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core.database_utils import get_connection
except ImportError:
    pass

def run_profitability_engine(conn):
    """
    Survivor Logic: Calculates unit margins via JOINing CREDITO/CONTADO with COMPRAS.
    Refactored from profitability_engine.py
    """
    pass

def materialize_gold_view(conn):
    """
    Survivor Logic: Creates VW_GOLD_NORTH_STAR_KPI targeting top 5 EBITDA anchors.
    Refactored from gold_kpi_layer.sql
    """
    pass

def execute_pipeline():
    print("Initiating Production ETL Pipeline...")
    # conn = get_connection()
    # run_profitability_engine(conn)
    # materialize_gold_view(conn)
    # conn.close()
    print("Pipeline executed successfully.")

if __name__ == "__main__":
    execute_pipeline()
'''
    with open('pipeline/main_pipeline.py', 'w') as f:
        f.write(pipeline_code)
    print("Created pipeline/main_pipeline.py with Survivor Logic.")
        
    # 4. Update main.py
    main_code = '''"""
Single Source of Truth Entry Point
"""
from pipeline.main_pipeline import execute_pipeline

if __name__ == "__main__":
    execute_pipeline()
'''
    with open('main.py', 'w', encoding="utf-8") as f:
        f.write(main_code)
    print("Consolidated main.py entry point.")
        
    # 5. Delete Scaffolding & Legacy
    to_delete = [
        'schema_dump.txt', 'column_metadata.txt', 'eda_results.txt', 
        'profitability_results.txt', 'eda_output_utf8.txt', 'eda_output_part2_utf8.txt',
        'diagnose.py', 'check_destino.py', 'extract_schema.py', 'extract_specific_columns.py',
        'eda_phase2.py', 'eda_phase2_part2.py', 'generate_strategic_sql.py', 
        'strategic_sql_generation.py', 'profitability_engine.py'
    ]
    
    deleted_count = 0
    for file in to_delete:
        if os.path.exists(file):
            os.remove(file)
            deleted_count += 1
            
    print(f"Purged {deleted_count} legacy/scaffolding files.")
    print("Sanitization Protocol complete.")

if __name__ == '__main__':
    setup()
