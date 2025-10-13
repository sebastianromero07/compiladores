import os
import re
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS

# --- Configuración del Servidor Flask ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, 'frontend'),
    template_folder=os.path.join(BASE_DIR, 'frontend')
)
CORS(app)

# ===============================================================
# 🧩 CLASE Grammar
# ===============================================================
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

        # Detectar terminales y no terminales con regex
        for symbol in rhs:
            if re.match(r"^[A-Z]('?)*$", symbol):  # Ej: A, B, A'
                self.non_terminals.add(symbol)
            elif symbol != 'ε':
                self.terminals.add(symbol)

    def finalize_terminals(self):
        """Detecta los terminales automáticamente (los que no son no-terminales)."""
        all_rhs = {sym for _, rhs in self.productions for sym in rhs}
        self.terminals = all_rhs - self.non_terminals


# ===============================================================
# 🧩 CLASE Item
# ===============================================================
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


# ===============================================================
# 🧩 CLASE LR1Parser
# ===============================================================
class LR1Parser:
    def __init__(self, grammar):
        self.grammar = grammar
        self.first_sets = {}
        self.follow_sets = {}
        self.first_table = []
        self.states = []
        self.goto_table = {}
        self.action_table = {}
        self.build_parser()

    # --------------------- FIRST ---------------------
    def compute_first_sets(self):
        """Calcula los conjuntos FIRST para todos los símbolos."""
        for terminal in self.grammar.terminals:
            self.first_sets[terminal] = {terminal}
        for non_terminal in self.grammar.non_terminals:
            self.first_sets[non_terminal] = set()

        changed = True
        while changed:
            changed = False
            for lhs, rhs in self.grammar.productions:
                old_size = len(self.first_sets[lhs])
                if not rhs or rhs == ['ε']:
                    self.first_sets[lhs].add('ε')
                else:
                    for symbol in rhs:
                        self.first_sets[lhs].update(self.first_sets.get(symbol, {symbol}) - {'ε'})
                        if 'ε' not in self.first_sets.get(symbol, set()):
                            break
                    else:
                        self.first_sets[lhs].add('ε')
                if len(self.first_sets[lhs]) != old_size:
                    changed = True

    def compute_first_table(self):
        """Construye una tabla legible de los conjuntos FIRST."""
        self.first_table = []
        for nt in sorted(self.grammar.non_terminals):
            first_of_nt = sorted(self.first_sets.get(nt, []))
            self.first_table.append({"nonterminal": nt, "first": first_of_nt})

    def first_of_string(self, symbols):
        """Calcula FIRST(βa)."""
        if not symbols:
            return {'ε'}
        result = set()
        for symbol in symbols:
            fs = self.first_sets.get(symbol, {symbol})
            result.update(fs - {'ε'})
            if 'ε' not in fs:
                break
        else:
            result.add('ε')
        return result

    # --------------------- FOLLOW ---------------------
    def compute_follow_sets(self):
        """Calcula los conjuntos FOLLOW para todos los no terminales."""
        self.follow_sets = {nt: set() for nt in self.grammar.non_terminals}
        self.follow_sets[self.grammar.start_symbol].add('$')

        changed = True
        while changed:
            changed = False
            for lhs, rhs in self.grammar.productions:
                for i, A in enumerate(rhs):
                    if A in self.grammar.non_terminals:
                        beta = rhs[i + 1:]
                        first_beta = self.first_of_string(beta)
                        old_size = len(self.follow_sets[A])

                        # Regla 2: FIRST(β) - {ε} ⊆ FOLLOW(A)
                        self.follow_sets[A].update(first_beta - {'ε'})

                        # Regla 3: si ε ∈ FIRST(β) o β vacío ⇒ FOLLOW(lhs) ⊆ FOLLOW(A)
                        if not beta or 'ε' in first_beta:
                            self.follow_sets[A].update(self.follow_sets[lhs])

                        if len(self.follow_sets[A]) != old_size:
                            changed = True

    # --------------------- CLOSURE y GOTO ---------------------
    def closure(self, items):
        closure_set = set(items)
        changed = True
        while changed:
            changed = False
            new_items = set()
            for item in closure_set:
                if item.dot_pos < len(item.rhs):
                    next_symbol = item.rhs[item.dot_pos]
                    if next_symbol in self.grammar.non_terminals:
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
        moved = {
            Item(item.lhs, item.rhs, item.dot_pos + 1, item.lookahead)
            for item in items
            if item.dot_pos < len(item.rhs) and item.rhs[item.dot_pos] == symbol
        }
        return self.closure(moved)

    # --------------------- CONSTRUCCIÓN DEL PARSER ---------------------
    def build_parser(self):
        self.compute_first_sets()
        self.compute_first_table()
        self.compute_follow_sets()

        # Producción aumentada: S' → S
        if not any(lhs == self.grammar.start_symbol + "'" for lhs, _ in self.grammar.productions):
            self.grammar.productions.insert(0, (self.grammar.start_symbol + "'", [self.grammar.start_symbol]))

        # Estado inicial
        augmented = self.grammar.start_symbol + "'"
        start_item = Item(augmented, [self.grammar.start_symbol], 0, '$')
        initial_state = self.closure({start_item})

        self.states = [initial_state]
        unmarked = [0]

        while unmarked:
            i = unmarked.pop(0)
            state = self.states[i]

            symbols = {it.rhs[it.dot_pos] for it in state if it.dot_pos < len(it.rhs)}
            for sym in symbols:
                goto_state = self.goto(state, sym)
                if not goto_state:
                    continue
                existing = None
                for j, s in enumerate(self.states):
                    if s == goto_state:
                        existing = j
                        break
                if existing is None:
                    j = len(self.states)
                    self.states.append(goto_state)
                    unmarked.append(j)
                    self.goto_table[(i, sym)] = j
                else:
                    self.goto_table[(i, sym)] = existing
        self.build_action_table()

    # --------------------- TABLAS ACTION / GOTO ---------------------
    def build_action_table(self):
        for i, state in enumerate(self.states):
            self.action_table[i] = {}
            for item in state:
                if item.dot_pos < len(item.rhs):
                    a = item.rhs[item.dot_pos]
                    if a in self.grammar.terminals and (i, a) in self.goto_table:
                        self.action_table[i][a] = ('shift', self.goto_table[(i, a)])
                elif item.lhs == self.grammar.start_symbol + "'" and item.lookahead == '$':
                    self.action_table[i]['$'] = ('accept', None)
                else:
                    for idx, (lhs, rhs) in enumerate(self.grammar.productions):
                        if lhs == item.lhs and rhs == item.rhs:
                            self.action_table[i][item.lookahead] = ('reduce', idx)
                            break

    # --------------------- VISUALIZACIÓN ---------------------
    def to_dot(self):
        """Genera el autómata LR(1) en formato DOT."""
        def esc(s: str) -> str:
            return s.replace('"', r'\"').replace("\\", "\\\\")
        lines = [
            'digraph LR1 {',
            '  rankdir=LR;',
            '  node [shape=box, style="rounded,filled", fillcolor="#ffffff", fontname="Inter"];',
            '  edge [fontname="Inter"];'
        ]
        for i, state in enumerate(self.states):
            items_txt = "\\n".join(esc(str(item)) for item in sorted(state, key=lambda it: (it.lhs, it.rhs, it.dot_pos)))
            label = f"I{i}\\n{items_txt}"
            lines.append(f'  I{i} [label="{label}"];')
        for (sid, symbol), tid in sorted(self.goto_table.items(), key=lambda x: (x[0][0], x[0][1])):
            lines.append(f'  I{sid} -> I{tid} [label="{esc(symbol)}"];')
        for sid, row in self.action_table.items():
            if row.get("$", (None,))[0] == "accept":
                lines.append('  Accept [shape=box, style="rounded,filled", fillcolor="#f5f5f5", label="Accept"];')
                lines.append(f'  I{sid} -> Accept [label="$"];')
                break
        lines.append('}')
        return "\n".join(lines)

    # --------------------- PARSEO ---------------------
    def parse(self, input_string):
        tokens = input_string.split() + ['$']
        stack = [0]
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
                    "action": f"❌ Error: No hay acción definida para estado {state} y símbolo {token}"
                })
                return False, steps

            action, value = self.action_table[state][token]

            if action == 'shift':
                stack.append(value)
                i += 1
                steps.append({
                    "stack": str(stack),
                    "input": ' '.join(tokens[i:]),
                    "action": f"Shift → estado {value}"
                })
            elif action == 'reduce':
                lhs, rhs = self.grammar.productions[value]
                if rhs != ['ε']:
                    for _ in range(len(rhs)):
                        if stack:
                            stack.pop()
                current_state = stack[-1] if stack else 0
                next_state = self.goto_table.get((current_state, lhs))
                if next_state is not None:
                    stack.append(next_state)
                steps.append({
                    "stack": str(stack),
                    "input": ' '.join(tokens[i:]),
                    "action": f"Reduce por {lhs} → {' '.join(rhs)}"
                })
            elif action == 'accept':
                steps.append({
                    "stack": str(stack),
                    "input": '$',
                    "action": "✅ Accept - Cadena aceptada"
                })
                return True, steps

        return False, steps


# ===============================================================
# 🧩 FUNCIÓN DE PARSEO DE TEXTO
# ===============================================================
def parse_grammar(grammar_text):
    grammar = Grammar()
    token_pattern = r"[A-Za-z]+'?|[a-z]+|[()*/+=;,-]|ε|\$"

    for line in grammar_text.strip().split('\n'):
        if '->' not in line:
            continue
        lhs, rhs = map(str.strip, line.split('->'))
        rhs_symbols = re.findall(token_pattern, rhs)
        if not rhs_symbols:
            rhs_symbols = ['ε']
        grammar.add_production(lhs, rhs_symbols)

    grammar.finalize_terminals()
    return grammar


# ===============================================================
# 🌐 ENDPOINTS FLASK
# ===============================================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/parse', methods=['POST'])
def handle_parse_request():
    data = request.json
    grammar_text = data.get('grammar')
    input_string = data.get('input_string')

    if not grammar_text:
        return jsonify({"error": "La gramática no puede estar vacía."}), 400

    try:
        grammar = parse_grammar(grammar_text)
        parser = LR1Parser(grammar)

        if input_string:
            accepted, parse_steps = parser.parse(input_string)
        else:
            accepted = True
            parse_steps = [{"stack": "N/A", "input": "Cadena vacía", "action": "No hay cadena para analizar"}]

        states_data = [{"id": i, "items": [str(item) for item in state]} for i, state in enumerate(parser.states)]

        return jsonify({
            "accepted": accepted,
            "first_sets": {k: list(v) for k, v in parser.first_sets.items()},
            "first_table": parser.first_table,
            "follow_sets": {k: list(v) for k, v in parser.follow_sets.items()},
            "canonical_collection": states_data,
            "parsing_table_action": parser.action_table,
            "parsing_steps": parse_steps,
            "lr1_dot": parser.to_dot()
        })

    except Exception as e:
        import traceback
        print("Error details:", traceback.format_exc())
        return jsonify({"error": f"Error al procesar la gramática: {str(e)}"}), 500


# ===============================================================
# 🚀 INICIO DEL SERVIDOR
# ===============================================================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
