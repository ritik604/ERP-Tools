
import sqlite3
import sys
import os

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/query_db.py \"<SQL_QUERY>\"")
        print("Example: python scripts/query_db.py \"SELECT * FROM auth_user LIMIT 5\"")
        return

    # Locate database file - assuming it's in the parent directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    db_path = os.path.join(project_root, 'db.sqlite3')

    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return

    query = sys.argv[1]

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(query)
        
        # specific handling for SELECT queries to display results
        if query.strip().upper().startswith("SELECT") or query.strip().upper().startswith("PRAGMA"):
            # Fetch headers if available
            if cursor.description:
                columns = [description[0] for description in cursor.description]
                print(f"Columns: {', '.join(columns)}")
                print("-" * 40)
            
            rows = cursor.fetchall()
            ifrows = False
            for row in rows:
                ifrows = True
                print(row)
            
            if not ifrows:
                print("No results found.")
        else:
            conn.commit()
            print(f"Query executed successfully. Rows affected: {cursor.rowcount}")
            
        conn.close()
    except Exception as e:
        print(f"Error executing query: {e}")

if __name__ == "__main__":
    main()
