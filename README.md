# Catálogo Flexi y Quirelli · Otoño–Invierno 2026

Sitio estático público para el inventario confirmado de Flexi Piedras Negras.
El repositorio es independiente de Growth OS: solo contiene la copia web lista
para GitHub Pages.

## Contenido

- 75 variantes de inventario confirmado, presentadas como 54 tarjetas: una
  por modelo, con todos sus colores disponibles indicados en la misma tarjeta.
- Filtros por marca, categoría y temporada; buscador por modelo o nombre.
- Enlace de consulta por WhatsApp desde cada producto.
- Fotografías de producto optimizadas para web; los modelos sin foto real
  conservan un placeholder claro, sin inventar producto o disponibilidad.

## Generar localmente

En la raíz de este repositorio:

```bash
python3 scripts/build_catalog.py
python3 scripts/validate_catalog.py
```

El generador lee los originales de Google Drive en modo lectura, extrae los ZIP
requeridos y crea `assets/` con JPEG progresivo a un máximo de 1600 px. No
modifica Drive ni el repositorio principal `growth-os`.

## Publicación

La publicación esperada es GitHub Pages desde la rama `main` y la raíz del
repositorio. No requiere backend ni secretos.
