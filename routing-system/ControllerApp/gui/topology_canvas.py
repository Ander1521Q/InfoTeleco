"""
gui/topology_canvas.py
======================
TopologyCanvas: Tkinter canvas that draws the network graph.

Features:
- Nodes as colored circles with router ID labels
- Edges as lines with cost labels
- Active routers in green, INACTIVE in red/gray
- Highlighted path (yellow edges + orange nodes)
- Drag nodes to reposition
- Auto-layout in a circle when positions are not set
"""

import math
import tkinter as tk
from tkinter import font as tkfont


# ─── Colours ────────────────────────────────────────────────────────────────
C_BG         = "#1e1e2e"
C_NODE_ACTIVE= "#4ade80"   # green
C_NODE_DOWN  = "#f87171"   # red
C_NODE_BORDER= "#ffffff"
C_EDGE       = "#94a3b8"
C_EDGE_PATH  = "#facc15"   # yellow
C_NODE_PATH  = "#fb923c"   # orange
C_TEXT_NODE  = "#0f172a"
C_TEXT_EDGE  = "#e2e8f0"
C_TEXT_COST  = "#fde68a"
NODE_R       = 28          # node radius px


class TopologyCanvas(tk.Canvas):
    """Drawable, draggable network topology canvas."""

    def __init__(self, master, **kwargs):
        kwargs.setdefault("bg",     C_BG)
        kwargs.setdefault("highlightthickness", 0)
        super().__init__(master, **kwargs)

        self._positions: dict   = {}   # {router_id: (x, y)}
        self._topology:  dict   = {}   # {router_id: [{neighbor_id, cost}]}
        self._statuses:  dict   = {}   # {router_id: "ACTIVE"|"INACTIVE"}
        self._path:      list   = []   # list of router_ids forming the path
        self._drag_node: str | None = None
        self._drag_offset = (0, 0)

        self.bind("<ButtonPress-1>",   self._on_press)
        self.bind("<B1-Motion>",       self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Configure>",       self._on_resize)

    # ──────────────────────────────────────────────── public API
    def update_topology(self, topology: dict, statuses: dict = None):
        """
        topology : {router_id: [{"neighbor_id": str, "cost": float}]}
        statuses : {router_id: "ACTIVE"|"INACTIVE"}
        """
        self._topology = topology
        self._statuses = statuses or {}
        self._ensure_positions()
        self._draw()

    def highlight_path(self, path: list):
        """Highlight a sequence of routers as the best path."""
        self._path = path
        self._draw()

    def clear_path(self):
        self._path = []
        self._draw()

    # ──────────────────────────────────────────────── layout
    def _ensure_positions(self):
        nodes = set(self._topology.keys())
        for nbs in self._topology.values():
            for nb in nbs:
                nodes.add(nb["neighbor_id"])

        w = self.winfo_width()  or 600
        h = self.winfo_height() or 400
        cx, cy = w / 2, h / 2
        r  = min(cx, cy) * 0.62

        # Keep existing positions; only place new nodes
        new_nodes = [n for n in sorted(nodes) if n not in self._positions]
        existing  = [n for n in sorted(nodes) if n in self._positions]

        # Rebuild circle including existing nodes so layout is stable
        all_nodes = existing + new_nodes
        n = len(all_nodes)
        for i, node in enumerate(all_nodes):
            if node not in self._positions:
                angle = 2 * math.pi * i / max(n, 1) - math.pi / 2
                self._positions[node] = (
                    cx + r * math.cos(angle),
                    cy + r * math.sin(angle)
                )

        # Remove positions for nodes no longer in topology
        gone = set(self._positions) - nodes
        for g in gone:
            del self._positions[g]

    # ──────────────────────────────────────────────── drawing
    def _draw(self):
        self.delete("all")
        if not self._topology:
            self._draw_empty()
            return

        path_edges = set()
        if len(self._path) >= 2:
            for i in range(len(self._path) - 1):
                a, b = self._path[i], self._path[i + 1]
                path_edges.add((a, b))
                path_edges.add((b, a))

        drawn_edges = set()
        for src, nbs in self._topology.items():
            for nb in nbs:
                dst  = nb["neighbor_id"]
                key  = tuple(sorted([src, dst]))
                if key in drawn_edges:
                    continue
                drawn_edges.add(key)

                xs, ys = self._positions.get(src, (0, 0))
                xd, yd = self._positions.get(dst, (0, 0))
                on_path = (src, dst) in path_edges

                # Draw edge line
                self.create_line(
                    xs, ys, xd, yd,
                    fill=C_EDGE_PATH if on_path else C_EDGE,
                    width=3 if on_path else 1.5,
                    tags="edge"
                )

                # Cost label at midpoint
                mx, my = (xs + xd) / 2, (ys + yd) / 2
                self.create_text(
                    mx, my - 10,
                    text=str(nb["cost"]),
                    fill=C_TEXT_COST if on_path else C_TEXT_EDGE,
                    font=("Consolas", 9, "bold" if on_path else "normal"),
                    tags="cost_label"
                )

        # Draw nodes
        for node, (x, y) in self._positions.items():
            status  = self._statuses.get(node, "ACTIVE").upper()
            active  = status in ("ACTIVE", "ACTIVO")
            on_path = node in self._path

            fill = C_NODE_PATH if on_path else (C_NODE_ACTIVE if active else C_NODE_DOWN)
            outline_w = 3 if on_path else 1.5

            self.create_oval(
                x - NODE_R, y - NODE_R, x + NODE_R, y + NODE_R,
                fill=fill, outline=C_NODE_BORDER, width=outline_w,
                tags=("node", f"node_{node}")
            )
            self.create_text(
                x, y,
                text=node,
                fill=C_TEXT_NODE,
                font=("Consolas", 11, "bold"),
                tags=("node_label", f"label_{node}")
            )

            # Status dot under node
            if not active:
                self.create_text(
                    x, y + NODE_R + 12,
                    text="● INACTIVE",
                    fill=C_NODE_DOWN,
                    font=("Consolas", 8),
                )

        # Legend
        self._draw_legend()

    def _draw_empty(self):
        self.create_text(
            self.winfo_width() // 2 or 300,
            self.winfo_height() // 2 or 200,
            text="No topology yet.\nConnect routers to see the network.",
            fill="#64748b",
            font=("Consolas", 12),
            justify="center"
        )

    def _draw_legend(self):
        items = [
            (C_NODE_ACTIVE, "Active router"),
            (C_NODE_DOWN,   "Inactive router"),
            (C_NODE_PATH,   "Path node"),
            (C_EDGE_PATH,   "Shortest path"),
        ]
        x, y = 14, 14
        for color, label in items:
            self.create_oval(x, y, x+12, y+12, fill=color, outline="")
            self.create_text(x+18, y+6, text=label, fill="#94a3b8",
                             font=("Consolas", 9), anchor="w")
            y += 20

    # ──────────────────────────────────────────────── drag
    def _on_press(self, event):
        for node, (x, y) in self._positions.items():
            if math.hypot(event.x - x, event.y - y) <= NODE_R:
                self._drag_node = node
                self._drag_offset = (event.x - x, event.y - y)
                return

    def _on_drag(self, event):
        if self._drag_node:
            ox, oy = self._drag_offset
            self._positions[self._drag_node] = (event.x - ox, event.y - oy)
            self._draw()

    def _on_release(self, event):
        self._drag_node = None

    def _on_resize(self, event):
        if self._topology:
            self._draw()
