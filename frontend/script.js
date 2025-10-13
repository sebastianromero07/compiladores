document.getElementById('parseBtn').addEventListener('click', async () => {
  const grammar = document.getElementById('grammar').value.trim();
  const inputString = document.getElementById('inputString').value.trim();
  const parseBtn = document.getElementById('parseBtn');
  const btnText = parseBtn.querySelector('.btn-text');

  if (!grammar) {
    showError('Por favor, ingrese una gramática.');
    return;
  }

  // Mostrar estado de carga
  parseBtn.disabled = true;
  btnText.innerHTML = '<div class="loading"><div class="spinner"></div>Analizando...</div>';

  try {
    const response = await fetch('/parse', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        grammar: grammar,
        input_string: inputString
      })
    });

    const data = await response.json();

    if (response.ok) {
      displayResults(data);
    } else {
      showError(data.error || 'Error desconocido en el servidor.');
    }
  } catch (error) {
    showError(`Error de conexión: ${error.message}`);
  } finally {
    // Restaurar botón
    parseBtn.disabled = false;
    btnText.innerHTML = 'Analizar Gramática';
  }
});

function showError(message) {
  const acceptanceEl = document.getElementById('acceptance');
  acceptanceEl.className = 'status error';
  acceptanceEl.innerHTML = `❌ Error: ${message}`;
  
  // Limpiar otros resultados
  document.getElementById('parsingSteps').innerHTML = '';
  document.getElementById('actionHeader').innerHTML = '';
  document.getElementById('actionBody').innerHTML = '';
  
  document.getElementById('result').style.display = 'block';
}

function displayResults(data) {
  // Mostrar resultado de aceptación
  const acceptanceEl = document.getElementById('acceptance');
  if (data.accepted) {
    acceptanceEl.className = 'status success';
    acceptanceEl.innerHTML = '✅ Cadena aceptada por la gramática';
  } else {
    acceptanceEl.className = 'status error';
    acceptanceEl.innerHTML = '❌ Cadena rechazada por la gramática';
  }

  // Mostrar pasos del parsing
  displayParsingSteps(data.parsing_steps);

  // Mostrar tabla ACTION
  displayActionTable(data.parsing_table_action);

  // Mostrar estados (colección canónica)
  displayStates(data.canonical_collection);

  // Mostrar conjuntos FIRST
  displayFirstSets(data.first_sets);
  //mostrar tabla first
  displayFirstTable(data.first_table);
  renderLR1Graph(data.lr1_dot);

  // Mostrar resultados
  document.getElementById('result').style.display = 'block';
}
function renderLR1Graph(dot) {
  const container = document.getElementById('lr1Graph');
  container.innerHTML = '';
  if (!dot) {
    container.innerHTML = '<p class="no-data">No hay grafo LR(1) para mostrar.</p>';
    return;
  }
  try {
    const viz = new Viz();
    viz.renderSVGElement(dot)
      .then(svg => {
        svg.style.maxWidth = '100%';
        container.appendChild(svg);
      })
      .catch(err => {
        container.innerHTML = `<pre class="error">${String(err)}</pre>`;
      });
  } catch (e) {
    container.innerHTML = `<pre class="error">${String(e)}</pre>`;
  }
}

function displayParsingSteps(steps) {
  const stepsList = document.getElementById('parsingSteps');
  stepsList.innerHTML = '';
  
  if (!steps || steps.length === 0) {
    stepsList.innerHTML = '<p class="no-data">No hay pasos de parsing para mostrar.</p>';
    return;
  }

  const table = document.createElement('table');
  table.className = 'steps-table';
  
  // Header
  const headerRow = document.createElement('tr');
  headerRow.innerHTML = `
    <th>Paso</th>
    <th>Pila</th>
    <th>Entrada</th>
    <th>Acción</th>
  `;
  table.appendChild(headerRow);
  
  // Pasos
  steps.forEach((step, index) => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${index + 1}</td>
      <td><code>${step.stack}</code></td>
      <td><code>${step.input}</code></td>
      <td>${step.action}</td>
    `;
    table.appendChild(row);
  });
  
  stepsList.appendChild(table);
}


function displayActionTable(actionTable) {
  const actionHeader = document.getElementById('actionHeader'); // <tr>
  const actionBody = document.getElementById('actionBody');     // <tbody>
  
  actionHeader.innerHTML = '';
  actionBody.innerHTML = '';
  
  if (!actionTable || Object.keys(actionTable).length === 0) {
    actionBody.innerHTML = '<tr><td colspan="100%">No hay tabla ACTION para mostrar.</td></tr>';
    return;
  }

  // 1) Obtener símbolos y ordenarlos: "$" primero, luego alfabético
  const symbolsSet = new Set();
  Object.values(actionTable).forEach(row => {
    Object.keys(row).forEach(sym => symbolsSet.add(sym));
  });
  const symbols = Array.from(symbolsSet).sort((a, b) => {
    if (a === '$') return -1;
    if (b === '$') return 1;
    return a.localeCompare(b);
  });

  // 2) HEADER: usar directamente el <tr id="actionHeader">
  const thState = document.createElement('th');
  thState.textContent = 'Estado';
  actionHeader.appendChild(thState);

  symbols.forEach(symbol => {
    const th = document.createElement('th');
    th.textContent = symbol;
    actionHeader.appendChild(th);
  });

  // 3) BODY: filas en el mismo orden de símbolos
  Object.keys(actionTable).sort((a, b) => parseInt(a) - parseInt(b)).forEach(state => {
    const row = document.createElement('tr');

    const stateCell = document.createElement('td');
    stateCell.textContent = state;
    stateCell.className = 'state-cell';
    row.appendChild(stateCell);

    symbols.forEach(symbol => {
      const cell = document.createElement('td');
      const action = actionTable[state][symbol];

      if (action) {
        if (Array.isArray(action)) {
          cell.textContent = `${action[0]} ${action[1] ?? ''}`.trim();
        } else {
          cell.textContent = action;
        }

        if (cell.textContent.includes('shift')) {
          cell.className = 'shift-action';
        } else if (cell.textContent.includes('reduce')) {
          cell.className = 'reduce-action';
        } else if (cell.textContent.includes('accept')) {
          cell.className = 'accept-action';
        }
      }

      row.appendChild(cell);
    });

    actionBody.appendChild(row);
  });
}

// ...existing code...

function displayStates(states) {
  const statesContainer = document.getElementById('states');
  statesContainer.innerHTML = '';
  
  if (!states || states.length === 0) {
    statesContainer.innerHTML = '<p class="no-data">No hay estados para mostrar.</p>';
    return;
  }

  states.forEach(state => {
    const stateDiv = document.createElement('div');
    stateDiv.className = 'state-item';
    
    const stateHeader = document.createElement('h4');
    stateHeader.textContent = `Estado ${state.id}`;
    stateDiv.appendChild(stateHeader);
    
    const itemsList = document.createElement('ul');
    itemsList.className = 'items-list';
    
    state.items.forEach(item => {
      const listItem = document.createElement('li');
      listItem.innerHTML = `<code>${item}</code>`;
      itemsList.appendChild(listItem);
    });
    
    stateDiv.appendChild(itemsList);
    statesContainer.appendChild(stateDiv);
  });
}

function displayFirstSets(firstSets) {
  const firstSetsContainer = document.getElementById('firstSets');
  firstSetsContainer.innerHTML = '';
  
  if (!firstSets || Object.keys(firstSets).length === 0) {
    firstSetsContainer.innerHTML = '<p class="no-data">No hay conjuntos FIRST para mostrar.</p>';
    return;
  }

  const table = document.createElement('table');
  table.className = 'first-sets-table';
  
  // Header
  const headerRow = document.createElement('tr');
  headerRow.innerHTML = `
    <th>Símbolo</th>
    <th>FIRST</th>
  `;
  table.appendChild(headerRow);
  
  // Body
  Object.entries(firstSets).forEach(([symbol, firstSet]) => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td><code>${symbol}</code></td>
      <td><code>{${firstSet.join(', ')}}</code></td>
    `;
    table.appendChild(row);
  });
  
  firstSetsContainer.appendChild(table);
}

function displayFirstTable(firstTable) {
  const container = document.getElementById('firstTable');
  if (!container) return;
  container.innerHTML = '';

  if (!firstTable || firstTable.length === 0) {
    container.innerHTML = '<p class="no-data">No hay tabla FIRST para mostrar.</p>';
    return;
  }

  const table = document.createElement('table');
  table.className = 'first-sets-table';

  const headerRow = document.createElement('tr');
  headerRow.innerHTML = `
    <th>Nonterminal</th>
    <th>FIRST</th>
  `;
  table.appendChild(headerRow);

  firstTable.forEach(row => {
    const tr = document.createElement('tr');
    const firstList = Array.isArray(row.first) ? row.first.join(', ') : '';
    tr.innerHTML = `
      <td><code>${row.nonterminal}</code></td>
      <td><code>{ ${firstList} }</code></td>
    `;
    table.appendChild(tr);
  });

  container.appendChild(table);
}

// Mejorar la experiencia del usuario con atajos de teclado
document.addEventListener('keydown', (e) => {
  if (e.ctrlKey && e.key === 'Enter') {
    document.getElementById('parseBtn').click();
  }
});

// Auto-resize de textareas
document.querySelectorAll('textarea').forEach(textarea => {
  textarea.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = this.scrollHeight + 'px';
  });
});