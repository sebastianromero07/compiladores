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
  // 1. Mostrar gramática aumentada
  displayAugmentedGrammar(data.augmented_grammar);
  expandSection('augmentedGrammar');

  // 2. Mostrar conjuntos FIRST
  displayFirstSets(data.first_sets);
  expandSection('firstSets');

  // 3. Mostrar autómata AFD LR(1)
  renderLR1Graph(data.lr1_dot);
  expandSection('lr1Graph');

  // 4. Mostrar tabla ACTION
  displayActionTable(data.parsing_table_action);
  
  // 5. Mostrar análisis de gramática
  if (data.grammar_analysis) {
    displayGrammarAnalysis(data.grammar_analysis);
  }
  
  expandSection('actionTableContent');

  // Mostrar resultados
  document.getElementById('result').style.display = 'block';
}

function displayGrammarAnalysis(analysis) {
  const container = document.getElementById('grammarAnalysis');
  container.innerHTML = '';

  // Crear el contenedor principal
  const analysisDiv = document.createElement('div');
  analysisDiv.className = 'grammar-analysis';

  // Título del tipo de gramática
  const grammarTypeDiv = document.createElement('div');
  grammarTypeDiv.className = `grammar-type ${analysis.is_lr1 ? 'lr1' : 'non-lr1'}`;
  
  const icon = analysis.is_lr1 ? '✅' : '❌';
  grammarTypeDiv.innerHTML = `${icon} ${analysis.grammar_type}`;
  analysisDiv.appendChild(grammarTypeDiv);

  // Si hay conflictos, mostrarlos
  if (!analysis.is_lr1 && analysis.conflicts && analysis.conflicts.length > 0) {
    const conflictsSection = document.createElement('div');
    conflictsSection.className = 'conflicts-section';

    const conflictsTitle = document.createElement('h4');
    conflictsTitle.className = 'conflicts-title';
    conflictsTitle.textContent = `Conflictos encontrados (${analysis.conflicts.length}):`;
    conflictsSection.appendChild(conflictsTitle);

    analysis.conflicts.forEach(conflict => {
      const conflictItem = document.createElement('div');
      conflictItem.className = 'conflict-item';

      const conflictHeader = document.createElement('div');
      conflictHeader.className = 'conflict-header';

      const conflictType = document.createElement('span');
      conflictType.className = `conflict-type ${conflict.type.replace('/', '-')}`;
      conflictType.textContent = conflict.type;

      const conflictLocation = document.createElement('span');
      conflictLocation.className = 'conflict-location';
      conflictLocation.textContent = `Estado ${conflict.state}, símbolo "${conflict.symbol}"`;

      conflictHeader.appendChild(conflictType);
      conflictHeader.appendChild(conflictLocation);

      const conflictDescription = document.createElement('div');
      conflictDescription.className = 'conflict-description';
      conflictDescription.textContent = conflict.description;

      conflictItem.appendChild(conflictHeader);
      conflictItem.appendChild(conflictDescription);

      conflictsSection.appendChild(conflictItem);
    });

    analysisDiv.appendChild(conflictsSection);
  } else if (analysis.is_lr1) {
    const noConflicts = document.createElement('div');
    noConflicts.className = 'no-conflicts';
    noConflicts.innerHTML = '🎉 La gramática es LR(1) - Sin conflictos';
    analysisDiv.appendChild(noConflicts);
  }

  container.appendChild(analysisDiv);
}

function displayAugmentedGrammar(augmentedGrammar) {
  const container = document.getElementById('augmentedGrammar');
  container.innerHTML = '';

  if (!augmentedGrammar || augmentedGrammar.length === 0) {
    container.innerHTML = '<p class="no-data">No hay gramática aumentada para mostrar.</p>';
    return;
  }

  // Crear contenedor de columnas
  const columnsContainer = document.createElement('div');
  columnsContainer.className = 'augmented-grammar-container';

  // Agrupar por símbolo no terminal
  const grouped = {};
  augmentedGrammar.forEach(production => {
    if (!grouped[production.lhs]) {
      grouped[production.lhs] = [];
    }
    grouped[production.lhs].push(production);
  });

  // Crear la visualización en columnas
  Object.entries(grouped).forEach(([lhs, productions]) => {
    const nonTerminalDiv = document.createElement('div');
    nonTerminalDiv.className = 'grammar-group';

    const header = document.createElement('h4');
    header.className = 'grammar-header';
    header.textContent = `${lhs}`;
    nonTerminalDiv.appendChild(header);

    const productionsList = document.createElement('div');
    productionsList.className = 'productions-list';

    productions.forEach(production => {
      const prodDiv = document.createElement('div');
      prodDiv.className = 'production-item';
      prodDiv.innerHTML = `<code>${production.rhs}</code>`;
      productionsList.appendChild(prodDiv);
    });

    nonTerminalDiv.appendChild(productionsList);
    columnsContainer.appendChild(nonTerminalDiv);
  });

  container.appendChild(columnsContainer);
}

async function downloadAsImage(elementId, filename) {
  const element = document.getElementById(elementId);
  if (!element) {
    alert('No hay contenido para descargar');
    return;
  }

  try {
    const canvas = await html2canvas(element, {
      backgroundColor: '#ffffff',
      scale: 2, // Mayor calidad
      logging: false,
      useCORS: true
    });
    
    const link = document.createElement('a');
    link.download = filename;
    link.href = canvas.toDataURL('image/png');
    link.click();
  } catch (error) {
    console.error('Error al generar imagen:', error);
    alert('Error al generar la imagen. Intenta con el formato DOT.');
  }
}

function renderLR1Graph(dot) {
  const container = document.getElementById('lr1Graph');
  container.innerHTML = '';
  
  if (!dot) {
    container.innerHTML = '<p class="no-data">No hay grafo LR(1) para mostrar.</p>';
    return;
  }

  // Crear controles para el grafo
  const controls = document.createElement('div');
  controls.className = 'graph-controls';
  controls.innerHTML = `
    <button id="downloadPng" class="control-btn">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
        <circle cx="8.5" cy="8.5" r="1.5"></circle>
        <polyline points="21 15 16 10 5 21"></polyline>
      </svg>
      Descargar PNG
    </button>
    <button id="downloadDot" class="control-btn">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
        <polyline points="7 10 12 15 17 10"></polyline>
        <line x1="12" y1="15" x2="12" y2="3"></line>
      </svg>
      Descargar DOT
    </button>
    <button id="viewText" class="control-btn">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
        <polyline points="14,2 14,8 20,8"></polyline>
      </svg>
      Ver como Texto
    </button>
  `;
  container.appendChild(controls);

  const graphContainer = document.createElement('div');
  graphContainer.className = 'graph-display';
  graphContainer.id = 'graphDisplay';
  container.appendChild(graphContainer);

  // Intentar renderizar con viz.js
  try {
    const viz = new Viz();
    viz.renderSVGElement(dot)
      .then(svg => {
        svg.style.maxWidth = '100%';
        svg.style.height = 'auto';
        svg.id = 'afdSvg';
        graphContainer.appendChild(svg);
        
        // Agregar controles de zoom
        addZoomControls(graphContainer, svg);
      })
      .catch(err => {
        console.error('Error viz.js:', err);
        showTextualRepresentation(graphContainer, dot);
      });
  } catch (e) {
    console.error('Error al inicializar viz.js:', e);
    showTextualRepresentation(graphContainer, dot);
  }

  // Event listeners para controles
  document.getElementById('downloadPng').addEventListener('click', () => {
    downloadAsImage('graphDisplay', 'afd_lr1.png');
  });

  document.getElementById('downloadDot').addEventListener('click', () => {
    downloadFile('afd_lr1.dot', dot);
  });

  document.getElementById('viewText').addEventListener('click', () => {
    showTextualRepresentation(graphContainer, dot);
  });
}
function addZoomControls(container, svg) {
  const controls = document.createElement('div');
  controls.className = 'zoom-controls';
  controls.innerHTML = `
    <button class="zoom-btn" data-action="zoom-in">+</button>
    <button class="zoom-btn" data-action="zoom-out">-</button>
    <button class="zoom-btn" data-action="reset">⟲</button>
  `;
  container.prepend(controls);

  let scale = 1;
  const svgElement = svg;

  controls.addEventListener('click', (e) => {
    const action = e.target.dataset.action;
    if (!action) return;

    if (action === 'zoom-in') {
      scale = Math.min(scale + 0.2, 3);
    } else if (action === 'zoom-out') {
      scale = Math.max(scale - 0.2, 0.5);
    } else if (action === 'reset') {
      scale = 1;
    }

    svgElement.style.transform = `scale(${scale})`;
    svgElement.style.transformOrigin = 'top left';
  });

  // Hacer el SVG arrastrable
  makeDraggable(svgElement);
}

function makeDraggable(element) {
  let isDragging = false;
  let startX, startY, scrollLeft, scrollTop;
  const container = element.parentElement;

  element.style.cursor = 'grab';

  element.addEventListener('mousedown', (e) => {
    isDragging = true;
    element.style.cursor = 'grabbing';
    startX = e.pageX - container.offsetLeft;
    startY = e.pageY - container.offsetTop;
    scrollLeft = container.scrollLeft;
    scrollTop = container.scrollTop;
  });

  document.addEventListener('mouseup', () => {
    isDragging = false;
    element.style.cursor = 'grab';
  });

  document.addEventListener('mousemove', (e) => {
    if (!isDragging) return;
    e.preventDefault();
    const x = e.pageX - container.offsetLeft;
    const y = e.pageY - container.offsetTop;
    const walkX = (x - startX) * 2;
    const walkY = (y - startY) * 2;
    container.scrollLeft = scrollLeft - walkX;
    container.scrollTop = scrollTop - walkY;
  });
}

function showTextualRepresentation(container, dot) {
  container.innerHTML = `
    <div class="textual-graph">
      <h4>Representación Textual del AFD LR(1)</h4>
      <p class="info-message">
        El grafo es demasiado grande para renderizar visualmente. 
        Aquí está la representación en formato DOT:
      </p>
      <pre class="dot-code">${escapeHtml(dot)}</pre>
      <p class="info-message">
        Puedes copiar este código y visualizarlo en 
        <a href="https://dreampuf.github.io/GraphvizOnline/" target="_blank">GraphvizOnline</a>
        o <a href="https://edotor.net/" target="_blank">Edotor</a>
      </p>
    </div>
  `;
}

function downloadFile(filename, content) {
  const blob = new Blob([content], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function escapeHtml(text) {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  };
  return text.replace(/[&<>"']/g, m => map[m]);
}

function displayParsingSteps(steps) {
  const stepsList = document.getElementById('parsingSteps');
  stepsList.innerHTML = '';

  if (!steps || steps.length === 0) {
    stepsList.innerHTML = '<p class="no-data">No hay pasos de parsing para mostrar.</p>';
    return;
  }

  // Crear tabla con diseño moderno que replica exactamente la imagen
  const tableContainer = document.createElement('div');
  tableContainer.className = 'trace-table-container';

  const table = document.createElement('table');
  table.className = 'trace-table';

  // Header con el título "Trace" centrado
  const titleRow = document.createElement('tr');
  titleRow.innerHTML = `<th colspan="4" class="trace-title">Trace</th>`;
  table.appendChild(titleRow);

  // Sub-header con las columnas
  const headerRow = document.createElement('tr');
  headerRow.innerHTML = `
    <th class="step-col">Step</th>
    <th class="stack-col">Stack</th>
    <th class="input-col">Input</th>
    <th class="action-col">Action</th>
  `;
  table.appendChild(headerRow);

  // Filas de datos
  steps.forEach((step, index) => {
    const row = document.createElement('tr');
    const stepNumber = step.step || (index + 1);

    // Formatear la pila - mostrar estados con espacios
    let stackDisplay = step.stack;
    if (typeof stackDisplay === 'string') {
      // Reemplazar comas por espacios para mejor legibilidad
      stackDisplay = stackDisplay.replace(/,/g, ' ');
    }

    // Formatear la entrada
    let inputDisplay = step.input;
    if (inputDisplay && inputDisplay !== '$') {
      inputDisplay = inputDisplay.replace(/\s+/g, ' ').trim();
    }

    // Formatear la acción exactamente como en la imagen
    let actionDisplay = step.action;
    if (actionDisplay.includes('Shift')) {
      actionDisplay = actionDisplay.replace('Shift ', 's');
    } else if (actionDisplay.startsWith('S')) {
      actionDisplay = actionDisplay.toLowerCase(); // s3, s4, etc.
    } else if (actionDisplay.startsWith('R')) {
      actionDisplay = actionDisplay.toLowerCase(); // r1, r2, r3, etc.
    } else if (actionDisplay === 'ACC' || actionDisplay.includes('Accept')) {
      actionDisplay = 'acc';
    } else if (actionDisplay.includes('ERROR')) {
      actionDisplay = 'error';
    }

    row.innerHTML = `
      <td class="step-cell">${stepNumber}</td>
      <td class="stack-cell">${stackDisplay}</td>
      <td class="input-cell">${inputDisplay}</td>
      <td class="action-cell ${getActionClass(actionDisplay)}">${actionDisplay}</td>
    `;
    table.appendChild(row);
  });

  tableContainer.appendChild(table);
  stepsList.appendChild(tableContainer);
}

// Función auxiliar para obtener la clase CSS según el tipo de acción
function getActionClass(action) {
  if (action.startsWith('s')) return 'shift-action';
  if (action.startsWith('r')) return 'reduce-action';
  if (action === 'acc') return 'accept-action';
  if (action === 'error') return 'error-action';
  return '';
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
          const [actionType, value] = action;

          if (actionType === 'conflict') {
            // Conflicto: mostrar todas las acciones separadas por /
            const conflictActions = value.map(([type, val]) => {
              if (type === 'shift') return `s${val}`;
              if (type === 'reduce') return `r${val + 1}`;
              if (type === 'accept') return 'acc';
              return type;
            }).join('/');

            cell.textContent = conflictActions;
            cell.className = 'conflict-action';
          } else if (actionType === 'shift') {
            cell.textContent = `s${value}`;
            cell.className = 'shift-action';
          } else if (actionType === 'reduce') {
            cell.textContent = `r${value + 1}`;
            cell.className = 'reduce-action';
          } else if (actionType === 'accept') {
            cell.textContent = 'acc';
            cell.className = 'accept-action';
          } else {
            cell.textContent = actionType;
          }
        } else {
          cell.textContent = action;

          // Clasificar por contenido del string
          if (cell.textContent.includes('shift') || cell.textContent.startsWith('s')) {
            cell.className = 'shift-action';
          } else if (cell.textContent.includes('reduce') || cell.textContent.startsWith('r')) {
            cell.className = 'reduce-action';
          } else if (cell.textContent === 'acc' || cell.textContent.includes('accept')) {
            cell.className = 'accept-action';
          }
        }
      } else {
        cell.textContent = '';
      }      row.appendChild(cell);
    });

    actionBody.appendChild(row);
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

// Event listener para el botón de análisis de cadena
document.getElementById('analyzeBtn').addEventListener('click', async () => {
  const grammar = document.getElementById('grammar').value.trim();
  const inputString = document.getElementById('inputString').value.trim();
  const analyzeBtn = document.getElementById('analyzeBtn');
  const btnText = analyzeBtn.querySelector('.btn-text');

  if (!grammar) {
    showError('Por favor, primero ingrese y analice una gramática.');
    return;
  }

  if (!inputString) {
    showError('Por favor, ingrese una cadena para analizar.');
    return;
  }

  // Mostrar estado de carga
  analyzeBtn.disabled = true;
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
      // Mostrar solo el resultado del análisis
      const acceptanceEl = document.getElementById('acceptance');
      const stepsTitle = document.getElementById('stepsTitle');

      if (data.accepted) {
        acceptanceEl.className = 'status success';
        acceptanceEl.innerHTML = '✅ Cadena aceptada por la gramática';
      } else {
        acceptanceEl.className = 'status error';
        acceptanceEl.innerHTML = '❌ Cadena rechazada por la gramática';
      }

      acceptanceEl.style.display = 'block';
      stepsTitle.style.display = 'block';      // Mostrar pasos del parsing
      displayParsingSteps(data.parsing_steps);

      // Mostrar árbol de derivación si existe
      if (data.parse_tree && data.accepted) {
        displayParseTree(data.parse_tree);
        expandSection('parseTree');
      }
    } else {
      showError(data.error || 'Error desconocido en el servidor.');
    }
  } catch (error) {
    showError(`Error de conexión: ${error.message}`);
  } finally {
    // Restaurar botón
    analyzeBtn.disabled = false;
    btnText.innerHTML = 'Analizar Cadena';
  }
});

function displayParseTree(tree) {
  const treeContainer = document.getElementById('parseTree');
  treeContainer.innerHTML = '';

  if (!tree) {
    treeContainer.innerHTML = '<p class="no-data">No se generó árbol de derivación.</p>';
    return;
  }

  // Agregar controles de descarga
  const controls = document.createElement('div');
  controls.className = 'graph-controls';
  controls.innerHTML = `
    <button id="downloadTreePng" class="control-btn">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
        <circle cx="8.5" cy="8.5" r="1.5"></circle>
        <polyline points="21 15 16 10 5 21"></polyline>
      </svg>
      Descargar PNG
    </button>
  `;
  treeContainer.appendChild(controls);

  const treeWrapper = document.createElement('div');
  treeWrapper.className = 'tree-wrapper';
  treeWrapper.id = 'treeDisplay';
  
  function buildNode(node) {
    const nodeContainer = document.createElement('div');
    nodeContainer.className = 'tree-node-container';

    const nodeCircle = document.createElement('div');
    nodeCircle.className = 'tree-node-circle';
    nodeCircle.textContent = node.symbol;
    nodeContainer.appendChild(nodeCircle);

    if (node.children && node.children.length > 0) {
      const childrenContainer = document.createElement('div');
      childrenContainer.className = 'tree-children-container';

      node.children.forEach((child, index) => {
        const childBranch = document.createElement('div');
        childBranch.className = 'tree-branch';

        const verticalLine = document.createElement('div');
        verticalLine.className = 'tree-line-vertical';
        childBranch.appendChild(verticalLine);

        const childNode = buildNode(child);
        childBranch.appendChild(childNode);

        childrenContainer.appendChild(childBranch);
      });

      if (node.children.length > 1) {
        const horizontalLine = document.createElement('div');
        horizontalLine.className = 'tree-line-horizontal';
        nodeContainer.appendChild(horizontalLine);
      }

      nodeContainer.appendChild(childrenContainer);
    }

    return nodeContainer;
  }

  const treeRoot = buildNode(tree);
  treeWrapper.appendChild(treeRoot);
  treeContainer.appendChild(treeWrapper);

  // Event listener para descargar árbol como imagen
  document.getElementById('downloadTreePng').addEventListener('click', () => {
    downloadAsImage('treeDisplay', 'arbol_derivacion.png');
  });
}
function initializeAccordion() {
  const accordionHeaders = document.querySelectorAll('.accordion-header');
  console.log(`Inicializando accordion: encontrados ${accordionHeaders.length} headers`);

  accordionHeaders.forEach((header, index) => {
    const sectionId = header.getAttribute('data-section');
    console.log(`Header ${index}: data-section="${sectionId}"`);
    
    header.addEventListener('click', () => {
      console.log(`Click en accordion header: ${sectionId}`);
      const content = document.getElementById(sectionId);
      const icon = header.querySelector('.accordion-icon');
      const container = header.parentElement;

      if (content && icon && container) {
        toggleAccordionSection(header, content, icon, container);
      } else {
        console.log(`Elementos faltantes para ${sectionId}:`, {
          content: !!content,
          icon: !!icon, 
          container: !!container
        });
      }
    });
  });
}

function toggleAccordionSection(header, content, icon, container) {
  const isCollapsed = content.classList.contains('collapsed');
  console.log(`Toggle accordion: ${content.id}, actualmente ${isCollapsed ? 'colapsado' : 'expandido'}`);

  if (isCollapsed) {
    // Expandir
    content.classList.remove('collapsed');
    content.classList.add('expanding');
    header.classList.remove('collapsed');
    container.classList.remove('collapsed');

    // Remover clase de animación después de que termine
    setTimeout(() => {
      content.classList.remove('expanding');
    }, 400);
  } else {
    // Colapsar
    content.classList.add('collapsing');

    setTimeout(() => {
      content.classList.add('collapsed');
      content.classList.remove('collapsing');
      header.classList.add('collapsed');
      container.classList.add('collapsed');
    }, 400);
  }
}

// Función para expandir una sección específica (útil cuando se cargan resultados)
function expandSection(sectionId) {
  const header = document.querySelector(`[data-section="${sectionId}"]`);
  const content = document.getElementById(sectionId);
  const icon = header?.querySelector('.accordion-icon');
  const container = header?.parentElement;

  if (header && content && content.classList.contains('collapsed')) {
    toggleAccordionSection(header, content, icon, container);
  }
}

// Función para colapsar todas las secciones
function collapseAllSections() {
  const accordionHeaders = document.querySelectorAll('.accordion-header');

  accordionHeaders.forEach(header => {
    const sectionId = header.getAttribute('data-section');
    const content = document.getElementById(sectionId);
    const icon = header.querySelector('.accordion-icon');
    const container = header.parentElement;

    if (content && !content.classList.contains('collapsed')) {
      toggleAccordionSection(header, content, icon, container);
    }
  });
}

// Función para expandir todas las secciones
function expandAllSections() {
  const accordionHeaders = document.querySelectorAll('.accordion-header');

  accordionHeaders.forEach(header => {
    const sectionId = header.getAttribute('data-section');
    const content = document.getElementById(sectionId);
    const icon = header.querySelector('.accordion-icon');
    const container = header.parentElement;

    if (content && content.classList.contains('collapsed')) {
      toggleAccordionSection(header, content, icon, container);
    }
  });
}

// Event listeners para botones de control
document.addEventListener('DOMContentLoaded', () => {
  // Inicializar accordion
  initializeAccordion();
  
  // Botón expandir todo
  const expandAllBtn = document.getElementById('expandAllBtn');
  if (expandAllBtn) {
    expandAllBtn.addEventListener('click', expandAllSections);
  }

  // Botón colapsar todo
  const collapseAllBtn = document.getElementById('collapseAllBtn');
  if (collapseAllBtn) {
    collapseAllBtn.addEventListener('click', collapseAllSections);
  }
});

// Función para hacer las columnas de la tabla redimensionables
function makeTableColumnsResizable(tableId) {
  const table = document.getElementById(tableId);
  if (!table) return;

  const headers = table.querySelectorAll('th');
  headers.forEach((header, index) => {
    // Crear el handle de redimensionamiento
    const resizer = document.createElement('div');
    resizer.className = 'column-resizer';
    resizer.style.cssText = `
      position: absolute;
      right: 0;
      top: 0;
      bottom: 0;
      width: 4px;
      background: transparent;
      cursor: col-resize;
      z-index: 10;
    `;

    header.style.position = 'relative';
    header.appendChild(resizer);

    let isResizing = false;
    let startX = 0;
    let startWidth = 0;

    resizer.addEventListener('mousedown', (e) => {
      isResizing = true;
      startX = e.pageX;
      startWidth = header.offsetWidth;
      
      document.addEventListener('mousemove', handleResize);
      document.addEventListener('mouseup', stopResize);
      
      e.preventDefault();
    });

    function handleResize(e) {
      if (!isResizing) return;
      
      const newWidth = startWidth + (e.pageX - startX);
      const minWidth = 60;
      const maxWidth = 300;
      
      if (newWidth >= minWidth && newWidth <= maxWidth) {
        header.style.width = newWidth + 'px';
        
        // También ajustar las celdas de la misma columna
        const rows = table.querySelectorAll('tbody tr');
        rows.forEach(row => {
          const cell = row.cells[index];
          if (cell) {
            cell.style.width = newWidth + 'px';
          }
        });
      }
    }

    function stopResize() {
      isResizing = false;
      document.removeEventListener('mousemove', handleResize);
      document.removeEventListener('mouseup', stopResize);
    }

    // Efecto visual al hover
    resizer.addEventListener('mouseenter', () => {
      resizer.style.background = 'var(--primary-color)';
      resizer.style.opacity = '0.5';
    });

    resizer.addEventListener('mouseleave', () => {
      if (!isResizing) {
        resizer.style.background = 'transparent';
      }
    });
  });
}

// Función mejorada para mostrar la tabla ACTION con columnas redimensionables
function displayActionTableWithResize(actionTable) {
  displayActionTable(actionTable);
  
  // Hacer las columnas redimensionables después de crear la tabla
  setTimeout(() => {
    makeTableColumnsResizable('actionTable');
  }, 100);
}
