---
name: interactive-html-visualization
description: Create simple, self-contained interactive HTML visualizations (charts, diagrams, simulations, explorers) as a single file with no build step. Use when the user asks to visualize data, build an interactive chart, animate an algorithm or concept, or make a small interactive explainer page.
---

# Interactive HTML Visualization

## Goal
Produce a single `.html` file that opens directly in a browser, works offline, and lets the user interact (hover, sliders, buttons, toggles, drag) with the visualization.

## Workflow
1. **Clarify the essentials** (only if missing): data source or sample data, what the user should be able to change, and the key insight to show.
2. **Pick the lightest tool that fits:**
   - Plain SVG/Canvas + vanilla JS: shapes, simple charts, animations, simulations (default choice).
   - D3.js (via CDN): data-driven SVG with scales, axes, and transitions.
   - Chart.js (via CDN): standard bar/line/pie charts with tooltips.
   - Three.js (via CDN): only for genuinely 3D content.
3. **Structure the file** (see template below).
4. **Verify**: check that controls update the view, there are no console errors, and the layout works at narrow and wide widths.
5. **Deliver** the complete file in one code block, followed by a short list of how to use the controls.

## Rules
- One file: inline `<style>` and `<script>`. No npm, no bundler, no framework unless requested.
- Pin CDN library versions (e.g., `https://cdn.jsdelivr.net/npm/d3@7`). Prefer one library at most.
- Keep data in a clearly labeled `const data = [...]` block at the top of the script so it's easy to replace.
- Use semantic, readable JS: small functions, no global mess, `const`/`let`.
- Make it responsive: use `viewBox` for SVG or resize the canvas on `resize`.
- Provide accessible basics: labels on controls, `aria-label` on key SVG elements, sufficient color contrast, and don't rely on color alone.
- Include a short on-page caption or legend explaining what the user is seeing.
- Avoid heavy animation loops; cap frame work and use `requestAnimationFrame`.
- Never fetch external data at runtime unless the user provides a URL; embed sample data instead.

## Interaction Patterns (pick what fits)
- **Hover/tooltip**: show values on `mouseover` or `pointermove`.
- **Sliders/inputs**: re-render on `input` events, not only `change`.
- **Play/pause/step**: a timer or `requestAnimationFrame` loop with a speed control.
- **Filter/toggle**: checkboxes or buttons that show/hide series.
- **Drag**: use Pointer Events so touch and mouse both work.
- **Reset**: a button that restores initial state.

## Template

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{Title}}</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 1rem; color: #222; }
    #chart { width: 100%; max-width: 800px; height: 420px; }
    .controls { display: flex; gap: 1rem; flex-wrap: wrap; align-items: center; margin-bottom: 1rem; }
    .caption { color: #555; font-size: 0.9rem; margin-top: 0.5rem; }
  </style>
</head>
<body>
  <h1>{{Title}}</h1>
  <div class="controls">
    <label>Value: <input id="param" type="range" min="0" max="100" value="50"></label>
    <output id="readout">50</output>
    <button id="reset">Reset</button>
  </div>
  <svg id="chart" viewBox="0 0 800 420" role="img" aria-label="{{Description}}"></svg>
  <p class="caption">{{What the user is seeing and how to interact.}}</p>

  <script>
    // ---- Data (replace with your own) ----
    const data = [
      { label: "A", value: 30 },
      { label: "B", value: 80 },
      { label: "C", value: 45 }
    ];

    // ---- Elements ----
    const svg = document.getElementById("chart");
    const param = document.getElementById("param");
    const readout = document.getElementById("readout");
    const NS = "http://www.w3.org/2000/svg";

    // ---- Render ----
    function render(p) {
      readout.textContent = p;
      svg.innerHTML = "";
      const barW = 80, gap = 40, maxH = 340;
      data.forEach((d, i) => {
        const h = (d.value * p / 100) / 100 * maxH;
        const x = 60 + i * (barW + gap);
        const y = 380 - h;

        const rect = document.createElementNS(NS, "rect");
        rect.setAttribute("x", x);
        rect.setAttribute("y", y);
        rect.setAttribute("width", barW);
        rect.setAttribute("height", h);
        rect.setAttribute("fill", "#4a7fd1");

        const title = document.createElementNS(NS, "title");
        title.textContent = `${d.label}: ${(d.value * p / 100).toFixed(1)}`;
        rect.appendChild(title);

        const label = document.createElementNS(NS, "text");
        label.setAttribute("x", x + barW / 2);
        label.setAttribute("y", 400);
        label.setAttribute("text-anchor", "middle");
        label.textContent = d.label;

        svg.append(rect, label);
      });
    }

    // ---- Events ----
    param.addEventListener("input", e => render(+e.target.value));
    document.getElementById("reset").addEventListener("click", () => {
      param.value = 50;
      render(50);
    });

    render(+param.value);
  </script>
</body>
</html>
