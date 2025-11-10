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
          // Compose and cache a full HTML document for printing/rasterization
          try {
            const valuesNow = this.fg ? (this.fg.get_values() || {}) : {};
            const widthDoc = cint(valuesNow.width) || null;
            const heightDoc = cint(valuesNow.height) || null;
            const marginDoc = cint(valuesNow.margin) || 0;
            const mm = (v) => (v != null ? `${v}mm` : "auto");
            const centerCss = `
              .label-preview-root { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; }
              .label-preview-root > :first-child { margin: auto; }
              #print-root { box-sizing: border-box; width: ${mm(widthDoc)}; height: ${mm(heightDoc)}; padding: ${mm(marginDoc)}; background: white; overflow: hidden; }
            `;
            this._lastHtmlDoc = `<!DOCTYPE html><html><head><meta charset="utf-8"><style>${style}</style><style>${centerCss}</style></head><body><div id="print-root"><div class="label-preview-root">${html}</div></div></body></html>`;
          } catch (e) {}
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

  async resolvePrinterName() {
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

  getPrintableHtml() {
    if (this._lastHtmlDoc) return this._lastHtmlDoc;
    const host = this.$paper_content && this.$paper_content[0];
    let html = '';
    if (host && host.shadowRoot) {
      const root = host.shadowRoot;
      // Collect styles and the wrapped content we inserted during render
      const styles = Array.from(root.querySelectorAll('style')).map(el => el.textContent || '').join('\n');
      const wrap = root.querySelector('.label-preview-root');
      const body = wrap ? wrap.innerHTML : '';
      html = `<!DOCTYPE html><html><head><meta charset="utf-8"><style>${styles}</style></head><body>${body}</body></html>`;
    } else {
      const body = this.$paper_content ? this.$paper_content.html() : '';
      html = `<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>${body || ''}</body></html>`;
    }
    return html;
  }

  ensureHtml2CanvasLoaded() {
    if (window.html2canvas) return Promise.resolve();
    if (this._h2cPromise) return this._h2cPromise;
    const src = 'https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js';
    this._h2cPromise = new Promise((resolve, reject) => {
      const s = document.createElement('script');
      s.src = src;
      s.async = true;
      s.defer = true;
      s.onload = () => resolve();
      s.onerror = () => reject(new Error('Failed to load html2canvas'));
      document.head.appendChild(s);
    });
    return this._h2cPromise;
  }

  rasterizeToImage(values) {
    const docHtml = this.getPrintableHtml();
    const width = cint(values.width) || null;
    const height = cint(values.height) || null;
    const mm2px = (v) => (v != null ? Math.round(v * 3.7795275591) : null);
    const wpx = mm2px(width) || 800;
    const hpx = mm2px(height) || 600;

    const iframe = document.createElement('iframe');
    iframe.style.position = 'fixed';
    iframe.style.left = '-10000px';
    iframe.style.top = '-10000px';
    iframe.style.width = `${wpx}px`;
    iframe.style.height = `${hpx}px`;
    document.body.appendChild(iframe);

    return new Promise((resolve, reject) => {
      const cleanup = () => { try { document.body.removeChild(iframe); } catch (e) {} };
      const render = () => {
        try {
          const d = iframe.contentDocument || iframe.contentWindow.document;
          d.open(); d.write(docHtml); d.close();
          const wait = () => setTimeout(() => {
            const root = d.getElementById('print-root') || d.body;
            window.html2canvas(root, { scale: 2, backgroundColor: '#ffffff', useCORS: true })
              .then((canvas) => {
                const url = canvas.toDataURL('image/png');
                cleanup();
                resolve(url);
              })
              .catch((err) => { cleanup(); reject(err); });
          }, 80);
          if (d.readyState === 'complete') wait();
          else d.addEventListener('readystatechange', () => { if (d.readyState === 'complete') wait(); });
        } catch (e) { cleanup(); reject(e); }
      };
      if (iframe.contentWindow) render();
      else iframe.addEventListener('load', render);
    });
  }

  buildImageHtml(imgUrl, values) {
    const width = cint(values.width) || null;
    const height = cint(values.height) || null;
    const margin = cint(values.margin) || 0;
    const mm = (v) => (v != null ? `${v}mm` : 'auto');
    const css = `
      html, body { height: 100%; margin: 0; }
      #page { box-sizing: border-box; width: ${mm(width)}; height: ${mm(height)}; padding: ${mm(margin)}; display: flex; align-items: center; justify-content: center; background: #fff; }
      #page img { max-width: 100%; max-height: 100%; display: block; }
    `;
    return `<!DOCTYPE html><html><head><meta charset="utf-8"><style>${css}</style></head><body><div id="page"><img src="${imgUrl}"></div></body></html>`;
  }

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
        return this.ensureHtml2CanvasLoaded()
          .then(() => this.rasterizeToImage(values))
          .then((imgUrl) => {
            const htmlDoc = this.buildImageHtml(imgUrl, values);
            const dataUrl = 'data:text/html;charset=utf-8,' + encodeURIComponent(htmlDoc);
            return qz.print(cfg, [{ type: 'html', format: 'file', data: dataUrl }]);
          });
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
