/** @odoo-module **/

import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

export const sgtThemeService = {
    dependencies: ["title"],
    async start(env, { title }) {
        async function applyThemeVariables() {
            try {
                const data = await rpc("/sgt_erp/active_theme", {});
                if (!data) return;

                // 1. Inject CSS Variables into Document Root
                if (data.css_variables) {
                    const root = document.documentElement;
                    for (const [prop, val] of Object.entries(data.css_variables)) {
                        if (val) {
                            root.style.setProperty(prop, val);
                        }
                    }
                }

                // 2. Set White-label Browser Title
                if (data.browser_title) {
                    try {
                        title.setParts({ zph: data.browser_title });
                    } catch (err) {
                        document.title = data.browser_title;
                    }
                }
            } catch (err) {
                console.warn("[SGT ERP] Unable to load active theme variables:", err);
            }
        }

        // Run when WebClient starts
        await applyThemeVariables();

        return {
            reloadTheme: applyThemeVariables,
        };
    },
};

registry.category("services").add("sgt_theme_service", sgtThemeService);

/**
 * Client action to immediately preview or revert a theme across the entire browser window
 */
function previewThemeAction(env, action) {
    const params = action.params || {};
    const cssVars = params.css_variables || {};
    const themeName = params.theme_name || "Theme";
    const isReset = params.is_reset || false;

    if (cssVars) {
        const root = document.documentElement;
        for (const [prop, val] of Object.entries(cssVars)) {
            if (val) {
                root.style.setProperty(prop, val);
            }
        }
    }

    if (env.services && env.services.notification) {
        if (isReset) {
            env.services.notification.add(
                `Đã thoát chế độ xem trước và khôi phục về theme chính thức: "${themeName}".`,
                {
                    title: `Khôi Phục Giao Diện`,
                    type: "success",
                    sticky: false,
                }
            );
        } else {
            env.services.notification.add(
                `Đang xem trước trực tiếp theme "${themeName}"! Bấm nút "Exit Preview (Hoàn tác)" trên thanh công cụ để khôi phục theme cũ.`,
                {
                    title: `Xem Trước Theme: ${themeName}`,
                    type: "info",
                    sticky: false,
                }
            );
        }
    }
}

registry.category("actions").add("sgt_preview_theme_action", previewThemeAction);
