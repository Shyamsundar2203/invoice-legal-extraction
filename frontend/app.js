// Point this at your running backend (defaults to current origin).
const API_BASE = window.location.origin && window.location.origin.startsWith("http")
  ? window.location.origin
  : "http://localhost:8000";

document.getElementById("api-base-display").textContent = API_BASE;

const form = document.getElementById("upload-form");
const fileInput = document.getElementById("file-input");
const dropzone = document.getElementById("dropzone");
const dropzoneText = document.getElementById("dropzone-text");
const statusEl = document.getElementById("status");
const submitBtn = document.getElementById("submit-btn");
const resultsEl = document.getElementById("results");

dropzone.addEventListener("click", () => fileInput.click());
dropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropzone.classList.add("dragover");
});
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("dragover");
  if (e.dataTransfer.files.length) {
    fileInput.files = e.dataTransfer.files;
    updateDropzoneLabel();
  }
});
fileInput.addEventListener("change", updateDropzoneLabel);

function updateDropzoneLabel() {
  if (fileInput.files.length) {
    dropzoneText.textContent = `Selected: ${fileInput.files[0].name}`;
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!fileInput.files.length) {
    setStatus("Please choose a file first.", true);
    return;
  }

  const docType = form.querySelector('input[name="doc_type"]:checked').value;
  const fd = new FormData();
  fd.append("file", fileInput.files[0]);

  submitBtn.disabled = true;
  setStatus("Processing document — running OCR + extraction…");
  resultsEl.hidden = true;

  try {
    const res = await fetch(`${API_BASE}/extract?doc_type=${docType}`, {
      method: "POST",
      body: fd,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Request failed (${res.status})`);
    }
    const result = await res.json();
    renderResult(result);
    setStatus(`Done in ${result.processing_time_ms.toFixed(0)} ms.`);
  } catch (err) {
    setStatus(`Error: ${err.message}`, true);
  } finally {
    submitBtn.disabled = false;
  }
});

function setStatus(msg, isError = false) {
  statusEl.textContent = msg;
  statusEl.classList.toggle("error", isError);
}

function confPill(conf) {
  const cls = conf >= 0.85 ? "conf-high" : "conf-low";
  return `<span class="conf-pill ${cls}">${(conf * 100).toFixed(0)}%</span>`;
}

function renderResult(result) {
  resultsEl.hidden = false;

  const badge = document.getElementById("confidence-badge");
  badge.textContent = result.needs_review
    ? `Needs review · ${(result.overall_confidence * 100).toFixed(0)}%`
    : `Looks good · ${(result.overall_confidence * 100).toFixed(0)}%`;
  badge.className = "badge " + (result.needs_review ? "review" : "ok");

  const data = result.data;
  const fieldsBody = document.querySelector("#fields-table tbody");
  fieldsBody.innerHTML = "";

  const fieldLabels = {
    invoice_number: "Invoice Number",
    invoice_date: "Invoice Date",
    due_date: "Due Date",
    vendor_name: "Vendor",
    buyer_name: "Buyer",
    subtotal: "Subtotal",
    tax_amount: "Tax",
    grand_total: "Grand Total",
    party_a: "Party A",
    party_b: "Party B",
    effective_date: "Effective Date",
    governing_law: "Governing Law",
    term_duration: "Term Duration",
  };

  for (const [key, label] of Object.entries(fieldLabels)) {
    if (!(key in data)) continue;
    const field = data[key];
    const row = document.createElement("tr");
    row.innerHTML = `
      <td class="field-name">${label}</td>
      <td class="field-value">${field.value ?? "—"} ${field.value ? confPill(field.confidence) : ""}</td>
    `;
    fieldsBody.appendChild(row);
  }

  // Line items (invoice)
  const itemsTitle = document.getElementById("items-title");
  const itemsTable = document.getElementById("items-table");
  const itemsBody = itemsTable.querySelector("tbody");
  itemsBody.innerHTML = "";
  if (data.line_items && data.line_items.length) {
    itemsTitle.hidden = false;
    itemsTable.hidden = false;
    for (const item of data.line_items) {
      const row = document.createElement("tr");
      row.innerHTML = `<td>${item.description ?? ""}</td><td>${item.quantity ?? ""}</td><td>${item.unit_price ?? ""}</td><td>${item.total ?? ""}</td>`;
      itemsBody.appendChild(row);
    }
  } else {
    itemsTitle.hidden = true;
    itemsTable.hidden = true;
  }

  // Clauses (contract)
  const clausesTitle = document.getElementById("clauses-title");
  const clausesList = document.getElementById("clauses-list");
  clausesList.innerHTML = "";
  if (data.clauses && data.clauses.length) {
    clausesTitle.hidden = false;
    for (const clause of data.clauses) {
      const div = document.createElement("div");
      div.className = "clause-item";
      div.innerHTML = `<span class="clause-type">${clause.clause_type.replace("_", " ")}</span>${clause.text}`;
      clausesList.appendChild(div);
    }
  } else {
    clausesTitle.hidden = true;
  }

  document.getElementById("raw-json").textContent = JSON.stringify(result, null, 2);

  const overlayLink = document.getElementById("overlay-link");
  overlayLink.href = `${API_BASE}/extract/${result.document_id}/overlay`;
  overlayLink.hidden = false;
}
