document.getElementById('parseBtn').addEventListener('click', async () => {
  const grammar = document.getElementById('grammar').value.trim();
  const inputString = document.getElementById('inputString').value.trim();

  if (!grammar) {
    alert('Por favor, ingresa una gramática.');
    return;
  }

  try {
    const response = await fetch('http://localhost:5000/parse', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ grammar, input_string: inputString })
    });

    const data = await response.json();

    if (data.error) {
      document.getElementById('acceptance').innerHTML = `<span class="error">Error: ${data.error}</span>`;
      document.getElementById('result').style.display = 'block';
      return;
    }

    // Mostrar resultado
    const acceptanceEl = document.getElementById('acceptance');
    if (data.accepted) {
      acceptanceEl.innerHTML = '<span class="success">✅ Aceptado</span>';
    } else {
      const lastStep = data.parsing_steps[data.parsing_steps.length - 1];
      acceptanceEl.innerHTML = `<span class="error">❌ Rechazado: ${lastStep ? lastStep.action : 'Error desconocido'}</span>`;
    }

    // Mostrar pasos
    const stepsList = document.getElementById('parsingSteps');
    stepsList.innerHTML = '';
    data.parsing_steps.forEach(step => {
      const li = document.createElement('li');
      li.textContent = `Pila: [${step.stack}] | Entrada: ${step.input} | Acción: ${step.action}`;
      stepsList.appendChild(li);
    });

    // Mostrar tabla ACTION
    const actionHeader = document.getElementById('actionHeader');
    const actionBody = document.getElementById('actionBody');
    actionHeader.innerHTML = '<th>Estado</th>';
    actionBody.innerHTML = '';

    if (data.parsing_table_action && Object.keys(data.parsing_table_action).length > 0) {
      const firstState = Object.keys(data.parsing_table_action)[0];
      const terminals = Object.keys(data.parsing_table_action[firstState]);

      terminals.forEach(term => {
        const th = document.createElement('th');
        th.textContent = term;
        actionHeader.appendChild(th);
      });

      for (const [state, actions] of Object.entries(data.parsing_table_action)) {
        const tr = document.createElement('tr');
        const td = document.createElement('td');
        td.textContent = state;
        tr.appendChild(td);
        terminals.forEach(term => {
          const cell = document.createElement('td');
          cell.textContent = actions[term] || '';
          tr.appendChild(cell);
        });
        actionBody.appendChild(tr);
      }
    }

    document.getElementById('result').style.display = 'block';

  } catch (error) {
    document.getElementById('acceptance').innerHTML = `<span class="error">Error de conexión: ${error.message}. Asegúrate de que el servidor Flask esté corriendo en http://localhost:5000.</span>`;
    document.getElementById('result').style.display = 'block';
  }
});
