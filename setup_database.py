"""
Script para inicializar la base de datos con las tablas y datos de ejemplo
"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "sslmode": os.getenv("DB_SSLMODE", "require"),
}

def setup_database():
    """Ejecuta el script SQL para inicializar la base de datos"""
    try:
        # Leer el script SQL
        script_path = os.path.join(os.path.dirname(__file__), "init_db.sql")
        with open(script_path, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        # Conectar y ejecutar
        print("Conectando a la base de datos...")
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        print("Ejecutando script de inicialización...")
        cur.execute(sql_script)
        conn.commit()
        
        print("✅ Base de datos inicializada correctamente!")
        
        # Mostrar las tablas creadas
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """)
        tables = cur.fetchall()
        print("\n📋 Tablas en la base de datos:")
        for table in tables:
            print(f"  - {table[0]}")
        
        # Mostrar cantidad de viajes insertados
        cur.execute("SELECT COUNT(*) FROM viajes")
        count = cur.fetchone()[0]
        print(f"\n🌍 {count} viajes disponibles en el catálogo")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error al inicializar la base de datos: {e}")
        raise

if __name__ == "__main__":
    setup_database()
