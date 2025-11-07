frappe.provide("frappe.foms");

class LabelPrintPage {
  constructor(wrapper, defaults = {}) {
    this.wrapper = wrapper;
    this.defaults = Object.assign(
      {
        size: "Custom",
        width: 110,
        height: 150,
        margin: 0,
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

  build_preview() {
    this.$preview = $(
      `
      <div class="label-print-preview" style="border: 1px solid var(--gray-400); height: 70vh; overflow: auto; display: flex; align-items: center; justify-content: center; background: repeating-linear-gradient(45deg, #f4f5f7 0px, #f4f5f7 12px, #eef0f2 12px, #eef0f2 24px);">
        <div class="placeholder" style="color: var(--gray-600); text-align: center; padding: 16px;">
          Select a Print Template, then click Render Preview
        </div>
      </div>
      `
    ).appendTo(this.page.body);

    this.$paper = $('<div class="paper" style="position: relative; width: auto; height: auto;"></div>')
      .appendTo(this.$preview)
      .hide();
    this.$frame = $(`<iframe style="width:100%; height:100%; border:0; background:white;"></iframe>`).appendTo(
      this.$paper
    );
    this.$hint = $(
      '<div class="paper-hint" style="position:absolute; inset:0; display:flex; align-items:center; justify-content:center; padding:16px; color: var(--gray-700); font-size:12px; text-align:center; background: rgba(255,255,255,0.9);"></div>'
    )
      .text(
        "Provide Reference DocType and Document Name to render the selected Print Format."
      )
      .appendTo(this.$paper)
      .hide();
  }

  build_actions() {
    this.$actions = $(
      `
        <div class="label-print-actions" style="padding: 8px 0; display: flex; gap: 8px; align-items: center;">
          <button class="btn btn-primary btn-sm render-btn">Render Preview</button>
        </div>
      `
    ).insertAfter(this.$preview);
    this.$renderBtn = this.$actions.find(".render-btn");
    this.$renderBtn.on("click", () => this.render_preview());
  }

  build_controls() {
    this.$controls = $(
      '<div class="label-print-controls" style="margin-top: 8px; margin-bottom: 16px;"></div>'
    ).insertAfter(this.$actions);
    $('<div style="font-weight:600; color: var(--gray-700); margin: 8px 0;">Settings</div>').insertBefore(
      this.$controls
    );

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

  build_printview_url(values) {
    if (!values.ref_doctype || !values.ref_name || !values.print_template) return null;
    const params = {
      doctype: values.ref_doctype,
      name: values.ref_name,
      format: values.print_template,
      no_letterhead: 1,
      _lang: frappe.boot.lang,
    };
    const q = Object.keys(params)
      .map((k) => `${encodeURIComponent(k)}=${encodeURIComponent(params[k])}`)
      .join("&");
    return `/printview?${q}`;
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

    // Apply dimensions in mm when provided
    const mm = (v) => (v != null ? `${v}mm` : "auto");
    this.$paper.css({
      width: mm(width),
      height: mm(height),
      margin: mm(margin),
      background: "white",
      boxShadow: "0 0 0 1px var(--gray-300) inset",
      display: "block",
      overflow: "hidden",
      alignSelf: "flex-start",
    });

    const url = this.build_printview_url(values);
    if (url) {
      this.$hint.hide();
      this.$frame.off("load").on("load", function () {
        try {
          const d = this.contentDocument || this.contentWindow.document;
          if (!d) return;
          const style = d.createElement("style");
          style.type = "text/css";
          style.textContent = `
            .action-banner { display: none !important; }
            body { background: white !important; }
          `;
          d.head && d.head.appendChild(style);
          const banner = d.querySelectorAll && d.querySelectorAll('.action-banner');
          banner && banner.forEach && banner.forEach((el) => (el.style.display = 'none'));
        } catch (e) {
          // ignore cross-origin or timing errors
        }
      });
      this.$frame.attr("src", url);
    } else {
      this.$frame.attr("src", "about:blank");
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
