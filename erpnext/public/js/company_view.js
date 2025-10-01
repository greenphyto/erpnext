console.log("COMP 123");

function load_view(){
// Hindari duplicate kalau reload
  if (document.querySelector(".company-switcher")) return;


  // Ambil default company user dari frappe.defaults
  let current_company = frappe.defaults.get_default("company_selected") || "No Selected"
  let company_color = frappe.defaults.get_default("company_color") || "#1F272E"

  // Buat elemen wrapper
  let div = document.createElement("div");
  div.className = "company-switcher";
  div.innerHTML = `
    <span><div class="company-indicator" title="${current_company}"></div></span>
    <span class="value">${current_company}</span>
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