🚀 Generador de Parser LR(1) - Proyecto Web
Este proyecto es una aplicación web interactiva que permite a los usuarios definir una gramática, generar la colección canónica de ítems LR(1), construir la tabla de análisis sintáctico y probar el parser con una cadena de entrada. La lógica principal del análisis sintáctico se maneja en un backend de Python utilizando la potente librería lark-parser.

![Imagen de la interfaz de la aplicación web mostrando las áreas de gramática, cadena y resultados]

✨ Características Principales
Interfaz Web Interactiva: Una interfaz de usuario limpia y fácil de usar para ingresar la gramática y la cadena de prueba.

Backend Potente con Python: Utiliza Flask como servidor web y lark-parser para toda la lógica de compiladores, garantizando un análisis correcto y eficiente.

Visualización Completa del Proceso:

Muestra la Colección Canónica de Ítems LR(1) (los estados del autómata).

Genera y visualiza la Tabla de Análisis Sintáctico LR(1) completa (acciones ACTION y transiciones GOTO).

Detalla el proceso de análisis paso a paso para la cadena de entrada, mostrando la pila, la entrada y la acción realizada en cada momento.

Manejo de Errores: Informa al usuario si la gramática es inválida o si la cadena es rechazada durante el análisis.

Arquitectura Cliente-Servidor: Demuestra una arquitectura web moderna y desacoplada, con el frontend (cliente) comunicándose con el backend (servidor) a través de una API REST.

🛠️ Tecnologías Utilizadas
Frontend (Cliente)
HTML5: Para la estructura de la página.

CSS3 (con Tailwind CSS): Para un diseño moderno y responsivo.

JavaScript (Vanilla): Para la lógica del lado del cliente, la interactividad y la comunicación con el backend (usando fetch).

Backend (Servidor)
Python 3: Como lenguaje principal del servidor.

Flask: Un micro-framework ligero para crear el servidor web y la API.

Lark (lark-parser): La librería clave que implementa la generación del parser LR(1) y el análisis de la gramática.

Flask-CORS: Para permitir las peticiones desde el frontend al backend.

⚙️ Instalación y Ejecución
Sigue estos pasos para ejecutar el proyecto en tu máquina local.

Prerrequisitos
Tener Python 3.8 o superior instalado.

Tener pip (el gestor de paquetes de Python) disponible en tu terminal.

Pasos
1. Clona o descarga este repositorio:

git clone [https://github.com/sebastianromero07/compiladores.git](https://github.com/sebastianromero07/compiladores.git)
cd nombre-del-directorio

2. Crea y activa un entorno virtual (Recomendado):
Esto aísla las dependencias del proyecto.

# Para Windows
python -m venv venv
venv\Scripts\activate

# Para macOS / Linux
python3 -m venv venv
source venv/bin/activate

3. Instala las dependencias de Python:
El archivo requirements.txt contiene todas las librerías necesarias.

pip install Flask lark Flask-Cors

(Opcional: puedes crear un archivo requirements.txt con los nombres de las librerías para una instalación más profesional con pip install -r requirements.txt)

4. Inicia el servidor Backend:
Ejecuta el siguiente comando en tu terminal. El servidor se iniciará en modo de depuración.

python app.py

Verás un mensaje indicando que el servidor está corriendo en http://127.0.0.1:5000. ¡No cierres esta terminal!

5. Abre la aplicación web:
En tu explorador de archivos, simplemente haz doble clic en el archivo index.html para abrirlo en tu navegador web preferido.

¡Listo! La página se cargará y podrás empezar a usar la herramienta.

USAGE
Define la Gramática: Escribe tu gramática en el área de texto correspondiente, siguiendo el formato de lark-parser.

Ingresa la Cadena: Escribe la cadena que deseas analizar en el campo de entrada.

Analiza: Haz clic en el botón "Generar y Analizar".

Revisa los Resultados: La aplicación se comunicará con el servidor Python y mostrará los estados, la tabla de análisis y los pasos del proceso en la parte inferior de la página.
