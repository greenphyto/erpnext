console.log("COMP 123");

function load_view(){
// Hindari duplicate kalau reload
  if (document.querySelector(".company-switcher")) return;


  // Ambil default company user dari frappe.defaults
  let current_company = frappe.defaults.get_default("company") || "No Company";

  // Buat elemen wrapper
  let div = document.createElement("div");
  div.className = "company-switcher";
  div.innerHTML = `
    <span><div class="company-indicator" title="Greenphyto Tech Sdn Bhd"></div></span>
    <span class="value">${current_company}</span>
  `;

  // Tambah ke body (atau tepat di bawah header)
  document.body.appendChild(div);

  // Tambah style
  const style = document.createElement("style");
  style.innerHTML = `
    .page-head-content{
        margin-top: 17px;
    }
    .company-switcher {
        position: fixed;
        top: 60px;
        right: 130px;
        background: #dcffdc;
        border: 1px solid #d1d8dd;
        border-radius: 0px 0px 6px 6px;
        padding: 3px 12px;
        font-size: 12px;
        font-weight: 500;
        color: #36414c;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
        z-index: 1030;
    }
    .company-indicator {
        width: 5px;
        height: 6px;
        margin-right: 6px;
        margin-top: 5.5px;
        background-color: #366f0eff;
        border-radius: 50%;
    }
    @media (max-width: 576px) {
        .company-switcher {
            right: 18px;
        }
    }
    .company-switcher .value {
      color: #366f0eff;
    }
  `;
  document.head.appendChild(style);
}

load_view();