"""Desktop onboarding wizard helpers for the launcher."""

from __future__ import annotations

import json
from typing import Any, Dict, Tuple

from ouroboros.config import SETTINGS_DEFAULTS


_OPENROUTER_MODEL_DEFAULTS = {
    "main": str(SETTINGS_DEFAULTS["OUROBOROS_MODEL"]),
    "code": str(SETTINGS_DEFAULTS["OUROBOROS_MODEL_CODE"]),
    "light": str(SETTINGS_DEFAULTS["OUROBOROS_MODEL_LIGHT"]),
    "fallback": str(SETTINGS_DEFAULTS["OUROBOROS_MODEL_FALLBACK"]),
}
_OPENAI_MODEL_DEFAULTS = {
    "main": "openai::gpt-5.2",
    "code": "openai::gpt-5.2",
    "light": "openai::gpt-4.1",
    "fallback": "openai::gpt-4.1",
}
_LOCAL_PRESETS: Dict[str, Dict[str, Any]] = {
    "qwen25-7b": {
        "label": "Qwen2.5-7B Instruct Q3_K_M",
        "source": "Qwen/Qwen2.5-7B-Instruct-GGUF",
        "filename": "qwen2.5-7b-instruct-q3_k_m.gguf",
        "context_length": 16384,
        "chat_format": "",
    },
    "qwen3-14b": {
        "label": "Qwen3-14B Instruct Q4_K_M",
        "source": "Qwen/Qwen3-14B-GGUF",
        "filename": "Qwen3-14B-Q4_K_M.gguf",
        "context_length": 16384,
        "chat_format": "",
    },
    "qwen3-32b": {
        "label": "Qwen3-32B Instruct Q4_K_M",
        "source": "Qwen/Qwen3-32B-GGUF",
        "filename": "Qwen3-32B-Q4_K_M.gguf",
        "context_length": 32768,
        "chat_format": "",
    },
}
_MODEL_SUGGESTIONS = [
    "anthropic/claude-opus-4.6",
    "anthropic/claude-sonnet-4.6",
    "google/gemini-3.1-pro-preview",
    "google/gemini-3-flash-preview",
    "openai/gpt-5.2",
    "openai/gpt-5.4",
    "openai::gpt-5.2",
    "openai::gpt-4.1",
    "openai-compatible::meta-llama/compatible",
    "cloudru::giga-model",
]


def _string(value: Any) -> str:
    return str(value or "").strip()


def _truthy(value: Any) -> bool:
    return _string(value).lower() in {"1", "true", "yes", "on"}


def _detect_local_preset(settings: dict) -> str:
    source = _string(settings.get("LOCAL_MODEL_SOURCE"))
    filename = _string(settings.get("LOCAL_MODEL_FILENAME"))
    if not source:
        return ""
    for preset_id, preset in _LOCAL_PRESETS.items():
        if source == preset["source"] and filename == preset["filename"]:
            return preset_id
    return "custom"


def _derive_provider_profile(settings: dict) -> str:
    if _string(settings.get("OPENROUTER_API_KEY")):
        return "openrouter"
    if _string(settings.get("OPENAI_API_KEY")):
        return "openai"
    if _string(settings.get("LOCAL_MODEL_SOURCE")):
        return "local"
    return "openrouter"


def _derive_local_routing_mode(settings: dict) -> str:
    use_main = _truthy(settings.get("USE_LOCAL_MAIN"))
    use_code = _truthy(settings.get("USE_LOCAL_CODE"))
    use_light = _truthy(settings.get("USE_LOCAL_LIGHT"))
    use_fallback = _truthy(settings.get("USE_LOCAL_FALLBACK"))
    if use_main and use_code and use_light and use_fallback:
        return "all"
    if not use_main and not use_code and not use_light and use_fallback:
        return "fallback"
    return "cloud"


def _initial_models(settings: dict, provider_profile: str) -> dict:
    defaults = _OPENAI_MODEL_DEFAULTS if provider_profile == "openai" else _OPENROUTER_MODEL_DEFAULTS
    return {
        "main": _string(settings.get("OUROBOROS_MODEL")) or defaults["main"],
        "code": _string(settings.get("OUROBOROS_MODEL_CODE")) or defaults["code"],
        "light": _string(settings.get("OUROBOROS_MODEL_LIGHT")) or defaults["light"],
        "fallback": _string(settings.get("OUROBOROS_MODEL_FALLBACK")) or defaults["fallback"],
    }


def build_onboarding_html(settings: dict) -> str:
    provider_profile = _derive_provider_profile(settings)
    models = _initial_models(settings, provider_profile)
    initial_state = {
        "providerProfile": provider_profile,
        "openrouterKey": _string(settings.get("OPENROUTER_API_KEY")),
        "openaiKey": _string(settings.get("OPENAI_API_KEY")),
        "anthropicKey": _string(settings.get("ANTHROPIC_API_KEY")),
        "budget": float(settings.get("TOTAL_BUDGET") or SETTINGS_DEFAULTS["TOTAL_BUDGET"]),
        "localPreset": _detect_local_preset(settings),
        "localSource": _string(settings.get("LOCAL_MODEL_SOURCE")),
        "localFilename": _string(settings.get("LOCAL_MODEL_FILENAME")),
        "localContextLength": int(settings.get("LOCAL_MODEL_CONTEXT_LENGTH") or SETTINGS_DEFAULTS["LOCAL_MODEL_CONTEXT_LENGTH"]),
        "localGpuLayers": int(settings.get("LOCAL_MODEL_N_GPU_LAYERS") if settings.get("LOCAL_MODEL_N_GPU_LAYERS") is not None else SETTINGS_DEFAULTS["LOCAL_MODEL_N_GPU_LAYERS"]),
        "localChatFormat": _string(settings.get("LOCAL_MODEL_CHAT_FORMAT")),
        "localRoutingMode": _derive_local_routing_mode(settings),
        "mainModel": models["main"],
        "codeModel": models["code"],
        "lightModel": models["light"],
        "fallbackModel": models["fallback"],
    }
    return (
        _WIZARD_HTML_TEMPLATE
        .replace("__INITIAL_STATE__", json.dumps(initial_state, ensure_ascii=True))
        .replace("__OPENROUTER_DEFAULTS__", json.dumps(_OPENROUTER_MODEL_DEFAULTS, ensure_ascii=True))
        .replace("__OPENAI_DEFAULTS__", json.dumps(_OPENAI_MODEL_DEFAULTS, ensure_ascii=True))
        .replace("__LOCAL_PRESETS__", json.dumps(_LOCAL_PRESETS, ensure_ascii=True))
        .replace("__MODEL_SUGGESTIONS__", json.dumps(_MODEL_SUGGESTIONS, ensure_ascii=True))
    )


def prepare_onboarding_settings(data: dict, current_settings: dict) -> Tuple[dict, str | None]:
    openrouter_key = _string(data.get("OPENROUTER_API_KEY"))
    openai_key = _string(data.get("OPENAI_API_KEY"))
    anthropic_key = _string(data.get("ANTHROPIC_API_KEY"))
    local_source = _string(data.get("LOCAL_MODEL_SOURCE"))
    local_filename = _string(data.get("LOCAL_MODEL_FILENAME"))
    local_chat_format = _string(data.get("LOCAL_MODEL_CHAT_FORMAT"))
    local_routing_mode = _string(data.get("LOCAL_ROUTING_MODE")) or "cloud"

    if openrouter_key and len(openrouter_key) < 10:
        return {}, "OpenRouter API key looks too short."
    if openai_key and len(openai_key) < 10:
        return {}, "OpenAI API key looks too short."
    if anthropic_key and len(anthropic_key) < 10:
        return {}, "Anthropic API key looks too short."

    has_local = bool(local_source)
    if not openrouter_key and not openai_key and not has_local:
        return {}, "Configure OpenRouter, OpenAI, or a local model before continuing."

    if has_local and "/" in local_source and not local_source.startswith(("/", "~")) and not local_filename:
        return {}, "Local HuggingFace sources need a GGUF filename."

    models = {
        "OUROBOROS_MODEL": _string(data.get("OUROBOROS_MODEL")),
        "OUROBOROS_MODEL_CODE": _string(data.get("OUROBOROS_MODEL_CODE")),
        "OUROBOROS_MODEL_LIGHT": _string(data.get("OUROBOROS_MODEL_LIGHT")),
        "OUROBOROS_MODEL_FALLBACK": _string(data.get("OUROBOROS_MODEL_FALLBACK")),
    }
    if not all(models.values()):
        return {}, "Confirm all four model lanes before starting Ouroboros."

    try:
        total_budget = float(data.get("TOTAL_BUDGET") or SETTINGS_DEFAULTS["TOTAL_BUDGET"])
    except (TypeError, ValueError):
        return {}, "Budget must be a number."
    if total_budget <= 0:
        return {}, "Budget must be greater than zero."

    try:
        local_context_length = int(data.get("LOCAL_MODEL_CONTEXT_LENGTH") or SETTINGS_DEFAULTS["LOCAL_MODEL_CONTEXT_LENGTH"])
        local_gpu_layers = int(data.get("LOCAL_MODEL_N_GPU_LAYERS") if data.get("LOCAL_MODEL_N_GPU_LAYERS") is not None else SETTINGS_DEFAULTS["LOCAL_MODEL_N_GPU_LAYERS"])
    except (TypeError, ValueError):
        return {}, "Local model context length and GPU layers must be integers."

    use_local = {
        "cloud": (False, False, False, False),
        "fallback": (False, False, False, True),
        "all": (True, True, True, True),
    }.get(local_routing_mode, (False, False, False, False))
    if not has_local:
        use_local = (False, False, False, False)

    prepared = dict(current_settings)
    prepared.update(models)
    prepared.update({
        "OPENROUTER_API_KEY": openrouter_key,
        "OPENAI_API_KEY": openai_key,
        "ANTHROPIC_API_KEY": anthropic_key,
        "TOTAL_BUDGET": total_budget,
        "LOCAL_MODEL_SOURCE": local_source if has_local else "",
        "LOCAL_MODEL_FILENAME": local_filename if has_local else "",
        "LOCAL_MODEL_CONTEXT_LENGTH": local_context_length,
        "LOCAL_MODEL_N_GPU_LAYERS": local_gpu_layers,
        "LOCAL_MODEL_CHAT_FORMAT": local_chat_format if has_local else "",
        "USE_LOCAL_MAIN": use_local[0],
        "USE_LOCAL_CODE": use_local[1],
        "USE_LOCAL_LIGHT": use_local[2],
        "USE_LOCAL_FALLBACK": use_local[3],
    })
    return prepared, None


_WIZARD_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Ouroboros Setup</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0b0910;
      --panel: rgba(20, 18, 28, 0.92);
      --panel-2: rgba(255, 255, 255, 0.04);
      --panel-3: rgba(232, 93, 111, 0.08);
      --border: rgba(255, 255, 255, 0.10);
      --border-strong: rgba(232, 93, 111, 0.35);
      --text: #edf2f7;
      --muted: rgba(237, 242, 247, 0.62);
      --accent: #e85d6f;
      --accent-2: #fb7185;
      --green: #34d399;
      --shadow: 0 28px 64px rgba(0, 0, 0, 0.45);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      padding: 24px;
      background:
        radial-gradient(circle at top left, rgba(232, 93, 111, 0.12), transparent 35%),
        radial-gradient(circle at top right, rgba(99, 102, 241, 0.12), transparent 30%),
        var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    .wizard-shell {
      max-width: 1040px;
      min-height: calc(100vh - 48px);
      margin: 0 auto;
      display: flex;
      flex-direction: column;
      gap: 18px;
      padding: 24px;
      border: 1px solid var(--border);
      border-radius: 24px;
      background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.02));
      backdrop-filter: blur(18px);
      box-shadow: var(--shadow);
    }
    .wizard-header {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 20px;
      align-items: start;
    }
    .wizard-title {
      font-size: 32px;
      font-weight: 700;
      letter-spacing: -0.02em;
      margin: 0 0 8px;
    }
    .wizard-subtitle {
      margin: 0;
      color: var(--muted);
      line-height: 1.5;
      max-width: 700px;
    }
    .wizard-badge {
      padding: 8px 12px;
      border-radius: 999px;
      background: var(--panel-2);
      border: 1px solid var(--border);
      color: var(--muted);
      font-size: 13px;
      white-space: nowrap;
    }
    .wizard-steps {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
    }
    .wizard-step {
      padding: 14px 16px;
      border-radius: 16px;
      background: var(--panel-2);
      border: 1px solid var(--border);
      min-width: 0;
    }
    .wizard-step.active {
      background: var(--panel-3);
      border-color: var(--border-strong);
      box-shadow: inset 0 0 0 1px rgba(232, 93, 111, 0.16);
    }
    .wizard-step.done {
      border-color: rgba(52, 211, 153, 0.22);
    }
    .wizard-step-index {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 26px;
      height: 26px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.08);
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      margin-bottom: 10px;
    }
    .wizard-step.active .wizard-step-index {
      background: rgba(232, 93, 111, 0.22);
      color: var(--text);
    }
    .wizard-step-title {
      font-size: 14px;
      font-weight: 600;
      margin: 0 0 4px;
    }
    .wizard-step-copy {
      font-size: 12px;
      color: var(--muted);
      line-height: 1.45;
      margin: 0;
    }
    .wizard-content {
      flex: 1 1 auto;
      min-height: 0;
      display: flex;
      flex-direction: column;
      gap: 18px;
      padding: 22px;
      border-radius: 20px;
      border: 1px solid var(--border);
      background: var(--panel);
    }
    .step-header {
      display: flex;
      justify-content: space-between;
      gap: 20px;
      align-items: flex-start;
      flex-wrap: wrap;
    }
    .step-title {
      font-size: 24px;
      font-weight: 700;
      margin: 0 0 6px;
    }
    .step-copy {
      margin: 0;
      color: var(--muted);
      max-width: 760px;
      line-height: 1.55;
    }
    .step-chip-row,
    .pill-row {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }
    .preset-pill,
    .mode-pill {
      border: 1px solid var(--border);
      background: rgba(255,255,255,0.03);
      color: var(--text);
      padding: 10px 14px;
      border-radius: 999px;
      cursor: pointer;
      font: inherit;
      transition: border-color 120ms ease, background 120ms ease, transform 120ms ease;
    }
    .preset-pill:hover,
    .mode-pill:hover {
      border-color: rgba(255,255,255,0.22);
      transform: translateY(-1px);
    }
    .preset-pill.active,
    .mode-pill.active {
      background: rgba(232, 93, 111, 0.16);
      border-color: var(--border-strong);
    }
    .grid {
      display: grid;
      gap: 16px;
    }
    .grid.two {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .grid.three {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
    .panel-card {
      padding: 18px;
      border-radius: 18px;
      background: rgba(255,255,255,0.03);
      border: 1px solid var(--border);
      min-width: 0;
    }
    .panel-card h3 {
      margin: 0 0 8px;
      font-size: 15px;
    }
    .panel-card p {
      margin: 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.5;
    }
    .field-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
    }
    .field {
      display: flex;
      flex-direction: column;
      gap: 8px;
      min-width: 0;
    }
    .field-label-row {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: baseline;
    }
    .field label {
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: rgba(237, 242, 247, 0.68);
    }
    .field-clear {
      color: rgba(237, 242, 247, 0.48);
      font-size: 11px;
      border: none;
      background: transparent;
      cursor: pointer;
      padding: 0;
    }
    .field-clear:hover { color: var(--text); }
    input, select {
      width: 100%;
      border-radius: 14px;
      border: 1px solid var(--border);
      background: rgba(11, 9, 16, 0.72);
      color: var(--text);
      padding: 12px 14px;
      font-size: 14px;
      outline: none;
      font-family: inherit;
      min-width: 0;
    }
    input:focus, select:focus {
      border-color: var(--border-strong);
      box-shadow: 0 0 0 3px rgba(232, 93, 111, 0.12);
    }
    .field-note,
    .inline-note {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
    }
    .inline-note code {
      padding: 1px 4px;
      border-radius: 6px;
      background: rgba(255,255,255,0.08);
    }
    .summary-card {
      display: flex;
      flex-direction: column;
      gap: 10px;
      padding: 18px;
      border-radius: 18px;
      background: rgba(255,255,255,0.03);
      border: 1px solid var(--border);
    }
    .summary-kv {
      display: grid;
      grid-template-columns: 180px minmax(0, 1fr);
      gap: 10px;
      align-items: start;
      font-size: 13px;
    }
    .summary-kv strong {
      color: rgba(237, 242, 247, 0.72);
      font-weight: 600;
    }
    .wizard-footer {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: center;
      flex-wrap: wrap;
      padding-top: 4px;
    }
    .footer-copy {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
      max-width: 620px;
    }
    .footer-actions {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }
    .btn {
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 12px 16px;
      font: inherit;
      cursor: pointer;
      transition: transform 120ms ease, border-color 120ms ease, background 120ms ease;
    }
    .btn:hover:not(:disabled) { transform: translateY(-1px); }
    .btn.secondary {
      background: rgba(255,255,255,0.03);
      color: var(--text);
    }
    .btn.primary {
      background: linear-gradient(135deg, var(--accent), var(--accent-2));
      border-color: rgba(251, 113, 133, 0.55);
      color: white;
      min-width: 170px;
      font-weight: 700;
    }
    .btn:disabled {
      opacity: 0.42;
      cursor: default;
      transform: none;
    }
    .wizard-error {
      min-height: 22px;
      color: #fca5a5;
      font-size: 13px;
    }
    .empty-state {
      padding: 18px;
      border: 1px dashed rgba(255,255,255,0.16);
      border-radius: 16px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.5;
    }
    @media (max-width: 900px) {
      body { padding: 16px; }
      .wizard-shell { min-height: calc(100vh - 32px); padding: 18px; }
      .wizard-steps,
      .field-grid,
      .grid.two,
      .grid.three { grid-template-columns: 1fr; }
      .summary-kv { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div id="root"></div>
  <script>
    const INITIAL_STATE = __INITIAL_STATE__;
    const MODEL_DEFAULTS = {
      openrouter: __OPENROUTER_DEFAULTS__,
      openai: __OPENAI_DEFAULTS__,
      local: __OPENROUTER_DEFAULTS__,
    };
    const LOCAL_PRESETS = __LOCAL_PRESETS__;
    const MODEL_SUGGESTIONS = __MODEL_SUGGESTIONS__;
    const STEP_ORDER = ["providers", "models", "runtime", "summary"];
    const STEP_META = {
      providers: {
        title: "Connect providers",
        copy: "Add every key you want to use now. You can continue only after at least one runnable provider or local model is configured.",
        footer: "Ultra-fast path: choose a profile, paste one key, then confirm visible model defaults on the next step."
      },
      models: {
        title: "Confirm every lane",
        copy: "This step is mandatory. Visible defaults prevent the old trap where OpenAI-only setups silently kept Anthropic or OpenRouter-shaped model values.",
        footer: "Keep the defaults if they match your plan, or edit any lane now. Plain openai/... still means OpenRouter-style routing; official OpenAI is openai::..."
      },
      runtime: {
        title: "Optional runtime details",
        copy: "Adjust budget, local model tuning, and optional Anthropic support. Skip this step if the defaults already look right.",
        footer: "Anthropic stays optional here because it is not required for the main desktop runtime path."
      },
      summary: {
        title: "Review before launch",
        copy: "Check the final provider, model, and routing picture. Ouroboros will save exactly this snapshot before starting.",
        footer: "The same values remain editable later in Settings."
      }
    };
    const state = Object.assign({}, INITIAL_STATE, { currentStep: "providers", error: "", saving: false, modelsDirty: false });
    const root = document.getElementById("root");

    function trim(value) {
      return String(value || "").trim();
    }

    function escapeHtml(value) {
      return String(value || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
    }

    function hasCloudProvider() {
      return trim(state.openrouterKey).length >= 10 || trim(state.openaiKey).length >= 10;
    }

    function hasLocalModel() {
      return trim(state.localSource).length > 0;
    }

    function isLocalFilesystemSource(value) {
      const text = trim(value);
      return text.startsWith("/") || text.startsWith("~");
    }

    function applyPresetSelection(presetId) {
      state.localPreset = presetId;
      if (!presetId) {
        state.localSource = "";
        state.localFilename = "";
        state.localContextLength = 16384;
        state.localChatFormat = "";
        if (!hasCloudProvider()) {
          state.localRoutingMode = "cloud";
        }
        return;
      }
      if (presetId === "custom") {
        if (!trim(state.localSource)) {
          state.localSource = "";
        }
        return;
      }
      const preset = LOCAL_PRESETS[presetId];
      if (!preset) {
        return;
      }
      state.localSource = preset.source;
      state.localFilename = preset.filename;
      state.localContextLength = preset.context_length;
      state.localChatFormat = preset.chat_format || "";
      if (state.providerProfile === "local") {
        state.localRoutingMode = "all";
      } else if (state.localRoutingMode === "cloud") {
        state.localRoutingMode = "fallback";
      }
    }

    function inferProviderProfile() {
      if (trim(state.openrouterKey).length >= 10) {
        return "openrouter";
      }
      if (trim(state.openaiKey).length >= 10) {
        return "openai";
      }
      if (hasLocalModel()) {
        return "local";
      }
      return state.providerProfile || "openrouter";
    }

    function applyModelDefaults(force) {
      if (state.modelsDirty && !force) {
        return;
      }
      const profile = inferProviderProfile();
      state.providerProfile = profile;
      const defaults = MODEL_DEFAULTS[profile] || MODEL_DEFAULTS.openrouter;
      state.mainModel = defaults.main;
      state.codeModel = defaults.code;
      state.lightModel = defaults.light;
      state.fallbackModel = defaults.fallback;
      state.modelsDirty = false;
    }

    function setProviderProfile(profile) {
      state.providerProfile = profile;
      if (profile === "local") {
        if (!state.localPreset) {
          applyPresetSelection("qwen25-7b");
        }
        state.localRoutingMode = "all";
      } else if (hasLocalModel() && state.localRoutingMode === "all") {
        state.localRoutingMode = "fallback";
      }
      applyModelDefaults(true);
      render();
    }

    function validateProvidersStep() {
      const hasOpenRouter = trim(state.openrouterKey).length >= 10;
      const hasOpenAI = trim(state.openaiKey).length >= 10;
      const localSource = trim(state.localSource);
      const localFilename = trim(state.localFilename);
      if (!hasOpenRouter && !hasOpenAI && !localSource) {
        return "Add OpenRouter, OpenAI, or a local model before continuing.";
      }
      if (trim(state.openrouterKey) && trim(state.openrouterKey).length < 10) {
        return "OpenRouter API key looks too short.";
      }
      if (trim(state.openaiKey) && trim(state.openaiKey).length < 10) {
        return "OpenAI API key looks too short.";
      }
      if (localSource && localSource.includes("/") && !isLocalFilesystemSource(localSource) && !localFilename) {
        return "HuggingFace local sources need a GGUF filename.";
      }
      return "";
    }

    function validateModelsStep() {
      if (!trim(state.mainModel) || !trim(state.codeModel) || !trim(state.lightModel) || !trim(state.fallbackModel)) {
        return "Fill all four model lanes before continuing.";
      }
      return "";
    }

    function validateRuntimeStep() {
      if (trim(state.anthropicKey) && trim(state.anthropicKey).length < 10) {
        return "Anthropic API key looks too short.";
      }
      if (!Number.isFinite(Number(state.budget)) || Number(state.budget) <= 0) {
        return "Budget must be greater than zero.";
      }
      if (hasLocalModel() && (!Number.isInteger(Number(state.localContextLength)) || Number(state.localContextLength) <= 0)) {
        return "Local context length must be a positive integer.";
      }
      if (!Number.isInteger(Number(state.localGpuLayers))) {
        return "Local GPU layers must be an integer.";
      }
      return "";
    }

    function validateCurrentStep() {
      if (state.currentStep === "providers") {
        return validateProvidersStep();
      }
      if (state.currentStep === "models") {
        return validateModelsStep();
      }
      if (state.currentStep === "runtime") {
        return validateRuntimeStep();
      }
      return "";
    }

    function nextStep() {
      const error = validateCurrentStep();
      state.error = error;
      if (error) {
        render();
        return;
      }
      const idx = STEP_ORDER.indexOf(state.currentStep);
      if (state.currentStep === "providers") {
        applyModelDefaults(false);
      }
      if (idx >= 0 && idx < STEP_ORDER.length - 1) {
        state.currentStep = STEP_ORDER[idx + 1];
      }
      state.error = "";
      render();
    }

    function previousStep() {
      const idx = STEP_ORDER.indexOf(state.currentStep);
      if (idx > 0) {
        state.currentStep = STEP_ORDER[idx - 1];
      }
      state.error = "";
      render();
    }

    function summaryRows() {
      const providers = [];
      if (trim(state.openrouterKey)) providers.push("OpenRouter");
      if (trim(state.openaiKey)) providers.push("OpenAI");
      if (trim(state.anthropicKey)) providers.push("Anthropic (advanced)");
      if (hasLocalModel()) providers.push("Local model");
      const localRoute = hasLocalModel()
        ? (state.localRoutingMode === "all" ? "all lanes local" : state.localRoutingMode === "fallback" ? "fallback lane local" : "cloud lanes only")
        : "disabled";
      const localSourceLabel = hasLocalModel()
        ? `${trim(state.localSource)}${trim(state.localFilename) ? " / " + trim(state.localFilename) : ""}`
        : "not configured";
      return [
        ["Providers", providers.length ? providers.join(", ") : "none"],
        ["Main", trim(state.mainModel)],
        ["Code", trim(state.codeModel)],
        ["Light", trim(state.lightModel)],
        ["Fallback", trim(state.fallbackModel)],
        ["Local routing", localRoute],
        ["Local source", localSourceLabel],
        ["Budget", `$${Number(state.budget || 0).toFixed(2)}`],
      ];
    }

    function renderStepContent() {
      const meta = STEP_META[state.currentStep];
      const providerProfile = inferProviderProfile();
      const suggestionOptions = MODEL_SUGGESTIONS.map((model) => `<option value="${escapeHtml(model)}"></option>`).join("");
      const summary = summaryRows().map(([label, value]) => `
        <div class="summary-kv">
          <strong>${escapeHtml(label)}</strong>
          <span>${escapeHtml(value)}</span>
        </div>
      `).join("");
      const localAdvanced = hasLocalModel() ? `
        <div class="grid two">
          <div class="field">
            <div class="field-label-row"><label for="local-context">Local Context Length</label></div>
            <input id="local-context" type="number" min="2048" step="1024" value="${escapeHtml(state.localContextLength)}">
            <div class="field-note">Used when the embedded llama.cpp server starts.</div>
          </div>
          <div class="field">
            <div class="field-label-row"><label for="local-gpu-layers">GPU Layers</label></div>
            <input id="local-gpu-layers" type="number" step="1" value="${escapeHtml(state.localGpuLayers)}">
            <div class="field-note">Use <code>-1</code> on Apple Silicon for full offload when it fits.</div>
          </div>
          <div class="field" style="grid-column: 1 / -1;">
            <div class="field-label-row">
              <label for="local-chat-format">Chat Format</label>
              <button class="field-clear" data-clear="local-chat-format" type="button">Clear</button>
            </div>
            <input id="local-chat-format" value="${escapeHtml(state.localChatFormat)}" placeholder="Leave empty for auto-detect">
          </div>
        </div>
      ` : `<div class="empty-state">No local model is configured yet, so the optional runtime section only needs budget and advanced Anthropic details.</div>`;
      const providersStep = `
        <div class="step-header">
          <div>
            <h2 class="step-title">${escapeHtml(meta.title)}</h2>
            <p class="step-copy">${escapeHtml(meta.copy)}</p>
          </div>
          <div class="pill-row">
            <button class="preset-pill ${providerProfile === "openrouter" ? "active" : ""}" data-profile="openrouter" type="button">OpenRouter default</button>
            <button class="preset-pill ${providerProfile === "openai" ? "active" : ""}" data-profile="openai" type="button">OpenAI only</button>
            <button class="preset-pill ${providerProfile === "local" ? "active" : ""}" data-profile="local" type="button">Local-first</button>
          </div>
        </div>
        <div class="grid two">
          <div class="panel-card">
            <h3>Cloud providers</h3>
            <p>Paste every key you want to configure now. OpenRouter remains the broadest multi-provider router. OpenAI-only mode uses official <code>openai::...</code> model values on the next step.</p>
          </div>
          <div class="panel-card">
            <h3>Local model</h3>
            <p>You can start with cloud, local, or both. If you configure a local preset now, the next step lets you choose whether it should power only fallback or every lane.</p>
          </div>
        </div>
        <div class="field-grid">
          <div class="field">
            <div class="field-label-row">
              <label for="openrouter-key">OpenRouter API Key</label>
              <button class="field-clear" data-clear="openrouter-key" type="button">Clear</button>
            </div>
            <input id="openrouter-key" type="password" placeholder="sk-or-v1-..." value="${escapeHtml(state.openrouterKey)}">
            <div class="field-note">Recommended when you want Anthropic, Google, OpenAI, and others through one router.</div>
          </div>
          <div class="field">
            <div class="field-label-row">
              <label for="openai-key">OpenAI API Key</label>
              <button class="field-clear" data-clear="openai-key" type="button">Clear</button>
            </div>
            <input id="openai-key" type="password" placeholder="sk-..." value="${escapeHtml(state.openaiKey)}">
            <div class="field-note">Official OpenAI runtime. The next step will visibly prefill <code>openai::...</code> lanes when this is the only cloud provider.</div>
          </div>
          <div class="field">
            <div class="field-label-row">
              <label for="local-preset">Local Model Preset</label>
              <button class="field-clear" data-clear="local-preset" type="button">Clear</button>
            </div>
            <select id="local-preset">
              <option value="" ${state.localPreset === "" ? "selected" : ""}>None</option>
              <option value="qwen25-7b" ${state.localPreset === "qwen25-7b" ? "selected" : ""}>Qwen2.5-7B Instruct Q3_K_M</option>
              <option value="qwen3-14b" ${state.localPreset === "qwen3-14b" ? "selected" : ""}>Qwen3-14B Instruct Q4_K_M</option>
              <option value="qwen3-32b" ${state.localPreset === "qwen3-32b" ? "selected" : ""}>Qwen3-32B Instruct Q4_K_M</option>
              <option value="custom" ${state.localPreset === "custom" ? "selected" : ""}>Custom source</option>
            </select>
            <div class="field-note">Local models can drive fallback only or all lanes later in this wizard.</div>
          </div>
          <div class="field">
            <div class="field-label-row">
              <label for="budget">Budget (USD)</label>
            </div>
            <input id="budget" type="number" min="1" step="1" value="${escapeHtml(state.budget)}">
            <div class="field-note">The global task budget can still be changed later in Settings.</div>
          </div>
          <div class="field" style="grid-column: 1 / -1;">
            <div class="field-label-row">
              <label for="local-source">Local Source</label>
              <button class="field-clear" data-clear="local-source" type="button">Clear</button>
            </div>
            <input id="local-source" placeholder="Qwen/Qwen2.5-7B-Instruct-GGUF or /absolute/path/model.gguf" value="${escapeHtml(state.localSource)}">
          </div>
          <div class="field" style="grid-column: 1 / -1;">
            <div class="field-label-row">
              <label for="local-filename">GGUF Filename</label>
              <button class="field-clear" data-clear="local-filename" type="button">Clear</button>
            </div>
            <input id="local-filename" placeholder="qwen2.5-7b-instruct-q3_k_m.gguf" value="${escapeHtml(state.localFilename)}">
            <div class="field-note">Needed for HuggingFace repo IDs. Leave empty only when the source is an absolute local file path.</div>
          </div>
        </div>
      `;
      const modelsStep = `
        <div class="step-header">
          <div>
            <h2 class="step-title">${escapeHtml(meta.title)}</h2>
            <p class="step-copy">${escapeHtml(meta.copy)}</p>
          </div>
          <div class="pill-row">
            <button class="preset-pill ${providerProfile === "openrouter" ? "active" : ""}" data-profile="openrouter" type="button">Apply OpenRouter defaults</button>
            <button class="preset-pill ${providerProfile === "openai" ? "active" : ""}" data-profile="openai" type="button">Apply OpenAI defaults</button>
          </div>
        </div>
        <div class="panel-card">
          <h3>Current profile</h3>
          <p>${providerProfile === "openai" ? "OpenAI-only mode detected. These defaults are explicit and official." : providerProfile === "local" ? "Local-first mode detected. The values below are still visible for clarity; local routing is selected separately." : "OpenRouter-style routing remains active. Unprefixed provider IDs like openai/gpt-5.2 continue to route through OpenRouter."}</p>
        </div>
        <div class="panel-card">
          <h3>Local routing</h3>
          <p>${hasLocalModel() ? "Choose whether the configured local model should power no lanes, only fallback, or every lane." : "No local model configured. Add one on the previous step if you want local routing choices here."}</p>
          <div class="step-chip-row" style="margin-top: 12px;">
            <button class="mode-pill ${state.localRoutingMode === "cloud" ? "active" : ""}" data-local-mode="cloud" type="button" ${hasLocalModel() ? "" : "disabled"}>Cloud only</button>
            <button class="mode-pill ${state.localRoutingMode === "fallback" ? "active" : ""}" data-local-mode="fallback" type="button" ${hasLocalModel() ? "" : "disabled"}>Fallback local</button>
            <button class="mode-pill ${state.localRoutingMode === "all" ? "active" : ""}" data-local-mode="all" type="button" ${hasLocalModel() ? "" : "disabled"}>All lanes local</button>
          </div>
        </div>
        <div class="grid two">
          <div class="field">
            <div class="field-label-row"><label for="main-model">Main Model</label></div>
            <input list="model-suggestions" id="main-model" value="${escapeHtml(state.mainModel)}">
            <div class="field-note">Primary reasoning and long-form task lane.</div>
          </div>
          <div class="field">
            <div class="field-label-row"><label for="code-model">Code Model</label></div>
            <input list="model-suggestions" id="code-model" value="${escapeHtml(state.codeModel)}">
            <div class="field-note">Coding and tool-heavy lane.</div>
          </div>
          <div class="field">
            <div class="field-label-row"><label for="light-model">Light Model</label></div>
            <input list="model-suggestions" id="light-model" value="${escapeHtml(state.lightModel)}">
            <div class="field-note">Lightweight tasks, summaries, and quick operations.</div>
          </div>
          <div class="field">
            <div class="field-label-row"><label for="fallback-model">Fallback Model</label></div>
            <input list="model-suggestions" id="fallback-model" value="${escapeHtml(state.fallbackModel)}">
            <div class="field-note">Fallback and resilience path.</div>
          </div>
        </div>
        <div class="inline-note">Official OpenAI is written as <code>openai::gpt-5.2</code>. Plain <code>openai/gpt-5.2</code> stays OpenRouter-style by design.</div>
        <datalist id="model-suggestions">${suggestionOptions}</datalist>
      `;
      const runtimeStep = `
        <div class="step-header">
          <div>
            <h2 class="step-title">${escapeHtml(meta.title)}</h2>
            <p class="step-copy">${escapeHtml(meta.copy)}</p>
          </div>
        </div>
        <div class="grid two">
          <div class="panel-card">
            <h3>Budget</h3>
            <p>Keep the launch budget conservative if you want safer first runs on a fresh install.</p>
            <div class="field" style="margin-top: 14px;">
              <div class="field-label-row"><label for="runtime-budget">Total Budget</label></div>
              <input id="runtime-budget" type="number" min="1" step="1" value="${escapeHtml(state.budget)}">
            </div>
          </div>
          <div class="panel-card">
            <h3>Anthropic (optional)</h3>
            <p>This remains advanced and optional in onboarding. It is useful for existing Claude Code flows but not required for the main desktop runtime.</p>
            <div class="field" style="margin-top: 14px;">
              <div class="field-label-row">
                <label for="anthropic-key">Anthropic API Key</label>
                <button class="field-clear" data-clear="anthropic-key" type="button">Clear</button>
              </div>
              <input id="anthropic-key" type="password" placeholder="sk-ant-..." value="${escapeHtml(state.anthropicKey)}">
            </div>
          </div>
        </div>
        ${localAdvanced}
      `;
      const summaryStep = `
        <div class="step-header">
          <div>
            <h2 class="step-title">${escapeHtml(meta.title)}</h2>
            <p class="step-copy">${escapeHtml(meta.copy)}</p>
          </div>
        </div>
        <div class="summary-card">
          ${summary}
        </div>
      `;
      return {
        providers: providersStep,
        models: modelsStep,
        runtime: runtimeStep,
        summary: summaryStep,
      }[state.currentStep];
    }

    function stepCards() {
      return STEP_ORDER.map((stepId, idx) => {
        const meta = STEP_META[stepId];
        const active = stepId === state.currentStep;
        const done = STEP_ORDER.indexOf(state.currentStep) > idx;
        return `
          <div class="wizard-step ${active ? "active" : ""} ${done ? "done" : ""}">
            <div class="wizard-step-index">${idx + 1}</div>
            <p class="wizard-step-title">${escapeHtml(meta.title)}</p>
            <p class="wizard-step-copy">${escapeHtml(meta.copy)}</p>
          </div>
        `;
      }).join("");
    }

    function render() {
      const meta = STEP_META[state.currentStep];
      const idx = STEP_ORDER.indexOf(state.currentStep);
      const nextLabel = state.currentStep === "summary"
        ? (state.saving ? "Saving..." : "Start Ouroboros")
        : (state.currentStep === "runtime" ? "Review summary" : "Continue");
      root.innerHTML = `
        <div class="wizard-shell">
          <div class="wizard-header">
            <div>
              <h1 class="wizard-title">Ouroboros</h1>
              <p class="wizard-subtitle">Desktop-first onboarding with explicit provider semantics, visible model defaults, and a stable path for OpenAI-only, OpenRouter, and local-first setups.</p>
            </div>
            <div class="wizard-badge">Step ${idx + 1} of ${STEP_ORDER.length}</div>
          </div>
          <div class="wizard-steps">${stepCards()}</div>
          <div class="wizard-content">
            ${renderStepContent()}
            <div class="wizard-footer">
              <div class="footer-copy">${escapeHtml(meta.footer)}</div>
              <div class="footer-actions">
                <button class="btn secondary" id="back-btn" type="button" ${idx === 0 || state.saving ? "disabled" : ""}>Back</button>
                ${state.currentStep === "runtime" ? `<button class="btn secondary" id="skip-runtime-btn" type="button" ${state.saving ? "disabled" : ""}>Skip optional step</button>` : ""}
                <button class="btn primary" id="next-btn" type="button" ${state.saving ? "disabled" : ""}>${escapeHtml(nextLabel)}</button>
              </div>
            </div>
            <div class="wizard-error">${escapeHtml(state.error)}</div>
          </div>
        </div>
      `;
      bindStepEvents();
    }

    function bindClearButtons() {
      root.querySelectorAll("[data-clear]").forEach((button) => {
        button.addEventListener("click", () => {
          const target = button.getAttribute("data-clear");
          if (target === "openrouter-key") state.openrouterKey = "";
          if (target === "openai-key") state.openaiKey = "";
          if (target === "anthropic-key") state.anthropicKey = "";
          if (target === "local-preset") {
            state.localPreset = "";
            state.localSource = "";
            state.localFilename = "";
            state.localRoutingMode = hasCloudProvider() ? "cloud" : "cloud";
          }
          if (target === "local-source") state.localSource = "";
          if (target === "local-filename") state.localFilename = "";
          if (target === "local-chat-format") state.localChatFormat = "";
          state.error = "";
          render();
        });
      });
    }

    function bindProviderStep() {
      const openrouterInput = document.getElementById("openrouter-key");
      const openaiInput = document.getElementById("openai-key");
      const localPreset = document.getElementById("local-preset");
      const localSource = document.getElementById("local-source");
      const localFilename = document.getElementById("local-filename");
      const budget = document.getElementById("budget");
      openrouterInput.addEventListener("input", () => { state.openrouterKey = openrouterInput.value; state.error = ""; });
      openaiInput.addEventListener("input", () => { state.openaiKey = openaiInput.value; state.error = ""; });
      localPreset.addEventListener("change", () => { applyPresetSelection(localPreset.value); state.error = ""; render(); });
      localSource.addEventListener("input", () => { state.localSource = localSource.value; state.localPreset = state.localPreset || "custom"; state.error = ""; });
      localFilename.addEventListener("input", () => { state.localFilename = localFilename.value; state.localPreset = state.localPreset || "custom"; state.error = ""; });
      budget.addEventListener("input", () => { state.budget = budget.value; state.error = ""; });
      root.querySelectorAll("[data-profile]").forEach((button) => {
        button.addEventListener("click", () => setProviderProfile(button.getAttribute("data-profile")));
      });
    }

    function bindModelsStep() {
      const map = {
        "main-model": "mainModel",
        "code-model": "codeModel",
        "light-model": "lightModel",
        "fallback-model": "fallbackModel",
      };
      Object.entries(map).forEach(([id, key]) => {
        const input = document.getElementById(id);
        input.addEventListener("input", () => {
          state[key] = input.value;
          state.modelsDirty = true;
          state.error = "";
        });
      });
      root.querySelectorAll("[data-profile]").forEach((button) => {
        button.addEventListener("click", () => setProviderProfile(button.getAttribute("data-profile")));
      });
      root.querySelectorAll("[data-local-mode]").forEach((button) => {
        button.addEventListener("click", () => {
          state.localRoutingMode = button.getAttribute("data-local-mode");
          state.error = "";
          render();
        });
      });
    }

    function bindRuntimeStep() {
      document.getElementById("runtime-budget").addEventListener("input", (event) => {
        state.budget = event.target.value;
        state.error = "";
      });
      const anthropic = document.getElementById("anthropic-key");
      anthropic.addEventListener("input", () => { state.anthropicKey = anthropic.value; state.error = ""; });
      if (document.getElementById("local-context")) {
        document.getElementById("local-context").addEventListener("input", (event) => {
          state.localContextLength = event.target.value;
          state.error = "";
        });
      }
      if (document.getElementById("local-gpu-layers")) {
        document.getElementById("local-gpu-layers").addEventListener("input", (event) => {
          state.localGpuLayers = event.target.value;
          state.error = "";
        });
      }
      if (document.getElementById("local-chat-format")) {
        document.getElementById("local-chat-format").addEventListener("input", (event) => {
          state.localChatFormat = event.target.value;
          state.error = "";
        });
      }
    }

    async function saveWizard() {
      const providersError = validateProvidersStep();
      const modelsError = validateModelsStep();
      const runtimeError = validateRuntimeStep();
      state.error = providersError || modelsError || runtimeError;
      if (state.error) {
        render();
        return;
      }
      state.saving = true;
      state.error = "";
      render();
      const payload = {
        OPENROUTER_API_KEY: trim(state.openrouterKey),
        OPENAI_API_KEY: trim(state.openaiKey),
        ANTHROPIC_API_KEY: trim(state.anthropicKey),
        TOTAL_BUDGET: Number(state.budget || 0),
        LOCAL_MODEL_SOURCE: trim(state.localSource),
        LOCAL_MODEL_FILENAME: trim(state.localFilename),
        LOCAL_MODEL_CONTEXT_LENGTH: Number(state.localContextLength || 0),
        LOCAL_MODEL_N_GPU_LAYERS: Number(state.localGpuLayers || 0),
        LOCAL_MODEL_CHAT_FORMAT: trim(state.localChatFormat),
        LOCAL_ROUTING_MODE: state.localRoutingMode,
        OUROBOROS_MODEL: trim(state.mainModel),
        OUROBOROS_MODEL_CODE: trim(state.codeModel),
        OUROBOROS_MODEL_LIGHT: trim(state.lightModel),
        OUROBOROS_MODEL_FALLBACK: trim(state.fallbackModel),
      };
      try {
        const result = await window.pywebview.api.save_wizard(payload);
        if (result !== "ok") {
          state.saving = false;
          state.error = result || "Failed to save onboarding settings.";
          render();
        }
      } catch (err) {
        state.saving = false;
        state.error = String(err || "Failed to save onboarding settings.");
        render();
      }
    }

    function bindStepEvents() {
      bindClearButtons();
      const back = document.getElementById("back-btn");
      const next = document.getElementById("next-btn");
      if (back) back.addEventListener("click", previousStep);
      if (next) {
        next.addEventListener("click", () => {
          if (state.currentStep === "summary") {
            saveWizard();
          } else {
            nextStep();
          }
        });
      }
      const skipRuntime = document.getElementById("skip-runtime-btn");
      if (skipRuntime) {
        skipRuntime.addEventListener("click", () => {
          const runtimeError = validateRuntimeStep();
          state.error = runtimeError;
          if (!runtimeError) {
            state.currentStep = "summary";
          }
          render();
        });
      }
      if (state.currentStep === "providers") bindProviderStep();
      if (state.currentStep === "models") bindModelsStep();
      if (state.currentStep === "runtime") bindRuntimeStep();
    }

    applyModelDefaults(false);
    render();
  </script>
</body>
</html>
"""
