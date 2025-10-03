function load_view(){
// Hindari duplicate kalau reload
  if (frappe.boot.sysdefaults.company_selected=="Disabled") return
  if (document.querySelector(".company-switcher")) return;


  // Ambil default company user dari frappe.defaults
  let current_company = frappe.boot.sysdefaults.company_selected || "No Selected"
  let company_color = frappe.boot.sysdefaults.company_color || "#1F272E"

  // Buat elemen wrapper
  let div = document.createElement("div");
  div.className = "company-switcher";
  div.innerHTML = `
    <span><div class="company-indicator" title="${current_company}"></div></span>
    <span class="value current-company" value="${current_company}">${current_company}</span>
  `;

  // Tambah ke body (atau tepat di bawah header)
  document.body.appendChild(div);

  // Tambah style
  const style = document.createElement("style");
  light_color = mapToBootstrapLight(company_color);
  style.innerHTML = `
    .page-actions{
        margin-bottom: -20px;
    }
    .company-switcher {
        display: flex;
        position: fixed;
        top: 60px;
        right: 130px;
        background: ${light_color};
        border: 1px solid #d1d8dd;
        border-radius: 0px 0px 6px 6px;
        padding: 3px 12px;
        font-size: 12px;
        font-weight: 500;
        color: ${company_color};
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
        z-index: 500;
        min-width: 100px;
    }
    .company-indicator {
        width: 5px;
        height: 6px;
        margin-right: 6px;
        margin-top: 5.5px;
        background-color: ${company_color};
        border-radius: 50%;
    }
    @media (max-width: 576px) {
        .company-switcher {
            right: 18px;
        }
    }
    .company-switcher .value {
      color: ${company_color};
    }
  `;
  document.head.appendChild(style);
}

function hexToRgb(hex) {
  hex = hex.replace(/^#/, "");
  let bigint = parseInt(hex, 16);
  return {
    r: (bigint >> 16) & 255,
    g: (bigint >> 8) & 255,
    b: bigint & 255
  };
}

function colorDistance(c1, c2) {
  return Math.sqrt(
    Math.pow(c1.r - c2.r, 2) +
    Math.pow(c1.g - c2.g, 2) +
    Math.pow(c1.b - c2.b, 2)
  );
}

function mapToBootstrapLight(hex) {
  if (!hex) return "#f8f9fa";

  const lightColors = [
    "#cfe2ff", // primary-subtle
    "#d1e7dd", // success-subtle
    "#f8d7da", // danger-subtle
    "#fff3cd", // warning-subtle
    "#cff4fc", // info-subtle
    "#f8f9fa"  // light
  ];

  const inputRgb = hexToRgb(hex);
  let nearest = null;
  let minDist = Infinity;

  for (const hexColor of lightColors) {
    const dist = colorDistance(inputRgb, hexToRgb(hexColor));
    if (dist < minDist) {
      minDist = dist;
      nearest = hexColor;
    }
  }

  return nearest;
}

load_view();


frappe.provide("custom");

custom.show_company_switcher = function (companies) {
    let html_tiles = `<div class="row g-3 justify-content-center" style="padding: 5px;">`;

    companies.forEach(c => {
        var background = mapToBootstrapLight(c.color)
        html_tiles += `
        <div class="col-12 col-md-6">
            <div class="card company-tile text-center" data-value="${c.value}" style="background-color: ${background}">
                <div class="card-body d-flex align-items-center justify-content-center" style="padding: 10px;">
                    <h5 class="card-title mb-0" style="color: ${c.color}">${c.name}</h5>
                </div>
            </div>
        </div>`;
    });

    html_tiles += `</div>`;

    let d = new frappe.ui.Dialog({
        title: "Switch Company",
        fields: [
            {
                fieldtype: "HTML",
                fieldname: "company_tiles",
                options: `
                <div style="max-height:60vh; overflow-y:auto; overflow-x:hidden; padding-right:5px;">
                    ${html_tiles}
                </div>`
            }
        ],
        primary_action_label: "Close",
        primary_action: () => d.hide()
    });

    d.show();

    // Styling tile
    d.$wrapper.find(".company-tile").css({
        cursor: "pointer",
        borderRadius: "12px",
        transition: "0.2s",
        boxShadow: "0 2px 6px rgba(0,0,0,0.1)",
        minHeight: "130px",
        marginBottom: "20px"
    }).hover(
        function () {
            $(this).css({
                transform: "translateY(-2px)",
                boxShadow: "0 4px 12px rgba(0,0,0,0.15)"
            });
        },
        function () {
            $(this).css({
                transform: "",
                boxShadow: "0 2px 6px rgba(0,0,0,0.1)"
            });
        }
    );

    // Event click
    d.$wrapper.find(".company-tile").on("click", function () {
        let value = $(this).data("value");
        frappe.msgprint("Switching to company: <b>" + value + "</b>");
        frappe.call({
          method: "erpnext.controllers.erp.switch_company",
          args: { company: value },
          callback: function(res) {
              if (res.message) {
                  frappe.show_alert({ message: "Switched to " + value, indicator: "green" });
                  d.hide();
                  // Optional: reload page supaya context ganti
                  hard_reload()
              }
          }
      });
});
};

function hard_reload(){
  frappe.ui.toolbar.clear_cache();
}

custom.listen_tab_change = async function () {
    try {
        let value = await frappe.xcall("erpnext.startup.boot.get_company_selected");
        if (!value || value === "Disabled" || value === "ALL") return;
        let cur_company = document.querySelector(".current-company")?.getAttribute("value");

        if (value !== cur_company) {
            frappe.msgprint(`Switching to company: <b>${value}</b>`);
            // Hard reload (bypass cache)
            hard_reload()
        }
    } catch (e) {
        console.error("Failed to check company:", e);
    }
};


window.addEventListener("focus", () => {
  custom.listen_tab_change()
});

frappe.show_switcher_company = function(){
  if (frappe.boot.sysdefaults.company_selected=="Disabled"){
    frappe.msgprint("Company switching disabled")
  }else{
    frappe.call({
        method: "erpnext.controllers.erp.get_company_availabe",
        callback: function (r) {
            if (!r.message || r.message.length === 0) {
                frappe.msgprint("No companies available.");
                return;
            }
  
            custom.show_company_switcher(r.message)
        }
      })
  }
}