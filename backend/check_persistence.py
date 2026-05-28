import os
import sys
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database URL - adjusting to the correct environment
DATABASE_URL = "postgresql://verificai:verificai123@localhost:5432/verificai"

def check_data():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    print("\n=== VERIFICAi DATABASE INSPECTION ===")
    
    # 1. Total records in general_analysis_results
    try:
        count = session.execute(text("SELECT COUNT(*) FROM general_analysis_results")).scalar()
        print(f"Total GeneralAnalysisResult: {count}")
        
        if count > 0:
            print("\n--- Latest Analysis Results ---")
            query = text("SELECT id, analysis_name, criteria_count, criteria_results FROM general_analysis_results ORDER BY id DESC LIMIT 3")
            results = session.execute(query).all()
            for r in results:
                res_id, name, c_count, c_results = r
                print(f"ID: {res_id} | Name: {name} | Criteria: {c_count}")
                
                if c_results:
                    # In modern SQLAlchemy with JSON column, c_results is already a dict
                    data = c_results if isinstance(c_results, dict) else json.loads(c_results)
                    print(f"  - Found {len(data)} criteria results in JSON field.")
                    for key, val in list(data.items())[:3]:
                        print(f"    * {key}: {val.get('name', 'N/A')}")
                else:
                    print("  - [!] criteria_results JSON is EMPTY or NULL")
    except Exception as e:
        print(f"Error checking general_analysis_results: {e}")

    # 2. Check CodeEntry
    try:
        count_code = session.execute(text("SELECT COUNT(*) FROM code_entries")).scalar()
        print(f"\nTotal CodeEntry records: {count_code}")
        if count_code > 0:
            latest_code = session.execute(text("SELECT id, original_name FROM code_entries ORDER BY id DESC LIMIT 1")).one()
            print(f"  - Latest CodeEntry: ID {latest_code[0]}, Name: {latest_code[1]}")
    except Exception as e:
        print(f"Error checking code_entries: {e}")

    session.close()

if __name__ == "__main__":
    check_data()
