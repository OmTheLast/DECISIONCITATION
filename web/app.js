const form = document.querySelector("#explain-form");
const callInput = document.querySelector("#call");
const incidentInput = document.querySelector("#incident");
const modelInput = document.querySelector("#model");
const submitButton = document.querySelector("#submit-btn");

const emptyState = document.querySelector("#empty-state");
const loadingState = document.querySelector("#loading-state");
const errorState = document.querySelector("#error-state");
const errorMessage = document.querySelector("#error-message");
const resultContent = document.querySelector("#result-content");
const resultCall = document.querySelector("#result-call");
const confidence = document.querySelector("#confidence");
const why = document.querySelector("#why");
const citations = document.querySelector("#citations");
const uncertainties = document.querySelector("#uncertainties");
const alternates = document.querySelector("#alternates");
const previewNote = document.querySelector("#preview-note");

const isLocalBackend =
  location.hostname === "127.0.0.1" || location.hostname === "localhost" || location.hostname === "";

const examples = [
  {
    call: "Penalty kick",
    incident: "A defender trips an attacker inside the penalty area while challenging for the ball.",
  },
  {
    call: "Indirect free kick for offside",
    incident:
      "An attacker in an offside position challenges a defender for the ball after a teammate passes it forward.",
  },
  {
    call: "Yellow card and direct free kick",
    incident: "A midfielder makes a reckless sliding tackle and stops a promising attack near the halfway line.",
  },
];

let exampleIndex = 0;

function setState(state) {
  emptyState.classList.toggle("hidden", state !== "empty");
  loadingState.classList.toggle("hidden", state !== "loading");
  errorState.classList.toggle("hidden", state !== "error");
  resultContent.classList.toggle("hidden", state !== "result");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function renderList(node, items, emptyText, renderer = (item) => item) {
  if (!items || !items.length) {
    node.classList.add("muted-output");
    node.textContent = emptyText;
    return;
  }

  node.classList.remove("muted-output");
  node.innerHTML = items.map((item) => `<div>${renderer(item)}</div>`).join("");
}

function renderResult(data) {
  resultCall.textContent = data.call_explained || "Call explanation";
  confidence.textContent = data.confidence ? `${data.confidence} confidence` : "confidence unknown";
  why.textContent = data.why_this_call_may_have_been_made || "No explanation returned.";

  citations.innerHTML = (data.citations || [])
    .map(
      (citation, index) => `
        <article class="citation" style="animation-delay: ${index * 70}ms">
          <div class="citation-head">
            <div>
              <strong>${escapeHtml(citation.law || "Law citation")}</strong>
              <small>${escapeHtml(citation.section_hint || "Section unavailable")}</small>
            </div>
            <span class="page-pill">p. ${escapeHtml(citation.page ?? "—")}</span>
          </div>
          <p>${escapeHtml(citation.relevance || "No relevance note returned.")}</p>
        </article>
      `,
    )
    .join("");

  renderList(uncertainties, data.uncertainties, "No uncertainties returned.");
  renderList(
    alternates,
    data.alternate_explanations,
    "No alternate paths returned.",
    (item) => `<strong>If:</strong> ${escapeHtml(item.if || "")}<br><strong>Then:</strong> ${escapeHtml(item.then || "")}`,
  );
}

async function explain(event) {
  event.preventDefault();
  setState("loading");
  submitButton.disabled = true;

  try {
    if (!isLocalBackend) {
      const demo = await loadDemoResponse();
      renderResult({
        ...demo,
        call_explained: callInput.value || demo.call_explained,
      });
      setState("result");
      return;
    }

    const response = await fetch("/api/explain", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        call: callInput.value,
        incident: incidentInput.value,
        model: modelInput.value,
      }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Explanation failed.");
    }

    renderResult(data);
    setState("result");
  } catch (error) {
    if (isLocalBackend) {
      errorMessage.textContent = error.message;
      setState("error");
    } else {
      const demo = await loadDemoResponse();
      renderResult(demo);
      setState("result");
    }
  } finally {
    submitButton.disabled = false;
  }
}

async function loadDemoResponse() {
  const response = await fetch("./demo-data.json", { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Demo response unavailable.");
  }
  return response.json();
}

function rotateExample() {
  exampleIndex = (exampleIndex + 1) % examples.length;
  callInput.value = examples[exampleIndex].call;
  incidentInput.value = examples[exampleIndex].incident;
}

function setupReveals() {
  const targets = document.querySelectorAll(".reveal");
  if (!("IntersectionObserver" in window)) {
    targets.forEach((target) => target.classList.add("is-visible"));
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.14 },
  );

  targets.forEach((target) => observer.observe(target));
}

form.addEventListener("submit", explain);
document.addEventListener("keydown", (event) => {
  if (event.key.toLowerCase() === "e" && event.metaKey) {
    event.preventDefault();
    rotateExample();
  }
});

setupReveals();

if (isLocalBackend) {
  previewNote.textContent = "Live local mode: explanations are served by your Python API and Ollama.";
} else {
  previewNote.textContent = "GitHub Pages preview mode: this page uses sample output. Run locally for live Ollama explanations.";
}
