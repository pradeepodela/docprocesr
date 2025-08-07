<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Invoice AI — Automated Invoice Processing</title>
  <!-- Tailwind CDN (Shadcn-like minimal design without build step) -->
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      darkMode: ['class'],
      theme: {
        extend: {
          colors: {
            border: 'hsl(240 3.7% 15.9%)',
            input: 'hsl(240 3.7% 15.9%)',
            ring: 'hsl(240 4.9% 83.9%)',
            background: 'hsl(240 10% 3.9%)',
            foreground: 'hsl(0 0% 98%)',
            primary: { DEFAULT: 'hsl(251 85% 66%)', foreground: 'hsl(0 0% 100%)' },
            muted: { DEFAULT: 'hsl(240 3.7% 15.9%)', foreground: 'hsl(240 5% 64.9%)' },
            card: { DEFAULT: 'hsl(240 10% 3.9%)', foreground: 'hsl(0 0% 98%)' },
            accent: { DEFAULT: 'hsl(240 3.7% 15.9%)', foreground: 'hsl(0 0% 98%)' },
          },
          borderRadius: {
            lg: '0.75rem',
            md: '0.5rem',
            sm: '0.375rem',
          },
          boxShadow: {
            card: '0 1px 0 0 rgba(255,255,255,0.04) inset, 0 1px 2px 0 rgba(0,0,0,0.4)',
          }
        }
      }
    }
  </script>
  <style>
    :root { color-scheme: dark; }
    .card { 
      background-color: rgb(10 10 12 / 1);
      color: hsl(0 0% 98%);
      border: 1px solid hsl(240 3.7% 15.9%);
      border-radius: 0.75rem;
      box-shadow: 0 1px 0 0 rgba(255,255,255,0.04) inset, 0 1px 2px 0 rgba(0,0,0,0.4);
    }
    .btn { 
      display: inline-flex; align-items: center; justify-content: center;
      white-space: nowrap; border-radius: 0.375rem; font-size: 0.875rem; font-weight: 500;
      transition: color, background, border, opacity .15s ease;
      outline: none; height: 2.25rem; padding: 0 .875rem;
    }
    .btn:focus-visible { box-shadow: 0 0 0 2px hsl(240 4.9% 83.9% / .6); }
    .btn-primary { background: hsl(251 85% 66%); color: white; }
    .btn-primary:hover { opacity: .95; }
    .btn-outline { border: 1px solid hsl(240 3.7% 15.9%); background: transparent; color: hsl(0 0% 98%); }
    .btn-outline:hover { background: hsl(240 3.7% 15.9% / .4); }
    .input { 
      display: flex; height: 2.25rem; width: 100%;
      border-radius: 0.5rem; border: 1px solid hsl(240 3.7% 15.9%); background: transparent;
      padding: 0 .75rem; font-size: .875rem; outline: none;
    }
    .input:focus { box-shadow: 0 0 0 2px hsl(240 4.9% 83.9% / .5); }
    .switch { position: relative; display: inline-flex; height: 24px; width: 44px; border-radius: 999px; border: 1px solid hsl(240 3.7% 15.9%); background: hsl(240 3.7% 15.9%); }
    .switch-thumb { position: absolute; top: 2px; left: 2px; height: 20px; width: 20px; border-radius: 999px; background: hsl(251 85% 66%); transition: transform .15s ease; }
    .switch[data-state="checked"] { background: hsl(251 85% 66% / 0.2); }
    .switch[data-state="checked"] .switch-thumb { transform: translateX(20px); }
    .kbd { border: 1px solid hsl(240 3.7% 15.9%); border-radius: 6px; padding: 2px 6px; font-size: 12px; color: hsl(240 5% 64.9%); }
    .muted { font-size: .875rem; color: hsl(240 5% 64.9%); }
    .upload-dashed { border: 1px dashed hsl(240 3.7% 15.9%); border-radius: 0.75rem; padding: 2.5rem; text-align: center; transition: border-color .15s ease, background .15s ease; cursor: pointer; }
    .upload-dashed:hover { border-color: hsl(251 85% 66% / .6); background: rgba(255,255,255,.02); }
    .progress-wrapper { width: 100%; background: rgba(255,255,255,.06); height: 8px; border-radius: 999px; overflow: hidden; }
    .progress-bar { height: 8px; background: hsl(251 85% 66%); width: 0%; transition: width .2s ease; }
  </style>
</head>
<body class="bg-background text-foreground">
  <div class="min-h-screen">
    <header class="sticky top-0 z-10 border-b border-border backdrop-blur supports-[backdrop-filter]:bg-background/70">
      <div class="mx-auto max-w-7xl px-4 py-3 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <div class="h-6 w-6 bg-primary rounded grid place-items-center text-white text-xs font-bold">IA</div>
          <span class="font-semibold">Invoice AI</span>
          <span class="kbd ml-3">Minimal UI</span>
        </div>
        <div class="flex items-center gap-2">
          <div class="muted hidden sm:block">Press Space to upload</div>
          <button id="clearBtn" class="btn btn-outline">Clear</button>
          <button id="themeToggle" aria-label="Toggle theme" class="switch" data-state="checked">
            <span class="switch-thumb"></span>
          </button>
        </div>
      </div>
    </header>

    <main class="mx-auto max-w-7xl p-4 grid grid-cols-1 lg:grid-cols-12 gap-4">
      <!-- Sidebar -->
      <aside class="lg:col-span-4 space-y-4">
        <div class="card p-4">
          <div class="flex items-center justify-between">
            <div>
              <div class="text-sm font-medium">Extraction Engine</div>
              <div class="muted">Choose LLM for data extraction</div>
            </div>
            <span class="text-xs px-2 py-1 rounded-full border border-border">Beta</span>
          </div>
          <div class="mt-3">
            <select id="llm_choice" class="input">
              <option value="Mistral">Mistral</option>
              <option value="OpenRouter">OpenRouter</option>
            </select>
          </div>
        </div>

        <div class="card p-4">
          <div class="text-sm font-medium mb-2">Output</div>
          <label class="flex items-center gap-2 mb-2">
            <input type="checkbox" id="include_detailed_csv" class="h-4 w-4" checked />
            <span class="muted">Detailed CSV (line-level)</span>
          </label>
          <label class="flex items-center gap-2">
            <input type="checkbox" id="include_summary_csv" class="h-4 w-4" checked />
            <span class="muted">Summary CSV (invoice-level)</span>
          </label>
          <div class="mt-4">
            <div class="text-sm font-medium">Confidence threshold</div>
            <div class="muted">Flag low-confidence fields</div>
            <input id="confidenceThreshold" type="range" min="0.5" max="0.99" step="0.01" value="0.85" class="w-full mt-2"/>
          </div>
        </div>

        <div class="card p-4">
          <details>
            <summary class="cursor-pointer text-sm font-medium">CSV Columns Overview</summary>
            <div class="muted mt-2 text-xs">
              file_number, invoice_number, invoice_date, vendor_name, customer_name, line_item_number,
              item_description, quantity, unit_price, line_total, subtotal, tax_amount, total_amount
            </div>
          </details>
        </div>

        <div class="muted text-xs px-1">Tip: Press <span class="kbd">Space</span> to open file picker</div>
      </aside>

      <!-- Main -->
      <section class="lg:col-span-8 space-y-4">
        <div class="card p-4">
          <div class="flex items-center justify-between">
            <div>
              <div class="font-semibold">Bulk Invoice to CSV</div>
              <div class="muted">Upload invoices. We'll OCR, extract, and structure.</div>
            </div>
            <span class="text-xs px-2 py-1 rounded-full border border-border">Ready</span>
          </div>

          <div class="mt-4">
            <div id="uploadArea" class="upload-dashed" role="button" tabindex="0" aria-label="Upload invoices. Click to browse or drag & drop.">
              <div class="text-5xl mb-2">☁️</div>
              <h3 class="text-lg font-medium">Drag & Drop invoices here</h3>
              <p class="muted">or click to browse — PDF, JPG, PNG — max 20 files</p>
              <button id="browseBtn" type="button" class="btn btn-outline mt-2">Browse files…</button>
              <input type="file" id="fileInput" multiple accept=".pdf,.jpg,.jpeg,.png" class="hidden">
            </div>

            <div id="fileList" class="mt-3"></div>

            <div class="flex flex-wrap items-center gap-2 mt-3">
              <button id="processBtn" class="btn btn-primary" disabled>Process All</button>
              <button id="sampleBtn" class="btn btn-outline">Try Sample</button>
            </div>
          </div>
        </div>

        <!-- Processing -->
        <div class="card p-4 hidden" id="processingCard">
          <div class="flex items-center justify-between">
            <h3 class="font-medium">Processing Invoices</h3>
            <span class="text-xs px-2 py-1 rounded-full border border-border">Live</span>
          </div>
          <div class="progress-wrapper mt-3">
            <div id="progressBar" class="progress-bar"></div>
          </div>
          <div class="flex items-center justify-between mt-2 text-sm">
            <span id="processingStatus" class="muted">Initializing...</span>
            <span id="progressMeta" class="muted"></span>
          </div>
        </div>

        <!-- Results -->
        <div class="card p-4 hidden" id="resultsCard">
          <div class="flex items-center justify-between mb-3">
            <h3 class="font-medium">Processing Results</h3>
            <div class="flex gap-2">
              <button class="btn btn-outline" id="downloadDetailed">Detailed CSV</button>
              <button class="btn btn-outline" id="downloadSummary">Summary CSV</button>
              <button class="btn btn-outline" id="downloadJson">Raw JSON</button>
            </div>
          </div>

          <!-- Stats -->
          <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div class="card p-3 text-center">
              <div class="muted">Invoices</div>
              <div id="totalInvoices" class="text-2xl font-semibold">0</div>
            </div>
            <div class="card p-3 text-center">
              <div class="muted">Line Items</div>
              <div id="totalLineItems" class="text-2xl font-semibold">0</div>
            </div>
            <div class="card p-3 text-center">
              <div class="muted">Total Amount</div>
              <div id="totalAmount" class="text-2xl font-semibold">$0.00</div>
            </div>
            <div class="card p-3 text-center">
              <div class="muted">Average / Invoice</div>
              <div id="averageAmount" class="text-2xl font-semibold">$0.00</div>
            </div>
          </div>

          <!-- CSV previews -->
          <div id="csvPreviews" class="card p-3 mt-3"></div>

          <!-- Per-invoice -->
          <h4 class="muted uppercase text-xs mt-3">Individual Invoices</h4>
          <div id="invoiceDetails" class="mt-2"></div>
        </div>
      </section>
    </main>
  </div>

  <script>
    // State
    let selectedFiles = [];
    let processingResults = null;

    // Elements
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    const fileList = document.getElementById('fileList');
    const processBtn = document.getElementById('processBtn');
    const sampleBtn = document.getElementById('sampleBtn');
    const processingCard = document.getElementById('processingCard');
    const resultsCard = document.getElementById('resultsCard');
    const progressBar = document.getElementById('progressBar');
    const processingStatus = document.getElementById('processingStatus');
    const progressMeta = document.getElementById('progressMeta');

    // Theme toggle
    const themeToggle = document.getElementById('themeToggle');
    let dark = true;
    document.documentElement.classList.add('dark');
    themeToggle.addEventListener('click', () => {
      dark = !dark;
      themeToggle.setAttribute('data-state', dark ? 'checked' : 'unchecked');
      document.documentElement.classList.toggle('dark', dark);
    });

    // File input change handler
    function handleFileSelection(files) {
      const fileArray = Array.from(files);
      const validFiles = fileArray.filter(f => {
        const ext = f.name.toLowerCase().split('.').pop();
        return ['pdf', 'jpg', 'jpeg', 'png'].includes(ext);
      });
      
      if (validFiles.length === 0) {
        showErrors(['No supported files found. Please select PDF, JPG, JPEG, or PNG files.']);
        return;
      }
      
      // Add new files to existing selection (up to 20 total)
      selectedFiles = [...selectedFiles, ...validFiles].slice(0, 20);
      renderFileList();
      processBtn.disabled = selectedFiles.length === 0;
      
      if (validFiles.length !== fileArray.length) {
        showErrors([`${fileArray.length - validFiles.length} file(s) were skipped (unsupported format)`]);
      }
    }

    // File input event listeners
    fileInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files.length > 0) {
        handleFileSelection(e.target.files);
      }
      // Reset input value to allow selecting same files again
      e.target.value = '';
    });

    // Upload area click handler
    uploadArea.addEventListener('click', (e) => {
      // Prevent triggering when clicking the browse button specifically
      if (e.target.id !== 'browseBtn') {
        fileInput.click();
      }
    });

    // Browse button click handler
    document.getElementById('browseBtn').addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      fileInput.click();
    });

    // Keyboard accessibility
    uploadArea.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        fileInput.click();
      }
    });

    // Drag and drop handlers
    uploadArea.addEventListener('dragover', (e) => {
      e.preventDefault();
      uploadArea.classList.add('ring-2', 'ring-primary');
    });

    uploadArea.addEventListener('dragleave', (e) => {
      e.preventDefault();
      // Only remove highlight if we're actually leaving the upload area
      if (!uploadArea.contains(e.relatedTarget)) {
        uploadArea.classList.remove('ring-2', 'ring-primary');
      }
    });

    uploadArea.addEventListener('drop', (e) => {
      e.preventDefault();
      uploadArea.classList.remove('ring-2', 'ring-primary');
      
      const files = e.dataTransfer.files;
      if (files && files.length > 0) {
        handleFileSelection(files);
      }
    });

    function renderFileList() {
      if (selectedFiles.length === 0) {
        fileList.innerHTML = '';
        return;
      }

      const items = selectedFiles.map((file, index) => {
        const size = (file.size / (1024 * 1024)).toFixed(2);
        const safeName = file.name.replace(/[&<>"']/g, (c) => ({
          '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
        }[c]));
        
        return `
          <div class="flex items-center justify-between border border-border rounded-md p-2 mb-2">
            <div class="flex items-center gap-2">
              <div class="h-8 w-8 rounded-md bg-muted grid place-items-center">📄</div>
              <div>
                <div class="text-sm font-medium">${safeName}</div>
                <div class="muted text-xs">${size} MB</div>
              </div>
            </div>
            <button class="btn btn-outline text-xs" data-remove-index="${index}">Remove</button>
          </div>
        `;
      }).join('');
      
      fileList.innerHTML = items;
      
      // Add remove button event listeners
      fileList.querySelectorAll('[data-remove-index]').forEach(btn => {
        btn.addEventListener('click', () => {
          const index = parseInt(btn.getAttribute('data-remove-index'));
          selectedFiles.splice(index, 1);
          renderFileList();
          processBtn.disabled = selectedFiles.length === 0;
        });
      });
    }

    // Keyboard shortcut: Space to open picker
    document.addEventListener('keydown', (e) => {
      if (e.code === 'Space' && document.activeElement === document.body) {
        e.preventDefault();
        fileInput.click();
      }
    });

    // Clear button
    document.getElementById('clearBtn').addEventListener('click', () => {
      selectedFiles = [];
      renderFileList();
      processBtn.disabled = true;
      processingCard.classList.add('hidden');
      resultsCard.classList.add('hidden');
      // Clear any error messages
      document.querySelectorAll('.error-message').forEach(el => el.remove());
    });

    // Sample button now calls backend with a bundled sample hosted in public/ if any,
    // otherwise falls back to showing a note to upload real files.
    sampleBtn.addEventListener('click', async () => {
      try {
        // Attempt to fetch a sample from backend (optional future endpoint)
        // For now, instruct user to upload a real file since backend returns real CSV.
        showErrors(['No built-in sample data. Please upload a PDF/JPG/PNG to generate real CSV previews.']);
      } catch (e) {
        showErrors(['Sample run unavailable. Upload a real invoice instead.']);
      }
    });

    // Process button
    processBtn.addEventListener('click', processFiles);

    async function processFiles() {
      if (selectedFiles.length === 0) {
        showErrors(['Please select at least one file.']);
        return;
      }

      processingCard.classList.remove('hidden');
      resultsCard.classList.add('hidden');
      simulateProgress();

      // Build FormData to send to Flask backend
      const formData = new FormData();
      selectedFiles.forEach(file => formData.append('files', file));
      formData.append('llm_choice', document.getElementById('llm_choice').value);
      formData.append('include_detailed_csv', document.getElementById('include_detailed_csv').checked ? 'on' : '');
      formData.append('include_summary_csv', document.getElementById('include_summary_csv').checked ? 'on' : '');
      const conf = document.getElementById('confidenceThreshold')?.value;
      if (conf) formData.append('confidence_threshold', conf);

      try {
        const response = await fetch('/upload', {
          method: 'POST',
          body: formData
        });

        // Handle non-2xx with JSON error body or generic message
        let result;
        try {
          result = await response.json();
        } catch {
          throw new Error(`Unexpected response (${response.status})`);
        }

        if (response.ok && result?.success) {
          processingResults = result;
          displayResults(result);
        } else {
          const errs = result?.errors?.length ? result.errors : [`Upload failed (${response.status}).`];
          showErrors(errs);
          processingCard.classList.add('hidden');
        }
      } catch (err) {
        showErrors([`Network error: ${err.message}`]);
        processingCard.classList.add('hidden');
      }
    }

    // Progress simulation
    function updateProgress(percent, message) {
      progressBar.style.width = Math.min(percent, 100) + '%';
      processingStatus.textContent = message;
      progressMeta.textContent = `${Math.round(Math.min(percent, 100))}%`;
    }

    function simulateProgress() {
      let progress = 0;
      const interval = setInterval(() => {
        progress += Math.random() * 12 + 3;
        if (progress >= 100) {
          progress = 100;
          clearInterval(interval);
          updateProgress(progress, 'Processing complete!');
        } else {
          updateProgress(progress, `Processing invoices... ${Math.round(progress)}%`);
        }
      }, 400);
    }

    // Results display
    function displayResults(result) {
      processingCard.classList.add('hidden');
      resultsCard.classList.remove('hidden');

      // Update stats
      document.getElementById('totalInvoices').textContent = result.stats.total_invoices;
      document.getElementById('totalLineItems').textContent = result.stats.total_line_items;
      document.getElementById('totalAmount').textContent = '$' + result.stats.total_amount.toFixed(2);
      document.getElementById('averageAmount').textContent = '$' + result.stats.average_amount.toFixed(2);

      setupDownloadButtons(result);
      showCSVPreviews(result);
      showInvoiceDetails(result.invoices);

      if (result.errors && result.errors.length > 0) {
        showErrors(result.errors);
      }
    }

    function setupDownloadButtons(result) {
      const timestamp = new Date().toISOString().slice(0, 19).replace(/[:.]/g, '-');

      document.getElementById('downloadDetailed').onclick = () => {
        if (result.csv_files?.detailed) {
          downloadCSV(result.csv_files.detailed, `invoices_detailed_${timestamp}.csv`);
        }
      };
      
      document.getElementById('downloadSummary').onclick = () => {
        if (result.csv_files?.summary) {
          downloadCSV(result.csv_files.summary, `invoices_summary_${timestamp}.csv`);
        }
      };
      
      document.getElementById('downloadJson').onclick = () => {
        const jsonData = JSON.stringify(result.invoices, null, 2);
        downloadJSON(jsonData, `invoices_raw_${timestamp}.json`);
      };
    }

    function downloadCSV(csvContent, filename) {
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);
      link.setAttribute('href', url);
      link.setAttribute('download', filename);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    }

    function downloadJSON(jsonContent, filename) {
      const blob = new Blob([jsonContent], { type: 'application/json;charset=utf-8;' });
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);
      link.setAttribute('href', url);
      link.setAttribute('download', filename);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    }

    function showCSVPreviews(result) {
      const previewsContainer = document.getElementById('csvPreviews');
      let html = '';

      if (result.csv_files?.detailed) {
        html += `
          <div class="mb-4">
            <h4 class="text-sm font-medium mb-2">Detailed CSV Preview</h4>
            <div class="overflow-x-auto border border-border rounded-md">
              <table class="w-full text-sm">
                <thead class="bg-muted">
                  <tr>
                    <th class="text-left p-2">File #</th>
                    <th class="text-left p-2">Invoice #</th>
                    <th class="text-left p-2">Vendor</th>
                    <th class="text-left p-2">Customer</th>
                    <th class="text-left p-2">Item</th>
                    <th class="text-left p-2">Qty</th>
                    <th class="text-left p-2">Unit Price</th>
                    <th class="text-left p-2">Total</th>
                  </tr>
                </thead>
                <tbody>${parseCSVPreview(result.csv_files.detailed, 5)}</tbody>
              </table>
            </div>
          </div>`;
      }

      if (result.csv_files?.summary) {
        html += `
          <div class="mb-2">
            <h4 class="text-sm font-medium mb-2">Summary CSV Preview</h4>
            <div class="overflow-x-auto border border-border rounded-md">
              <table class="w-full text-sm">
                <thead class="bg-muted">
                  <tr>
                    <th class="text-left p-2">File #</th>
                    <th class="text-left p-2">Invoice #</th>
                    <th class="text-left p-2">Date</th>
                    <th class="text-left p-2">Vendor</th>
                    <th class="text-left p-2">Customer</th>
                    <th class="text-left p-2">Items</th>
                    <th class="text-left p-2">Total</th>
                  </tr>
                </thead>
                <tbody>${parseCSVPreview(result.csv_files.summary, 5)}</tbody>
              </table>
            </div>
          </div>`;
      }

      previewsContainer.innerHTML = html;
    }

    function parseCSVPreview(csvContent, maxRows) {
      const lines = csvContent.trim().split('\n');
      let html = '';
      
      for (let i = 1; i < Math.min(lines.length, maxRows + 1); i++) {
        const values = lines[i].split(',');
        html += '<tr>';
        for (let j = 0; j < Math.min(values.length, 8); j++) {
          const val = values[j] ? values[j].replace(/"/g, '') : '';
          html += `<td class="p-2 border-t border-border">${val}</td>`;
        }
        html += '</tr>';
      }
      return html;
    }

    function showInvoiceDetails(invoices) {
      const details = document.getElementById('invoiceDetails');
      let html = '';
      
      invoices.forEach((invoice, index) => {
        const total = (invoice.total_amount || 0).toFixed(2);
        const status = (invoice.total_amount || 0) > 0 ? 'Processed' : 'Needs Review';
        
        html += `
          <div class="border border-border rounded-md p-3 mb-3">
            <div class="flex items-center justify-between">
              <div>
                <div class="muted text-xs">Invoice ${index + 1}</div>
                <div class="font-medium">${invoice.invoice_number || 'N/A'} — ${invoice.vendor_name || 'N/A'}</div>
              </div>
              <div class="text-right">
                <span class="text-xs px-2 py-1 rounded-full border border-border">${status}</span>
                <div class="mt-2 font-semibold">${total}</div>
              </div>
            </div>
            <div class="grid md:grid-cols-2 gap-3 mt-3">
              <div class="border border-border rounded-md p-2">
                <div class="muted text-xs">Invoice Info</div>
                <div class="text-sm mt-1">
                  <div><strong>Number:</strong> ${invoice.invoice_number || 'N/A'}</div>
                  <div><strong>Date:</strong> ${invoice.invoice_date || 'N/A'}</div>
                  <div><strong>Vendor:</strong> ${invoice.vendor_name || 'N/A'}</div>
                  <div><strong>Customer:</strong> ${invoice.customer_name || 'N/A'}</div>
                </div>
              </div>
              <div class="border border-border rounded-md p-2">
                <div class="muted text-xs">Line Items</div>
                <div class="text-sm mt-1">
                  ${(invoice.line_items || []).length > 0
                    ? invoice.line_items.map((item, idx) =>
                        `<div class="flex items-center justify-between mb-1">
                          <span>${idx + 1}. ${item.description || 'N/A'}</span>
                          <span>Qty: ${item.quantity || 0} — ${(item.total_price || 0).toFixed(2)}</span>
                        </div>`
                      ).join('')
                    : '<div>No line items found</div>'
                  }
                </div>
              </div>
            </div>
          </div>`;
      });
      
      details.innerHTML = html;
    }

    function showErrors(errors) {
      const messages = Array.isArray(errors) ? errors : [String(errors || 'Unknown error')];
      const errorHtml = messages.map(error => 
        `<div class="error-message border border-red-500/35 bg-red-500/12 text-red-200 text-sm rounded-md p-3 mb-3">
          ⚠️ ${error}
        </div>`
      ).join('');
      
      // Find the main upload card and prepend errors
      const uploadCard = document.querySelector('.card');
      uploadCard.insertAdjacentHTML('afterbegin', errorHtml);
      
      // Auto-remove errors after 5 seconds
      setTimeout(() => {
        document.querySelectorAll('.error-message').forEach(el => el.remove());
      }, 5000);
    }

    // Initialize the app
    document.addEventListener('DOMContentLoaded', () => {
      console.log('Invoice AI initialized');
      processBtn.disabled = true;
    });
  </script>
</body>
</html>
