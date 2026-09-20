import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import vm from "node:vm";
import test from "node:test";

// Exercise panel callbacks without Steam, a browser, or a hardware connection.
async function harness() {
  let state = {
    ok: true, config: { mode: "auto", percent: 15, curve: [10, 30, 40, 70, 100] },
    anchors: [40, 55, 65, 75, 95], full_speed_c: 95, recovery_c: 98,
    quiet_points: [[45, 0], [55, 15], [65, 25], [75, 35], [85, 55], [90, 75], [95, 100]],
    telemetry: { hardware_mode: 2, rpm: 2100, cpu_c: 43 }, effective_percent: null,
  };
  let values = [], cursor = 0, effect, cleanup, timer, mounted = false;
  const sent = [];
  const clone = value => JSON.parse(JSON.stringify(value));
  const context = vm.createContext({
    window: {
      SP_REACT: {
        createElement: (type, props, ...children) => ({ type, props: props || {}, children }),
        useState(initial) {
          const index = cursor++;
          if (!(index in values)) values[index] = initial;
          return [values[index], value => { values[index] = value; }];
        },
        useEffect(callback) { if (!mounted) effect = callback; },
      },
      DFL: Object.fromEntries(["PanelSection", "PanelSectionRow", "DropdownItem", "SliderField", "ButtonItem"].map(name => [name, name])),
    },
    callable: name => async config => {
      if (name === "set_config") {
        sent.push(clone(config));
        state = { ...state, config: clone(config), effective_percent: 15,
          telemetry: { ...state.telemetry, hardware_mode: 1 } };
      }
      return clone(state);
    },
    definePlugin: callback => callback,
    setInterval: callback => { timer = callback; return 1; }, clearInterval() {},
  });
  const source = await readFile(new URL("../src/panel.js", import.meta.url), "utf8");
  vm.runInContext(source.replace("export default definePlugin", "globalThis.plugin = definePlugin"), context);
  const render = () => { cursor = 0; return vm.runInContext("Panel()", context); };
  const mount = async () => {
    values = []; mounted = false; render(); mounted = true; cleanup = effect();
    // Drain the async refresh across the VM boundary before inspecting a render.
    await new Promise(resolve => setImmediate(resolve));
    return render();
  };
  return { render, mount, sent, poll: () => timer(), unmount: () => cleanup() };
}

function nodes(tree) { return [tree, ...tree.children.filter(child => child && typeof child === "object").flatMap(nodes)]; }
function component(tree, type) { return nodes(tree).find(node => node.type === type); }
function button(tree, label) { return nodes(tree).find(node => node.type === "ButtonItem" && node.children.includes(label)); }

test("Quiet selection survives polling and remount, then applies without replacing custom settings", async () => {
  const ui = await harness();
  let tree = await ui.mount();
  const dropdown = component(tree, "DropdownItem");
  assert.ok(dropdown.props.rgOptions.some(option => option.label === "Quiet" && option.data === "quiet"));
  dropdown.props.onChange({ data: "quiet" });
  await ui.poll();
  assert.equal(component(ui.render(), "DropdownItem").props.selectedOption, "quiet");
  ui.unmount();
  tree = await ui.mount();
  assert.equal(component(tree, "DropdownItem").props.selectedOption, "quiet");
  assert.equal(component(tree, "SliderField"), undefined);
  assert.equal(component(tree, "svg").props["aria-label"], "Fan curve from 45 to 95 degrees");
  await button(tree, "Apply changes").props.onClick();
  assert.deepEqual(ui.sent, [{ mode: "quiet", percent: 15, curve: [10, 30, 40, 70, 100] }]);
  assert.equal(button(ui.render(), "Apply changes").props.disabled, true);
  assert.match(JSON.stringify(ui.render()), /Quiet · 15% duty/);
  ui.unmount();
});

test("Custom editor retains zero minimum and the fixed 95 C endpoint after selecting Quiet", async () => {
  const ui = await harness();
  let tree = await ui.mount();
  component(tree, "DropdownItem").props.onChange({ data: "quiet" });
  component(ui.render(), "DropdownItem").props.onChange({ data: "curve" });
  tree = ui.render();
  const sliders = nodes(tree).filter(node => node.type === "SliderField");
  assert.deepEqual(sliders.map(slider => slider.props.value), [10, 30, 40, 70, 100]);
  assert.ok(sliders.every(slider => slider.props.min === 0));
  assert.equal(sliders[4].props.label, "95 °C");
  assert.equal(sliders[4].props.disabled, true);
  assert.equal(component(tree, "svg").props["aria-label"], "Fan curve from 40 to 95 degrees");
  ui.unmount();
});
