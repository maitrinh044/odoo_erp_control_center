/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class LiveThemePreviewWidget extends Component {
    static template = "sgt_erp_control_center.LiveThemePreview";
    static props = {
        ...standardWidgetProps,
    };

    setup() {
        this.state = useState({
            isDark: false,
            viewMode: "desktop",
        });
    }

    get themeData() {
        const d = (this.props.record && this.props.record.data) || {};
        return {
            primary: d.primary_color || "#165DFF",
            secondary: d.secondary_color || "#09244B",
            accent: d.accent_color || "#FFB020",
            bg: d.background_color || (this.state.isDark ? "#111827" : "#F4F6FA"),
            cardBg: d.card_background || d.card_bg || (this.state.isDark ? "#1F2937" : "#FFFFFF"),
            text: d.text_color || (this.state.isDark ? "#F9FAFB" : "#1D2129"),
            border: d.border_color || (this.state.isDark ? "#374151" : "#E5E7EB"),
            navbarBg: d.navbar_bg || "#09244B",
            navbarText: d.navbar_text_color || "#FFFFFF",
            navbarHover: d.navbar_hover_color || d.navbar_hover_bg || "#165DFF",
            sidebarBg: d.sidebar_bg || (this.state.isDark ? "#111827" : "#071A34"),
            sidebarText: d.sidebar_text_color || (this.state.isDark ? "#9CA3AF" : "#D1D5DB"),
            sidebarActive: d.sidebar_active_color || d.primary_color || "#165DFF",
            btnPrimary: d.btn_primary_color || d.btn_primary_bg || d.primary_color || "#165DFF",
            btnSecondary: d.btn_secondary_color || "#6B7280",
            btnText: d.btn_text_color || "#FFFFFF",
            btnRadius: (d.btn_radius !== undefined && d.btn_radius !== null ? d.btn_radius : 6) + "px",
            cardRadius: (d.card_radius !== undefined && d.card_radius !== null ? d.card_radius : 10) + "px",
            fontFamily: d.font_family ? `${d.font_family}, sans-serif` : "Inter, sans-serif",
            listAlternateRow: d.list_alternate_row !== false,
        };
    }

    toggleDark() {
        this.state.isDark = !this.state.isDark;
    }

    toggleViewMode(mode) {
        this.state.viewMode = mode;
    }
}

export const liveThemePreviewWidget = {
    component: LiveThemePreviewWidget,
};

registry.category("view_widgets").add("sgt_live_theme_preview", liveThemePreviewWidget);
