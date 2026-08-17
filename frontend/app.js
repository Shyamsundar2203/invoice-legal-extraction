// DocuExtract AI · Frontend Client Controller
const API_BASE = window.location.origin && window.location.origin.startsWith("http")
  ? window.location.origin
  : "http://localhost:8000";

document.getElementById("api-base-display").textContent = API_BASE;

const form = document.getElementById("upload-form");
const fileInput = document.getElementById("file-input");
const dropzone = document.getElementById("dropzone");
const filePreviewPill = document.getElementById("file-preview-pill");
const selectedFilename = document.getElementById("selected-filename");
const clearFileBtn = document.getElementById("clear-file-btn");
const submitBtn = document.getElementById("submit-btn");
const btnSpinner = document.getElementById("btn-spinner");
const statusBar = document.getElementById("status-bar");
const statusMessage = document.getElementById("status-message");
const resultsSection = document.getElementById("results");
const sampleInvoiceBtn = document.getElementById("sample-invoice-btn");
const sampleContractBtn = document.getElementById("sample-contract-btn");
const exportCsvBtn = document.getElementById("export-csv-btn");

let currentSelectedFile = null;
let currentResultData = null;

// Document Type Toggle
document.querySelectorAll('input[name="doc_type"]').forEach((radio) => {
  radio.addEventListener("change", (e) => {
    document.querySelectorAll(".toggle-option").forEach((opt) => opt.classList.remove("active"));
    e.target.closest(".toggle-option").classList.add("active");
  });
});

// Dropzone Drag & Drop
dropzone.addEventListener("click", (e) => {
  if (e.target !== clearFileBtn && !clearFileBtn.contains(e.target)) {
    fileInput.click();
  }
});

dropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropzone.classList.add("dragover");
});

dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));

dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("dragover");
  if (e.dataTransfer.files.length) {
    handleFileSelect(e.dataTransfer.files[0]);
  }
});

fileInput.addEventListener("change", () => {
  if (fileInput.files.length) {
    handleFileSelect(fileInput.files[0]);
  }
});

clearFileBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  currentSelectedFile = null;
  fileInput.value = "";
  filePreviewPill.hidden = true;
  dropzone.querySelector(".dropzone-content").hidden = false;
});

function handleFileSelect(file) {
  currentSelectedFile = file;
  selectedFilename.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
  filePreviewPill.hidden = false;
  dropzone.querySelector(".dropzone-content").hidden = true;
}

// 1-Click Sample Invoice Loader
if (sampleInvoiceBtn) {
  sampleInvoiceBtn.addEventListener("click", async () => {
    try {
      setStatus("Loading sample invoice fixture…");
      const res = await fetch("/sample_invoice.png");
      if (!res.ok) throw new Error("Could not fetch sample_invoice.png");
      const blob = await res.blob();
      const file = new File([blob], "sample_invoice.png", { type: "image/png" });
      handleFileSelect(file);

      // Select Invoice radio
      document.querySelector('input[name="doc_type"][value="invoice"]').checked = true;
      document.getElementById("label-invoice").classList.add("active");
      document.getElementById("label-contract").classList.remove("active");
      setStatus("Sample invoice loaded! Click 'Extract Document Entities' below.");
    } catch (err) {
      setStatus("Error loading sample: " + err.message, true);
    }
  });
}

// 1-Click Sample Contract Loader
if (sampleContractBtn) {
  sampleContractBtn.addEventListener("click", async () => {
    try {
      setStatus("Loading sample contract fixture…");
      const res = await fetch("/sample_contract.png");
      if (!res.ok) throw new Error("Could not fetch sample_contract.png");
      const blob = await res.blob();
      const file = new File([blob], "sample_contract.png", { type: "image/png" });
      handleFileSelect(file);

      // Select Contract radio
      document.querySelector('input[name="doc_type"][value="contract"]').checked = true;
      document.getElementById("label-contract").classList.add("active");
      document.getElementById("label-invoice").classList.remove("active");
      setStatus("Sample contract loaded! Click 'Extract Document Entities' below.");
    } catch (err) {
      setStatus("Error loading sample: " + err.message, true);
    }
  });
}

// Form Submission
form.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!currentSelectedFile) {
    setStatus("Please choose or drag a document first, or click a sample button.", true);
    return;
  }

  const docType = form.querySelector('input[name="doc_type"]:checked').value;
  const fd = new FormData();
  fd.append("file", currentSelectedFile);

  submitBtn.disabled = true;
  btnSpinner.hidden = false;
  setStatus("Extracting layout, OCR tokens, and entity schema…");
  resultsSection.hidden = true;

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
    currentResultData = result;
    renderResult(result);
    setStatus(`Extraction complete in ${result.processing_time_ms.toFixed(0)} ms.`);
  } catch (err) {
    setStatus(`Error: ${err.message}`, true);
  } finally {
    submitBtn.disabled = false;
    btnSpinner.hidden = true;
  }
});

function setStatus(msg, isError = false) {
  statusBar.hidden = false;
  statusBar.className = `status-bar ${isError ? "error" : ""}`;
  statusMessage.textContent = msg;
}

// Tab Switching
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));
    btn.classList.add("active");
    const target = document.getElementById(btn.dataset.tab);
    if (target) target.classList.add("active");
  });
});

// Render Results
function renderResult(result) {
  resultsSection.hidden = false;
  resultsSection.scrollIntoView({ behavior: "smooth" });

  document.getElementById("result-doc-name").textContent = result.filename;
  document.getElementById("meta-doc-type").textContent = result.doc_type.toUpperCase();
  document.getElementById("meta-time").textContent = `⚡ ${result.processing_time_ms.toFixed(0)} ms`;

  const data = result.data;
  const currSym = data.currency_symbol || "$";
  const currCode = data.currency_code || "USD";
  document.getElementById("meta-currency").textContent = `Currency: ${currCode} (${currSym})`;

  // Confidence Badge
  const badge = document.getElementById("confidence-badge");
  const confPct = (result.overall_confidence * 100).toFixed(0);
  if (result.needs_review) {
    badge.textContent = `⚠️ Review Required · ${confPct}% Conf`;
    badge.className = "badge review";
  } else {
    badge.textContent = `✓ High Confidence · ${confPct}% Conf`;
    badge.className = "badge ok";
  }

  // Overlay Link
  const overlayBtn = document.getElementById("overlay-pdf-btn");
  overlayBtn.href = `${API_BASE}/extract/${result.document_id}/overlay`;

  // Render Analytics Banner (Math Check or Risk Analysis)
  const analyticsBanner = document.getElementById("analytics-banner");
  analyticsBanner.innerHTML = "";

  if (result.doc_type === "invoice" && data.math_validation) {
    const mv = data.math_validation;
    const isOk = mv.is_valid;
    const banner = document.createElement("div");
    banner.className = `banner-card ${isOk ? "math-ok" : "math-warn"}`;
    banner.innerHTML = `
      <div class="banner-left">
        <span class="banner-icon">${isOk ? "⚖️" : "⚠️"}</span>
        <div>
          <span class="banner-title">${isOk ? "Ledger Math Balanced & Verified" : "Reconciliation Discrepancy Detected"}</span>
          <span class="banner-desc">${mv.message}</span>
        </div>
      </div>
      <div class="banner-metrics">
        <span class="metric-pill">Subtotal: ${currSym}${mv.subtotal ? mv.subtotal.toFixed(2) : "0.00"}</span>
        <span class="metric-pill">Tax: ${currSym}${mv.tax_amount ? mv.tax_amount.toFixed(2) : "0.00"}</span>
        <span class="metric-pill">Total: ${currSym}${mv.extracted_grand_total ? mv.extracted_grand_total.toFixed(2) : "0.00"}</span>
      </div>
    `;
    analyticsBanner.appendChild(banner);
  } else if (result.doc_type === "contract") {
    const riskScore = data.overall_risk_score || "LOW";
    const banner = document.createElement("div");
    const scoreClass = riskScore === "HIGH" ? "math-warn" : "math-ok";
    banner.className = `banner-card ${scoreClass}`;
    banner.innerHTML = `
      <div class="banner-left">
        <span class="banner-icon">🛡️</span>
        <div>
          <span class="banner-title">Contract Risk Assessment: ${riskScore} RISK</span>
          <span class="banner-desc">${data.risk_flags && data.risk_flags.length ? `${data.risk_flags.length} potential legal risk flag(s) identified.` : "No high-liability or non-standard terms detected."}</span>
        </div>
      </div>
    `;
    analyticsBanner.appendChild(banner);
  }

  // Render Structured Entity Cards
  const container = document.getElementById("fields-container");
  container.innerHTML = "";

  const fieldLabels = {
    invoice_number: "Invoice Number",
    invoice_date: "Invoice Date",
    due_date: "Due Date",
    vendor_name: "Vendor / Supplier",
    vendor_tax_id: "Tax ID / GSTIN",
    buyer_name: "Customer / Buyer",
    subtotal: `Subtotal (${currSym})`,
    tax_amount: `Tax Amount (${currSym})`,
    grand_total: `Grand Total (${currSym})`,
    contract_title: "Agreement Title",
    party_a: "Contracting Party A",
    party_b: "Contracting Party B",
    effective_date: "Effective Agreement Date",
    governing_law: "Governing Law / Jurisdiction",
    term_duration: "Contract Term Duration",
  };

  for (const [key, label] of Object.entries(fieldLabels)) {
    if (!(key in data)) continue;
    const field = data[key];
    const val = (typeof field === "object" ? field.value : field) || "—";
    const conf = field && field.confidence ? (field.confidence * 100).toFixed(0) : 0;
    const isHigh = field && field.confidence >= 0.65;

    const card = document.createElement("div");
    card.className = "entity-card";
    card.innerHTML = `
      <div class="entity-header">
        <span class="entity-label">${label}</span>
        ${field && field.value ? `<span class="conf-tag ${isHigh ? 'conf-high' : 'conf-low'}">${conf}%</span>` : ''}
      </div>
      <div class="entity-value">${val}</div>
    `;
    container.appendChild(card);
  }

  // Line items (Invoices)
  const itemsSection = document.getElementById("line-items-section");
  const itemsTable = document.getElementById("items-table");
  const itemsBody = itemsTable.querySelector("tbody");
  itemsBody.innerHTML = "";

  if (data.line_items && data.line_items.length) {
    itemsSection.hidden = false;
    data.line_items.forEach((item) => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td><strong>${item.description || "Item"}</strong></td>
        <td>${item.quantity || "1"}</td>
        <td>${currSym}${item.unit_price || "—"}</td>
        <td><strong>${currSym}${item.total || "—"}</strong></td>
        <td><span class="conf-tag conf-high">${(item.confidence * 100).toFixed(0)}%</span></td>
      `;
      itemsBody.appendChild(row);
    });
  } else {
    itemsSection.hidden = true;
  }

  // Contract Clauses & Risk Flags
  const clausesSection = document.getElementById("clauses-section");
  const clausesList = document.getElementById("clauses-list");
  const riskSummaryBox = document.getElementById("contract-risk-summary");
  clausesList.innerHTML = "";

  if (result.doc_type === "contract") {
    clausesSection.hidden = false;

    // Risk Summary Box
    const score = data.overall_risk_score || "LOW";
    const scoreTag = score === "HIGH" ? "risk-level-high" : (score === "MEDIUM" ? "risk-level-medium" : "risk-level-low");
    riskSummaryBox.innerHTML = `
      <span>Overall Agreement Liability Rating</span>
      <span class="risk-level-tag ${scoreTag}">${score} RISK</span>
    `;

    // Render Risk Flags
    if (data.risk_flags && data.risk_flags.length) {
      data.risk_flags.forEach((f) => {
        const flagCard = document.createElement("div");
        flagCard.className = "risk-flag-card";
        flagCard.innerHTML = `
          <div class="risk-flag-header">
            <span class="risk-clause-title">⚠️ ${f.clause_type.replace(/_/g, " ").toUpperCase()}</span>
            <span class="risk-level-tag ${f.risk_level === 'HIGH' ? 'risk-level-high' : 'risk-level-medium'}">${f.risk_level}</span>
          </div>
          <p class="risk-reason">${f.reason}</p>
          <div class="risk-rec"><strong>Recommendation:</strong> ${f.recommendation}</div>
        `;
        clausesList.appendChild(flagCard);
      });
    }

    // Render Clauses
    if (data.clauses && data.clauses.length) {
      data.clauses.forEach((c) => {
        const card = document.createElement("div");
        card.className = "clause-card";
        card.innerHTML = `
          <span class="clause-type-badge">${c.clause_type.replace(/_/g, " ")}</span>
          <p class="clause-body">${c.text}</p>
        `;
        clausesList.appendChild(card);
      });
    }
  } else {
    clausesSection.hidden = true;
  }

  // Raw JSON
  document.getElementById("raw-json").textContent = JSON.stringify(result, null, 2);

  // Raw OCR Text
  document.getElementById("raw-ocr-text").textContent = result.raw_ocr_text || "No raw text available.";
}

// Copy JSON
document.getElementById("copy-json-btn").addEventListener("click", () => {
  const jsonText = document.getElementById("raw-json").textContent;
  if (jsonText) {
    navigator.clipboard.writeText(jsonText).then(() => {
      showToast("JSON successfully copied to clipboard!");
    });
  }
});

// Export to CSV
if (exportCsvBtn) {
  exportCsvBtn.addEventListener("click", () => {
    if (!currentResultData) {
      showToast("Please extract a document first.");
      return;
    }

    const data = currentResultData.data;
    let csvRows = [];

    if (currentResultData.doc_type === "invoice") {
      csvRows.push(["Field", "Value"]);
      csvRows.push(["Invoice Number", data.invoice_number ? data.invoice_number.value : ""]);
      csvRows.push(["Invoice Date", data.invoice_date ? data.invoice_date.value : ""]);
      csvRows.push(["Due Date", data.due_date ? data.due_date.value : ""]);
      csvRows.push(["Vendor", data.vendor_name ? data.vendor_name.value : ""]);
      csvRows.push(["Buyer", data.buyer_name ? data.buyer_name.value : ""]);
      csvRows.push(["Subtotal", data.subtotal ? data.subtotal.value : ""]);
      csvRows.push(["Tax Amount", data.tax_amount ? data.tax_amount.value : ""]);
      csvRows.push(["Grand Total", data.grand_total ? data.grand_total.value : ""]);
      csvRows.push([]);
      csvRows.push(["Line Item Description", "Quantity", "Unit Price", "Total"]);

      if (data.line_items) {
        data.line_items.forEach((item) => {
          csvRows.push([
            `"${(item.description || "").replace(/"/g, '""')}"`,
            item.quantity || "",
            item.unit_price || "",
            item.total || "",
          ]);
        });
      }
    } else {
      csvRows.push(["Field", "Value"]);
      csvRows.push(["Party A", data.party_a ? data.party_a.value : ""]);
      csvRows.push(["Party B", data.party_b ? data.party_b.value : ""]);
      csvRows.push(["Effective Date", data.effective_date ? data.effective_date.value : ""]);
      csvRows.push(["Governing Law", data.governing_law ? data.governing_law.value : ""]);
      csvRows.push(["Term Duration", data.term_duration ? data.term_duration.value : ""]);
      csvRows.push(["Overall Risk Score", data.overall_risk_score || ""]);
      csvRows.push([]);
      csvRows.push(["Clause Type", "Clause Text"]);

      if (data.clauses) {
        data.clauses.forEach((c) => {
          csvRows.push([c.clause_type, `"${(c.text || "").replace(/"/g, '""')}"`]);
        });
      }
    }

    const csvContent = "data:text/csv;charset=utf-8," + csvRows.map((e) => e.join(",")).join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `${currentResultData.filename.split(".")[0]}_extracted.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast("CSV exported successfully!");
  });
}

function showToast(msg) {
  const toast = document.getElementById("toast");
  toast.textContent = msg;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2500);
}
