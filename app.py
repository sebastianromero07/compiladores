import os
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS 
import re
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
        self.productions = []           # lista de (lhs, rhs_list)
        self.start_symbol = None
        self.terminals = set()
        self.non_terminals = set()
        self._rhs_symbols = set()       # todos los símbolos que aparecen en RHS

    def add_production(self, lhs, rhs):
        if self.start_symbol is None:
            self.start_symbol = lhs
        self.non_terminals.add(lhs)
        self.productions.append((lhs, rhs))
        # solo registramos lo que aparece en RHS; NO clasificamos aún
        for s in rhs:
            self._rhs_symbols.add(s)

    def finalize_symbols(self):
        # terminales = símbolos en RHS que no son no-terminales y no son ε
        self.terminals = set(sym for sym in self._rhs_symbols
                             if sym not in self.non_terminals and sym != 'ε')


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
    def compute_first_table(self):
        """Tabla FIRST por no terminal (no por producción)."""
        self.first_table = []
        # ordenar los no terminales para que el orden sea estable
        for nt in sorted(self.grammar.non_terminals):
            first_of_nt = sorted(self.first_sets.get(nt, []))
            self.first_table.append({
                "nonterminal": nt,
                "first": first_of_nt
            })

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
        """Calcula la clausura LR(1) sin autoexpandir el símbolo aumentado."""
        closure_set = set(items)
        base_start = self.grammar.start_symbol.rstrip("'")
        augmented_start = base_start + "'"

        changed = True
        while changed:
            changed = False
            new_items = set()

            for item in closure_set:
                if item.dot_pos < len(item.rhs):
                    next_symbol = item.rhs[item.dot_pos]

                    if next_symbol in self.grammar.non_terminals:
                        # Evita expandir el símbolo aumentado sobre sí mismo
                        if next_symbol == augmented_start and item.lhs == augmented_start:
                            continue

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
        """Construye los estados y tablas del parser LR(1)."""
        self.compute_first_sets()
        self.compute_first_table()

        # Determinar el símbolo aumentado
        if self.grammar.start_symbol.endswith("'"):
            augmented_start = self.grammar.start_symbol
            base_symbol = self.grammar.start_symbol.rstrip("'")
        else:
            base_symbol = self.grammar.start_symbol
            augmented_start = base_symbol + "'"

        # Agregar la producción aumentada solo si no existe ya
        if not any(lhs.strip() == augmented_start for lhs, _ in self.grammar.productions):
            self.grammar.productions.insert(0, (augmented_start, [base_symbol]))

        # Estado inicial
        initial_item = Item(augmented_start, [base_symbol], 0, '$')
        initial_state = self.closure({initial_item})

        self.states = [initial_state]
        unmarked = [0]

        # Construcción de estados
        while unmarked:
            state_id = unmarked.pop(0)
            current_state = self.states[state_id]

            symbols = {item.rhs[item.dot_pos] for item in current_state if item.dot_pos < len(item.rhs)}

            for symbol in symbols:
                goto_state = self.goto(current_state, symbol)
                if not goto_state:
                    continue

                existing_id = next((i for i, s in enumerate(self.states) if s == goto_state), None)
                if existing_id is None:
                    new_id = len(self.states)
                    self.states.append(goto_state)
                    unmarked.append(new_id)
                    self.goto_table[(state_id, symbol)] = new_id
                else:
                    self.goto_table[(state_id, symbol)] = existing_id

        # Finalmente construir ACTION
        self.build_action_table()

    
    def build_action_table(self):
        """Construye la tabla ACTION robusta (aceptación segura y sin duplicados)."""
        base_start = self.grammar.start_symbol.rstrip("'")
        augmented_start = base_start + "'"

        for state_id, state in enumerate(self.states):
            self.action_table[state_id] = {}

            for item in state:
                # --- 1️⃣ Acción SHIFT ---
                if item.dot_pos < len(item.rhs):
                    next_symbol = item.rhs[item.dot_pos]
                    if next_symbol in self.grammar.terminals:
                        if (state_id, next_symbol) in self.goto_table:
                            next_state = self.goto_table[(state_id, next_symbol)]
                            self.action_table[state_id][next_symbol] = ('shift', next_state)
                    continue

                # --- 2️⃣ Acción ACCEPT ---
                # Acepta solo si es el símbolo inicial aumentado completo
                if (
                    item.dot_pos == len(item.rhs)
                    and item.lookahead == '$'
                    and item.lhs in {augmented_start, self.grammar.start_symbol}
                ):
                    self.action_table[state_id]['$'] = ('accept', None)
                    continue


                # --- 3️⃣ Acción REDUCE ---
                # Buscar producción correspondiente
                for prod_index, (lhs, rhs) in enumerate(self.grammar.productions):
                    if lhs == item.lhs and rhs == item.rhs:
                        self.action_table[state_id][item.lookahead] = ('reduce', prod_index)
                        break
    
    

    def to_dot(self):
        def esc(s: str) -> str:
            return s.replace('"', r'\"')

        lines = []
        lines.append('digraph LR1 {')
        lines.append('  rankdir=LR;')
        lines.append('  node [shape=box, style="rounded,filled", fillcolor="#ffffff", fontname="Inter"];')
        lines.append('  edge [fontname="Inter"];')

        # Nodos: cada estado con sus ítems
        for i, state in enumerate(self.states):
            items_txt = "\\n".join(esc(str(item)) for item in state)
            label = f'I{i}\\n{items_txt}'
            lines.append(f'  I{i} [label="{label}"];')

        # Aristas: desde goto_table
        for (sid, symbol), tid in self.goto_table.items():
            lines.append(f'  I{sid} -> I{tid} [label="{esc(symbol)}"];')

        # Nodo accept opcional si quieres mostrarlo explícito:
        # Buscar estado con acción accept
        for sid, row in self.action_table.items():
            if row.get("$", (None,))[0] == "accept":
                lines.append('  Accept [shape=box, style="rounded,filled", fillcolor="#f5f5f5"];')
                lines.append(f'  I{sid} -> Accept [label="$"];')
                break

        lines.append('}')
        return "\n".join(lines)
    
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
    grammar = Grammar()
    for raw in grammar_text.strip().split('\n'):
        line = raw.strip()
        if not line:
                continue

            # Soporta "->" y "→"
        parts = re.split(r'\s*(?:->|→)\s*', line)
        if len(parts) != 2:
            continue

        lhs, rhs = parts[0].strip(), parts[1].strip()
        rhs = rhs.replace('\xa0', ' ')  # normaliza espacios no estándar

            # RESPETA LOS ESPACIOS: "(A)" ≠ "( A )"
        if rhs in ('ε', ''):
            rhs_symbols = ['ε']
        else:
            rhs_symbols = rhs.split()  # split exacto por espacio

        grammar.add_production(lhs, rhs_symbols)

    grammar.finalize_symbols()  # <-- fuera del bucle
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
            "first_table": parser.first_table,
            "canonical_collection": states_data,
            "parsing_table_action": parser.action_table,
            "parsing_table_goto": goto_table_json,
            "parsing_steps": parse_steps,
            "lr1_dot": parser.to_dot()   # <-- aquí
        })



    except Exception as e:
        import traceback
        print("Error details:", traceback.format_exc())  # Para debug
        return jsonify({"error": f"Error al procesar la gramática: {str(e)}"}), 500
    
# --- Iniciar el servidor ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)