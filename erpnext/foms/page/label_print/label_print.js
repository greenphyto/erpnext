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
    } else {
      // If no doc provided, keep hint
      // clear any previous rendered content
      this.$paper_content.empty();
      this.$hint.show();
    }
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
