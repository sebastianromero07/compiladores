import os
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS 

# Obtener la ruta absoluta del directorio actual
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# --- Configuración del Servidor Flask ---
app = Flask(__name__,
            static_folder=os.path.join(BASE_DIR, 'frontend'),
            template_folder=os.path.join(BASE_DIR, 'frontend'))
CORS(app)

# --- Implementación del Parser LR(1) ---

class Grammar:
    def __init__(self):
        self.productions = []
        self.start_symbol = None
        self.terminals = set()
        self.non_terminals = set()
        
    def add_production(self, lhs, rhs):
        if self.start_symbol is None:
            self.start_symbol = lhs
        self.non_terminals.add(lhs)
        self.productions.append((lhs, rhs))
        
        for symbol in rhs:
            if symbol.islower() or symbol in ['(', ')', '+', '*', '/', '-', '=', ';', ',', 'ε']:
                self.terminals.add(symbol)
            else:
                self.non_terminals.add(symbol)

class Item:
    def __init__(self, lhs, rhs, dot_pos, lookahead):
        self.lhs = lhs
        self.rhs = rhs
        self.dot_pos = dot_pos
        self.lookahead = lookahead
        
    def __str__(self):
        rhs_with_dot = self.rhs[:self.dot_pos] + ['•'] + self.rhs[self.dot_pos:]
        return f"[{self.lhs} -> {' '.join(rhs_with_dot)}, {self.lookahead}]"
    
    def __eq__(self, other):
        return (self.lhs == other.lhs and 
                self.rhs == other.rhs and 
                self.dot_pos == other.dot_pos and 
                self.lookahead == other.lookahead)
    
    def __hash__(self):
        return hash((self.lhs, tuple(self.rhs), self.dot_pos, self.lookahead))

class LR1Parser:
    def __init__(self, grammar):
        self.grammar = grammar
        self.first_sets = {}
        self.states = []
        self.goto_table = {}
        self.action_table = {}
        self.build_parser()
    
    def compute_first_sets(self):
        """Calcula los conjuntos FIRST para todos los símbolos"""
        # Inicializar FIRST sets
        for terminal in self.grammar.terminals:
            self.first_sets[terminal] = {terminal}
        
        for non_terminal in self.grammar.non_terminals:
            self.first_sets[non_terminal] = set()
        
        # Iterativo hasta que no haya cambios
        changed = True
        while changed:
            changed = False
            for lhs, rhs in self.grammar.productions:
                old_size = len(self.first_sets[lhs])
                
                if not rhs or rhs == ['ε']:  # Producción vacía
                    self.first_sets[lhs].add('ε')
                else:
                    for symbol in rhs:
                        self.first_sets[lhs].update(self.first_sets[symbol] - {'ε'})
                        if 'ε' not in self.first_sets[symbol]:
                            break
                    else:
                        # Todos los símbolos derivan ε
                        self.first_sets[lhs].add('ε')
                
                if len(self.first_sets[lhs]) != old_size:
                    changed = True
    
    def first_of_string(self, symbols):
        """Calcula FIRST de una secuencia de símbolos"""
        if not symbols:
            return {'ε'}
        
        result = set()
        for symbol in symbols:
            first_symbol = self.first_sets.get(symbol, {symbol})
            result.update(first_symbol - {'ε'})
            if 'ε' not in first_symbol:
                break
        else:
            result.add('ε')
        
        return result
    
    def closure(self, items):
        """Calcula la clausura de un conjunto de ítems"""
        closure_set = set(items)
        
        changed = True
        while changed:
            changed = False
            new_items = set()
            
            for item in closure_set:
                if item.dot_pos < len(item.rhs):
                    next_symbol = item.rhs[item.dot_pos]
                    if next_symbol in self.grammar.non_terminals:
                        # Beta es lo que sigue después del símbolo
                        beta = item.rhs[item.dot_pos + 1:] + [item.lookahead]
                        first_beta = self.first_of_string(beta)
                        
                        for lhs, rhs in self.grammar.productions:
                            if lhs == next_symbol:
                                for lookahead in first_beta:
                                    if lookahead != 'ε':
                                        new_item = Item(lhs, rhs, 0, lookahead)
                                        if new_item not in closure_set:
                                            new_items.add(new_item)
                                            changed = True
            
            closure_set.update(new_items)
        
        return closure_set
    
    def goto(self, items, symbol):
        """Calcula GOTO(items, symbol)"""
        goto_items = set()
        
        for item in items:
            if (item.dot_pos < len(item.rhs) and 
                item.rhs[item.dot_pos] == symbol):
                new_item = Item(item.lhs, item.rhs, item.dot_pos + 1, item.lookahead)
                goto_items.add(new_item)
        
        return self.closure(goto_items)
    
    def build_parser(self):
        """Construye los estados y las tablas del parser LR(1)"""
        self.compute_first_sets()
        
        # Estado inicial: S' -> •S, $
        augmented_start = self.grammar.start_symbol + "'"
        initial_item = Item(augmented_start, [self.grammar.start_symbol], 0, '$')
        initial_state = self.closure({initial_item})
        
        self.states = [initial_state]
        unmarked = [0]
        
        # Construir todos los estados
        while unmarked:
            state_id = unmarked.pop(0)
            current_state = self.states[state_id]
            
            # Encontrar todos los símbolos que pueden seguir al punto
            symbols = set()
            for item in current_state:
                if item.dot_pos < len(item.rhs):
                    symbols.add(item.rhs[item.dot_pos])
            
            # Para cada símbolo, calcular GOTO
            for symbol in symbols:
                goto_state = self.goto(current_state, symbol)
                if goto_state:
                    # Buscar si este estado ya existe
                    existing_state_id = None
                    for i, state in enumerate(self.states):
                        if state == goto_state:
                            existing_state_id = i
                            break
                    
                    if existing_state_id is None:
                        # Nuevo estado
                        new_state_id = len(self.states)
                        self.states.append(goto_state)
                        unmarked.append(new_state_id)
                        self.goto_table[(state_id, symbol)] = new_state_id
                    else:
                        self.goto_table[(state_id, symbol)] = existing_state_id
        
        # Construir las tablas ACTION y GOTO
        self.build_action_table()
    
    def build_action_table(self):
        """Construye la tabla ACTION"""
        for state_id, state in enumerate(self.states):
            self.action_table[state_id] = {}
            
            for item in state:
                if item.dot_pos < len(item.rhs):
                    # SHIFT
                    next_symbol = item.rhs[item.dot_pos]
                    if next_symbol in self.grammar.terminals:
                        if (state_id, next_symbol) in self.goto_table:
                            next_state = self.goto_table[(state_id, next_symbol)]
                            self.action_table[state_id][next_symbol] = ('shift', next_state)
                else:
                    # REDUCE o ACCEPT
                    if item.lhs == self.grammar.start_symbol + "'" and item.lookahead == '$':
                        self.action_table[state_id]['$'] = ('accept', None)
                    else:
                        # Encontrar el número de la producción
                        prod_num = None
                        for i, (lhs, rhs) in enumerate(self.grammar.productions):
                            if lhs == item.lhs and rhs == item.rhs:
                                prod_num = i
                                break
                        
                        if prod_num is not None:
                            self.action_table[state_id][item.lookahead] = ('reduce', prod_num)
    
    def parse(self, input_string):
        """Analiza una cadena usando el parser LR(1)"""
        tokens = input_string.split() + ['$']
        stack = [0]  # Pila de estados
        steps = []
        
        i = 0
        while i < len(tokens):
            state = stack[-1]
            token = tokens[i]
            
            steps.append({
                "stack": str(stack),
                "input": ' '.join(tokens[i:]),
                "action": f"Estado {state}, símbolo {token}"
            })
            
            if state not in self.action_table or token not in self.action_table[state]:
                steps.append({
                    "stack": str(stack),
                    "input": ' '.join(tokens[i:]),
                    "action": f"Error: No hay acción definida para estado {state} y símbolo {token}"
                })
                return False, steps
            
            action, value = self.action_table[state][token]
            
            if action == 'shift':
                stack.append(value)
                i += 1
                steps.append({
                    "stack": str(stack),
                    "input": ' '.join(tokens[i:]),
                    "action": f"Shift {value}"
                })
            elif action == 'reduce':
                lhs, rhs = self.grammar.productions[value]
                # Pop 2 * |rhs| elementos (estado y símbolo)
                for _ in range(len(rhs)):
                    if stack:
                        stack.pop()
                
                # GOTO
                current_state = stack[-1] if stack else 0
                if (current_state, lhs) in self.goto_table:
                    stack.append(self.goto_table[(current_state, lhs)])
                
                steps.append({
                    "stack": str(stack),
                    "input": ' '.join(tokens[i:]),
                    "action": f"Reduce por {lhs} -> {' '.join(rhs)}"
                })
            elif action == 'accept':
                steps.append({
                    "stack": str(stack),
                    "input": '$',
                    "action": "Accept - Cadena aceptada"
                })
                return True, steps
        
        return False, steps

def parse_grammar(grammar_text):
    """Convierte la gramática de texto al objeto Grammar"""
    grammar = Grammar()
    
    for line in grammar_text.strip().split('\n'):
        line = line.strip()
        if not line or '->' not in line:
            continue
        
        lhs, rhs = line.split('->', 1)
        lhs = lhs.strip()
        rhs = rhs.strip()
        
        if rhs == 'ε' or rhs == '':
            rhs_symbols = ['ε']
        else:
            rhs_symbols = rhs.split()
        
        grammar.add_production(lhs, rhs_symbols)
    
    return grammar

# --- Endpoints de la API ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/test')
def test():
    import os
    path = os.path.join(BASE_DIR, 'frontend', 'index.html')
    exists = os.path.exists(path)
    return f"Archivo index.html existe: {exists} en {path}"

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('frontend', filename)

@app.route('/parse', methods=['POST'])
def handle_parse_request():
    data = request.json
    grammar_text = data.get('grammar')
    input_string = data.get('input_string')

    if not grammar_text:
        return jsonify({"error": "La gramática no puede estar vacía."}), 400

    try:
        # Parsear la gramática
        grammar = parse_grammar(grammar_text)
        
        # Crear el parser LR(1)
        parser = LR1Parser(grammar)
        
        # Analizar la cadena
        if input_string:
            accepted, parse_steps = parser.parse(input_string)
        else:
            accepted = True
            parse_steps = [{
                "stack": "N/A",
                "input": "Cadena vacía",
                "action": "No hay cadena para analizar"
            }]
        
        # Formatear los datos para el frontend
        states_data = []
        for i, state in enumerate(parser.states):
            state_info = {
                "id": i,
                "items": [str(item) for item in state]
            }
            states_data.append(state_info)
        
        # Convertir goto_table para JSON (tuplas a strings)
        goto_table_json = {}
        for (state_id, symbol), target_state in parser.goto_table.items():
            key = f"{state_id},{symbol}"
            goto_table_json[key] = target_state
        
        return jsonify({
            "accepted": accepted,
            "first_sets": {k: list(v) for k, v in parser.first_sets.items()},
            "canonical_collection": states_data,
            "parsing_table_action": parser.action_table,
            "parsing_table_goto": goto_table_json,
            "parsing_steps": parse_steps
        })

    except Exception as e:
        import traceback
        print("Error details:", traceback.format_exc())  # Para debug
        return jsonify({"error": f"Error al procesar la gramática: {str(e)}"}), 500
    
# --- Iniciar el servidor ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)