frappe.pages['unity'].on_page_load = function(wrapper) {
	var parent = $('<div class="unity"></div>').appendTo(wrapper);

  var url = "Build/forweb.framework.js";
  var framework = document.createElement("script");
  framework.src = url;

  var loaderUrl = "Build/forweb.loader.js";
  var script = document.createElement("script");
  script.src = loaderUrl;
  script.onload = () => {
    // code for instantiating the build
	  parent.html(frappe.render_template("unity", {}));
    
    if (/iPhone|iPad|iPod|Android/i.test(navigator.userAgent)) {
      // Mobile device style: fill the whole browser client area with the game canvas:
      var meta = document.createElement('meta');
      meta.name = 'viewport';
      meta.content = 'width=device-width, height=device-height, initial-scale=1.0, user-scalable=no, shrink-to-fit=yes';
      document.getElementsByTagName('head')[0].appendChild(meta);

      var canvas = document.querySelector("#unity-canvas");
      canvas.style.width = "100%";
      canvas.style.height = "100%";
      canvas.style.position = "fixed";

      document.body.style.textAlign = "left";
    }
    
    createUnityInstance(document.querySelector("#unity-canvas"), {
      dataUrl: "{{ url_for('static', filename='Build/forweb.data') }}",
      frameworkUrl: "{{ url_for('static', filename='Build/forweb.framework.js') }}",
      codeUrl: "{{ url_for('static', filename='Build/forweb.wasm') }}",
      streamingAssetsUrl: "StreamingAssets",
      companyName: "DefaultCompany",
      productName: "forfrappe",
      productVersion: "0.1",
      // matchWebGLToCanvasSize: false, // Uncomment this to separately control WebGL canvas render size and DOM element size.
      // devicePixelRatio: 1, // Uncomment this to override low DPI rendering on high DPI displays.
    });
  };
  
  document.head.appendChild(script);
  document.head.appendChild(framework);
}
