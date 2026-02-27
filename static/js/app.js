/* SentezCopy - single page cart + upload */
const $ = (q) => document.querySelector(q);
const $$ = (q) => Array.from(document.querySelectorAll(q));

const state = {
  // admin-editable price rules. Loaded from /api/public/price_rules
  price_rules: {},
  size_factor: { A3: 2.0, A4: 1.0, A5: 0.75 },

  // public config
  config: { shipping_enabled: true, free_shipping_limit: 500, shipping_fee: 80, whatsapp_number: "", bank_recipient_name: "", bank_iban: "" },

  cart: [],
  selectedUpload: null,
  opts: { paper: "A4", color: "bw", duplex: "single", binding: "none", paper_type: "80_1hamur", pages: 1, copies: 1, nup: 1 },
  invType: "individual"
};

function fmtTRY(v){
  const n = Number(v) || 0;
  return "₺" + n.toFixed(2).replace(".", ",");
}

async function uploadFiles(fileList){
  const fd = new FormData();
  Array.from(fileList).forEach(f=> fd.append("files", f));
  const r = await fetch("/api/upload", { method:"POST", body: fd });
  const j = await r.json();
  if(!j.ok) throw new Error(j.error || "Yükleme başarısız");
  return j.files || [];
}


function updateCalcUI(){
  const pageUnitEl = $("#pageUnit");
  const fileFeeEl = $("#fileFee");
  const calcTotalEl = $("#calcTotal");

  const { unit, fee } = calcFileFee(state.opts);
  pageUnitEl && (pageUnitEl.value = fmtTRY(unit));
  fileFeeEl && (fileFeeEl.value = fmtTRY(fee));
  calcTotalEl && (calcTotalEl.textContent = fmtTRY(fee));

  // Enable add button only when file is selected
  const addBtn = $("#addToCart");
  if(addBtn) addBtn.disabled = !state.selectedUpload;

  renderCartPreview();
}


function unitPrice(opts){
  const paper = String(opts.paper||"A4").toUpperCase();
  const color = String(opts.color||"bw");
  const pt = String(opts.paper_type||"80_1hamur");

  const rule = state.price_rules?.[pt];

  // Prefer explicit per-size prices (new admin panel)
  const key = `${color === 'color' ? 'color' : 'bw'}_${paper.toLowerCase()}`; // e.g. bw_a4
  const explicit = Number(rule?.[key] ?? 0);
  if(explicit > 0) return explicit;

  // Backward compatibility: old DB had only A4 + size factor
  const baseA4 = color === "color" ? Number(rule?.color_a4||0) : Number(rule?.bw_a4||0);
  const sizeFactor = Number(state.size_factor?.[paper] ?? 1.0);

  // fallback: if rules not loaded yet
  const fallbackBase = color === "color" ? 0.9 : 0.5;
  return (baseA4 || fallbackBase) * sizeFactor;
}

function calcFileFee(opts){
  const pages = Math.max(1, Number(opts.pages||1));
  const copies = Math.max(1, Number(opts.copies||1));
  const duplex = String(opts.duplex||"single");
  const nup = Math.max(1, Number(opts.nup||1));
  // Yaprak mantığı: tek yüz kapasite = nup, çift yüz kapasite = nup*2
  const cap = duplex === "double" ? (nup * 2) : nup;
  const billable = Math.ceil(pages / cap);

  const unit = unitPrice(opts);
  const fee = billable * unit * copies;
  return { unit, fee, billable, pages, copies };
}

function lineTotal(item){
  return calcFileFee(item).fee;
}


function calcTotals(){
  const subtotal = state.cart.reduce((s,it)=> s + lineTotal(it), 0);
  let shipping = 0;
  if(state.config.shipping_enabled){
    shipping = subtotal >= Number(state.config.free_shipping_limit||0) ? 0 : Number(state.config.shipping_fee||0);
  }
  const grand = subtotal + shipping;
  return { subtotal, shipping, grand };
}

function setStatus(t){ const el=$("#status"); if(el) el.textContent=t||""; }

function updateTop(){
  const count = state.cart.length;
  const cc = $("#cartCount");
  if(cc) cc.textContent = String(count);
}

function renderCart(){
  updateTop();
  const cartEl = $("#cart");
  const checkout = $("#checkout");
  const clearBtn = $("#clearCart");
  if(!cartEl) return;

  if(!state.cart.length){
    cartEl.classList.add("empty");
    cartEl.innerHTML = `
      <div class="empty-ico">🧾</div>
      <div class="empty-title">Sepet boş</div>
      <div class="empty-sub">Dosya eklemek için soldan yükle.</div>
    `;
    if(checkout) checkout.disabled = true;
    if(clearBtn) clearBtn.disabled = true;
  } else {
    cartEl.classList.remove("empty");
    cartEl.innerHTML = state.cart.map((it, idx) => {
      const paper = (it.paper||"A4").toUpperCase();
      const nup = Math.max(1, Number(it.nup||1));
      const nupLabel = `1x${nup}`;
      const duplexIcon = it.duplex === "double" ? "⇅" : "⇵";
      const colorBoxStyle = it.color === "color"
        ? 'background: linear-gradient(90deg,#ff0000 0%,#ff9900 18%,#ffee00 36%,#00c853 54%,#00b0ff 72%,#7c4dff 100%);'
        : 'background: linear-gradient(90deg,#000 0%,#fff 100%);';
      return `
        <div class="cartrow">
          <div class="fname">${escapeHtml(it.filename)}</div>
          <div class="rbadges">
            <span class="badge">${paper}</span>
            <span class="badge" title="Kağıt başına sayfa">${nupLabel}</span>
            <span class="badge icon" title="Tek/Çift">${duplexIcon}</span>
            <span class="badge colorbox" title="Renk" style="${colorBoxStyle}"></span>
            <span class="badge price">${fmtTRY(lineTotal(it))}</span>
            <button class="delbtn" data-del="${idx}" aria-label="Sil">🗑</button>
          </div>
        </div>
      `;
    }).join("");

    cartEl.querySelectorAll("[data-del]").forEach(btn=>{
      btn.addEventListener("click", ()=>{
        const idx = Number(btn.dataset.del);
        if(Number.isFinite(idx)) state.cart.splice(idx,1);
        renderCart();
        renderTotals();
      });
    });

    if(checkout) checkout.disabled = false;
    if(clearBtn) clearBtn.disabled = false;
  }

  renderTotals();
}

function _nupGrid(nup){
  const v = Math.max(1, Number(nup||1));
  if(v === 2) return { cols: 1, rows: 2 };
  if(v === 4) return { cols: 2, rows: 2 };
  if(v === 6) return { cols: 2, rows: 3 };
  return { cols: 1, rows: 1 };
}

function renderCartPreview(){
  const box = $("#cartPreview");
  if(!box) return;

  // Preview only when a file is selected OR when cart has items
  if(!state.selectedUpload && !state.cart.length){
    box.innerHTML = "";
    return;
  }

  const nup = Math.max(1, Number(state.opts.nup||1));
  const duplex = String(state.opts.duplex||"single");
  const g = _nupGrid(nup);

  const mkSheet = (startNo)=>{
    const cells = [];
    for(let i=0;i<nup;i++) cells.push(`<div class="cell">${startNo+i}</div>`);
    const style = `grid-template-columns: repeat(${g.cols}, 1fr); grid-template-rows: repeat(${g.rows}, 1fr);`;
    return `<div class="sheet" style="${style}">${cells.join("")}</div>`;
  };

  const front = `<div class="pvcard"><div class="pvtitle">Ön Yüz</div>${mkSheet(1)}</div>`;
  const back = duplex === "double"
    ? `<div class="pvcard"><div class="pvtitle">Arka Yüz</div>${mkSheet(nup+1)}</div>`
    : "";

  box.innerHTML = `
    <div class="pvh">Önizleme</div>
    <div class="pvgrid" style="grid-template-columns:${duplex==="double"?"1fr 1fr":"1fr"};">
      ${front}
      ${back}
    </div>
    <div class="pvnote">↻ <span>Kağıt başına sayfa: <b>1x${nup}</b></span></div>
  `;
}

function renderTotals(){
  const {subtotal, shipping, grand} = calcTotals();
  const set = (id, val) => { const el = $(id); if(el) el.textContent = fmtTRY(val); };
  set("#subtotal", subtotal);
  set("#shipping", shipping);
  set("#grand", grand);
  set("#mSub", subtotal);
  set("#mShip", shipping);
  set("#mGrand", grand);
}

function escapeHtml(s){
  return String(s||"").replace(/[&<>"']/g, (m)=>({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;" }[m]));
}

async function loadPublic(){
  try{
    const rr = await fetch("/api/public/price_rules");
    const j = await rr.json();
    state.price_rules = j.rules || {};
    state.size_factor = j.size_factor || state.size_factor;
  }catch(_){}

  try{
    const cr = await fetch("/api/public/config");
    state.config = await cr.json();
  }catch(_){}

  renderPriceTable();

  const shipInfo = $("#shipInfo");
  if(shipInfo){
    if(!state.config.shipping_enabled){
      shipInfo.textContent = "Kargo kapalı.";
    }else{
      shipInfo.textContent = `₺${Number(state.config.free_shipping_limit||0).toFixed(0)} üzeri kargo ücretsiz, altı ₺${Number(state.config.shipping_fee||0).toFixed(0)}.`;
    }
  }
}

function wireQuickCalc(){
  const form = $("#quickCalc");
  if(!form) return;

  const pagesEl = $("#qcPages");
  const paperEl = $("#qcPaper");
  const colorEl = $("#qcColor");
  const typeEl = $("#qcPaperType");
  const duplexEl = $("#qcDuplex");
  const copiesEl = $("#qcCopies");
  const out = $("#qcTotal");

  function compute(){
    const pages = Math.max(1, Number(pagesEl?.value || 1));
    const copies = Math.max(1, Number(copiesEl?.value || 1));
    const color = String(colorEl?.value || "bw");
    const paper = String(paperEl?.value || "A4").toUpperCase();
    const paper_type = String(typeEl?.value || "80_1hamur");
    const duplex = String(duplexEl?.value || "single");

    const billable = duplex === "double" ? Math.ceil(pages/2) : pages;
    const total = billable * unitPrice({paper, color, paper_type}) * copies;
    out && (out.textContent = fmtTRY(total));
  }

  form.addEventListener("submit", (e)=>{ e.preventDefault(); compute(); });
  [pagesEl, paperEl, colorEl, typeEl, duplexEl, copiesEl]
    .filter(Boolean)
    .forEach(el=> el.addEventListener("input", ()=>{ compute(); renderPriceTable(); }));

  compute();
  renderPriceTable();
}

function wirePaperSelect(){
  const sel = document.querySelector('#paperSelect');
  if(!sel) return;
  sel.addEventListener('change', ()=>{
    state.opts.paper = String(sel.value || 'A4').toUpperCase();
    updateCalcUI && updateCalcUI();
  });
}

function wireSegButtons(){
  $$(".segbtn").forEach(b=>{
    b.addEventListener("click", ()=>{
      const group = b.closest(".seg") || b.closest(".tile-row") || b.closest(".tile-grid") || b.closest(".mini-row");
      if(group){
        group.querySelectorAll(".segbtn").forEach(x=>x.classList.remove("active"));
        b.classList.add("active");
      }
      if(b.dataset.paper) state.opts.paper = b.dataset.paper;
      if(b.dataset.color) state.opts.color = b.dataset.color;
      if(b.dataset.duplex) state.opts.duplex = b.dataset.duplex;
      if(b.dataset.nup) state.opts.nup = Math.max(1, Number(b.dataset.nup||1));
      // kalite kaldırıldı (tek fiyat mantığı)
      if(b.dataset.ptype) state.opts.paper_type = b.dataset.ptype;
      updateCalcUI && updateCalcUI();
      if(b.dataset.invtype){
        state.invType = b.dataset.invtype;
        $("#invIndividual").hidden = state.invType !== "individual";
        $("#invCorporate").hidden = state.invType !== "corporate";
      }
    });
  });

  const binding = $("#binding");
  if(binding){
    binding.addEventListener("change", ()=>{
      state.opts.binding = binding.value;
      updateCalcUI && updateCalcUI();
    });
  }
}


function wireQty(){
  const copies = $("#copies"), pages = $("#pages");
  const incC=$("#incCopies"), decC=$("#decCopies");

  function sync(){
    if(copies) state.opts.copies = Math.max(1, Number(copies.value||1));
    if(pages) state.opts.pages = Math.max(1, Number(pages.value||1));
    updateCalcUI && updateCalcUI();
  }

  copies && copies.addEventListener("input", sync);
  pages && pages.addEventListener("input", sync);

  incC && incC.addEventListener("click", ()=>{
    if(!copies) return;
    copies.value = String(Math.max(1, Number(copies.value||1) + 1));
    sync();
  });
  decC && decC.addEventListener("click", ()=>{
    if(!copies) return;
    copies.value = String(Math.max(1, Number(copies.value||1) - 1));
    sync();
  });

  sync();
}

function wireUpload(){
  const drop = $("#drop");
  const file = $("#file");
  const addBtn = $("#addToCart");

  if(!drop || !file) return;

  drop.addEventListener("click", (e)=>{ if((e.target && (e.target.id==="resetUpload" || e.target.closest("#resetUpload")))) return; file.click(); });

  function setSelected(uploaded){
    state.selectedUpload = uploaded;
    addBtn.disabled = !uploaded;
    const nameEl = $("#uploadName");
    const titleEl = $("#uploadTitle");
    const resetBtn = $("#resetUpload");
    if(uploaded){
      // auto-fill page count (PDF)
      const pages = Math.max(1, Number(uploaded.pages || 1));
      state.opts.pages = pages;
      const pagesInp = $("#pages");
      if(pagesInp){
        pagesInp.value = String(pages);
        pagesInp.disabled = true;
        pagesInp.readOnly = true;
      }
      nameEl && (nameEl.textContent = uploaded.filename);
      titleEl && (titleEl.textContent = "Yüklendi ✅");
      resetBtn && (resetBtn.disabled = false);
      setStatus(`Yüklendi: ${uploaded.filename}`);
    } else {
      const pagesInp = $("#pages");
      if(pagesInp){
        pagesInp.value = "1";
        pagesInp.disabled = true;
        pagesInp.readOnly = true;
      }
      nameEl && (nameEl.textContent = "");
      titleEl && (titleEl.textContent = "Buraya tıkla, dosyanı seç ve yükle!");
      resetBtn && (resetBtn.disabled = true);
      setStatus("");
    }
    updateCalcUI && updateCalcUI();
  }

  drop.addEventListener("dragover", (e)=>{ e.preventDefault(); drop.classList.add("drag"); });
  drop.addEventListener("dragleave", ()=> drop.classList.remove("drag"));
  drop.addEventListener("drop", async (e)=>{
    e.preventDefault(); drop.classList.remove("drag");
    const files = e.dataTransfer.files;
    if(!files || !files.length) return;
    try{
      const up = await uploadFiles(files);
      setSelected(up[0] || null);
    }catch(err){
      setStatus(String(err.message||err));
      setSelected(null);
    }
  });

  file.addEventListener("change", async ()=>{
    if(!file.files || !file.files.length) return;
    try{
      const up = await uploadFiles(file.files);
      setSelected(up[0] || null);
    }catch(err){
      setStatus(String(err.message||err));
      setSelected(null);
    }finally{
      file.value = "";
    }
  });


const resetBtn = $("#resetUpload");
if(resetBtn){
  resetBtn.disabled = true;
  resetBtn.addEventListener("click", (e)=>{
    e.preventDefault();
    state.selectedUpload = null;
    addBtn.disabled = true;
    state.opts.pages = 1;
    const pagesInp = $("#pages");
    if(pagesInp){
      pagesInp.value = "1";
      pagesInp.disabled = true;
      pagesInp.readOnly = true;
    }
    $("#uploadName") && ($("#uploadName").textContent = "");
    $("#uploadTitle") && ($("#uploadTitle").textContent = "Buraya tıkla, dosyanı seç ve yükle!");
    resetBtn.disabled = true;
    setStatus("");
    updateCalcUI && updateCalcUI();
  });
}

  addBtn.addEventListener("click", ()=>{
    if(!state.selectedUpload) return;
    const it = {
      filename: state.selectedUpload.filename,
      stored_name: state.selectedUpload.stored_name,
      mime: state.selectedUpload.mime,
      paper: state.opts.paper,
      color: state.opts.color,
      duplex: state.opts.duplex,
      binding: state.opts.binding,
      paper_type: state.opts.paper_type,
      pages: state.opts.pages,
      copies: state.opts.copies,
      nup: state.opts.nup
    };
    state.cart.push(it);
    state.selectedUpload = null;
    addBtn.disabled = true;
    setStatus("Sepete eklendi.");
    renderCart();
  });
}

function wireCartButtons(){
  $("#clearCart")?.addEventListener("click", ()=>{
    state.cart = [];
    renderCart();
  });

  $("#checkout")?.addEventListener("click", ()=>{
    // go to /sepet page (hidden from main)
    try{ sessionStorage.setItem("sentez_cart", JSON.stringify(state.cart)); }catch(e){}
    window.location.href = "/sepet";
  });

  $("#cartBtn")?.addEventListener("click", ()=>{
    openCartTopModal();
  });
}

function openCartTopModal(){
  const m = $("#cartTopModal");
  if(!m) return;
  renderCartTop();
  m.hidden = false;
}
function closeCartTopModal(){
  const m = $("#cartTopModal");
  if(m) m.hidden = true;
}

function wireCartTopModal(){
  const modal = $("#cartTopModal");
  if(modal){
    modal.addEventListener("click", (e)=>{
      const t = e.target;
      if(t && t.dataset && t.dataset.close) closeCartTopModal();
    });
  }
  $("#topGoCalc")?.addEventListener("click", ()=>{
    closeCartTopModal();
    document.querySelector("#calc")?.scrollIntoView({behavior:"smooth"});
  });
  $("#topGoCheckout")?.addEventListener("click", ()=>{
    try{ sessionStorage.setItem("sentez_cart", JSON.stringify(state.cart)); }catch(e){}
    window.location.href = "/sepet";
  });
}

function renderCartTop(){
  const list = $("#cartTopList");
  if(!list) return;

  if(!state.cart.length){
    list.classList.add("empty");
    list.innerHTML = `
      <div class="empty-ico">🧾</div>
      <div class="empty-title">Sepet boş</div>
      <div class="empty-sub">Ana sayfadan dosya ekleyebilirsin.</div>
    `;
  }else{
    list.classList.remove("empty");
    list.innerHTML = state.cart.map((it, idx)=>{
      const paper = (it.paper||"A4").toUpperCase();
      const nup = Math.max(1, Number(it.nup||1));
      const nupLabel = `1x${nup}`;
      const duplexIcon = it.duplex === "double" ? "⇅" : "⇵";
      const colorBoxStyle = it.color === "color"
        ? 'background: linear-gradient(90deg,#ff0000 0%,#ff9900 18%,#ffee00 36%,#00c853 54%,#00b0ff 72%,#7c4dff 100%);'
        : 'background: linear-gradient(90deg,#000 0%,#fff 100%);';
      return `
        <div class="cartrow">
          <div class="fname">${escapeHtml(it.filename)}</div>
          <div class="rbadges">
            <span class="badge">${paper}</span>
            <span class="badge" title="Kağıt başına sayfa">${nupLabel}</span>
            <span class="badge icon">${duplexIcon}</span>
            <span class="badge colorbox" style="${colorBoxStyle}"></span>
            <span class="badge price">${fmtTRY(lineTotal(it))}</span>
            <button class="delbtn" data-topdel="${idx}">🗑</button>
          </div>
        </div>
      `;
    }).join("");

    list.querySelectorAll("[data-topdel]").forEach(btn=>{
      btn.addEventListener("click", ()=>{
        const idx = Number(btn.dataset.topdel);
        if(Number.isFinite(idx)) state.cart.splice(idx, 1);
        renderCart();
        renderTotals();
        renderCartTop();
      });
    });
  }

  const t = calcTotals();
  $("#topSub") && ($("#topSub").textContent = fmtTRY(t.subtotal));
  $("#topShip") && ($("#topShip").textContent = fmtTRY(t.shipping));
  $("#topGrand") && ($("#topGrand").textContent = fmtTRY(t.grand));
}

function openModal(){
  const modal = $("#modal");
  if(!modal) return;
  $("#checkoutMsg").textContent = "";
  modal.hidden = false;
  renderTotals();
}

function closeModal(){
  const modal = $("#modal");
  if(!modal) return;
  modal.hidden = true;
}

function wireModal(){
  const modal = $("#modal");
  if(!modal) return;
  modal.addEventListener("click", (e)=>{
    const t = e.target;
    if(t && t.dataset && t.dataset.close) closeModal();
  });

  const invReq = $("#invReq");
  invReq?.addEventListener("change", ()=>{
    $("#invFields").hidden = !invReq.checked;
  });

  $("#confirmOrder")?.addEventListener("click", submitOrder);
}

function renderSepetList(){
  const el = $("#sepetList");
  if(!el) return;
  if(!state.cart.length){
    el.classList.add("empty");
    el.innerHTML = `
      <div class="empty-ico">🧾</div>
      <div class="empty-title">Sepet boş</div>
      <div class="empty-sub">Ana sayfaya dönüp dosya ekleyebilirsin.</div>
    `;
    $("#confirmOrder") && ($("#confirmOrder").disabled = true);
    return;
  }
  el.classList.remove("empty");
  el.innerHTML = state.cart.map((it, idx)=>{
    const paper = (it.paper||"A4").toUpperCase();
    const duplexIcon = it.duplex === "double" ? "⇅" : "⇵";
    const colorBoxStyle = it.color === "color"
      ? 'background: linear-gradient(90deg,#ff0000 0%,#ff9900 18%,#ffee00 36%,#00c853 54%,#00b0ff 72%,#7c4dff 100%);'
      : 'background: linear-gradient(90deg,#000 0%,#fff 100%);';
    return `
      <div class="cartrow">
        <div class="fname">${escapeHtml(it.filename)}</div>
        <div class="rbadges">
          <span class="badge">${paper}</span>
          <span class="badge icon">${duplexIcon}</span>
          <span class="badge colorbox" style="${colorBoxStyle}"></span>
          <span class="badge price">${fmtTRY(lineTotal(it))}</span>
          <button class="delbtn" data-del="${idx}">🗑</button>
        </div>
      </div>
    `;
  }).join("");

  el.querySelectorAll("[data-del]").forEach(btn=>{
    btn.addEventListener("click", ()=>{
      const idx = Number(btn.dataset.del);
      if(Number.isFinite(idx)) state.cart.splice(idx,1);
      renderSepetList();
      renderTotals();
      try{ sessionStorage.setItem("sentez_cart", JSON.stringify(state.cart)); }catch(e){}
    });
  });
  $("#confirmOrder") && ($("#confirmOrder").disabled = false);
}

function wireSepetPage(){
  const root = $("#sepetPage");
  if(!root) return;
  try{
    const raw = sessionStorage.getItem("sentez_cart");
    if(raw) state.cart = JSON.parse(raw) || [];
  }catch(e){}

  renderSepetList();
  renderTotals();

  // invoice toggle
  const invReq = $("#invReq");
  invReq?.addEventListener("change", ()=>{
    $("#invFields").hidden = !invReq.checked;
  });
  root.querySelectorAll("[data-invtype]").forEach(btn=>{
    btn.addEventListener("click", ()=>{
      root.querySelectorAll("[data-invtype]").forEach(b=> b.classList.remove("active"));
      btn.classList.add("active");
      state.invType = btn.dataset.invtype;
      const ind = $("#invIndividual");
      const corp = $("#invCorporate");
      if(ind && corp){
        ind.hidden = state.invType !== "individual";
        corp.hidden = state.invType !== "corporate";
      }
    });
  });

  $("#confirmOrder")?.addEventListener("click", submitOrder);
}

function openTrackModal(){
  const m = $("#trackModal");
  if(m){
    $("#trackMsg") && ($("#trackMsg").innerHTML = "");
    m.hidden = false;
  }
}
function closeTrackModal(){
  const m = $("#trackModal");
  if(m) m.hidden = true;
}
function wireTrack(){
  const btn = $("#trackBtn");
  if(btn) btn.addEventListener("click", openTrackModal);
  const modal = $("#trackModal");
  if(modal){
    modal.addEventListener("click", (e)=>{
      const t = e.target;
      if(t && t.dataset && t.dataset.close) closeTrackModal();
    });
  }
  $("#trackSubmit")?.addEventListener("click", async ()=>{
    const id = $("#tOrderId")?.value.trim();
    const phone = $("#tPhone")?.value.trim();
    const msg = $("#trackMsg");
    if(msg) msg.innerHTML = `<div class="muted">Sorgulanıyor...</div>`;
    try{
      const qs = [];
      if(id) qs.push(`order_code=${encodeURIComponent(id)}`);
      if(phone) qs.push(`phone=${encodeURIComponent(phone)}`);
      const r = await fetch(`/api/order/track?${qs.join("&")}`);
      const j = await r.json();
      if(!j.ok) throw new Error(j.error || "Bulunamadı");
      const statusMap = {
        awaiting_receipt: "Dekont Bekleniyor",
        ready_to_print: "Baskıya Hazır",
        printed: "Basıldı",
        shipped: "Kargolandı",
        completed: "Tamamlandı",
        cancelled: "İptal"
      };

      const orders = j.orders ? j.orders : (j.order ? [j.order] : []);
      if(!orders.length) throw new Error("Sipariş bulunamadı.");

      const cards = orders.map(o=>{
        const st = statusMap[o.status] || o.status || "-";
        const cargo = (o.cargo_company || o.tracking_no)
          ? `<div class="track-meta"><span class="muted">Kargo:</span> <b>${escapeHtml(o.cargo_company||"-")}</b> <span class="muted">Takip:</span> <b>${escapeHtml(o.tracking_no||"-")}</b></div>`
          : "";
        return `
          <div class="track-card">
            <div class="track-head"><span class="track-ok">✓</span> <div>#${escapeHtml(o.order_code||"-")} <span class="muted">Durum:</span> <b>${escapeHtml(st)}</b></div></div>
            <div class="track-meta"><span class="muted">Toplam:</span> <b>${fmtTRY(o.grand_total_try)}</b></div>
            ${cargo}
          </div>
        `;
      }).join("");
      if(msg) msg.innerHTML = cards;
    }catch(err){
      if(msg) msg.innerHTML = `<div class="track-card"><div class="track-warn">Hata:</div><div class="muted" style="margin-top:6px;">${escapeHtml(String(err.message||err))}</div></div>`;
    }
  });
}

function buildWhatsappMessage(orderCode, grand){
  const name = state.config.bank_recipient_name ? `Alıcı: ${state.config.bank_recipient_name}\n` : "";
  const iban = state.config.bank_iban ? `IBAN: ${state.config.bank_iban}\n` : "";
  const txt =
`Merhaba, online sipariş oluşturdum.\n` +
`Sipariş No: #${orderCode}\n` +
`Ödenecek Tutar: ${fmtTRY(grand)}\n\n` +
`${name}${iban}` +
`Dekontu buradan ileteceğim.`;
  return txt;
}

async function submitOrder(){
  const {subtotal, shipping, grand} = calcTotals();
  const payload = {
    items: state.cart,
    customer: {
      name: $("#cName")?.value || "",
      phone: $("#cPhone")?.value || "",
      note: $("#cNote")?.value || ""
    },
    invoice: {
      requested: $("#invReq")?.checked || false,
      type: state.invType,
      tc_no: $("#tcNo")?.value || "",
      tax_no: $("#taxNo")?.value || "",
      tax_office: $("#taxOffice")?.value || "",
      company_title: $("#companyTitle")?.value || "",
      city: $("#invCity")?.value || "",
      district: $("#invDistrict")?.value || "",
      address: $("#invAddress")?.value || ""
    }
  };

  $("#confirmOrder").disabled = true;
  $("#checkoutMsg").textContent = "Kaydediliyor...";
  try{
    const r = await fetch("/api/order/create", { method:"POST", headers:{ "Content-Type":"application/json" }, body: JSON.stringify(payload) });
    const j = await r.json();
    if(!j.ok) throw new Error(j.error || "Sipariş oluşturulamadı");

    const orderCode = j.order.order_code || j.order.id;
    const msg = buildWhatsappMessage(orderCode, j.order.grand_total_try);
    const wa = `https://wa.me/${(state.config.whatsapp_number||"").replace(/\D/g,"")}?text=${encodeURIComponent(msg)}`;
    $("#checkoutMsg").innerHTML = `✅ Sipariş oluşturuldu: <b>#${orderCode}</b><br/>WhatsApp açılıyor...`;

    // clear cart after success
    state.cart = [];
    renderCart();
    renderTotals();

    setTimeout(()=>{ window.open(wa, "_blank"); }, 350);
    setTimeout(()=>{ closeModal(); }, 650);
  }catch(err){
    $("#checkoutMsg").textContent = "Hata: " + String(err.message||err);
  }finally{
    $("#confirmOrder").disabled = false;
  }
}

function initMarquee(){
  const track = $("#workTrack");
  if(!track) return;
  const items = Array.from(track.children);
  // duplicate content inside the same track so it stays single-row
  items.forEach(n => track.appendChild(n.cloneNode(true)));
}

function initReveal(){
  const els = $$(".reveal");
  if(!els.length) return;
  const io = new IntersectionObserver((entries)=>{
    entries.forEach(e=>{
      if(e.isIntersecting){
        e.target.classList.add('in');
        io.unobserve(e.target);
      }
    });
  }, { threshold: 0.12 });
  els.forEach(el=> io.observe(el));
}

function wireSmooth(){
  const btn = $("#reviewBtn");
  if(btn){
    btn.addEventListener('click', (e)=>{
      const target = document.querySelector(btn.getAttribute('href'));
      if(target){
        e.preventDefault();
        target.scrollIntoView({behavior:'smooth', block:'start'});
      }
    });
  }
}



function initHowto(){
  const steps = Array.from(document.querySelectorAll('.howto-step'));
  if(!steps.length) return;

  let idx = 0;
  let timer = null;
  let paused = false;

  function activate(stepEl){
    steps.forEach((el,i)=>{
      const active = el === stepEl;
      el.classList.toggle('is-active', active);
      el.setAttribute('aria-expanded', active ? 'true' : 'false');
      if(active) idx = i;
    });
  }

  function start(){
    if(timer) clearInterval(timer);
    timer = setInterval(()=>{
      if(paused) return;
      const next = steps[(idx + 1) % steps.length];
      activate(next);
    }, 3600);
  }

  steps.forEach(el=>{
    el.addEventListener('click', ()=>{ paused = true; activate(el); });
    el.addEventListener('mouseenter', ()=>{ paused = true; });
    el.addEventListener('mouseleave', ()=>{ paused = false; });
    el.addEventListener('focus', ()=>{ paused = true; });
    el.addEventListener('blur', ()=>{ paused = false; });
  });

  // keyboard navigation
  steps.forEach(el=>{
    el.addEventListener('keydown', (e)=>{
      const i = steps.indexOf(el);
      if(e.key === 'Enter' || e.key === ' '){
        e.preventDefault();
        paused = true;
        activate(el);
      }
      if(e.key === 'ArrowRight' || e.key === 'ArrowDown'){
        e.preventDefault();
        paused = true;
        const next = steps[(i + 1) % steps.length];
        next.focus();
        activate(next);
      }
      if(e.key === 'ArrowLeft' || e.key === 'ArrowUp'){
        e.preventDefault();
        paused = true;
        const prev = steps[(i - 1 + steps.length) % steps.length];
        prev.focus();
        activate(prev);
      }
    });
  });

  // initial
  activate(steps[0]);
  start();

  // resume auto after user interaction (gentle)
  document.addEventListener('click', (e)=>{
    if(e.target.closest('.howto')){
      // stay paused
      return;
    }
    paused = false;
  });
}

function renderPriceTable(){
  const tb = document.querySelector('#priceTable tbody');
  if(!tb) return;
  const rules = state.price_rules || {};

  const sel = (document.querySelector('#qcPaper')?.value || 'A4').toUpperCase();
  const titleEl = document.querySelector('#priceListSize');
  if(titleEl) titleEl.textContent = sel;

  const rows = Object.keys(rules).map(k=>{
    const r = rules[k];
    const label = r?.label || k;
    const bw = fmtTRY(Number(r?.[`bw_${sel.toLowerCase()}`] ?? r?.bw_a4 ?? 0));
    const col = fmtTRY(Number(r?.[`color_${sel.toLowerCase()}`] ?? r?.color_a4 ?? 0));
    return `<tr><td>${label}</td><td>${bw}</td><td>${col}</td></tr>`;
  }).join('');
  tb.innerHTML = rows || '<tr><td colspan="3" class="muted">Fiyatlar yüklenemedi</td></tr>';
}

function wirePriceDrawer(){
  const fab = $('#priceFab');
  const dr = $('#priceDrawer');
  const close = $('#priceClose');
  if(!fab || !dr || !close) return;

  function open(){
    dr.hidden = false;
    dr.setAttribute('aria-hidden','false');
    // small focus assist
    setTimeout(()=>{ $('#qcPages')?.focus(); }, 50);
  }
  function shut(){
    dr.hidden = true;
    dr.setAttribute('aria-hidden','true');
  }

  fab.addEventListener('click', open);
  close.addEventListener('click', shut);
  document.addEventListener('keydown', (e)=>{
    if(e.key === 'Escape' && !dr.hidden) shut();
  });
}

function init(){
  $("#year") && ($("#year").textContent = String(new Date().getFullYear()));
  loadPublic();
  wireSegButtons();
  wirePaperSelect();
  wireQty();
  wireUpload();
  wireCartButtons();
  wireModal();
  wireSepetPage();
  wireTrack();
  wireCartTopModal();
  wireQuickCalc();
  wirePriceDrawer();
  initMarquee();
  initReveal();
  initHowto();
  wireSmooth();
  updateCalcUI();
  renderCart();
  renderTotals();
}

document.addEventListener("DOMContentLoaded", init);
