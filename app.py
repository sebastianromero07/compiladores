import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from lark import Lark, exceptions

# Obtener la ruta absoluta del directorio actual
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# --- Configuración del Servidor Flask ---
app = Flask(__name__,
            static_folder=os.path.join(BASE_DIR, 'frontend'),
            template_folder=os.path.join(BASE_DIR, 'frontend'))
CORS(app)



# --- Lógica del Parser (Adaptada para Lark) ---

def format_lark_states(parser):
    """
    Extrae y formatea los estados (colección canónica) y las transiciones 
    del objeto parser de Lark.
    """
    formatted_states = []
    for i, state in parser.analysis.states.items():
        state_info = {
            "id": i,
            "items": [],
            "transitions": {}
        }
        # Formatear los ítems del estado
        for item in state:
            # Recrear la representación textual de la regla
            rule_text = f"{item.origin.name} -> {' '.join(map(str, item.origin.expansion))} "
            # Insertar el punto
            rule_parts = rule_text.split()
            rule_parts.insert(item.ptr + 2, '•')
            item_text = ' '.join(rule_parts)
            # El lookahead se extrae del final del ítem
            lookahead = sorted(list(item.lookahead))
            state_info["items"].append(f"[{item_text}, {', '.join(lookahead)}]")
        
        # Formatear las transiciones
        for symbol, next_state_id in state.transitions.items():
            state_info["transitions"][symbol] = next_state_id
            
        formatted_states.append(state_info)
    return formatted_states

def format_lark_table(parser):
    """
    Extrae y formatea las tablas ACTION y GOTO del objeto parser de Lark.
    """
    action_table = {}
    goto_table = {}
    
    # La tabla de acciones de Lark combina SHIFT y REDUCE
    for state_id, actions in parser.analysis.action.items():
        action_table[state_id] = {}
        goto_table[state_id] = {}
        for symbol, action in actions.items():
            if isinstance(action, int): # Es un SHIFT
                action_table[state_id][symbol] = f"s{action}"
            else: # Es un REDUCE
                # action[1] contiene la regla (Rule object)
                rule = action[1]
                # Para encontrar el índice de la regla, necesitamos buscarlo.
                # Lark no provee un índice directo, así que lo representamos con la regla misma.
                rule_text = f"{rule.origin.name} -> {' '.join(map(str, rule.expansion))}"
                action_table[state_id][symbol] = f"reduce: {rule_text}"

    # La tabla goto es más directa
    for state_id, gotos in parser.analysis.goto.items():
        for symbol, next_state_id in gotos.items():
            goto_table[state_id][symbol] = next_state_id
            
    return action_table, goto_table
    

# --- Endpoint de la API ---

from flask import render_template

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/test')
def test():
    import os
    path = os.path.join(BASE_DIR, 'frontend', 'index.html')
    exists = os.path.exists(path)
    return f"Archivo index.html existe: {exists} en {path}"


@app.route('/parse', methods=['POST'])
def handle_parse_request():
    data = request.json
    grammar = data.get('grammar')
    input_string = data.get('input_string')

    if not grammar:
        return jsonify({"error": "La gramática no puede estar vacía."}), 400

    try:
        # 1. Crear el parser LR(1) con Lark
        # El start symbol se infiere como el LHS de la primera regla
        start_symbol = grammar.strip().split('\n')[0].split('->')[0].strip()
        
        # Lark necesita que los no-terminales en mayúsculas no estén entre comillas
        # y los terminales en minúsculas. Ajustamos la gramática si es necesario.
        # Esta es una simplificación, gramáticas complejas podrían requerir más pre-procesamiento.
        
        lark_parser = Lark(grammar, parser='lr', start=start_symbol, keep_all_tokens=True)
        
        # 2. Extraer los datos del parser para visualización
        states_data = format_lark_states(lark_parser.parser)
        action_table, goto_table = format_lark_table(lark_parser.parser)
        
        # Lark no expone públicamente los conjuntos First/Follow de una manera simple,
        # ya que son parte del proceso de construcción interno.
        # Dejaremos estas secciones vacías, ya que la herramienta principal es Lark.
        first_sets = {"info": "Lark no expone directamente los First Sets."}
        follow_sets = {"info": "Lark no expone directamente los Follow Sets."}

        # 3. Analizar la cadena de entrada y trazar los pasos
        parse_steps = []
        try:
            # Usamos el InteractiveParser para seguir los pasos
            interactive_parser = lark_parser.parse_interactive(input_string)
            stack_symbols = []
            for token in interactive_parser.iter_parse():
                action = interactive_parser.parser_state.value
                
                # Estado actual de la pila de Lark
                stack_str = " ".join(str(s) for s in interactive_parser.parser_state.state_stack)
                
                # Símbolos en la pila (aproximación)
                if token.type == '$END':
                    input_rem = '$'
                else:
                    stack_symbols.append(token.value)
                    input_rem = " ".join(t.value for t in interactive_parser.tokens)
                
                parse_steps.append({
                    "stack": stack_str,
                    "input": input_rem,
                    "action": f"Shift '{token.value}' ({token.type})"
                })
            
            # Último paso: Aceptar
            stack_str = " ".join(str(s) for s in interactive_parser.parser_state.state_stack)
            parse_steps.append({"stack": stack_str, "input": "$", "action": "Accept"})
            accepted = True

        except (exceptions.UnexpectedToken, exceptions.UnexpectedCharacters) as e:
            accepted = False
            stack_str = " ".join(str(s) for s in getattr(e, 'parser_state',_).state_stack) if hasattr(e, 'parser_state') else 'N/A'
            
            parse_steps.append({
                "stack": stack_str,
                "input": e.token if hasattr(e, 'token') else 'N/A',
                "action": f"Error: {e}"
            })

        # 4. Enviar todos los datos de vuelta como JSON
        return jsonify({
            "accepted": accepted,
            "first_sets": first_sets,
            "follow_sets": follow_sets,
            "canonical_collection": states_data,
            "parsing_table_action": action_table,
            "parsing_table_goto": goto_table,
            "parsing_steps": parse_steps
        })

    except Exception as e:
        # Capturar errores de gramática de Lark u otros problemas
        return jsonify({"error": f"Error al procesar la gramática o la cadena: {str(e)}"}), 500


# --- Iniciar el servidor ---
if __name__ == '__main__':
    # Correr en modo debug para ver errores detallados durante el desarrollo
    # El host '0.0.0.0' lo hace accesible en la red local
    app.run(host='0.0.0.0', port=5000, debug=True)
