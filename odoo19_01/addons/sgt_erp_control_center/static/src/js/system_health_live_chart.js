/** @odoo-module **/

import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

const MAX_HISTORY = 60;

/**
 * Shared Telemetry Manager to coordinate a single polling loop for both CPU and RAM charts
 */
class TelemetryManager {
    constructor() {
        this.listeners = new Set();
        this.cpuHistory = new Array(MAX_HISTORY).fill(0);
        this.ramHistory = new Array(MAX_HISTORY).fill(0);
        this.isPaused = false;
        this.intervalMs = 2000;
        this.pollTimer = null;
        this.isFetching = false;
        this.stats = {
            cpu: { percentage: 0, cores: 1, load_1m: 0, load_5m: 0, load_15m: 0, model: "" },
            ram: { percentage: 0, used_gb: 0, free_gb: 0, total_gb: 0 },
            storage: { os_disk_percentage: 0, data_disk_percentage: 0, database_size_mb: 0 },
            system: { active_connections: 1, uptime: "N/A", server_time: "--:--:--" },
        };

        this.onVisibilityChange = this.handleVisibilityChange.bind(this);
        document.addEventListener("visibilitychange", this.onVisibilityChange);
    }

    subscribe(listener) {
        this.listeners.add(listener);
        if (this.listeners.size === 1) {
            this.fetchStats();
            this.startPolling();
        } else {
            // Immediate notify with latest cached state
            listener(this.stats, this.cpuHistory, this.ramHistory, this.isPaused, this.intervalMs);
        }
    }

    unsubscribe(listener) {
        this.listeners.delete(listener);
        if (this.listeners.size === 0) {
            this.stopPolling();
        }
    }

    startPolling() {
        this.stopPolling();
        if (!this.isPaused && this.listeners.size > 0) {
            this.pollTimer = setInterval(() => {
                this.fetchStats();
            }, this.intervalMs);
        }
    }

    stopPolling() {
        if (this.pollTimer) {
            clearInterval(this.pollTimer);
            this.pollTimer = null;
        }
    }

    handleVisibilityChange() {
        if (document.hidden) {
            this.stopPolling();
        } else if (!this.isPaused && this.listeners.size > 0) {
            this.fetchStats();
            this.startPolling();
        }
    }

    togglePause() {
        this.isPaused = !this.isPaused;
        if (this.isPaused) {
            this.stopPolling();
        } else {
            this.fetchStats();
            this.startPolling();
        }
        this.notify();
    }

    changeInterval(ms) {
        this.intervalMs = ms;
        if (!this.isPaused) {
            this.startPolling();
        }
        this.notify();
    }

    async fetchStats() {
        if (this.isFetching) return;
        this.isFetching = true;
        try {
            const data = await rpc("/sgt_erp/system_health/live_stats", {});
            if (data && data.cpu && data.ram) {
                this.stats = data;

                this.cpuHistory.push(data.cpu.percentage || 0);
                if (this.cpuHistory.length > MAX_HISTORY) {
                    this.cpuHistory.shift();
                }

                this.ramHistory.push(data.ram.percentage || 0);
                if (this.ramHistory.length > MAX_HISTORY) {
                    this.ramHistory.shift();
                }

                this.notify();
            }
        } catch (err) {
            console.warn("[SGT Health Live] Telemetry poll notice:", err);
        } finally {
            this.isFetching = false;
        }
    }

    notify() {
        for (const listener of this.listeners) {
            listener(this.stats, this.cpuHistory, this.ramHistory, this.isPaused, this.intervalMs);
        }
    }
}

const telemetryManager = new TelemetryManager();

/**
 * Common Canvas Rendering Helper (Pure White Background)
 */
function drawTelemetryWaveform(canvas, dataPoints, strokeColor, fillColorTop, fillColorBottom, maxValue = 100) {
    if (!canvas) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;

    if (width === 0 || height === 0) return;

    if (canvas.width !== Math.round(width * dpr) || canvas.height !== Math.round(height * dpr)) {
        canvas.width = Math.round(width * dpr);
        canvas.height = Math.round(height * dpr);
    }

    const ctx = canvas.getContext("2d");
    ctx.resetTransform ? ctx.resetTransform() : ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.scale(dpr, dpr);

    // 1. Fill Clean White Background
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, width, height);

    // 2. Draw Subtle Light Grid Lines (25%, 50%, 75%, 100%)
    ctx.lineWidth = 1;
    ctx.strokeStyle = "#f1f5f9";
    ctx.fillStyle = "#94a3b8";
    ctx.font = "10px sans-serif";

    const horizontalSteps = 4;
    for (let i = 0; i <= horizontalSteps; i++) {
        const y = Math.round((height / horizontalSteps) * i) - 0.5;
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();

        if (i === 0) {
            ctx.fillText("100%", 6, 12);
        } else if (i === 2) {
            ctx.fillText("50%", 6, y - 3);
        }
    }

    // Vertical grid lines (10 intervals)
    const verticalSteps = 10;
    for (let j = 1; j < verticalSteps; j++) {
        const x = Math.round((width / verticalSteps) * j) - 0.5;
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
    }

    if (!dataPoints || dataPoints.length < 2) return;

    const stepX = width / (MAX_HISTORY - 1);

    // 3. Draw Soft Area Fill Gradient
    const gradient = ctx.createLinearGradient(0, 0, 0, height);
    gradient.addColorStop(0, fillColorTop);
    gradient.addColorStop(1, fillColorBottom);

    ctx.beginPath();
    dataPoints.forEach((val, index) => {
        const clampedVal = Math.max(0, Math.min(val, maxValue));
        const x = index * stepX;
        const y = height - (clampedVal / maxValue) * (height - 8) - 4;
        if (index === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    });
    ctx.lineTo(width, height);
    ctx.lineTo(0, height);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();

    // 4. Draw Crisp Waveform Stroke Line
    ctx.beginPath();
    dataPoints.forEach((val, index) => {
        const clampedVal = Math.max(0, Math.min(val, maxValue));
        const x = index * stepX;
        const y = height - (clampedVal / maxValue) * (height - 8) - 4;
        if (index === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    });
    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = 2;
    ctx.lineJoin = "round";
    ctx.stroke();

    // 5. Head Pulse Point at the latest value
    const latestVal = dataPoints[dataPoints.length - 1];
    const clampedLatest = Math.max(0, Math.min(latestVal, maxValue));
    const headX = (dataPoints.length - 1) * stepX;
    const headY = height - (clampedLatest / maxValue) * (height - 8) - 4;

    ctx.beginPath();
    ctx.arc(headX, headY, 3.5, 0, Math.PI * 2);
    ctx.fillStyle = "#ffffff";
    ctx.fill();
    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = 2;
    ctx.stroke();
}

/**
 * CPU Live Waveform Widget (Embedded inside CPU Card)
 */
export class LiveCpuChartWidget extends Component {
    static template = "sgt_erp_control_center.LiveCpuChart";
    static props = {
        ...standardWidgetProps,
    };

    setup() {
        this.cpuCanvasRef = useRef("cpuCanvas");
        this.state = useState({
            isPaused: telemetryManager.isPaused,
            intervalMs: telemetryManager.intervalMs,
            stats: telemetryManager.stats,
        });

        this.listener = (stats, cpuHistory, ramHistory, isPaused, intervalMs) => {
            this.state.stats = stats;
            this.state.isPaused = isPaused;
            this.state.intervalMs = intervalMs;
            this.renderChart(cpuHistory);
            this.syncParentCard(stats);
        };

        this.onResize = () => {
            this.renderChart(telemetryManager.cpuHistory);
        };

        onMounted(() => {
            telemetryManager.subscribe(this.listener);
            window.addEventListener("resize", this.onResize);
            this.renderChart(telemetryManager.cpuHistory);
            this.syncParentCard(telemetryManager.stats);
        });

        onWillUnmount(() => {
            telemetryManager.unsubscribe(this.listener);
            window.removeEventListener("resize", this.onResize);
        });
    }

    syncParentCard(stats) {
        const card = this.cpuCanvasRef.el?.closest(".card");
        if (!card || !stats || !stats.cpu) return;

        // 1. Header Badge
        const badge = card.querySelector(".o_live_cpu_badge");
        if (badge) {
            badge.textContent = `${stats.cpu.percentage}% Load`;
        }

        // 2. Load 1m, 5m, 15m
        const load1m = card.querySelector(".o_live_cpu_load_1m");
        if (load1m && stats.cpu.load_1m != null) load1m.textContent = stats.cpu.load_1m;
        const load5m = card.querySelector(".o_live_cpu_load_5m");
        if (load5m && stats.cpu.load_5m != null) load5m.textContent = stats.cpu.load_5m;
        const load15m = card.querySelector(".o_live_cpu_load_15m");
        if (load15m && stats.cpu.load_15m != null) load15m.textContent = stats.cpu.load_15m;

        // 3. Progressbar
        const pbarContainer = card.querySelector(".o_live_cpu_pbar_container");
        if (pbarContainer) {
            const valEl = pbarContainer.querySelector(".o_progressbar_value");
            if (valEl) valEl.textContent = `${Math.round(stats.cpu.percentage)}%`;
            const barFill = pbarContainer.querySelector(".o_progress");
            if (barFill) barFill.style.width = `${Math.min(100, Math.max(0, stats.cpu.percentage))}%`;
        }
    }

    renderChart(cpuHistory) {
        drawTelemetryWaveform(
            this.cpuCanvasRef.el,
            cpuHistory,
            "#2563eb",                 // Royal Blue Line
            "rgba(37, 99, 235, 0.16)",  // Top gradient fill
            "rgba(37, 99, 235, 0.01)",  // Bottom gradient fill
            100
        );
    }

    togglePause() {
        telemetryManager.togglePause();
    }

    changeInterval(ms) {
        telemetryManager.changeInterval(ms);
    }

    refreshNow() {
        telemetryManager.fetchStats();
    }
}

/**
 * RAM Live Waveform Widget (Embedded inside RAM Card)
 */
export class LiveRamChartWidget extends Component {
    static template = "sgt_erp_control_center.LiveRamChart";
    static props = {
        ...standardWidgetProps,
    };

    setup() {
        this.ramCanvasRef = useRef("ramCanvas");
        this.state = useState({
            isPaused: telemetryManager.isPaused,
            intervalMs: telemetryManager.intervalMs,
            stats: telemetryManager.stats,
        });

        this.listener = (stats, cpuHistory, ramHistory, isPaused, intervalMs) => {
            this.state.stats = stats;
            this.state.isPaused = isPaused;
            this.state.intervalMs = intervalMs;
            this.renderChart(ramHistory);
            this.syncParentCard(stats);
        };

        this.onResize = () => {
            this.renderChart(telemetryManager.ramHistory);
        };

        onMounted(() => {
            telemetryManager.subscribe(this.listener);
            window.addEventListener("resize", this.onResize);
            this.renderChart(telemetryManager.ramHistory);
            this.syncParentCard(telemetryManager.stats);
        });

        onWillUnmount(() => {
            telemetryManager.unsubscribe(this.listener);
            window.removeEventListener("resize", this.onResize);
        });
    }

    syncParentCard(stats) {
        const card = this.ramCanvasRef.el?.closest(".card");
        if (!card || !stats || !stats.ram) return;

        // 1. Header Badge
        const badge = card.querySelector(".o_live_ram_badge");
        if (badge) {
            badge.textContent = `${stats.ram.percentage}% Used`;
        }

        // 2. Used, Free, Total GB
        const usedEl = card.querySelector(".o_live_ram_used");
        if (usedEl && stats.ram.used_gb != null) usedEl.textContent = stats.ram.used_gb;
        const freeEl = card.querySelector(".o_live_ram_free");
        if (freeEl && stats.ram.free_gb != null) freeEl.textContent = stats.ram.free_gb;
        const totalEl = card.querySelector(".o_live_ram_total");
        if (totalEl && stats.ram.total_gb != null) totalEl.textContent = stats.ram.total_gb;

        // 3. Progressbar
        const pbarContainer = card.querySelector(".o_live_ram_pbar_container");
        if (pbarContainer) {
            const valEl = pbarContainer.querySelector(".o_progressbar_value");
            if (valEl) valEl.textContent = `${Math.round(stats.ram.percentage)}%`;
            const barFill = pbarContainer.querySelector(".o_progress");
            if (barFill) barFill.style.width = `${Math.min(100, Math.max(0, stats.ram.percentage))}%`;
        }

        // 4. Server Uptime and Time
        if (stats.system) {
            const uptimeEl = card.querySelector(".o_live_server_uptime");
            if (uptimeEl && stats.system.uptime) uptimeEl.textContent = stats.system.uptime;
            const timeEl = card.querySelector(".o_live_server_time");
            if (timeEl && stats.system.server_time) timeEl.textContent = stats.system.server_time;
        }
    }

    renderChart(ramHistory) {
        drawTelemetryWaveform(
            this.ramCanvasRef.el,
            ramHistory,
            "#7c3aed",                 // Vivid Violet Line
            "rgba(124, 58, 237, 0.16)", // Top gradient fill
            "rgba(124, 58, 237, 0.01)", // Bottom gradient fill
            100
        );
    }

    refreshNow() {
        telemetryManager.fetchStats();
    }
}

export const liveCpuChartWidget = {
    component: LiveCpuChartWidget,
};

export const liveRamChartWidget = {
    component: LiveRamChartWidget,
};

// Register separate widgets into Odoo 19 view_widgets registry
registry.category("view_widgets").add("sgt_live_cpu_chart", liveCpuChartWidget);
registry.category("view_widgets").add("sgt_live_ram_chart", liveRamChartWidget);
registry.category("view_widgets").add("sgt_live_system_health", liveCpuChartWidget);
