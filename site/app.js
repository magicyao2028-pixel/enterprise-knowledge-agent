const documents = [
  {document_id:"KB-RET-001",title:"Damaged Product Return Procedure",department:"Customer Operations",updated_at:"2026-07-15",tags:["return","damaged product","refund","evidence"],content:"A damaged-product request should be submitted within seven calendar days after delivery. The customer should provide the order number and a clear photo or video showing the damage. A customer-service lead may approve a refund or replacement after the evidence is reviewed. Food-safety complaints must be escalated immediately and should not wait for the standard review queue."},
  {document_id:"KB-SVC-002",title:"Customer Complaint Escalation Standard",department:"Customer Operations",updated_at:"2026-07-20",tags:["complaint","escalation","response time","service"],content:"Urgent complaints involving safety, suspected fraud, a public-platform escalation, or repeated service failure must be assigned to the duty manager within 30 minutes. Other unresolved complaints should be escalated after two unsuccessful handling attempts. The case record must preserve the customer request, evidence, actions taken, owner, and next response deadline."},
  {document_id:"KB-INV-003",title:"Inventory Replenishment Review",department:"Supply Chain",updated_at:"2026-07-10",tags:["inventory","replenishment","stock","supplier"],content:"A replenishment proposal requires current available stock, average daily sales, supplier lead time, minimum order quantity, and promotion plans. Orders above the approved monthly purchase budget require the business owner's approval. A recommendation is advisory until a supply-chain owner confirms the forecast and supplier terms."},
  {document_id:"KB-CNT-004",title:"AIGC Content Review Checklist",department:"Content Operations",updated_at:"2026-07-28",tags:["aigc","content","brand","copyright","review"],content:"AI-generated public content must be checked for product accuracy, brand consistency, prohibited claims, copyright risk, personal information, and platform rules before publication. The reviewer should retain the source brief, generated version, final approved asset, and approval record. Publication remains a human decision."},
  {document_id:"KB-TRV-005",title:"Domestic Travel Reimbursement Policy",department:"Finance",updated_at:"2026-08-01",review_due_at:"2026-12-31",claim_key:"travel.domestic_hotel_ceiling",claim_value:"CNY 500 per night",tags:["travel","hotel","reimbursement","policy"],content:"The domestic business-travel hotel reimbursement ceiling is CNY 500 per night. Exceptions require written finance approval before booking."},
  {document_id:"KB-TRV-006",title:"Regional Travel Reimbursement Memo",department:"Regional Operations",updated_at:"2026-08-05",review_due_at:"2026-12-31",claim_key:"travel.domestic_hotel_ceiling",claim_value:"CNY 650 per night",tags:["travel","hotel","reimbursement","memo"],content:"The domestic business-travel hotel reimbursement ceiling is CNY 650 per night for regional teams. The memo does not identify whether it supersedes the finance policy."},
  {document_id:"KB-SUP-007",title:"Legacy Supplier Quote Requirement",department:"Procurement",updated_at:"2025-01-15",review_due_at:"2025-12-31",claim_key:"procurement.minimum_supplier_quotes",claim_value:"three quotes",tags:["supplier","quotes","procurement","legacy"],content:"A purchase request above CNY 20,000 requires three supplier quotes before approval. This legacy notice has not completed its scheduled policy review."},
  {document_id:"KB-FUT-008",title:"Future Inventory Safety Stock Policy",department:"Supply Chain",updated_at:"2026-09-01",review_due_at:"2027-01-31",claim_key:"inventory.safety_stock_cover",claim_value:"fourteen days",tags:["inventory","safety stock","future policy"],content:"The future inventory safety stock policy requires fourteen days of cover. Its update date is later than the current analysis date and it must not be treated as current evidence."}
];

const analysisDate = "2026-08-14";
const maxSourceAgeDays = 90;

const stopWords = new Set(["a","an","and","are","as","at","be","by","can","do","for","from","how","i","in","is","it","of","on","or","our","should","the","to","what","when","where","which","with"]);
const sensitiveTerms = ["api key","bank account","credential","password","private key","secret token"];
const normalForms = {complaints:"complaint",escalated:"escalate",escalating:"escalate",escalation:"escalate",returns:"return"};
const tokenize = value => (value.toLowerCase().match(/[a-z0-9]+/g) || []).filter(token => !stopWords.has(token)).map(token => normalForms[token] || token);
const queryTermsFor = value => {
  const terms = new Set(tokenize(value));
  if (terms.has("quickly") || terms.has("time")) ["minutes","immediately","deadline"].forEach(term => terms.add(term));
  return terms;
};
const escapeHtml = value => String(value).replace(/[&<>'"]/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"})[char]);

function bestExcerpt(content, queryTerms) {
  const sentences = content.split(/(?<=[.!?])\s+/).filter(Boolean);
  return sentences.sort((a,b) => overlap(b,queryTerms) - overlap(a,queryTerms))[0].slice(0,280);
}

function overlap(value, queryTerms) {
  const terms = new Set(tokenize(value));
  return [...queryTerms].filter(term => terms.has(term)).length;
}

function chunkDocument(document, maxWords = 55) {
  const sentences = document.content.split(/(?<=[.!?])\s+/).filter(Boolean);
  const chunks = [];
  let current = [];
  let words = 0;
  sentences.forEach(sentence => {
    const length = sentence.split(/\s+/).length;
    if (current.length && words + length > maxWords) {
      chunks.push(current.join(" "));
      current = [];
      words = 0;
    }
    current.push(sentence);
    words += length;
  });
  if (current.length) chunks.push(current.join(" "));
  return (chunks.length ? chunks : [document.content]).map((text,index) => ({
    chunk_id:`${document.document_id}-C${String(index + 1).padStart(3,"0")}`,
    text
  }));
}

function retrieve(query, department = "") {
  const queryTerms = queryTermsFor(query);
  if (!queryTerms.size) return [];
  const hits = [];
  documents.filter(document => !department || document.department === department).forEach(document => {
    const titleTerms = new Set(tokenize(document.title));
    const tagTerms = new Set(tokenize(document.tags.join(" ")));
    chunkDocument(document).forEach(chunk => {
      const contentTerms = new Set(tokenize(chunk.text));
      const matched = [...queryTerms].filter(term => titleTerms.has(term) || tagTerms.has(term) || contentTerms.has(term));
      if (!matched.length) return;
      let score = matched.reduce((total,term) => total + (titleTerms.has(term) ? 3 : 0) + (tagTerms.has(term) ? 2 : 0) + (contentTerms.has(term) ? 1 : 0), 0);
      score += matched.length / queryTerms.size;
      if (`${document.title} ${chunk.text}`.toLowerCase().includes(query.trim().toLowerCase())) score += 4;
      hits.push({...document, ...chunk, matched, score:Number(score.toFixed(3)), excerpt:bestExcerpt(chunk.text,queryTerms)});
    });
  });
  const best = new Map();
  hits.forEach(hit => {
    if (!best.has(hit.document_id) || best.get(hit.document_id).score < hit.score) best.set(hit.document_id,hit);
  });
  return [...best.values()].sort((a,b) => b.score - a.score || a.document_id.localeCompare(b.document_id)).slice(0,3);
}

function assessEvidence(hits) {
  const asOf = new Date(`${analysisDate}T00:00:00Z`);
  const stale = [];
  const claims = new Map();
  hits.forEach(hit => {
    const ageDays = Math.floor((asOf - new Date(`${hit.updated_at}T00:00:00Z`)) / 86400000);
    const reasons = [];
    if (ageDays < 0) reasons.push(`source update date ${hit.updated_at} is later than analysis date ${analysisDate}`);
    else if (ageDays > maxSourceAgeDays) reasons.push(`source age ${ageDays} days exceeds limit ${maxSourceAgeDays}`);
    if (hit.review_due_at && hit.review_due_at < analysisDate) reasons.push(`review due date ${hit.review_due_at} has passed`);
    if (reasons.length) stale.push({document_id:hit.document_id,reasons});
    if (hit.claim_key && hit.claim_value) {
      if (!claims.has(hit.claim_key)) claims.set(hit.claim_key,new Map());
      const values = claims.get(hit.claim_key);
      if (!values.has(hit.claim_value)) values.set(hit.claim_value,[]);
      values.get(hit.claim_value).push(hit.document_id);
    }
  });
  const conflicts = [...claims.entries()].filter(([,values]) => values.size > 1).map(([claim_key,values]) => ({
    claim_key,
    variants:[...values.entries()].map(([claim_value,document_ids]) => ({claim_value,document_ids}))
  }));
  return {state:conflicts.length ? "conflicting" : stale.length ? "stale" : "clear",stale,conflicts};
}

function ask(query, department = "") {
  const trace = [{tool:"validate_query",purpose:"Check query shape and policy boundaries.",status:"completed"}];
  if (sensitiveTerms.some(term => query.toLowerCase().includes(term))) {
    trace.push({tool:"safety_boundary",purpose:"Block requests for secrets or credentials.",status:"blocked"});
    return {status:"blocked",answer:"I cannot provide or retrieve passwords, credentials, private keys, or secret tokens.",confidence:{label:"not applicable",score:1},review:true,hits:[],trace};
  }
  const hits = retrieve(query, department);
  trace.push({tool:"retrieve_chunks",purpose:"Filter metadata and rank stable local document chunks.",status:"completed"});
  if (!hits.length) {
    trace.push({tool:"evidence_gate",purpose:"Abstain because no source supports an answer.",status:"no evidence"});
    return {status:"no evidence",answer:"I could not find enough evidence in the approved knowledge corpus. Please ask a knowledge owner.",confidence:{label:"none",score:0},review:true,hits,trace};
  }
  const governanceHits = hits.filter(hit => hit.score >= hits[0].score * .6);
  const governance = assessEvidence(governanceHits);
  trace.push({tool:"assess_source_governance",purpose:"Check materially relevant sources for age, review dates and structured claim conflicts.",status:"completed"});
  if (governance.state !== "clear") {
    const conflict = governance.state === "conflicting";
    trace.push({tool:"evidence_governance_gate",purpose:"Stop composition and route unresolved evidence to a knowledge owner.",status:conflict ? "conflicting evidence" : "stale evidence"});
    return {
      status:conflict ? "conflicting evidence" : "stale evidence",
      answer:conflict ? "The approved corpus contains conflicting structured policy values. A knowledge owner must resolve the source of truth." : "The supporting evidence is stale for this analysis date. A knowledge owner must verify the current policy.",
      confidence:{label:"not applicable",score:0},review:true,hits,trace,governance
    };
  }
  const queryTerms = queryTermsFor(query);
  const coverage = hits[0].matched.length / Math.max(1,queryTerms.size);
  const score = Math.min(1,.45 + coverage * .45 + Math.min(hits[0].score,10) / 100);
  const label = score >= .8 ? "high" : score >= .6 ? "medium" : "low";
  trace.push({tool:"evaluate_evidence",purpose:"Estimate lexical coverage and keep uncertainty visible.",status:"completed"});
  trace.push({tool:"compose_grounded_answer",purpose:"Compose only from retrieved excerpts and attach citations.",status:"completed"});
  return {status:"answered",answer:hits.slice(0,2).map(hit => `${hit.excerpt} [${hit.chunk_id}]`).join(" "),confidence:{label,score:Number(score.toFixed(2))},review:label === "low",hits,trace,governance};
}

function render(result) {
  document.getElementById("run-status").textContent = result.status === "answered" ? "Complete" : "Needs review";
  document.getElementById("answer-status").textContent = result.status;
  document.getElementById("answer-text").textContent = result.answer;
  document.getElementById("confidence").textContent = `${result.confidence.label} · ${result.confidence.score.toFixed(2)}`;
  document.getElementById("review-note").textContent = result.review ? "Human review required: the request was blocked, unsupported, stale, conflicting, or low-confidence." : `Freshness check clear as of ${analysisDate}; human verification remains required.`;
  document.getElementById("evidence-count").textContent = `${result.hits.length} source${result.hits.length === 1 ? "" : "s"}`;
  document.getElementById("evidence-list").innerHTML = result.hits.length ? result.hits.map(hit => `
    <article class="evidence-card">
      <div class="source">${escapeHtml(hit.chunk_id)} · ${escapeHtml(hit.department)}</div>
      <h3>${escapeHtml(hit.title)}</h3>
      <p>${escapeHtml(hit.excerpt)}</p>
      <small>Updated ${escapeHtml(hit.updated_at)}${hit.review_due_at ? ` · Review due ${escapeHtml(hit.review_due_at)}` : ""}</small>
      <div class="match-row"><span>Matched: ${escapeHtml(hit.matched.join(", "))}</span><span>Score ${hit.score.toFixed(2)}</span></div>
    </article>`).join("") : '<div class="empty">No approved source supported this request.</div>';
  document.getElementById("trace-list").innerHTML = result.trace.map(step => `<li class="${step.status === "blocked" ? "blocked" : ""}"><strong>${escapeHtml(step.tool)}</strong> — ${escapeHtml(step.purpose)} <small>(${escapeHtml(step.status)})</small></li>`).join("");
}

function runQuestion(question) {
  const cleaned = question.trim();
  if (!cleaned) return;
  render(ask(cleaned, document.getElementById("department").value));
}

document.getElementById("question-form").addEventListener("submit", event => {
  event.preventDefault();
  runQuestion(document.getElementById("question").value);
});
document.querySelectorAll("[data-question]").forEach(button => button.addEventListener("click", () => {
  document.getElementById("question").value = button.dataset.question;
  runQuestion(button.dataset.question);
}));

runQuestion(document.getElementById("question").value);
