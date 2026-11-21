import sqlite3
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

# Database URL
db_url = "sqlite:///data/database.db"

st.title("Database Inspector")

try:
    # Create engine
    engine = create_engine(db_url)
    
    # Check if database is accessible
    with engine.connect() as conn:
        st.success("✅ Database connected successfully!")
        
        # Get all table names
        result = conn.execute(text("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            ORDER BY name;
        """))
        
        tables = result.fetchall()
        st.write(f"### Found {len(tables)} tables:")
        
        if tables:
            for i, table in enumerate(tables):
                table_name = table[0]
                st.write(f"• **{i+1}. {table_name}**")
                
                # Get row count
                count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                row_count = count_result.fetchone()[0]
                st.write(f"  Rows: {row_count}")
                
                # Get table schema
                schema_result = conn.execute(text(f"PRAGMA table_info({table_name})"))
                columns = schema_result.fetchall()
                st.write(f"  Columns: {len(columns)}")
                
                for col in columns:
                    st.write(f"    - {col[1]} ({col[2]})")
        else:
            st.warning("No tables found in database")
            
except Exception as e:
    st.error(f"❌ Database connection failed: {e}")
    st.error(f"Database path: data/database.db")
