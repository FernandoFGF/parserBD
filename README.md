# SiPM Data Tools

Herramienta profesional unificada para la validación y corrección de datos crudos de SiPM antes de subirlos a la base de datos de DUNE.

## 📂 Estructura

- `main.py`: Ejecutable principal automatizado.
- `input/`: Carpeta donde debes arrastrar tus `Box##` originales.
- `output/`: Carpeta donde aparecerán tus datos listos, renombrados a `Box##_checked` junto con un archivo log con los reportes.
- `config.py`: Archivo de configuración global (aquí puedes cambiar el fabricante, el envío o el Box ID para la validación de manifiestos).
- `validators/`: Librería interna con los scripts de validación (escritos en inglés).
- `fixes/`: Librería interna con los scripts de corrección automática (escritos en inglés).

## 🚀 Cómo usarlo

1. **Configurar los metadatos**: Abre `config.py` y ajusta `MANUFACTURER`, `DELIVERY_ID`, y `TEST_BOX_ID` si hace falta para el nuevo lote de datos a revisar.
2. **Coloca los datos**: Arrastra o copia las carpetas originales enteras (ej. `Box05`, `Box12`) dentro de la carpeta **`input/`**.
3. **Procesar**: Haz doble clic en `main.py` o ejecuta el siguiente comando en la terminal:
   ```bash
   python main.py
   ```
4. **Revisar resultados**: 
   - Ve a la carpeta **`output/`**.
   - Allí encontrarás el archivo **`global_validation_log.txt`**. Ábrelo: solo contendrá los errores reales o las modificaciones ("fixes") que ha hecho.
   - Si no hay reportes de error para una caja, significa que está perfecta.
   - Encontrarás tus cajas listas y parcheadas con el nombre `Box05_checked`. Esa es la carpeta que debes subir a la base de datos de DUNE.
