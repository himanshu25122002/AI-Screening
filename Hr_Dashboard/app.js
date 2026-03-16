const API_BASE = window.ENV.API_BASE;

const state = {
  route: "hr",
  cache: {
    vacancies: null,
    candidates: null,
    forms: null,
    interviewsIndex: null,
  },
  globalSearch: "",
  tables: new Map(), // id -> tableState
};

const $ = (sel, root=document) => root.querySelector(sel);
const $$ = (sel, root=document) => Array.from(root.querySelectorAll(sel));

function escapeHtml(str){
  return String(str ?? "")
    .replaceAll("&","&amp;")
    .replaceAll("<","&lt;")
    .replaceAll(">","&gt;")
    .replaceAll('"',"&quot;")
    .replaceAll("'","&#039;");
}

function fmtDate(v){
  if(!v) return "";
  const d = new Date(v);
  if(Number.isNaN(d.getTime())) return String(v);
  return d.toLocaleString(undefined, {year:"numeric", month:"short", day:"2-digit", hour:"2-digit", minute:"2-digit"});
}
function fmtNumber(v){
  if(v === null || v === undefined || v === "") return "";
  const n = Number(v);
  if(Number.isNaN(n)) return String(v);
  return new Intl.NumberFormat().format(n);
}
function pick(obj, keys){
  for(const k of keys){
    if(obj && obj[k] !== undefined && obj[k] !== null) return obj[k];
  }
  return undefined;
}

function toast(type, title, msg, timeout=3200){
  const wrap = $("#toastWrap");
  const el = document.createElement("div");
  el.className = `toast ${type || ""}`;
  el.innerHTML = `
    <div class="toastIcon" aria-hidden="true">${type==="good"?"✓":type==="bad"?"!":type==="warn"?"⚑":"i"}</div>
    <div class="toastText">
      <div class="toastTitle">${escapeHtml(title || "Notice")}</div>
      <div class="toastMsg">${escapeHtml(msg || "")}</div>
    </div>
    <button class="toastClose" aria-label="Close">×</button>
  `;
  wrap.appendChild(el);
  const close = () => el.remove();
  $(".toastClose", el).addEventListener("click", close);
  window.setTimeout(close, timeout);
}

async function apiFetch(path, options={}){
  const url = `${API_BASE}${path}`;
  const opts = { ...options };
  opts.headers = opts.headers || {};
  if(!(opts.body instanceof FormData) && opts.body && !opts.headers["Content-Type"]){
    opts.headers["Content-Type"] = "application/json";
  }
  try{
    const res = await fetch(url, opts);
    const ct = res.headers.get("content-type") || "";
    let data = null;
    if(ct.includes("application/json")){
      data = await res.json().catch(()=>null);
    }else{
      data = await res.text().catch(()=>null);
    }
    if(!res.ok){
      const detail = (data && (data.detail || data.message)) ? (data.detail || data.message) : `HTTP ${res.status}`;
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    return data;
  }catch(err){
    throw err;
  }
}

function setHeader(title, subtitle){
  $("#pageTitle").textContent = title;
  $("#pageSubtitle").textContent = subtitle;
}

function setRoute(route){
  state.route = route;
  $$(".navItem").forEach(b => b.classList.toggle("active", b.dataset.route === route));
  if(route === "hr"){
    setHeader("HR Intake", "Create roles, define evaluation criteria, and ingest resumes.");
    renderHRIntake();
  }else if(route === "pipeline"){
    setHeader("Hiring Pipeline", "Track candidates, send forms, and manage interview links.");
    renderPipeline();
  }else if(route === "forms"){
    setHeader("Candidate Forms", "Review submitted forms with filters and quick access links.");
    renderCandidateForms();
  }else if(route === "interviews"){
    setHeader("AI Interviews", "View interview outcomes and inspect question-by-question transcripts.");
    renderAIInterviews();
  }
}

function skeletonCard(lines=6){
  return `
    <div class="card">
      <div class="cardHeader">
        <div>
          <div class="skeleton" style="width: 180px; height: 16px;"></div>
          <div class="skeleton" style="width: 320px; height: 12px; margin-top:10px; opacity:.8"></div>
        </div>
        <div class="skeleton" style="width: 90px; height: 36px; border-radius: 14px;"></div>
      </div>
      <div class="cardBody">
        <div class="skelRow">
          <div class="skeleton skelBlock"></div>
          <div class="skeleton skelBlock"></div>
          <div class="skeleton skelBlock"></div>
        </div>
        <div style="margin-top:12px"></div>
        ${Array.from({length:lines}).map(()=>`<div class="skeleton" style="height: 12px; margin-top:10px; width:${Math.max(55, Math.random()*90)}%"></div>`).join("")}
      </div>
    </div>
  `;
}

function tableSkeleton(){
  return `
    <div class="tableWrap">
      <div class="tableTools">
        <div class="toolsLeft">
          <div class="skeleton" style="width: 220px; height: 34px; border-radius: 999px"></div>
          <div class="skeleton" style="width: 220px; height: 34px; border-radius: 999px; opacity:.8"></div>
        </div>
        <div class="toolsRight">
          <div class="skeleton" style="width: 120px; height: 34px; border-radius: 14px"></div>
        </div>
      </div>
      <div style="padding:12px">
        ${Array.from({length:8}).map(()=>`<div class="skeleton" style="height:12px; margin: 12px 0; width:${60+Math.random()*35}%"></div>`).join("")}
      </div>
      <div class="pagination">
        <div class="skeleton" style="width:160px; height: 30px; border-radius: 999px"></div>
        <div class="skeleton" style="width:220px; height: 30px; border-radius: 999px"></div>
      </div>
    </div>
  `;
}

function makeTableState(id){
  if(!state.tables.has(id)){
    state.tables.set(id, {
      id,
      q: "",
      sortKey: null,
      sortDir: "asc",
      page: 1,
      pageSize: 10,
      filterJobId: "",
      filterJobName: "",
    });
  }
  return state.tables.get(id);
}

function normalizeStr(v){
  return String(v ?? "").toLowerCase().trim();
}

function applyGlobalSearch(q){
  state.globalSearch = normalizeStr(q);
  // re-render current route without refetch
  if(state.route === "hr") renderHRIntake(true);
  if(state.route === "pipeline") renderPipeline(true);
  if(state.route === "forms") renderCandidateForms(true);
  if(state.route === "interviews") renderAIInterviews(true);
}

function buildTable({id, columns, rows, rowKeyFn, tools, emptyText="No records found."}){
  const ts = makeTableState(id);

  const localQ = normalizeStr(ts.q);
  const globalQ = state.globalSearch;

  let filtered = rows.slice();

  // tool filters can be implemented via tools callback already, but keep general search here:
  const q = globalQ || localQ;
  if(q){
    filtered = filtered.filter(r => {
      const joined = columns.map(c => {
        const v = (typeof c.value === "function") ? c.value(r) : r[c.key];
        return String(v ?? "");
      }).join(" • ").toLowerCase();
      return joined.includes(q);
    });
  }

  // sorting
  if(ts.sortKey){
    const col = columns.find(c => c.key === ts.sortKey);
    const getter = col ? (r => (typeof col.value === "function" ? col.value(r) : r[col.key])) : (r => r[ts.sortKey]);
    filtered.sort((a,b)=>{
      const av = getter(a);
      const bv = getter(b);
      const an = Number(av), bn = Number(bv);
      let cmp;
      if(!Number.isNaN(an) && !Number.isNaN(bn)){
        cmp = an - bn;
      }else{
        cmp = String(av ?? "").localeCompare(String(bv ?? ""), undefined, {numeric:true, sensitivity:"base"});
      }
      return ts.sortDir === "asc" ? cmp : -cmp;
    });
  }

  const total = filtered.length;
  const pages = Math.max(1, Math.ceil(total / ts.pageSize));
  ts.page = Math.min(ts.page, pages);
  const start = (ts.page - 1) * ts.pageSize;
  const pageRows = filtered.slice(start, start + ts.pageSize);

  const thead = `
    <thead>
      <tr>
        ${columns.map(c=>{
          const active = ts.sortKey === c.key;
          const icon = active ? (ts.sortDir === "asc" ? "▲" : "▼") : "↕";
          return `<th data-key="${escapeHtml(c.key)}" title="Sort">
            ${escapeHtml(c.label)} <span class="sort">${icon}</span>
          </th>`;
        }).join("")}
      </tr>
    </thead>
  `;

  const tbody = pageRows.length ? `
    <tbody>
      ${pageRows.map(r=>{
        const rk = rowKeyFn ? rowKeyFn(r) : (r.id ?? JSON.stringify(r).slice(0,32));
        return `<tr data-rowkey="${escapeHtml(rk)}">
          ${columns.map(c=>{
            if(typeof c.render === "function"){
              return `<td>${c.render(r)}</td>`;
            }
            const v = typeof c.value === "function" ? c.value(r) : r[c.key];
            return `<td>${escapeHtml(v ?? "")}</td>`;
          }).join("")}
        </tr>`;
      }).join("")}
    </tbody>
  ` : `<tbody><tr><td colspan="${columns.length}" class="muted">${escapeHtml(emptyText)}</td></tr></tbody>`;

  const html = `
    <div class="tableWrap" data-table="${escapeHtml(id)}">
      <div class="tableTools">
        <div class="toolsLeft">
          ${tools?.left || ""}
        </div>
        <div class="toolsRight">
          ${tools?.right || ""}
        </div>
      </div>
      <div style="overflow:auto">
        <table>
          ${thead}
          ${tbody}
        </table>
      </div>
      <div class="pagination">
        <div class="pageInfo">${escapeHtml(total)} records • Page ${escapeHtml(ts.page)} / ${escapeHtml(pages)}</div>
        <div class="pager">
          <select class="input" style="width:140px; padding:8px 10px; border-radius:12px" data-role="pagesize">
            ${[10,20,50,100].map(n=>`<option value="${n}" ${ts.pageSize===n?"selected":""}>${n}/page</option>`).join("")}
          </select>
          <button class="pageBtn" data-role="prev" ${ts.page<=1?"disabled":""}>Prev</button>
          <button class="pageBtn" data-role="next" ${ts.page>=pages?"disabled":""}>Next</button>
        </div>
      </div>
    </div>
  `;

  return { html, bind(root){
    const wrap = $(`[data-table="${CSS.escape(id)}"]`, root);
    if(!wrap) return;

    $$("th[data-key]", wrap).forEach(th=>{
      th.addEventListener("click", ()=>{
        const key = th.dataset.key;
        if(ts.sortKey === key){
          ts.sortDir = ts.sortDir === "asc" ? "desc" : "asc";
        }else{
          ts.sortKey = key;
          ts.sortDir = "asc";
        }
        rerenderRouteNoFetch();
      });
    });

    const ps = $('[data-role="pagesize"]', wrap);
    ps?.addEventListener("change", ()=>{
      ts.pageSize = Number(ps.value) || 10;
      ts.page = 1;
      rerenderRouteNoFetch();
    });

    $('[data-role="prev"]', wrap)?.addEventListener("click", ()=>{
      ts.page = Math.max(1, ts.page - 1);
      rerenderRouteNoFetch();
    });
    $('[data-role="next"]', wrap)?.addEventListener("click", ()=>{
      ts.page = ts.page + 1;
      rerenderRouteNoFetch();
    });
  }};
}

function rerenderRouteNoFetch(){
  if(state.route === "hr") renderHRIntake(true);
  if(state.route === "pipeline") renderPipeline(true);
  if(state.route === "forms") renderCandidateForms(true);
  if(state.route === "interviews") renderAIInterviews(true);
}

function openModal({title, bodyHtml, footerHtml, onBind}){
  $("#modalTitle").textContent = title || "Details";
  $("#modalBody").innerHTML = bodyHtml || "";
  $("#modalFooter").innerHTML = footerHtml || "";
  const overlay = $("#modalOverlay");
  overlay.hidden = false;

  const close = ()=>{
    overlay.hidden = true;
    $("#modalBody").innerHTML = "";
    $("#modalFooter").innerHTML = "";
    document.removeEventListener("keydown", onEsc);
  };
  const onEsc = (e)=>{ if(e.key === "Escape") close(); };

  $("#modalClose").onclick = close;
  overlay.addEventListener("click", (e)=>{ if(e.target === overlay) close(); }, {once:true});
  document.addEventListener("keydown", onEsc);

  if(typeof onBind === "function") onBind({close});
}

function parseMaybeJson(v){
  if(v === null || v === undefined) return v;
  if(typeof v === "object") return v;
  const s = String(v).trim();
  if(!s) return v;
  if((s.startsWith("{") && s.endsWith("}")) || (s.startsWith("[") && s.endsWith("]"))){
    try{ return JSON.parse(s); }catch{ return v; }
  }
  return v;
}

function vacancyDisplayName(v){
  return pick(v, ["job_role","job_name","role","title","external_job_id","id"]) ?? "—";
}

function candidateDisplayName(c){
  return pick(c, ["name","candidate_name","full_name","candidate","first_name"]) ?? "—";
}

function safeUrl(u){
  if(!u) return "";
  const s = String(u).trim();
  return s;
}

/* ------------------ Data loaders ------------------ */

async function loadVacancies(force=false){
  if(state.cache.vacancies && !force) return state.cache.vacancies;
  const data = await apiFetch(`/vacancies`);
  const list = Array.isArray(data) ? data : (data?.data || data?.items || []);
  state.cache.vacancies = list;
  return list;
}

async function loadCandidates(force=false){
  if(state.cache.candidates && !force) return state.cache.candidates;
  const data = await apiFetch(`/candidates`);
  const list = Array.isArray(data) ? data : (data?.data || data?.items || []);
  state.cache.candidates = list;
  return list;
}

async function loadForms(force=false){
  // Endpoint not explicitly listed except status; using /candidate-form/status as "submitted forms"
  if(state.cache.forms && !force) return state.cache.forms;
  const data = await apiFetch(`/candidate-form/status`);
  const list = Array.isArray(data) ? data : (data?.data || data?.items || []);
  state.cache.forms = list;
  return list;
}

/* ------------------ HR Intake ------------------ */

function criteriaRowTemplate(idx, name="", weight=""){
  return `
    <div class="row" data-crit-row="${idx}">
      <div class="field" style="flex: 1 1 320px">
        <label>Criterion name</label>
        <input class="input" type="text" data-crit-name value="${escapeHtml(name)}" placeholder="e.g., Problem solving" />
      </div>
      <div class="field" style="flex: 0 0 220px; min-width: 180px">
        <label>Weight %</label>
        <input class="input" type="number" data-crit-weight value="${escapeHtml(weight)}" placeholder="e.g., 25" min="0" max="100" step="1" />
      </div>
      <div class="field" style="flex: 0 0 160px; min-width: 140px; justify-content:flex-end">
        <label>&nbsp;</label>
        <button class="btn btnDanger btnSmall" data-crit-remove>Remove</button>
      </div>
    </div>
  `;
}

function buildVacancyPayloadFromForm(root){
  const get = (id)=> $(`#${id}`, root)?.value ?? "";

  const payload = {
    external_job_id: get("v_external_job_id"),
    job_role: get("v_job_role"),
    experience_years: Number(get("v_experience_years") || 0),
    experience_level: get("v_experience_years"), 
    budget_min: Number(get("v_budget_min") || 0),
    budget_max: Number(get("v_budget_max") || 0),
    google_calendar_link: get("v_google_calendar_link"),
    resume_cutoff_score: Number(get("v_resume_cutoff_score") || 0),
    interview_cutoff_score: Number(get("v_interview_cutoff_score") || 0),
    interview_duration_minutes: Number(get("v_interview_duration_minutes") || 0),
    interview_custom_prompt: get("v_interview_custom_prompt"),
    job_summary: get("v_job_summary"),
    key_responsibilities: get("v_key_responsibilities")
      .split(",")
      .map(s => s.trim())
      .filter(Boolean),
    required_skills: get("v_required_skills")
      .split(",")
      .map(s => s.trim())
      .filter(Boolean),
    culture_traits: get("v_culture_traits")
      .split(",")
      .map(s => s.trim())
      .filter(Boolean),
    created_by: "HR Dashboard",
  };

  const criteria = {};
  $$('[data-crit-row]', root).forEach(row=>{
    const name = $('[data-crit-name]', row)?.value?.trim();
    const weight = $('[data-crit-weight]', row)?.value;

    if(name){
      criteria[name] = Number(weight || 0);
    }
  });

  // backend field name unknown; keep "interview_evaluation_criteria" as a reasonable key,
  // but do NOT change backend logic. If backend expects another key, it will ignore.
  payload.interview_evaluation_criteria = criteria;

  return payload;
}

async function renderHRIntake(noFetch=false){
  const content = $("#content");
  if(!noFetch){
    content.innerHTML = `
      <div class="grid">
        ${skeletonCard(5)}
        ${skeletonCard(4)}
      </div>
      ${tableSkeleton()}
    `;
  }

  let vacancies = state.cache.vacancies;
  if(!noFetch || !vacancies){
    try{
      vacancies = await loadVacancies(false);
    }catch(err){
      toast("bad","Failed to load jobs", err.message);
      vacancies = vacancies || [];
    }
  }

  const vTableId = "vacanciesTable";
  const ts = makeTableState(vTableId);

  const vacancyOptions = [`<option value="">All jobs</option>`]
    .concat(vacancies.map(v=>{
      const id = pick(v, ["id","vacancy_id","external_job_id"]);
      const label = vacancyDisplayName(v);
      return `<option value="${escapeHtml(String(id ?? ""))}">${escapeHtml(label)}</option>`;
    })).join("");

  const filteredVacancies = vacancies; // table has global search anyway

  const table = buildTable({
    id: vTableId,
    columns: [
      { key: "external_job_id", label: "External ID", value: r => pick(r, ["external_job_id","externalId","external_job"]) ?? "" },
      { key: "job_role", label: "Job Role", value: r => vacancyDisplayName(r) },
      { key: "experience_years", label: "Exp (yrs)", value: r => pick(r, ["experience_years","experience","years"]) ?? "" },
      { key: "budget", label: "Budget", value: r => {
        const mn = pick(r, ["budget_min","min_budget","budgetMin"]);
        const mx = pick(r, ["budget_max","max_budget","budgetMax"]);
        if(mn===undefined && mx===undefined) return "";
        return `${fmtNumber(mn ?? "")} — ${fmtNumber(mx ?? "")}`;
      }},
      { key: "resume_cutoff_score", label: "Resume Cutoff", value: r => pick(r, ["resume_cutoff_score","resume_cutoff"]) ?? "" },
      { key: "interview_cutoff_score", label: "Interview Cutoff", value: r => pick(r, ["interview_cutoff_score","interview_cutoff"]) ?? "" },
      { key: "google_calendar_link", label: "Calendar", render: r => {
        const link = safeUrl(pick(r, ["google_calendar_link","calendar_link","calendar"]));
        if(!link) return `<span class="muted">—</span>`;
        return `<a class="link" href="${escapeHtml(link)}" target="_blank" rel="noreferrer">Open</a>`;
      }},
    ],
    rows: filteredVacancies,
    rowKeyFn: r => pick(r, ["id","external_job_id","vacancy_id"]) ?? vacancyDisplayName(r),
    tools: {
      left: `
        <input class="miniInput" data-role="tableSearch" type="search" placeholder="Search jobs…" value="${escapeHtml(ts.q)}" />
        <span class="badge">Tip: click headers to sort</span>
      `,
      right: `
        <button class="btn btnSmall btnGhost" data-role="reloadVacancies"><span class="btnIcon">↻</span>Reload</button>
      `
    },
    emptyText: "No jobs yet. Create your first vacancy to start the pipeline."
  });

  content.innerHTML = `
    <div class="grid">
      <div class="card">
        <div class="cardHeader">
          <div>
            <div class="cardTitle">Create Job Vacancy</div>
            <div class="cardDesc">Define role details + thresholds. Add interview evaluation criteria with weights.</div>
          </div>
          <div class="chip"><strong>POST</strong> /vacancies</div>
        </div>
        <div class="cardBody">
          <form id="vacancyForm" autocomplete="off">
            <div class="row">
              <div class="field">
                <label>external_job_id</label>
                <input id="v_external_job_id" class="input" type="text" placeholder="e.g., EXT-2026-031" required />
              </div>
              <div class="field">
                <label>job_role</label>
                <input id="v_job_role" class="input" type="text" placeholder="e.g., Frontend Engineer" required />
              </div>
              <div class="field">
                <label>experience_years</label>
                <input id="v_experience_years" class="input" type="number" min="0" step="1" placeholder="e.g., 4" />
              </div>
            </div>

            <div class="row">
              <div class="field">
                <label>budget_min</label>
                <input id="v_budget_min" class="input" type="number" min="0" step="1" placeholder="e.g., 1200000" />
              </div>
              <div class="field">
                <label>budget_max</label>
                <input id="v_budget_max" class="input" type="number" min="0" step="1" placeholder="e.g., 1800000" />
              </div>
              <div class="field">
                <label>google_calendar_link</label>
                <input id="v_google_calendar_link" class="input" type="url" placeholder="https://calendar.google.com/…" />
              </div>
            </div>

            <div class="divider"></div>

            <div class="row">
              <div class="field">
                <label>resume_cutoff_score</label>
                <input id="v_resume_cutoff_score" class="input" type="number" step="0.1" placeholder="e.g., 70" />
              </div>
              <div class="field">
                <label>interview_cutoff_score</label>
                <input id="v_interview_cutoff_score" class="input" type="number" step="0.1" placeholder="e.g., 75" />
              </div>
              <div class="field">
                <label>interview_duration_minutes</label>
                <input id="v_interview_duration_minutes" class="input" type="number" min="0" step="1" placeholder="e.g., 20" />
              </div>
            </div>

            <div class="row">
              <div class="field" style="flex: 1 1 100%">
                <label>interview_custom_prompt</label>
                <textarea id="v_interview_custom_prompt" class="input" placeholder="Optional: tailored instructions for the AI interview…"></textarea>
              </div>
            </div>

            <div class="row">
              <div class="field">
                <label>job_summary</label>
                <textarea id="v_job_summary" class="input" placeholder="A crisp role summary…"></textarea>
              </div>
              <div class="field">
                <label>key_responsibilities</label>
                <textarea id="v_key_responsibilities" class="input" placeholder="Core responsibilities…"></textarea>
              </div>
            </div>

            <div class="row">
              <div class="field">
                <label>required_skills</label>
                <textarea id="v_required_skills" class="input" placeholder="Skills, tools, must-haves…"></textarea>
              </div>
              <div class="field">
                <label>culture_traits</label>
                <textarea id="v_culture_traits" class="input" placeholder="Values and team behaviors…"></textarea>
              </div>
            </div>

            <div class="divider"></div>

            <div class="row" style="align-items:center; justify-content:space-between">
              <div>
                <div class="cardTitle" style="font-size:14px">Interview Evaluation Criteria</div>
                <div class="cardDesc">Add weighted criteria (name + weight %). Weights are not enforced client-side.</div>
              </div>
              <div class="row" style="gap:10px">
                <button type="button" class="btn btnSmall btnGhost" id="addCriterion">
                  <span class="btnIcon">＋</span><span>Add criterion</span>
                </button>
              </div>
            </div>

            <div style="margin-top:12px; display:flex; flex-direction:column; gap:10px" id="criteriaWrap">
              ${criteriaRowTemplate(0, "Communication", 25)}
              ${criteriaRowTemplate(1, "Technical depth", 45)}
              ${criteriaRowTemplate(2, "Role fit", 30)}
            </div>

            <div class="divider"></div>

            <div class="row" style="justify-content:flex-end">
              <button class="btn btnPrimary" type="submit">
                <span class="btnIcon" aria-hidden="true">⟡</span>
                <span>Create Vacancy</span>
              </button>
            </div>
          </form>
        </div>
      </div>

      <div class="card">
        <div class="cardHeader">
          <div>
            <div class="cardTitle">Manual Resume Upload</div>
            <div class="cardDesc">Attach a candidate to a job vacancy. Upload PDF to ingest.</div>
          </div>
          <div class="chip"><strong>POST</strong> /candidates</div>
        </div>
        <div class="cardBody">
          <form id="candidateUploadForm" autocomplete="off">
            <div class="field">
              <label>Select job</label>
              <select id="c_job" class="input">
                ${vacancies.map(v=>{
                  const id = pick(v, ["id","vacancy_id","external_job_id"]);
                  const label = vacancyDisplayName(v);
                  return `<option value="${escapeHtml(String(id ?? ""))}">${escapeHtml(label)}</option>`;
                }).join("")}
              </select>
            </div>

            <div class="row">
              <div class="field">
                <label>Candidate name</label>
                <input id="c_name" class="input" type="text" placeholder="e.g., A. Sharma" />
              </div>
              <div class="field">
                <label>Email</label>
                <input id="c_email" class="input" type="email" placeholder="name@domain.com" />
              </div>
            </div>

            <div class="field">
              <label>Resume file (PDF)</label>
              <input id="c_resume" class="input" type="file" accept="application/pdf" />
            </div>

            <div class="divider"></div>

            <div class="row" style="justify-content:flex-end">
              <button class="btn btnPrimary" type="submit">
                <span class="btnIcon">⇪</span>
                <span>Upload Candidate</span>
              </button>
            </div>

            <div class="cardDesc" style="margin-top:10px">
              Note: Payload is sent as multipart/form-data to match typical upload patterns.
            </div>
          </form>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="cardHeader">
        <div>
          <div class="cardTitle">Created Jobs</div>
          <div class="cardDesc">Search, sort, and select. Use this list to manage bulk actions in the pipeline.</div>
        </div>
        <div class="row" style="gap:10px; align-items:center">
          <span class="chip"><strong>GET</strong> /vacancies</span>
        </div>
      </div>
      <div class="cardBody" style="padding:0">
        ${table.html}
      </div>
    </div>
  `;

  // bind vacancy creation
  const vf = $("#vacancyForm");
  vf.addEventListener("submit", async (e)=>{
    e.preventDefault();
    const payload = buildVacancyPayloadFromForm(document);

    const btn = vf.querySelector('button[type="submit"]');
    const prev = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<span class="btnIcon">…</span><span>Creating</span>`;
    try{
      await apiFetch(`/vacancies`, {method:"POST", body: JSON.stringify(payload)});
      toast("good","Vacancy created","Job has been created successfully.");
      vf.reset();
      // keep criteria but clear values? leave as-is for convenience
      state.cache.vacancies = null;
      await loadVacancies(true);
      renderHRIntake(true);
    }catch(err){
      toast("bad","Create vacancy failed", err.message);
    }finally{
      btn.disabled = false;
      btn.innerHTML = prev;
    }
  });

  // bind criteria add/remove
  const cw = $("#criteriaWrap");
  let critIdx = $$('[data-crit-row]', cw).length;
  $("#addCriterion").addEventListener("click", ()=>{
    const html = document.createElement("div");
    html.innerHTML = criteriaRowTemplate(critIdx++, "", "");
    cw.appendChild(html.firstElementChild);
    bindCriteriaRemove(cw);
  });
  bindCriteriaRemove(cw);

  function bindCriteriaRemove(root){
    $$("[data-crit-remove]", root).forEach(btn=>{
      if(btn._bound) return;
      btn._bound = true;
      btn.addEventListener("click", ()=>{
        const row = btn.closest("[data-crit-row]");
        row?.remove();
      });
    });
  }

  // candidate upload
  const cf = $("#candidateUploadForm");
  cf.addEventListener("submit", async (e)=>{
    e.preventDefault();
    const fd = new FormData();
    // do not change backend logic; append common keys
    fd.append("job_id", $("#c_job").value);
    fd.append("name", $("#c_name").value || "");
    fd.append("email", $("#c_email").value || "");
    const file = $("#c_resume").files?.[0];
    if(file) fd.append("resume", file);

    const btn = cf.querySelector('button[type="submit"]');
    const prev = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<span class="btnIcon">…</span><span>Uploading</span>`;
    try{
      await apiFetch(`/candidates`, {method:"POST", body: fd});
      toast("good","Candidate uploaded","Resume has been queued for processing.");
      cf.reset();
      state.cache.candidates = null;
    }catch(err){
      toast("bad","Upload failed", err.message);
    }finally{
      btn.disabled = false;
      btn.innerHTML = prev;
    }
  });

  // bind table tools
  const tableRoot = content;
  table.bind(tableRoot);

  const search = $('[data-role="tableSearch"]', tableRoot);
  search?.addEventListener("input", ()=>{
    const s = makeTableState(vTableId);
    s.q = search.value;
    s.page = 1;
    rerenderRouteNoFetch();
  });

  $('[data-role="reloadVacancies"]', tableRoot)?.addEventListener("click", async ()=>{
    try{
      state.cache.vacancies = null;
      await loadVacancies(true);
      toast("good","Reloaded","Vacancies refreshed.");
      renderHRIntake(true);
    }catch(err){
      toast("bad","Reload failed", err.message);
    }
  });
}

/* ------------------ Hiring Pipeline ------------------ */

function statusPill(status){
  const s = normalizeStr(status);
  let tone = "badge";
  if(s.includes("shortlist") || s.includes("pass") || s.includes("qualified")) tone = "badge";
  if(s.includes("reject") || s.includes("fail")) tone = "badge";
  return `<span class="badge" style="border-radius:999px">${escapeHtml(status || "—")}</span>`;
}

async function renderPipeline(noFetch=false){
  const content = $("#content");
  if(!noFetch){
    content.innerHTML = `
      <div class="kpiRow">
        <div class="kpi"><div class="skeleton" style="width:90px;height:12px"></div><div class="skeleton" style="width:120px;height:22px;margin-top:10px"></div><div class="skeleton" style="width:180px;height:12px;margin-top:10px;opacity:.7"></div></div>
        <div class="kpi"><div class="skeleton" style="width:110px;height:12px"></div><div class="skeleton" style="width:120px;height:22px;margin-top:10px"></div><div class="skeleton" style="width:160px;height:12px;margin-top:10px;opacity:.7"></div></div>
        <div class="kpi"><div class="skeleton" style="width:120px;height:12px"></div><div class="skeleton" style="width:120px;height:22px;margin-top:10px"></div><div class="skeleton" style="width:140px;height:12px;margin-top:10px;opacity:.7"></div></div>
        <div class="kpi"><div class="skeleton" style="width:100px;height:12px"></div><div class="skeleton" style="width:120px;height:22px;margin-top:10px"></div><div class="skeleton" style="width:190px;height:12px;margin-top:10px;opacity:.7"></div></div>
      </div>
      ${tableSkeleton()}
    `;
  }

  let [vacancies, candidates] = [state.cache.vacancies, state.cache.candidates];
  if(!noFetch || !vacancies){
    try{ vacancies = await loadVacancies(false); }catch(err){ toast("bad","Failed to load jobs", err.message); vacancies = vacancies || []; }
  }
  if(!noFetch || !candidates){
    try{ candidates = await loadCandidates(false); }catch(err){ toast("bad","Failed to load candidates", err.message); candidates = candidates || []; }
  }

  const tableId = "candidatesTable";
  const ts = makeTableState(tableId);

  const vacancyById = new Map(vacancies.map(v => [String(pick(v,["id","vacancy_id","external_job_id"]) ?? ""), v]));
  const jobOptions = [`<option value="">All jobs</option>`].concat(
    vacancies.map(v=>{
      const id = pick(v,["id","vacancy_id","external_job_id"]);
      return `<option value="${escapeHtml(String(id ?? ""))}" ${String(ts.filterJobId||"")===String(id||"")?"selected":""}>${escapeHtml(vacancyDisplayName(v))}</option>`;
    })
  ).join("");

  let rows = candidates.slice();

  // job filter (supports candidate.job_id/vacancy_id/external_job_id)
  if(ts.filterJobId){
    rows = rows.filter(c=>{
      const cid = pick(c, ["job_id","vacancy_id","vacancyId","external_job_id","job_external_id","jobExternalId"]);
      return String(cid ?? "") === String(ts.filterJobId);
    });
  }

  // KPIs
  const total = candidates.length;
  const filteredCount = rows.length;
  const withResumeScore = candidates.filter(c => pick(c, ["resume_score","score","resumeScore"]) !== undefined).length;
  const pending = candidates.filter(c => {
    const s = normalizeStr(pick(c, ["status","candidate_status","stage"]));
    return !s || s.includes("new") || s.includes("applied") || s.includes("pending");
  }).length;

  const table = buildTable({
    id: tableId,
    columns: [
      { key:"name", label:"Candidate Name", value: r => candidateDisplayName(r) },
      { key:"email", label:"Email", value: r => pick(r, ["email","candidate_email"]) ?? "" },
      { key:"resume", label:"Resume Link", render: r => {
        const link = safeUrl(pick(r, ["resume_link","resume_url","resume","pdf_url","resumeLink"]));
        if(!link){
          return `<span class="muted">—</span>`;
        }
        return `<a href="${link}" target="_blank" class="link">📄 View Resume</a>`;
      }},
      { key:"job", label:"Job Name", value: r => {
        const jid = String(pick(r, ["job_id","vacancy_id","vacancyId","external_job_id"]) ?? "");
        const v = vacancyById.get(jid);
        return v ? vacancyDisplayName(v) : (pick(r, ["job_role","job_name","job"]) ?? "");
      }},
      { key:"resume_score", label:"Resume Score", value: r => pick(r, ["resume_score","score","resumeScore"]) ?? "" },
      { key:"status", label:"Status", render: r => statusPill(pick(r, ["status","candidate_status","stage"])) },
      { key:"applied_at", label:"Applied At", value: r => fmtDate(pick(r, ["applied_at","created_at","appliedAt","timestamp"])) },
      { key:"actions", label:"Actions", render: r => {
        const id = pick(r, ["id","candidate_id","candidateId"]);
        return `
          <div class="cellActions">
            <button class="btn btnSmall btnGhost" data-act="sendForm" data-id="${escapeHtml(String(id ?? ""))}">Send Form</button>
            <button class="btn btnSmall btnPrimary" data-act="sendFinal" data-id="${escapeHtml(String(id ?? ""))}">Final Interview</button>
          </div>
        `;
      }},
    ],
    rows,
    rowKeyFn: r => pick(r, ["id","candidate_id","email"]) ?? candidateDisplayName(r),
    tools: {
      left: `
        <input class="miniInput" data-role="tableSearch" type="search" placeholder="Search candidates…" value="${escapeHtml(ts.q)}" />
        <select class="miniInput miniSelect" data-role="jobFilter">${jobOptions}</select>
      `,
      right: `
        <button class="btn btnSmall btnGhost" data-role="refreshCandidates"><span class="btnIcon">↻</span>Refresh</button>
        <button class="btn btnSmall btnPrimary" data-role="bulkSend"><span class="btnIcon">⇢</span>Send Form (Bulk)</button>
      `
    },
    emptyText: "No candidates found for the selected filters."
  });

  content.innerHTML = `
    <div class="kpiRow">
      <div class="kpi">
        <div class="kpiLabel">Total candidates</div>
        <div class="kpiValue">${escapeHtml(fmtNumber(total))}</div>
        <div class="kpiMeta">All jobs, all stages</div>
      </div>
      <div class="kpi">
        <div class="kpiLabel">In current view</div>
        <div class="kpiValue">${escapeHtml(fmtNumber(filteredCount))}</div>
        <div class="kpiMeta">After job filter</div>
      </div>
      <div class="kpi">
        <div class="kpiLabel">With resume score</div>
        <div class="kpiValue">${escapeHtml(fmtNumber(withResumeScore))}</div>
        <div class="kpiMeta">Scored by ATS</div>
      </div>
      <div class="kpi">
        <div class="kpiLabel">Pending / new</div>
        <div class="kpiValue">${escapeHtml(fmtNumber(pending))}</div>
        <div class="kpiMeta">Ready for outreach</div>
      </div>
    </div>

    <div class="card">
      <div class="cardHeader">
        <div>
          <div class="cardTitle">Candidates</div>
          <div class="cardDesc">Send Google forms, trigger final interview links, and bulk-send by vacancy.</div>
        </div>
        <div class="row" style="gap:10px; align-items:center">
          <span class="chip"><strong>GET</strong> /candidates</span>
        </div>
      </div>
      <div class="cardBody" style="padding:0">
        ${table.html}
      </div>
    </div>
  `;

  table.bind(content);

  const search = $('[data-role="tableSearch"]', content);
  search?.addEventListener("input", ()=>{
    const s = makeTableState(tableId);
    s.q = search.value;
    s.page = 1;
    rerenderRouteNoFetch();
  });

  const jobFilter = $('[data-role="jobFilter"]', content);
  jobFilter?.addEventListener("change", ()=>{
    const s = makeTableState(tableId);
    s.filterJobId = jobFilter.value;
    s.page = 1;
    rerenderRouteNoFetch();
  });

  $('[data-role="refreshCandidates"]', content)?.addEventListener("click", async ()=>{
    try{
      state.cache.candidates = null;
      await loadCandidates(true);
      toast("good","Refreshed","Candidates updated.");
      renderPipeline(true);
    }catch(err){
      toast("bad","Refresh failed", err.message);
    }
  });

  // row actions
  $$('button[data-act="sendForm"]', content).forEach(btn=>{
    btn.addEventListener("click", async ()=>{
      const id = btn.dataset.id;
      if(!id) return;
      const prev = btn.textContent;
      btn.disabled = true;
      btn.textContent = "Sending…";
      try{
        await apiFetch(`/candidates/${encodeURIComponent(id)}/send-form`, {method:"POST"});
        toast("good","Form sent","Candidate form link has been sent.");
      }catch(err){
        toast("bad","Send failed", err.message);
      }finally{
        btn.disabled = false;
        btn.textContent = prev;
      }
    });
  });

  $$('button[data-act="sendFinal"]', content).forEach(btn=>{
    btn.addEventListener("click", async ()=>{
      const id = btn.dataset.id;
      if(!id) return;
      const prev = btn.textContent;
      btn.disabled = true;
      btn.textContent = "Sending…";
      try{
        await apiFetch(`/candidates/${encodeURIComponent(id)}/send-final-interview`, {method:"POST"});
        toast("good","Interview link sent","Final interview link has been sent.");
      }catch(err){
        toast("bad","Send failed", err.message);
      }finally{
        btn.disabled = false;
        btn.textContent = prev;
      }
    });
  });

  // bulk send form by vacancy
  $('[data-role="bulkSend"]', content)?.addEventListener("click", ()=>{
    const vId = ts.filterJobId || "";
    openModal({
      title: "Bulk Send Form",
      bodyHtml: `
        <div class="split">
          <div class="card" style="box-shadow:none">
            <div class="cardHeader">
              <div>
                <div class="cardTitle">Choose vacancy</div>
                <div class="cardDesc">Sends Google form to all candidates mapped to selected vacancy.</div>
              </div>
              <div class="chip"><strong>POST</strong> /vacancies/{id}/send-form-bulk</div>
            </div>
            <div class="cardBody">
              <div class="field">
                <label>Vacancy</label>
                <select id="bulkVacancy" class="input">${jobOptions}</select>
              </div>
              <div class="divider"></div>
              <div class="row" style="justify-content:flex-end">
                <button class="btn btnPrimary" id="confirmBulk"><span class="btnIcon">⇢</span>Send Bulk</button>
              </div>
            </div>
          </div>
          <div class="card" style="box-shadow:none">
            <div class="cardHeader">
              <div>
                <div class="cardTitle">Safety</div>
                <div class="cardDesc">This action can notify multiple candidates. Confirm before sending.</div>
              </div>
            </div>
            <div class="cardBody">
              <div class="qa">
                <div class="q">What happens?</div>
                <div class="a">The backend triggers form delivery for all candidates under the vacancy id you choose.</div>
              </div>
              <div class="qa">
                <div class="q">Tip</div>
                <div class="a">Filter by job first, then open bulk send to avoid selecting the wrong vacancy.</div>
              </div>
            </div>
          </div>
        </div>
      `,
      footerHtml: `<button class="btn btnGhost" id="bulkClose">Close</button>`,
      onBind: ({close})=>{
        const sel = $("#bulkVacancy");
        if(vId) sel.value = vId;

        $("#bulkClose").onclick = close;
        $("#confirmBulk").onclick = async ()=>{
          const id = sel.value;
          if(!id){
            toast("warn","Select a vacancy","Choose a vacancy to send bulk forms.");
            return;
          }
          const btn = $("#confirmBulk");
          const prev = btn.textContent;
          btn.disabled = true;
          btn.textContent = "Sending…";
          try{
            await apiFetch(`/vacancies/${encodeURIComponent(id)}/send-form-bulk`, {method:"POST"});
            toast("good","Bulk send started","Form links have been triggered in bulk.");
            close();
          }catch(err){
            toast("bad","Bulk send failed", err.message);
          }finally{
            btn.disabled = false;
            btn.textContent = prev;
          }
        };
      }
    });
  });
}

/* ------------------ Candidate Forms ------------------ */

async function renderCandidateForms(noFetch=false){
  const content = $("#content");
  if(!noFetch){
    content.innerHTML = `
      <div class="grid">
        ${skeletonCard(4)}
        ${skeletonCard(4)}
      </div>
      ${tableSkeleton()}
    `;
  }

  let [vacancies, forms] = [state.cache.vacancies, state.cache.forms];
  if(!noFetch || !vacancies){
    try{ vacancies = await loadVacancies(false); }catch(err){ toast("bad","Failed to load jobs", err.message); vacancies = vacancies || []; }
  }
  if(!noFetch || !forms){
    try{ forms = await loadForms(false); }catch(err){ toast("bad","Failed to load forms", err.message); forms = forms || []; }
  }

  const tableId = "formsTable";
  const ts = makeTableState(tableId);

  const vacancyById = new Map(vacancies.map(v => [String(pick(v,["id","vacancy_id","external_job_id"]) ?? ""), v]));
  const jobOptions = [`<option value="">All jobs</option>`].concat(
    vacancies.map(v=>{
      const id = pick(v,["id","vacancy_id","external_job_id"]);
      return `<option value="${escapeHtml(String(id ?? ""))}" ${String(ts.filterJobId||"")===String(id||"")?"selected":""}>${escapeHtml(vacancyDisplayName(v))}</option>`;
    })
  ).join("");

  let rows = forms.slice();
  if(ts.filterJobId){
    rows = rows.filter(f=>{
      const jid = pick(f, ["job_id","vacancy_id","vacancyId","external_job_id"]);
      return String(jid ?? "") === String(ts.filterJobId);
    });
  }

  const table = buildTable({
    id: tableId,
    columns: [
      { key:"name", label:"Candidate Name", value: r => pick(r, ["name","candidate_name","full_name"]) ?? "" },
      { key:"email", label:"Email", value: r => pick(r, ["email"]) ?? "" },
      { key:"phone", label:"Phone", value: r => pick(r, ["phone","phone_number","mobile"]) ?? "" },
      { key:"job", label:"Job Name", value: r => {
        const jid = String(pick(r, ["job_id","vacancy_id","external_job_id"]) ?? "");
        const v = vacancyById.get(jid);
        return v ? vacancyDisplayName(v) : (pick(r, ["job_role","job_name","job"]) ?? "");
      }},
      { key:"experience", label:"Experience", value: r => pick(r, ["experience","experience_years","total_experience"]) ?? "" },
      { key:"current_ctc", label:"Current CTC", value: r => pick(r, ["current_ctc","currentCTC"]) ?? "" },
      { key:"expected_ctc", label:"Expected CTC", value: r => pick(r, ["expected_ctc","expectedCTC"]) ?? "" },
      { key:"notice_period", label:"Notice Period", value: r => pick(r, ["notice_period","noticePeriod"]) ?? "" },
      { key:"portfolio", label:"Portfolio link", render: r => {
        const link = safeUrl(pick(r, ["portfolio","portfolio_link","portfolioLink","github","linkedin"]));
        if(!link) return `<span class="muted">—</span>`;
        return `<a class="link" href="${escapeHtml(link)}" target="_blank" rel="noreferrer">Open</a>`;
      }},
      { key:"submitted_at", label:"Submission date", value: r => fmtDate(pick(r, ["submitted_at","submission_date","created_at","timestamp"])) },
    ],
    rows,
    rowKeyFn: r => pick(r, ["id","email","submitted_at"]) ?? JSON.stringify(r).slice(0,24),
    tools: {
      left: `
        <input class="miniInput" data-role="tableSearch" type="search" placeholder="Search submissions…" value="${escapeHtml(ts.q)}" />
        <select class="miniInput miniSelect" data-role="jobFilter">${jobOptions}</select>
      `,
      right: `
        <button class="btn btnSmall btnGhost" data-role="refreshForms"><span class="btnIcon">↻</span>Refresh</button>
      `
    },
    emptyText: "No submissions available."
  });

  content.innerHTML = `
    <div class="card">
      <div class="cardHeader">
        <div>
          <div class="cardTitle">Form Submissions</div>
          <div class="cardDesc">Review candidate-provided details and open portfolios in a new tab.</div>
        </div>
        <div class="chip"><strong>GET</strong> /candidate-form/status</div>
      </div>
      <div class="cardBody" style="padding:0">
        ${table.html}
      </div>
    </div>
  `;

  table.bind(content);

  const search = $('[data-role="tableSearch"]', content);
  search?.addEventListener("input", ()=>{
    const s = makeTableState(tableId);
    s.q = search.value;
    s.page = 1;
    rerenderRouteNoFetch();
  });

  const jobFilter = $('[data-role="jobFilter"]', content);
  jobFilter?.addEventListener("change", ()=>{
    const s = makeTableState(tableId);
    s.filterJobId = jobFilter.value;
    s.page = 1;
    rerenderRouteNoFetch();
  });

  $('[data-role="refreshForms"]', content)?.addEventListener("click", async ()=>{
    try{
      state.cache.forms = null;
      await loadForms(true);
      toast("good","Refreshed","Forms updated.");
      renderCandidateForms(true);
    }catch(err){
      toast("bad","Refresh failed", err.message);
    }
  });
}

/* ------------------ AI Interviews ------------------ */

function getTranscriptFromInterviewDetail(detail){
  if(!detail) return [];
  const data = detail.data ?? detail;
  const t = pick(data, ["interview_transcript","transcript","qa","qna","conversation"]);
  const parsed = parseMaybeJson(t);

  if(Array.isArray(parsed)){
    // expected: [{question, answer}] or {q,a}
    return parsed.map((x, i)=>({
      question: pick(x, ["question","q","prompt"]) ?? `Question ${i+1}`,
      answer: pick(x, ["answer","a","response"]) ?? ""
    }));
  }

  // If transcript is a string blob, attempt to split
  if(typeof parsed === "string"){
    const s = parsed.trim();
    if(!s) return [];
    return [{question:"Transcript", answer:s}];
  }

  return [];
}

async function renderAIInterviews(noFetch=false){
  const content = $("#content");
  if(!noFetch){
    content.innerHTML = `
      ${tableSkeleton()}
      <div class="grid">
        ${skeletonCard(6)}
        ${skeletonCard(6)}
      </div>
    `;
  }

  let candidates = state.cache.candidates;
  if(!noFetch || !candidates){
    try{ candidates = await loadCandidates(false); }catch(err){ toast("bad","Failed to load candidates", err.message); candidates = candidates || []; }
  }
  let vacancies = state.cache.vacancies;
  if(!noFetch || !vacancies){
    try{ vacancies = await loadVacancies(false); }catch(err){ toast("bad","Failed to load jobs", err.message); vacancies = vacancies || []; }
  }
  const vacancyById = new Map(vacancies.map(v => [String(pick(v,["id","vacancy_id","external_job_id"]) ?? ""), v]));

  const tableId = "interviewsTable";
  const ts = makeTableState(tableId);

  // This view uses candidates list as index; interview details loaded per candidate when viewing transcript
  const rows = candidates.map(c=>{
    const jobId = String(pick(c, ["job_id","vacancy_id","external_job_id"]) ?? "");
    const v = vacancyById.get(jobId);
    return {
      _candidate: c,
      candidate_id: pick(c, ["id","candidate_id","candidateId"]),
      candidate_name: candidateDisplayName(c),
      job_profile: v ? vacancyDisplayName(v) : (pick(c, ["job_role","job","job_name"]) ?? ""),
      overall_score: pick(c, ["interview_score","overall_score","score","ai_score"]),
      recommendation: pick(c, ["recommendation","ai_recommendation","verdict"]),
    };
  });

  const table = buildTable({
    id: tableId,
    columns: [
      { key:"candidate_name", label:"Candidate", value: r => r.candidate_name },
      { key:"job_profile", label:"Job Profile", value: r => r.job_profile },
      { key:"overall_score", label:"Overall Score", value: r => r.overall_score ?? "" },
      { key:"recommendation", label:"Recommendation", value: r => r.recommendation ?? "" },
      { key:"view", label:"Transcript", render: r => {
        const id = r.candidate_id;
        return `<button class="btn btnSmall btnPrimary" data-act="viewTranscript" data-id="${escapeHtml(String(id ?? ""))}" data-name="${escapeHtml(r.candidate_name)}">View</button>`;
      }},
    ],
    rows,
    rowKeyFn: r => r.candidate_id ?? r.candidate_name,
    tools: {
      left: `
        <input class="miniInput" data-role="tableSearch" type="search" placeholder="Search interviews…" value="${escapeHtml(ts.q)}" />
        <span class="badge">Select a candidate to open transcript</span>
      `,
      right: `
        <button class="btn btnSmall btnGhost" data-role="refresh"><span class="btnIcon">↻</span>Refresh</button>
      `
    },
    emptyText: "No candidates available."
  });

  content.innerHTML = `
    <div class="card">
      <div class="cardHeader">
        <div>
          <div class="cardTitle">Interview Results</div>
          <div class="cardDesc">Open a candidate transcript. Details are fetched from <span class="muted">GET /interviews/{candidate_id}</span>.</div>
        </div>
        <div class="chip"><strong>GET</strong> /interviews/{candidate_id}</div>
      </div>
      <div class="cardBody" style="padding:0">
        ${table.html}
      </div>
    </div>
  `;

  table.bind(content);

  const search = $('[data-role="tableSearch"]', content);
  search?.addEventListener("input", ()=>{
    const s = makeTableState(tableId);
    s.q = search.value;
    s.page = 1;
    rerenderRouteNoFetch();
  });

  $('[data-role="refresh"]', content)?.addEventListener("click", async ()=>{
    try{
      state.cache.candidates = null;
      await loadCandidates(true);
      toast("good","Refreshed","Interview index updated.");
      renderAIInterviews(true);
    }catch(err){
      toast("bad","Refresh failed", err.message);
    }
  });

  $$('button[data-act="viewTranscript"]', content).forEach(btn=>{
    btn.addEventListener("click", async ()=>{
      const id = btn.dataset.id;
      const name = btn.dataset.name || "Candidate";
      if(!id){
        toast("warn","Missing candidate id","Cannot load interview details.");
        return;
      }

      openModal({
        title: `Interview Transcript — ${name}`,
        bodyHtml: `
          <div class="split">
            <div class="card" style="box-shadow:none">
              <div class="cardHeader">
                <div>
                  <div class="cardTitle">Details</div>
                  <div class="cardDesc">Loaded from the backend interview endpoint.</div>
                </div>
              </div>
              <div class="cardBody" id="interviewMeta">
                <div class="skeleton" style="height:14px;width:70%"></div>
                <div class="skeleton" style="height:14px;width:55%;margin-top:10px"></div>
                <div class="skeleton" style="height:14px;width:62%;margin-top:10px"></div>
                <div class="divider"></div>
                <div class="skeleton" style="height:12px;width:90%;margin-top:10px;opacity:.7"></div>
                <div class="skeleton" style="height:12px;width:82%;margin-top:10px;opacity:.7"></div>
                <div class="skeleton" style="height:12px;width:78%;margin-top:10px;opacity:.7"></div>
              </div>
            </div>

            <div class="card" style="box-shadow:none">
              <div class="cardHeader">
                <div>
                  <div class="cardTitle">Transcript</div>
                  <div class="cardDesc">Q/A rendered in order. Empty transcript will show a placeholder.</div>
                </div>
              </div>
              <div class="cardBody" id="transcriptBody">
                <div class="skeleton" style="height:14px;width:60%"></div>
                <div class="skeleton" style="height:12px;width:90%;margin-top:10px;opacity:.75"></div>
                <div class="skeleton" style="height:12px;width:86%;margin-top:10px;opacity:.75"></div>
              </div>
            </div>
          </div>
        `,
        footerHtml: `<button class="btn btnGhost" id="closeInterview">Close</button>`,
        onBind: async ({close})=>{
          $("#closeInterview").onclick = close;

          try{
            const detail = await apiFetch(`/interviews/${encodeURIComponent(id)}`);
            const data = detail?.data ?? detail;

            const overall = pick(data, ["overall_score","score","total_score","final_score"]);
            const rec = pick(data, ["recommendation","verdict","final_recommendation"]);
            const profile = pick(data, ["job_profile","job_role","job","role"]);
            const created = fmtDate(pick(data, ["created_at","timestamp","interview_date"]));

            $("#interviewMeta").innerHTML = `
              <div class="row" style="gap:10px; flex-wrap:wrap">
                <span class="chip"><strong>Candidate ID</strong> ${escapeHtml(String(id))}</span>
                ${profile ? `<span class="chip"><strong>Job</strong> ${escapeHtml(String(profile))}</span>` : ``}
                ${overall !== undefined ? `<span class="chip"><strong>Score</strong> ${escapeHtml(String(overall))}</span>` : ``}
                ${rec ? `<span class="chip"><strong>Rec</strong> ${escapeHtml(String(rec))}</span>` : ``}
                ${created ? `<span class="chip"><strong>When</strong> ${escapeHtml(String(created))}</span>` : ``}
              </div>
              <div class="divider"></div>
              <div class="cardDesc">If transcript is stored as JSON, it will be rendered as Q/A blocks. Otherwise it is shown as raw text.</div>
            `;

            const transcript = getTranscriptFromInterviewDetail(detail);
            if(!transcript.length){
              $("#transcriptBody").innerHTML = `<div class="qa"><div class="q">No transcript available</div><div class="a">The backend did not return transcript data for this candidate.</div></div>`;
            }else{
              $("#transcriptBody").innerHTML = `
                <div class="transcript">
                  ${transcript.map((qa,i)=>`
                    <div class="qa">
                      <div class="q">Q${i+1}. ${escapeHtml(qa.question || "")}</div>
                      <div class="a">${escapeHtml(qa.answer || "")}</div>
                    </div>
                  `).join("")}
                </div>
              `;
            }
          }catch(err){
            toast("bad","Failed to load interview details", err.message);
            $("#interviewMeta").innerHTML = `<div class="qa"><div class="q">Error</div><div class="a">${escapeHtml(err.message)}</div></div>`;
            $("#transcriptBody").innerHTML = `<div class="qa"><div class="q">Transcript unavailable</div><div class="a">Please try again later.</div></div>`;
          }
        }
      });
    });
  });
}

/* ------------------ Global bindings ------------------ */

function bindNav(){
  $$(".navItem").forEach(btn=>{
    btn.addEventListener("click", ()=>{
      const r = btn.dataset.route;
      if(!r) return;
      setRoute(r);
      // close on mobile
      $("#sidebar")?.classList.remove("open");
    });
  });

  $("#sidebarToggle").addEventListener("click", ()=>{
    $("#sidebar").classList.toggle("open");
  });
}

function bindGlobalSearch(){
  const input = $("#globalSearchInput");
  const clear = $("#globalSearchClear");
  input.addEventListener("input", ()=>{
    applyGlobalSearch(input.value);
    clear.style.visibility = input.value ? "visible" : "hidden";
  });
  clear.addEventListener("click", ()=>{
    input.value = "";
    clear.style.visibility = "hidden";
    applyGlobalSearch("");
    input.focus();
  });
  clear.style.visibility = "hidden";
}

function bindRefreshCurrent(){
  $("#refreshCurrent").addEventListener("click", async ()=>{
    try{
      if(state.route === "hr"){
        state.cache.vacancies = null;
        await loadVacancies(true);
        toast("good","Refreshed","HR Intake data updated.");
        renderHRIntake(true);
      }
      if(state.route === "pipeline"){
        state.cache.candidates = null;
        state.cache.vacancies = null;
        await Promise.all([loadVacancies(true), loadCandidates(true)]);
        toast("good","Refreshed","Pipeline updated.");
        renderPipeline(true);
      }
      if(state.route === "forms"){
        state.cache.forms = null;
        state.cache.vacancies = null;
        await Promise.all([loadVacancies(true), loadForms(true)]);
        toast("good","Refreshed","Forms updated.");
        renderCandidateForms(true);
      }
      if(state.route === "interviews"){
        state.cache.candidates = null;
        await loadCandidates(true);
        toast("good","Refreshed","Interviews index updated.");
        renderAIInterviews(true);
      }
    }catch(err){
      toast("bad","Refresh failed", err.message);
    }
  });
}

(function init(){
  bindNav();
  bindGlobalSearch();
  bindRefreshCurrent();
  setRoute("hr");
})();
