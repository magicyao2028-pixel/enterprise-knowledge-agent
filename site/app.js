const documents = [
  {document_id:"KB-RET-001",title:"Damaged Product Return Procedure",department:"Customer Operations",updated_at:"2026-07-15",tags:["return","damaged product","refund","evidence"],content:"A damaged-product request should be submitted within seven calendar days after delivery. The customer should provide the order number and a clear photo or video showing the damage. A customer-service lead may approve a refund or replacement after the evidence is reviewed. Food-safety complaints must be escalated immediately and should not wait for the standard review queue."},
  {document_id:"KB-SVC-002",title:"Customer Complaint Escalation Standard",department:"Customer Operations",updated_at:"2026-07-20",tags:["complaint","escalation","response time","service"],content:"Urgent complaints involving safety, suspected fraud, a public-platform escalation, or repeated service failure must be assigned to the duty manager within 30 minutes. Other unresolved complaints should be escalated after two unsuccessful handling attempts. The case record must preserve the customer request, evidence, actions taken, owner, and next response deadline."},
  {document_id:"KB-INV-003",title:"Inventory Replenishment Review",department:"Supply Chain",updated_at:"2026-07-10",tags:["inventory","replenishment","stock","supplier"],content:"A replenishment proposal requires current available stock, average daily sales, supplier lead time, minimum order quantity, and promotion plans. Orders above the approved monthly purchase budget require the business owner's approval. A recommendation is advisory until a supply-chain owner confirms the forecast and supplier terms."},
  {document_id:"KB-CNT-004",title:"AIGC Content Review Checklist",department:"Content Operations",updated_at:"2026-07-28",tags:["aigc","content","brand","copyright","review"],content:"AI-generated public content must be checked for product accuracy, brand consistency, prohibited claims, copyright risk, personal information, and platform rules before publication. The reviewer should retain the source brief, generated version, final approved asset, and approval record. Publication remains a human decision."}
];

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

function retrieve(query) {
  const queryTerms = queryTermsFor(query);
  if (!queryTerms.size) return [];
  return documents.map(document => {
    const titleTerms = new Set(tokenize(document.title));
    const tagTerms = new Set(tokenize(document.tags.join(" ")));
    const contentTerms = new Set(tokenize(document.content));
    const matched = [...queryTerms].filter(term => titleTerms.has(term) || tagTerms.has(term) || contentTerms.has(term));
    let score = matched.reduce((total,term) => total + (titleTerms.has(term) ? 3 : 0) + (tagTerms.has(term) ? 2 : 0) + (contentTerms.has(term) ? 1 : 0), 0);
    score += matched.length / queryTerms.size;
    if (`${document.title} ${document.content}`.toLowerCase().includes(query.trim().toLowerCase())) score += 4;
    return {...document, matched, score:Number(score.toFixed(3)), excerpt:bestExcerpt(document.content,queryTerms)};
  }).filter(hit => hit.matched.length).sort((a,b) => b.score - a.score || a.document_id.localeCompare(b.document_id)).slice(0,3);
}

function ask(query) {
  const trace = [{tool:"validate_query",purpose:"Check query shape and policy boundaries.",status:"completed"}];
  if (sensitiveTerms.some(term => query.toLowerCase().includes(term))) {
    trace.push({tool:"safety_boundary",purpose:"Block requests for secrets or credentials.",status:"blocked"});
    return {status:"blocked",answer:"I cannot provide or retrieve passwords, credentials, private keys, or secret tokens.",confidence:{label:"not applicable",score:1},review:true,hits:[],trace};
  }
  const hits = retrieve(query);
  trace.push({tool:"retrieve_documents",purpose:"Rank local documents with explicit lexical evidence.",status:"completed"});
  if (!hits.length) {
    trace.push({tool:"evidence_gate",purpose:"Abstain because no source supports an answer.",status:"no evidence"});
    return {status:"no evidence",answer:"I could not find enough evidence in the approved knowledge corpus. Please ask a knowledge owner.",confidence:{label:"none",score:0},review:true,hits,trace};
  }
  const queryTerms = queryTermsFor(query);
  const coverage = hits[0].matched.length / Math.max(1,queryTerms.size);
  const score = Math.min(1,.45 + coverage * .45 + Math.min(hits[0].score,10) / 100);
  const label = score >= .8 ? "high" : score >= .6 ? "medium" : "low";
  trace.push({tool:"evaluate_evidence",purpose:"Estimate lexical coverage and keep uncertainty visible.",status:"completed"});
  trace.push({tool:"compose_grounded_answer",purpose:"Compose only from retrieved excerpts and attach citations.",status:"completed"});
  return {status:"answered",answer:hits.slice(0,2).map(hit => `${hit.excerpt} [${hit.document_id}]`).join(" "),confidence:{label,score:Number(score.toFixed(2))},review:label === "low",hits,trace};
}

function render(result) {
  document.getElementById("run-status").textContent = result.status === "answered" ? "Complete" : "Needs review";
  document.getElementById("answer-status").textContent = result.status;
  document.getElementById("answer-text").textContent = result.answer;
  document.getElementById("confidence").textContent = `${result.confidence.label} · ${result.confidence.score.toFixed(2)}`;
  document.getElementById("review-note").textContent = result.review ? "Human review required: the request was blocked, unsupported, or low-confidence." : "Human verification remains required before operational action.";
  document.getElementById("evidence-count").textContent = `${result.hits.length} source${result.hits.length === 1 ? "" : "s"}`;
  document.getElementById("evidence-list").innerHTML = result.hits.length ? result.hits.map(hit => `
    <article class="evidence-card">
      <div class="source">${escapeHtml(hit.document_id)} · ${escapeHtml(hit.department)}</div>
      <h3>${escapeHtml(hit.title)}</h3>
      <p>${escapeHtml(hit.excerpt)}</p>
      <small>Updated ${escapeHtml(hit.updated_at)}</small>
      <div class="match-row"><span>Matched: ${escapeHtml(hit.matched.join(", "))}</span><span>Score ${hit.score.toFixed(2)}</span></div>
    </article>`).join("") : '<div class="empty">No approved source supported this request.</div>';
  document.getElementById("trace-list").innerHTML = result.trace.map(step => `<li class="${step.status === "blocked" ? "blocked" : ""}"><strong>${escapeHtml(step.tool)}</strong> — ${escapeHtml(step.purpose)} <small>(${escapeHtml(step.status)})</small></li>`).join("");
}

function runQuestion(question) {
  const cleaned = question.trim();
  if (!cleaned) return;
  render(ask(cleaned));
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
