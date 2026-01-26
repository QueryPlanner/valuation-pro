import duckdb
import os

DB_MAIN = '/Volumes/lord-ssd/data/sec-data/sec-notes.duckdb'
DB_SOURCE = 'sec_fsn.duckdb'
DB_TEST = 'temp_merge_test.duckdb'

def test_merge():
    if os.path.exists(DB_TEST):
        os.remove(DB_TEST)

    con = duckdb.connect(DB_TEST)
    
    # 1. Replicate Schema from Main DB
    print("Replicating schema...")
    con.execute(f"ATTACH '{DB_MAIN}' AS main_db")
    con.execute("CREATE TABLE sub AS SELECT * FROM main_db.sub WHERE 1=0") # Empty table
    con.execute("CREATE TABLE num AS SELECT * FROM main_db.num WHERE 1=0") # Empty table
    con.execute("DETACH main_db")
    
    # 2. Attach Source
    print("Attaching source...")
    con.execute(f"ATTACH '{DB_SOURCE}' AS source_db")
    
    # 3. Test SUB Merge (Handling types and order)
    print("Testing SUB merge...")
    # Get column names from target to ensure order
    cols_sub = [row[0] for row in con.execute("DESCRIBE sub").fetchall()]
    cols_sub_str = ", ".join(cols_sub)
    
    # Construct Select with Casts
    # mapping: source_col -> cast expression
    # default to casting to VARCHAR
    select_parts = []
    for col in cols_sub:
        # Check if source has this col
        # In source, some might be different types
        select_parts.append(f"CAST(source_db.sub.{col} AS VARCHAR)")
        
    select_query = ", ".join(select_parts)
    
    # Insert a few rows that are NOT in main (simulated by just taking some from source)
    sql_sub = f"""
    INSERT INTO sub ({cols_sub_str})
    SELECT {select_query}
    FROM source_db.sub
    LIMIT 10;
    """
    try:
        con.execute(sql_sub)
        print("Successfully inserted 10 rows into SUB")
    except Exception as e:
        print(f"FAILED SUB INSERT: {e}")
        return

    # 4. Test NUM Merge
    print("Testing NUM merge...")
    cols_num = [row[0] for row in con.execute("DESCRIBE num").fetchall()]
    cols_num_str = ", ".join(cols_num)
    
    select_parts_num = []
    for col in cols_num:
        select_parts_num.append(f"CAST(source_db.num.{col} AS VARCHAR)")
    
    select_query_num = ", ".join(select_parts_num)
    
    sql_num = f"""
    INSERT INTO num ({cols_num_str})
    SELECT {select_query_num}
    FROM source_db.num
    LIMIT 10;
    """
    try:
        con.execute(sql_num)
        print("Successfully inserted 10 rows into NUM")
    except Exception as e:
        print(f"FAILED NUM INSERT: {e}")
        return

    print("Merge Test PASSED.")
    con.close()
    if os.path.exists(DB_TEST):
        os.remove(DB_TEST)

if __name__ == "__main__":
    test_merge()
