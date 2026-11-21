import sqlite3
import pandas as pd
import streamlit as st

class DatabaseManager:
    def __init__(self, db_path='database.db'):
        self.db_path = db_path
    
    def get_connection(self):
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            return conn
        except Exception as e:
            st.error(f"Database connection error: {e}")
            return None
    
    def check_connection(self):
        try:
            conn = self.get_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                conn.close()
                return len(tables) > 0
        except Exception as e:
            st.error(f"Connection check failed: {e}")
            return False
    
    def get_table_info(self):
        try:
            conn = self.get_connection()
            if not conn:
                return None
            
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            table_info = {}
            for table in tables:
                table_name = table[0]
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                
                # Get column info
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                
                table_info[table_name] = {
                    'count': count,
                    'columns': [col[1] for col in columns]
                }
            
            conn.close()
            return table_info
        except Exception as e:
            st.error(f"Error getting table info: {e}")
            return None

# Initialize database manager
db_manager = DatabaseManager()

# Main app
st.title("SQLite Database Manager")

# Check database connection
if db_manager.check_connection():
    st.success("✅ Database connected successfully!")
    
    # Show database info
    table_info = db_manager.get_table_info()
    if table_info:
        st.write("### Database Tables:")
        for table_name, info in table_info.items():
            st.write(f"• **{table_name}**: {info['count']} rows")
            st.write(f"  Columns: {', '.join(info['columns'])}")
    
    # Database management controls
    with st.expander("🔧 Database Management"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Refresh Data"):
                st.rerun()
        
        with col2:
            if st.button("Show All Tables"):
                try:
                    conn = db_manager.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                    tables = cursor.fetchall()
                    for table in tables:
                        st.write(f"✅ {table[0]}")
                    conn.close()
                except Exception as e:
                    st.error(f"Error: {e}")
        
        with col3:
            if st.button("Test Query"):
                try:
                    conn = db_manager.get_connection()
                    df = pd.read_sql_query("SELECT sqlite_version()", conn)
                    st.write("SQLite Version:", df.iloc[0, 0])
                    conn.close()
                except Exception as e:
                    st.error(f"Query failed: {e}")

else:
    st.error("❌ Database connection failed!")
