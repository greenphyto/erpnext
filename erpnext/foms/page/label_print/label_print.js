frappe.provide("frappe.foms");

class LabelPrintPage {
  constructor(wrapper, defaults = {}) {
    this.wrapper = wrapper;
    this.defaults = Object.assign(
      {
        size: "Custom",
        width: 110,
        height: 150,
        margin: 5,
        print_template: "Label Print",
        ref_doctype: "Delivery Note",
        ref_name: "DO-2024-001",
      },
      defaults || {}
    );

    this.page = frappe.ui.make_app_page({
      parent: wrapper,
      title: "Label Print",
      single_column: true,
    });

    this.build_skeleton();
    this.build_preview();
    this.build_actions();
    this.build_controls();
    this.init_tabs();
    this.build_qz_panel();
    this.apply_defaults();
    this.bind_events();
    this.update_render_btn_state(this.has_template());
    // Only render if a print template is provided; otherwise keep placeholder
    if (this.defaults && this.defaults.print_template) {
      this.render_preview();
    }
  }

  build_skeleton() {
    // Render static HTML (label_print.html) into the page
    try {
      const html = frappe.render_template("label_print", {});
      $(html).appendTo(this.page.body);
    } catch (e) {
      // Fallback minimal structure
      $(
        '<div class="label-print-preview"><div class="placeholder">Select a Print Template, then click Render Preview</div></div>' +
          '<div class="label-print-actions"><button class="btn btn-primary btn-sm render-btn">Render Preview</button></div>' +
          '<div class="label-print-settings-title">Settings</div>' +
          '<div class="label-print-controls"></div>'
      ).appendTo(this.page.body);
    }
  }

  build_preview() {
    this.$preview = $(this.page.body).find('.label-print-preview');
    // Ensure margin visible even if external CSS isn't loaded yet
    this.$preview.css('margin', '15px');

    this.$paper = $('<div class="paper"></div>')
      .appendTo(this.$preview)
      .hide();
    this.$paper_content = $('<div class="paper-content"></div>').appendTo(this.$paper);
    this.$hint = $('<div class="paper-hint"></div>')
      .text(
        "Provide Reference DocType and Document Name to render the selected Print Format."
      )
      .appendTo(this.$paper)
      .hide();
  }

  init_tabs() {
    const $root = $(this.page.body).find('.label-print-tabs');
    if (!$root.length) return;
    // Simple tab toggler to avoid SPA route interference
    const showTab = (target) => {
      $root.find('.nav-link').removeClass('active');
      $root.find(`.nav-link[data-target="${target}"]`).addClass('active');
      $root.find('.tab-pane').removeClass('active show').hide();
      const $pane = $root.find(target);
      $pane.addClass('active show').show();
    };
    $root.on('click', '.nav-link', (e) => {
      e.preventDefault();
      const target = $(e.currentTarget).attr('data-target');
      if (target) showTab(target);
    });
    // Initialize default
    showTab('#tab-settings');
  }

  build_actions() {
    this.$actions = $(this.page.body).find('.label-print-actions');
    this.$renderBtn = this.$actions.find(".render-btn");
    this.$renderBtn.on("click", () => this.render_preview());

    // Print button
    this.$printBtn = this.$actions.find(".print-btn");
    if (!this.$printBtn.length) {
      this.$printBtn = $('<button class="btn btn-secondary btn-sm print-btn">Print</button>').appendTo(this.$actions);
    }
    this.$printBtn.on("click", () => this.handle_print());
    this.update_print_btn_state(false);
  }

  build_controls() {
    this.$controls = $(this.page.body).find('.label-print-controls');

    this.fg = new frappe.ui.FieldGroup({
      fields: [
        {
          fieldtype: "Select",
          fieldname: "size",
          label: "Size",
          options: ["Custom", "A4", "A5", "Letter"].join("\n"),
          default: "Custom",
        },
        {
          fieldtype: "Float",
          fieldname: "width",
          label: "Width (mm)",
          description: "Page width in millimeters",
        },
        {
          fieldtype: "Float",
          fieldname: "height",
          label: "Height (mm)",
          description: "Page height in millimeters",
        },
        {
          fieldtype: "Float",
          fieldname: "margin",
          label: "Margin (mm)",
          description: "Outer margin in millimeters",
        },
        { fieldtype: "Column Break" },
        {
          fieldtype: "Link",
          fieldname: "print_template",
          label: "Print Template",
          options: "Print Format",
          reqd: 1,
        },
        {
          fieldtype: "Link",
          fieldname: "ref_doctype",
          label: "Reference DocType",
          options: "DocType",
          placeholder: "Optional for preview",
        },
        {
          fieldtype: "Dynamic Link",
          fieldname: "ref_name",
          label: "Document Name",
          options: "ref_doctype",
          placeholder: "Optional for preview",
        },
      ],
      body: this.$controls,
    });

    this.fg.make();
  }

  build_qz_panel() {
    // Create a simple QZ section with connect/refresh and printer select
    let $panel = $(this.page.body).find('.label-print-qz');
    if (!$panel.length) {
      $panel = $('<div class="label-print-qz"></div>').appendTo(this.page.body);
      $('<div class="label-print-settings-title">QZ Tray</div>').appendTo($panel);
    }
    const $actions = $('<div class="label-print-qz-actions" style="display:flex; gap:8px; align-items:center; margin: 4px 0 8px;"></div>').appendTo($panel);
    this.$qzConnectBtn = $('<button class="btn btn-default btn-sm qz-connect-btn">Connect</button>').appendTo($actions);
    this.$qzRefreshBtn = $('<button class="btn btn-default btn-sm qz-refresh-btn" disabled>Refresh Printers</button>').appendTo($actions);
    const $selectWrap = $('<div class="label-print-qz-select"></div>').appendTo($panel);

    this.qzFg = new frappe.ui.FieldGroup({
      fields: [
        {
          fieldtype: 'Select',
          fieldname: 'qz_printer',
          label: 'Printer',
          options: '',
          description: 'Select printer for QZ Tray',
        },
      ],
      body: $selectWrap,
    });
    this.qzFg.make();

    // Load saved printer
    try {
      const saved = localStorage.getItem('label_print.qz_printer');
      if (saved && this.qzFg.fields_dict.qz_printer) {
        this.qzFg.set_value('qz_printer', saved);
      }
    } catch (e) {}

    // Bind events
    this.$qzConnectBtn.on('click', () => this.handle_qz_connect());
    this.$qzRefreshBtn.on('click', () => this.refresh_printers());
    const f = () => this.qzFg && this.qzFg.fields_dict && this.qzFg.fields_dict.qz_printer;
    if (f()) {
      f().df.onchange = () => {
        try {
          const val = f().get_value();
          localStorage.setItem('label_print.qz_printer', val || '');
        } catch (e) {}
      };
    }
  }

  apply_defaults() {
    const d = this.defaults || {};
    const keys = [
      "size",
      "width",
      "height",
      "margin",
      "print_template",
      "ref_doctype",
      "ref_name",
    ];
    keys.forEach((k) => {
      if (d[k] !== undefined && d[k] !== null && this.fg.fields_dict[k]) {
        this.fg.set_value(k, d[k]);
      }
    });

    // If a preset size is passed, auto-apply dims when missing
    this.apply_size_controls(d);
  }

  bind_events() {
    [
      "size",
      "width",
      "height",
      "margin",
      "print_template",
      "ref_doctype",
      "ref_name",
    ].forEach((f) => {
      if (!(this.fg.fields_dict[f] && this.fg.fields_dict[f].df)) return;
      if (f === "print_template") {
        this.fg.fields_dict[f].df.onchange = () => {
          const has = this.has_template();
          this.update_render_btn_state(has);
          if (has) this.render_preview();
        };
      } else if (f === "ref_doctype") {
        this.fg.fields_dict[f].df.onchange = () => {
          this.fg.set_value("ref_name", "");
          if (this.has_template()) this.render_preview();
        };
      } else {
        this.fg.fields_dict[f].df.onchange = () => {
          if (this.has_template()) this.render_preview();
        };
      }
    });
  }

  has_template() {
    const f = this.fg && this.fg.fields_dict && this.fg.fields_dict["print_template"];
    return !!(f && f.get_value && f.get_value());
  }

  update_render_btn_state(enabled) {
    if (!this.$renderBtn) return;
    this.$renderBtn.prop("disabled", !enabled);
  }

  update_print_btn_state(enabled) {
    if (!this.$printBtn) return;
    this.$printBtn.prop("disabled", !enabled);
  }

  apply_size_controls(values) {
    values = values || {};
    const presets = {
      A4: { width: 210, height: 297 },
      A5: { width: 148, height: 210 },
      Letter: { width: 216, height: 279 },
    };

    if (values.size && values.size !== "Custom" && presets[values.size]) {
      if (!values.width) this.fg.set_value("width", presets[values.size].width);
      if (!values.height) this.fg.set_value("height", presets[values.size].height);
    }
  }

  // Render print format HTML directly (no printview wrapper/gutter)
  fetch_and_render(values) {
    const args = {
      doc: values.ref_doctype,
      name: values.ref_name,
      print_format: values.print_template,
      no_letterhead: 1,
      _lang: frappe.boot.lang,
    };
    const $btn = this.$renderBtn;
    $btn && $btn.prop("disabled", true).addClass("btn-loading");
    frappe.call({
      method: "frappe.www.printview.get_html_and_style",
      args,
      callback: (r) => {
        try {
          const msg = r && r.message ? r.message : {};
          const html = msg.html || "";
          const style = msg.style || "";
          // Cache latest style and html for printing as plain fragment
          this._printStyle = style;
          this._printContent = html;
          // Compose and cache a full HTML document for printing/rasterization (no longer used)
          // Left intentionally blank to honor plain-fragment printing
          // Render into shadow DOM if available to avoid CSS leaking
          const host = this.$paper_content[0];
          if (host && host.attachShadow) {
            const root = host.shadowRoot || host.attachShadow({ mode: 'open' });
            root.innerHTML = '';
            const styleEl = document.createElement('style');
            styleEl.textContent = `${style}`;
            const styleCenter = document.createElement('style');
            styleCenter.textContent = `
              .label-preview-root { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; }
              .label-preview-root > :first-child { margin: auto; }
            `;
            const wrap = document.createElement('div');
            wrap.className = 'label-preview-root';
            wrap.innerHTML = html;
            root.appendChild(styleEl);
            root.appendChild(styleCenter);
            root.appendChild(wrap);
          } else {
            // Fallback: inject style + html directly
            const centerCss = `
              <style>
                .paper-content { display: flex; align-items: center; justify-content: center; }
                .paper-content > :first-child { margin: auto; }
              </style>
            `;
            this.$paper_content.html(`${centerCss}<style>${style}</style>${html}`);
          }
        } finally {
          $btn && $btn.removeClass("btn-loading").prop("disabled", false);
        }
      },
      error: () => {
        $btn && $btn.removeClass("btn-loading").prop("disabled", false);
        frappe.msgprint({
          title: __("Render Failed"),
          message: __("Unable to render Print Format HTML."),
          indicator: "red",
        });
      },
    });
  }

  render_preview() {
    const f = this.fg && this.fg.fields_dict && this.fg.fields_dict["print_template"];
    const print_template = f && f.get_value ? f.get_value() : null;
    if (!print_template) {
      // keep placeholder and disable paper
      this.$preview.find(".placeholder").show();
      this.$paper.hide();
      this.update_render_btn_state(false);
      return;
    }
    this.update_render_btn_state(true);
    const values = this.fg.get_values() || {};
    this.apply_size_controls(values);

    const width = cint(values.width) || null;
    const height = cint(values.height) || null;
    const margin = cint(values.margin) || 0;

    // Style the paper visibility
    this.$preview.find(".placeholder").hide();
    this.$paper.show();
    // Ensure we start at the top to avoid apparent cut-off
    try { this.$preview.scrollTop(0).scrollLeft(0); } catch (e) {}

    // Apply dimensions in mm when provided
    const mm = (v) => (v != null ? `${v}mm` : "auto");
    this.$paper.css({
      width: mm(width),
      height: mm(height),
      padding: mm(margin),
      background: "white",
      boxShadow: "0 0 0 1px var(--gray-300) inset",
      display: "block",
      overflow: "hidden",
      alignSelf: "center",
    });

    if (values.ref_doctype && values.ref_name) {
      this.$hint.hide();
      this.fetch_and_render(values);
      this.update_print_btn_state(true);
    } else {
      // If no doc provided, keep hint
      // clear any previous rendered content
      this.$paper_content.empty();
      this.$hint.show();
      this.update_print_btn_state(false);
    }
  }

  // --- QZ Tray Integration ---
  ensureQZLoaded() {
    if (window.qz) return Promise.resolve();
    if (this._qzLoadPromise) return this._qzLoadPromise;
    const src = 'https://cdn.jsdelivr.net/npm/qz-tray@2.2.3/qz-tray.js';
    this._qzLoadPromise = new Promise((resolve, reject) => {
      const s = document.createElement('script');
      s.src = src;
      s.async = true;
      s.defer = true;
      s.onload = () => resolve();
      s.onerror = () => reject(new Error('Failed to load QZ Tray library'));
      document.head.appendChild(s);
    });
    return this._qzLoadPromise;
  }

  setupQZSecurity() {
    // Allow unsigned printing if QZ Tray permits it (user setting)
    try {
      if (window.qz && qz.security) {
        qz.security.setCertificatePromise((resolve, reject) => resolve(null));
        qz.security.setSignaturePromise((toSign) => (resolve, reject) => resolve(null));
      }
    } catch (e) {
      // no-op; use defaults
    }
  }

  connectQZ() {
    if (!window.qz) return Promise.reject(new Error('QZ Tray not loaded'));
    if (qz.websocket.isActive()) return Promise.resolve();
    // Try default, then secure/insecure fallbacks
    const tryDefault = () => qz.websocket.connect();
    const trySecure = () => qz.websocket.connect({ usingSecure: true });
    const tryInsecure = () => qz.websocket.connect({ usingSecure: false });
    return tryDefault()
      .catch(() => (window.location.protocol === 'https:' ? trySecure() : tryInsecure()))
      .catch(() => (window.location.protocol === 'https:' ? tryInsecure() : trySecure()));
  }

  handle_qz_connect() {
    const $btn = this.$qzConnectBtn;
    $btn && $btn.prop('disabled', true).addClass('btn-loading');
    this.ensureQZLoaded()
      .then(() => { this.setupQZSecurity(); return this.connectQZ(); })
      .then(() => {
        this.$qzRefreshBtn && this.$qzRefreshBtn.prop('disabled', false);
        frappe.show_alert({ message: __('QZ Connected'), indicator: 'green' });
        return this.refresh_printers();
      })
      .catch((err) => {
        console.error('QZ connect failed', err);
        frappe.msgprint({ title: __('QZ Connect Failed'), message: err && err.message ? frappe.utils.escape_html(err.message) : __('Unable to connect to QZ Tray'), indicator: 'red' });
      })
      .finally(() => { $btn && $btn.removeClass('btn-loading').prop('disabled', false); });
  }

  refresh_printers() {
    if (!window.qz || !qz.websocket.isActive()) {
      frappe.msgprint(__('Connect to QZ first.'));
      return Promise.resolve();
    }
    const fg = this.qzFg && this.qzFg.fields_dict && this.qzFg.fields_dict.qz_printer;
    if (!fg) return Promise.resolve();
    const $sel = fg.$input;
    if ($sel && $sel.prop) $sel.prop('disabled', true);
    return qz.printers.find()
      .then(async (list) => {
        const printers = Array.isArray(list) ? list : [];
        // Populate select options
        if ($sel && $sel.length) {
          $sel.empty();
          $sel.append(`<option value="">${__('Select a printer')}</option>`);
          printers.forEach((p) => {
            const safe = p;
            $sel.append(`<option value="${frappe.utils.escape_html(safe)}">${frappe.utils.escape_html(safe)}</option>`);
          });
        }
        // Try to set default
        let toSet = null;
        try { toSet = await qz.printers.getDefault(); } catch (e) {}
        const saved = (() => { try { return localStorage.getItem('label_print.qz_printer'); } catch (e) { return null; } })();
        if (saved && printers.includes(saved)) toSet = saved;
        if (toSet && fg.set_value) fg.set_value('qz_printer', toSet);
      })
      .catch((err) => {
        console.error('List printers failed', err);
        frappe.msgprint({ title: __('List Printers Failed'), message: err && err.message ? frappe.utils.escape_html(err.message) : __('Unable to list printers'), indicator: 'red' });
      })
      .finally(() => { if ($sel && $sel.prop) $sel.prop('disabled', false); });
  }

  getSelectedPrinter() {
    const fg = this.qzFg && this.qzFg.fields_dict && this.qzFg.fields_dict.qz_printer;
    if (fg && fg.get_value) {
      const v = fg.get_value();
      if (v) return v;
    }
    try { const saved = localStorage.getItem('label_print.qz_printer'); if (saved) return saved; } catch (e) {}
    return null;
  }

  buildPlainFragment(values) {
    const width = cint(values.width) || null;
    const height = cint(values.height) || null;
    const margin = cint(values.margin) || 0;
    const mm = (v) => (v != null ? `${v}mm` : 'auto');
    const extraCss = `
      .label-preview-root { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; }
      .label-preview-root > :first-child { margin: auto; }
      #print-root { box-sizing: border-box; width: ${mm(width)}; height: ${mm(height)}; padding: ${mm(margin)}; background: white; overflow: hidden; }
    `;
    let style = this._printStyle || '';
    let content = this._printContent || '';
    if (!content) {
      // Fallback: extract from preview
      const host = this.$paper_content && this.$paper_content[0];
      if (host && host.shadowRoot) {
        const root = host.shadowRoot;
        const styles = Array.from(root.querySelectorAll('style')).map(el => el.textContent || '').join('\n');
        const wrap = root.querySelector('.label-preview-root');
        style = style || styles;
        content = wrap ? wrap.innerHTML : content;
      } else if (this.$paper_content) {
        content = this.$paper_content.html() || content;
      }
    }
    return `<style>${style}</style><style>${extraCss}</style><div id="print-root"><div class="label-preview-root">${content}</div></div>`;
  }

  async resolvePrinterName() {
    const selected = this.getSelectedPrinter();
    if (selected) return selected;
    try {
      const def = await qz.printers.getDefault();
      if (def) return def;
    } catch (e) {}
    try {
      const list = await qz.printers.find();
      if (Array.isArray(list) && list.length) {
        console.warn('No default printer; using first available:', list[0]);
        frappe.show_alert(__('No default printer; using: {0}', [list[0]]));
        return list[0];
      }
    } catch (e) {}
    throw new Error('No printers found');
  }

  // Removed html2canvas/raster functions to honor plain HTML printing

  handle_print() {
    const values = this.fg.get_values() || {};
    if (!(values.ref_doctype && values.ref_name && this.has_template())) {
      frappe.msgprint(__('Please select Print Template and Reference document first.'));
      return;
    }

    const $btn = this.$printBtn;
    $btn && $btn.prop('disabled', true).addClass('btn-loading');

    const width = cint(values.width) || null;
    const height = cint(values.height) || null;
    const margin = cint(values.margin) || 0;

    const after = () => $btn && $btn.removeClass('btn-loading').prop('disabled', false);

    this.ensureQZLoaded()
      .then(() => {
        this.setupQZSecurity();
        return this.connectQZ();
      })
      .then(() => this.resolvePrinterName())
      .then((printer) => {
        const cfg = qz.configs.create(printer, {
          units: 'mm',
          size: width && height ? { width, height } : undefined,
          margins: { top: margin, right: margin, bottom: margin, left: margin },
          scaleContent: true,
        });
        const fragment = this.buildPlainFragment(values);
        return qz.print(cfg, [{ type: 'html', format: 'plain', data: fragment }]);
      })
      .then(() => {
        frappe.show_alert({ message: __('Sent to printer.'), indicator: 'green' });
      })
      .catch((err) => {
        console.error('QZ print failed', err);
        const msg = [
          __('Unable to print via QZ Tray.'),
          err && err.message ? `<div style="margin-top:6px"><code>${frappe.utils.escape_html(err.message)}</code></div>` : '',
          '<hr/>',
          __('Checklist:'),
          '<ul style="margin-top:6px;">',
          `<li>${__('QZ Tray is installed and running')}</li>`,
          `<li>${__('In QZ Settings → Security, enable "Allow unsigned requests" for development')}</li>`,
          `<li>${__('Ensure this site origin is allowed/whitelisted in QZ Tray')}</li>`,
          `<li>${__('If this page is HTTPS, secure connection may be required')}</li>`,
          '</ul>',
          `<div style="margin-top:6px">${__('Download:')} <a href="https://qz.io/download/" target="_blank" rel="noopener">qz.io/download</a></div>`
        ].join('');
        frappe.msgprint({ title: __('Print Failed'), message: msg, indicator: 'red' });
      })
      .finally(after);
  }
}

frappe.foms.LabelPrintPage = LabelPrintPage;

frappe.pages["label-print"].on_page_load = function (wrapper) {
  const defaults = Object.assign({}, (frappe.route_options || {}));
  frappe.label_print = new frappe.foms.LabelPrintPage(wrapper, defaults);
};

function cint(v) {
  const n = parseFloat(v);
  return isFinite(n) ? n : null;
}
