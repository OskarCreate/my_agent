-- Script para inicializar las tablas de viajes y reservaciones

-- Tabla de viajes
CREATE TABLE IF NOT EXISTS viajes (
    id SERIAL PRIMARY KEY,
    destino VARCHAR(255) NOT NULL,
    descripcion TEXT,
    precio DECIMAL(10, 2) NOT NULL,
    fecha_salida DATE NOT NULL,
    fecha_regreso DATE NOT NULL,
    cupos_disponibles INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de reservaciones
CREATE TABLE IF NOT EXISTS reservaciones (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL,
    viaje_id INTEGER NOT NULL REFERENCES viajes(id),
    num_personas INTEGER NOT NULL DEFAULT 1,
    fecha_reservacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    estado VARCHAR(50) DEFAULT 'confirmada',
    total DECIMAL(10, 2) NOT NULL,
    CONSTRAINT fk_viaje FOREIGN KEY (viaje_id) REFERENCES viajes(id) ON DELETE CASCADE
);

-- Índices para mejorar el rendimiento
CREATE INDEX IF NOT EXISTS idx_viajes_fecha_salida ON viajes(fecha_salida);
CREATE INDEX IF NOT EXISTS idx_reservaciones_usuario ON reservaciones(usuario_id);
CREATE INDEX IF NOT EXISTS idx_reservaciones_viaje ON reservaciones(viaje_id);

-- Datos de ejemplo
INSERT INTO viajes (destino, descripcion, precio, fecha_salida, fecha_regreso, cupos_disponibles) VALUES
    ('Cancún, México', 'Playas paradisíacas con todo incluido. Hotel 5 estrellas frente al mar.', 1299.99, '2025-12-15', '2025-12-22', 20),
    ('París, Francia', 'Tour romántico por la ciudad del amor. Incluye Torre Eiffel y Louvre.', 2499.99, '2025-11-20', '2025-11-27', 15),
    ('Machu Picchu, Perú', 'Aventura histórica en las ruinas incas. Incluye guía y transporte.', 1899.99, '2026-01-10', '2026-01-17', 12),
    ('Tokyo, Japón', 'Experiencia cultural única. Templos, tecnología y gastronomía.', 3299.99, '2026-02-05', '2026-02-15', 10),
    ('Cartagena, Colombia', 'Ciudad amurallada y playas caribeñas. Historia y diversión.', 899.99, '2025-12-01', '2025-12-08', 25),
    ('Nueva York, USA', 'La Gran Manzana te espera. Broadway, museos y Times Square.', 1799.99, '2025-11-25', '2025-12-02', 18),
    ('Barcelona, España', 'Arte, arquitectura y playa mediterránea. Sagrada Familia y más.', 2199.99, '2026-03-15', '2026-03-22', 14),
    ('Río de Janeiro, Brasil', 'Carnaval, playas y el Cristo Redentor. Pura alegría.', 1599.99, '2026-02-20', '2026-02-27', 22)
ON CONFLICT DO NOTHING;

-- Reservaciones de ejemplo (opcional, para testing)
-- INSERT INTO reservaciones (usuario_id, viaje_id, num_personas, total) VALUES
--     (1, 1, 2, 2599.98),
--     (1, 5, 1, 899.99);
