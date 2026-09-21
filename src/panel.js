// Built with the official @decky/api bundle; React and UI components come from Decky.
const R = window.SP_REACT;
const h = R.createElement;
const { PanelSection, PanelSectionRow, DropdownItem, SliderField, ButtonItem } = window.DFL;
const getStatus = callable("get_status");
const setConfig = callable("set_config");
// Steam can unmount the QAM while displaying a dropdown in its main window.
// Keep pending edits across those remounts and notify whichever panel is mounted.
const draft = { config: { mode: "auto", percent: 60, curve: [40, 50, 70, 85, 100] }, dirty: false, listeners: new Set() };
const publishDraft = () => draft.listeners.forEach(listener => listener());

function FanIcon() {
  return h("svg", { viewBox: "0 0 24 24", width: "1em", height: "1em", fill: "none", stroke: "currentColor", strokeWidth: 1.6 },
    h("circle", { cx: 12, cy: 12, r: 2.2 }),
    ...[0, 90, 180, 270].map(angle => h("path", { key: angle, transform: `rotate(${angle} 12 12)`, d: "M11 9 C5 9 5 2 9 2 C13 2 15 5 13 9" })));
}

function Panel() {
  const [status, updateStatus] = R.useState(null);
  const [editing, updateEditing] = R.useState(draft.config);
  const [dirty, updateDirty] = R.useState(draft.dirty);
  const [busy, updateBusy] = R.useState(false);
  const [error, updateError] = R.useState("");
  R.useEffect(() => {
    let alive = true;
    let pending = false;
    const syncDraft = () => { updateEditing(draft.config); updateDirty(draft.dirty); };
    draft.listeners.add(syncDraft);
    const refresh = async () => {
      if (pending) return;
      pending = true;
      try {
        const next = await getStatus();
        if (!alive) return;
        if (!next.ok) { updateError(next.error || "The fan service is unavailable."); return; }
        updateStatus(next);
        if (!draft.dirty) draft.config = next.config;
        syncDraft();
      } catch (cause) {
        if (alive) updateError(String(cause));
      } finally { pending = false; }
    };
    refresh();
    const timer = setInterval(refresh, 2000);
    return () => { alive = false; clearInterval(timer); draft.listeners.delete(syncDraft); };
  }, []);

  const edit = changes => {
    draft.config = { ...draft.config, ...changes };
    draft.dirty = true;
    publishDraft();
  };
  const apply = async config => {
    updateBusy(true);
    updateError("");
    try {
      const next = await setConfig(config);
      if (!next.ok) throw new Error(next.error || next.fault || "Fan setting could not be applied.");
      updateStatus(next);
      draft.config = next.config;
      draft.dirty = false;
      publishDraft();
    } catch (cause) { updateError(cause.message || String(cause)); }
    finally { updateBusy(false); }
  };
  const telemetry = status?.telemetry;
  const modeLabel = telemetry?.hardware_mode === 2 ? "Firmware automatic" : telemetry?.hardware_mode === 1 ? ({ quiet: "Quiet", curve: "Custom curve" }[status?.config?.mode] || "Manual") : "Unavailable";
  const row = (key, node) => h(PanelSectionRow, { key }, node);
  const note = (text, color = "#aeb8c4") => h("div", { style: { fontSize: "12px", lineHeight: "1.5", padding: "6px 0", color } }, text);
  const controls = [
    row("telemetry", h("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", padding: "4px 0 12px" } },
      h("div", null, note("Fan speed"), h("strong", { style: { fontSize: "22px" } }, telemetry ? `${telemetry.rpm.toLocaleString()} RPM` : "—")),
      h("div", null, note("CPU temperature"), h("strong", { style: { fontSize: "22px" } }, telemetry ? `${telemetry.cpu_c.toFixed(1)} °C` : "—")))),
    row("state", note(`${modeLabel}${telemetry?.hardware_mode === 1 && status?.effective_percent != null ? ` · ${status.effective_percent}% duty` : ""}`)),
    row("mode", h(DropdownItem, { label: "Fan mode", selectedOption: editing.mode, disabled: busy || !status,
      rgOptions: [{ label: "Automatic", data: "auto" }, { label: "Manual", data: "manual" }, { label: "Custom curve", data: "curve" }, { label: "Quiet", data: "quiet" }],
      onChange: option => edit({ mode: option.data }) }))
  ];
  if (editing.mode === "manual") controls.push(row("duty", h(SliderField, { label: "Fan duty", value: editing.percent, min: 0, max: 100, step: 1, showValue: true, disabled: busy,
    onChange: value => edit({ percent: Math.round(value) }) })));
  const anchors = status?.anchors || [40, 55, 65, 75, 95];
  if (editing.mode === "quiet") {
    controls.push(row("quiet", note("Quiet allows warmer operation with less fan noise. Your custom curve is kept separately.")));
    if (status?.quiet_points) controls.push(row("quiet-points", note(status.quiet_points.map(([temperature, duty]) => `${temperature} °C: ${duty}%`).join(" · "))));
  }
  if (editing.mode === "curve" || (editing.mode === "quiet" && status?.quiet_points)) {
    const curvePoints = editing.mode === "quiet" ? status.quiet_points : anchors.map((temperature, index) => [temperature, editing.curve[index]]);
    const start = curvePoints[0][0], end = curvePoints[curvePoints.length - 1][0];
    const points = curvePoints.map(([temperature, value]) => `${8 + (temperature - start) / (end - start) * 224},${78 - value * 0.6}`).join(" ");
    controls.push(row("graph", h("svg", { viewBox: "0 0 240 90", role: "img", "aria-label": `Fan curve from ${start} to ${end} degrees`, style: { width: "100%", height: "90px" } },
      h("path", { d: "M8 10 V80 H236", stroke: "#556373", fill: "none" }),
      h("polyline", { points, fill: "none", stroke: "#66d9ef", strokeWidth: 3 }))));
  }
  if (editing.mode === "curve") {
    anchors.forEach((temperature, index) => controls.push(row(`point-${temperature}`, h(SliderField, {
      label: `${temperature} °C`, value: editing.curve[index], min: 0, max: 100, step: 1, showValue: true,
      disabled: busy || index === anchors.length - 1,
      onChange: value => {
        const curve = [...editing.curve];
        curve[index] = Math.round(value);
        for (let i = index - 1; i >= 0; i--) curve[i] = Math.min(curve[i], curve[index]);
        for (let i = index + 1; i < curve.length; i++) curve[i] = Math.max(curve[i], curve[index]);
        curve[curve.length - 1] = 100;
        edit({ curve });
      }
    }))));
  }
  controls.push(row("apply", h(ButtonItem, { layout: "below", disabled: busy || !status || !dirty, onClick: () => apply(editing) }, busy ? "Applying…" : "Apply changes")));
  controls.push(row("auto", h(ButtonItem, { layout: "below", disabled: busy || !status, onClick: () => apply({ ...editing, mode: "auto" }) }, "Restore automatic control")));
  if (dirty) controls.push(row("unsaved", note("Changes are waiting to be applied.")));
  if (status?.fault) controls.push(row("fault", note(status.fault, "#ffbe7a")));
  if (error) controls.push(row("error", note(error, "#ffbe7a")));
  controls.push(row("help", note(`0% allows a stop when cool. Nonzero output uses a 10% running floor. Full cooling starts at ${status?.full_speed_c ?? 95} °C; firmware recovery starts at ${status?.recovery_c ?? 98} °C. Control continues with this menu closed.`)));
  return h(PanelSection, { title: "AYANEO 3" }, ...controls);
}

export default definePlugin(() => ({
  title: h("div", { className: window.DFL.staticClasses.Title }, "Ayaneo3 Fans"),
  content: h(Panel),
  icon: h(FanIcon)
}));
