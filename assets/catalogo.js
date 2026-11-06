(function () {
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function norm(s) {
    return String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  }

  function init() {
    var root = document.getElementById("catalogo");
    if (!root || root.dataset.pronto) return;
    root.dataset.pronto = "1";

    var base = new URL("../assets/catalogo.json", location.href);
    fetch(base)
      .then(function (r) { return r.json(); })
      .then(function (dados) { montar(root, dados); })
      .catch(function () { root.textContent = "Não foi possível carregar o catálogo."; });
  }

  function montar(root, dados) {
    var campos = [
      ["pais", "País"],
      ["programa", "Programa"],
      ["tipo", "Tipo de documento"],
      ["idioma", "Idioma"],
      ["ano", "Ano"],
    ];
    var estado = { q: "" };
    campos.forEach(function (c) { estado[c[0]] = ""; });

    root.innerHTML =
      '<div class="cat-filtros"></div><p class="cat-contagem"></p><ul class="cat-lista"></ul>';
    var caixa = root.querySelector(".cat-filtros");

    var busca = document.createElement("input");
    busca.type = "search";
    busca.placeholder = "Buscar por título, autor ou palavra-chave";
    busca.addEventListener("input", function () { estado.q = busca.value; render(); });
    caixa.appendChild(busca);

    campos.forEach(function (c) {
      var valores = Array.from(new Set(dados.map(function (d) { return d[c[0]]; }).filter(Boolean)));
      valores.sort(function (a, b) { return c[0] === "ano" ? b.localeCompare(a) : a.localeCompare(b); });
      var sel = document.createElement("select");
      sel.innerHTML = '<option value="">' + c[1] + " (todos)</option>" +
        valores.map(function (v) { return '<option value="' + esc(v) + '">' + esc(v) + "</option>"; }).join("");
      sel.addEventListener("change", function () { estado[c[0]] = sel.value; render(); });
      caixa.appendChild(sel);
    });

    function render() {
      var q = norm(estado.q);
      var res = dados.filter(function (d) {
        if (campos.some(function (c) { return estado[c[0]] && d[c[0]] !== estado[c[0]]; })) return false;
        if (!q) return true;
        var texto = norm([d.titulo, d.autores, (d.palavras || []).join(" ")].join(" "));
        return q.split(/\s+/).every(function (t) { return texto.indexOf(t) !== -1; });
      });
      res.sort(function (a, b) { return (b.ano || "0").localeCompare(a.ano || "0"); });
      root.querySelector(".cat-contagem").textContent = res.length + " de " + dados.length + " documento(s)";
      var pagina = new URL("../documentos/", location.href);
      root.querySelector(".cat-lista").innerHTML = res.length ? res.map(function (d) {
        var meta = [d.ano, d.pais, d.programa, d.tipo, d.idioma, d.fonte].filter(Boolean).map(esc).join(" · ");
        return '<li><a href="' + pagina + esc(d.id) + '/">' + esc(d.titulo) + "</a>" +
          (d.autores ? '<div class="cat-autores">' + esc(d.autores) + "</div>" : "") +
          '<div class="cat-meta">' + meta + "</div>" +
          (d.link ? '<a class="cat-fonte" href="' + esc(d.link) + '" target="_blank" rel="noopener">Fonte original ↗</a>' : "") +
          "</li>";
      }).join("") : '<li class="cat-vazio">Nenhum documento corresponde aos filtros selecionados.</li>';
    }
    render();
  }

  if (typeof document$ !== "undefined") document$.subscribe(init);
  else document.addEventListener("DOMContentLoaded", init);
})();
