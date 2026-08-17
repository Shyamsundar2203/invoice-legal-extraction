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
const sampleInvoiceBtn = document.getElementById("sample-invoice-btn");
const sampleContractBtn = document.getElementById("sample-contract-btn");
const exportCsvBtn = document.getElementById("export-csv-btn");
const copyJsonBtn = document.getElementById("copy-json-btn");

let currentResult = null;

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

// 1-Click Sample Loaders
if (sampleInvoiceBtn) {
  sampleInvoiceBtn.addEventListener("click", async () => {
    try {
      setStatus("Loading sample invoice…");
      const res = await fetch("/sample_invoice.png");
      const blob = await res.blob();
      const file = new File([blob], "sample_invoice.png", { type: "image/png" });
      const dt = new DataTransfer();
      dt.items.add(file);
      fileInput.files = dt.files;
      updateDropzoneLabel();
      document.querySelector('input[name="doc_type"][value="invoice"]').checked = true;
      setStatus("Sample invoice selected! Click 'Extract Data'.");
    } catch (err) {
      setStatus("Error loading sample: " + err.message, true);
    }
  });
}

if (sampleContractBtn) {
  sampleContractBtn.addEventListener("click", async () => {
    try {
      setStatus("Loading sample contract…");
      const res = await fetch("/sample_contract.png");
      const blob = await res.blob();
      const file = new File([blob], "sample_contract.png", { type: "image/png" });
      const dt = new DataTransfer();
      dt.items.add(file);
      fileInput.files = dt.files;
      updateDropzoneLabel();
      document.querySelector('input[name="doc_type"][value="contract"]').checked = true;
      setStatus("Sample contract selected! Click 'Extract Data'.");
    } catch (err) {
      setStatus("Error loading sample: " + err.message, true);
    }
  });
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
    currentResult = result;
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
  const cls = conf >= 0.7 ? "conf-high" : "conf-low";
  return `<span class="conf-pill ${cls}">${(conf * 100).toFixed(0)}%</span>`;
}

function renderResult(result) {
  resultsEl.hidden = false;
  resultsEl.scrollIntoView({ behavior: "smooth" });

  document.getElementById("doc-meta-info").textContent = `${result.filename} · ${result.doc_type.toUpperCase()} · ${result.processing_time_ms.toFixed(0)} ms`;

  const badge = document.getElementById("confidence-badge");
  badge.textContent = result.needs_review
    ? `Needs review · ${(result.overall_confidence * 100).toFixed(0)}%`
    : `Looks good · ${(result.overall_confidence * 100).toFixed(0)}%`;
  badge.className = "badge " + (result.needs_review ? "review" : "ok");

  const data = result.data;
  const currSym = data.currency_symbol || "$";

  // Math Check Banner (Invoice)
  const mathBanner = document.getElementById("math-banner");
  if (result.doc_type === "invoice" && data.math_validation) {
    const mv = data.math_validation;
    mathBanner.hidden = false;
    mathBanner.className = `math-banner ${mv.is_valid ? "" : "warn"}`;
    mathBanner.textContent = mv.message;
  } else if (result.doc_type === "contract" && data.overall_risk_score) {
    mathBanner.hidden = false;
    mathBanner.className = `math-banner ${data.overall_risk_score === "HIGH" ? "warn" : ""}`;
    mathBanner.textContent = `Agreement Liability Rating: ${data.overall_risk_score} RISK (${data.risk_flags ? data.risk_flags.length : 0} risk flag(s) identified)`;
  } else {
    mathBanner.hidden = true;
  }

  // Structured Fields Table
  const fieldsBody = document.querySelector("#fields-table tbody");
  fieldsBody.innerHTML = "";

  const fieldLabels = {
    invoice_number: "Invoice Number",
    invoice_date: "Invoice Date",
    due_date: "Due Date",
    vendor_name: "Vendor",
    vendor_tax_id: "Tax ID",
    buyer_name: "Buyer",
    subtotal: "Subtotal",
    tax_amount: "Tax Amount",
    grand_total: "Grand Total",
    contract_title: "Agreement Title",
    party_a: "Party A",
    party_b: "Party B",
    effective_date: "Effective Date",
    governing_law: "Governing Law",
    term_duration: "Term Duration",
  };

  for (const [key, label] of Object.entries(fieldLabels)) {
    if (!(key in data)) continue;
    const field = data[key];
    const val = (typeof field === "object" ? field.value : field) || "—";
    const conf = field && field.confidence ? field.confidence : 0;
    const row = document.createElement("tr");
    row.innerHTML = `
      <td class="field-name">${label}</td>
      <td class="field-value">${val} ${field && field.value ? confPill(conf) : ""}</td>
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
      row.innerHTML = `<td>${item.description ?? ""}</td><td>${item.quantity ?? ""}</td><td>${currSym}${item.unit_price ?? ""}</td><td>${currSym}${item.total ?? ""}</td>`;
      itemsBody.appendChild(row);
    }
  } else {
    itemsTitle.hidden = true;
    itemsTable.hidden = true;
  }

  // Clauses & Risk Flags (contract)
  const clausesTitle = document.getElementById("clauses-title");
  const clausesList = document.getElementById("clauses-list");
  clausesList.innerHTML = "";

  if (result.doc_type === "contract") {
    clausesTitle.hidden = false;

    // Risk flags
    if (data.risk_flags && data.risk_flags.length) {
      data.risk_flags.forEach((f) => {
        const div = document.createElement("div");
        div.className = "clause-item";
        div.style.borderColor = "var(--warn)";
        div.style.background = "var(--warn-soft)";
        div.innerHTML = `<span class="clause-type" style="color:var(--warn)">⚠️ RISK [${f.risk_level}]: ${f.clause_type}</span>${f.reason}<br><small style="color:#5c6470">Recommendation: ${f.recommendation}</small>`;
        clausesList.appendChild(div);
      });
    }

    // Clauses
    if (data.clauses && data.clauses.length) {
      for (const clause of data.clauses) {
        const div = document.createElement("div");
        div.className = "clause-item";
        div.innerHTML = `<span class="clause-type">${clause.clause_type.replace("_", " ")}</span>${clause.text}`;
        clausesList.appendChild(div);
      }
    }
  } else {
    clausesTitle.hidden = true;
  }

  document.getElementById("raw-json").textContent = JSON.stringify(result, null, 2);

  const overlayLink = document.getElementById("overlay-link");
  overlayLink.href = `${API_BASE}/extract/${result.document_id}/overlay`;
  overlayLink.hidden = false;
}

// Copy JSON
if (copyJsonBtn) {
  copyJsonBtn.addEventListener("click", () => {
    const jsonText = document.getElementById("raw-json").textContent;
    if (jsonText) {
      navigator.clipboard.writeText(jsonText).then(() => {
        showToast("JSON copied to clipboard!");
      });
    }
  });
}

// Export CSV
if (exportCsvBtn) {
  exportCsvBtn.addEventListener("click", () => {
    if (!currentResult) {
      showToast("Extract a document first.");
      return;
    }

    const data = currentResult.data;
    let rows = [];

    if (currentResult.doc_type === "invoice") {
      rows.push(["Field", "Value"]);
      rows.push(["Invoice Number", data.invoice_number ? data.invoice_number.value : ""]);
      rows.push(["Invoice Date", data.invoice_date ? data.invoice_date.value : ""]);
      rows.push(["Due Date", data.due_date ? data.due_date.value : ""]);
      rows.push(["Vendor", data.vendor_name ? data.vendor_name.value : ""]);
      rows.push(["Buyer", data.buyer_name ? data.buyer_name.value : ""]);
      rows.push(["Subtotal", data.subtotal ? data.subtotal.value : ""]);
      rows.push(["Tax Amount", data.tax_amount ? data.tax_amount.value : ""]);
      rows.push(["Grand Total", data.grand_total ? data.grand_total.value : ""]);
      rows.push([]);
      rows.push(["Item Description", "Quantity", "Unit Price", "Total"]);
      if (data.line_items) {
        data.line_items.forEach((item) => {
          rows.push([
            `"${(item.description || "").replace(/"/g, '""')}"`,
            item.quantity || "",
            item.unit_price || "",
            item.total || "",
          ]);
        });
      }
    } else {
      rows.push(["Field", "Value"]);
      rows.push(["Party A", data.party_a ? data.party_a.value : ""]);
      rows.push(["Party B", data.party_b ? data.party_b.value : ""]);
      rows.push(["Effective Date", data.effective_date ? data.effective_date.value : ""]);
      rows.push(["Governing Law", data.governing_law ? data.governing_law.value : ""]);
      rows.push(["Term Duration", data.term_duration ? data.term_duration.value : ""]);
      rows.push([]);
      rows.push(["Clause Type", "Text"]);
      if (data.clauses) {
        data.clauses.forEach((c) => {
          rows.push([c.clause_type, `"${(c.text || "").replace(/"/g, '""')}"`]);
        });
      }
    }

    const csvContent = "data:text/csv;charset=utf-8," + rows.map((r) => r.join(",")).join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `${currentResult.filename.split(".")[0]}_extracted.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast("CSV downloaded!");
  });
}

function showToast(msg) {
  const toast = document.getElementById("toast");
  toast.textContent = msg;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2000);
}
