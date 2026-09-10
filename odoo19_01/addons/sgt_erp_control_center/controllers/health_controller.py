# -*- coding: utf-8 -*-
import os
import platform
import shutil
from datetime import datetime
from odoo import http, fields, _
from odoo.http import request
from odoo.tools import config

def _get_dir_size_mb(path):
    total = 0
    try:
        if os.path.exists(path):
            for dirpath, dirnames, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if not os.path.islink(fp):
                        total += os.path.getsize(fp)
    except Exception:
        pass
    return round(total / (1024 * 1024), 2)


_last_cpu_stat = {'idle': 0.0, 'total': 0.0}

def _get_cpu_instant_percentage(cores=1):
    global _last_cpu_stat
    cpu_percentage = None
    if os.path.exists('/proc/stat'):
        try:
            with open('/proc/stat', 'r') as f:
                first_line = f.readline().strip()
                if first_line.startswith('cpu'):
                    parts = [float(x) for x in first_line.split()[1:]]
                    idle = parts[3] + (parts[4] if len(parts) > 4 else 0.0)
                    total = sum(parts)
                    if _last_cpu_stat['total'] > 0:
                        idle_delta = idle - _last_cpu_stat['idle']
                        total_delta = total - _last_cpu_stat['total']
                        if total_delta > 0:
                            usage = 100.0 * (1.0 - max(0.0, idle_delta) / total_delta)
                            cpu_percentage = round(min(100.0, max(0.0, usage)), 1)
                    _last_cpu_stat['idle'] = idle
                    _last_cpu_stat['total'] = total
        except Exception:
            pass

    if cpu_percentage is None:
        if hasattr(os, 'getloadavg'):
            try:
                load = os.getloadavg()
                cpu_percentage = round(min((load[0] / cores) * 100.0, 100.0), 1)
            except Exception:
                cpu_percentage = 0.0
        else:
            cpu_percentage = 0.0

    return cpu_percentage


class SgtSystemHealthController(http.Controller):

    @http.route('/sgt_erp/system_health/live_stats', type='jsonrpc', auth='user', methods=['POST'])
    def get_live_stats(self, **kwargs):
        """Fetch high-precision real-time system metrics for OWL live monitor."""
        env = kwargs.get('env')
        if not env:
            try:
                env = request.env
            except Exception:
                env = None
        
        # 1. CPU Telemetry
        cores = os.cpu_count() or 1
        cpu_load_1m, cpu_load_5m, cpu_load_15m = 0.0, 0.0, 0.0
        if hasattr(os, 'getloadavg'):
            try:
                load = os.getloadavg()
                cpu_load_1m = round(load[0], 2)
                cpu_load_5m = round(load[1], 2)
                cpu_load_15m = round(load[2], 2)
            except Exception:
                pass

        cpu_percentage = _get_cpu_instant_percentage(cores=cores)

        cpu_model = platform.processor() or "Generic CPU"
        if os.path.exists('/proc/cpuinfo'):
            try:
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if 'model name' in line:
                            cpu_model = line.split(':', 1)[1].strip()
                            break
            except Exception:
                pass

        # 2. RAM Telemetry
        ram_total_gb, ram_used_gb, ram_free_gb, ram_percentage = 0.0, 0.0, 0.0, 0.0
        if os.path.exists('/proc/meminfo'):
            try:
                mem = {}
                with open('/proc/meminfo', 'r') as f:
                    for line in f:
                        parts = line.split(':')
                        if len(parts) == 2:
                            mem[parts[0].strip()] = parts[1].strip()
                total_kb = int(mem.get('MemTotal', '0 kB').split()[0])
                avail_kb = int(mem.get('MemAvailable', '0 kB').split()[0])
                used_kb = max(0, total_kb - avail_kb)
                ram_total_gb = round(total_kb / (1024 * 1024), 2)
                ram_used_gb = round(used_kb / (1024 * 1024), 2)
                ram_free_gb = round(avail_kb / (1024 * 1024), 2)
                ram_percentage = round((used_kb / total_kb) * 100.0, 1) if total_kb else 0.0
            except Exception:
                pass

        # 3. Server Uptime
        uptime_str = "N/A"
        if os.path.exists('/proc/uptime'):
            try:
                with open('/proc/uptime', 'r') as f:
                    uptime_seconds = float(f.readline().split()[0])
                    days = int(uptime_seconds // (24 * 3600))
                    hours = int((uptime_seconds % (24 * 3600)) // 3600)
                    minutes = int((uptime_seconds % 3600) // 60)
                    if days > 0:
                        uptime_str = f"{days}d {hours}h {minutes}m"
                    else:
                        uptime_str = f"{hours}h {minutes}m"
            except Exception:
                pass

        # 4. Storage & Disks
        os_disk_percentage = 0.0
        try:
            os_total, os_used, _ = shutil.disk_usage('/')
            os_disk_percentage = round((os_used / os_total) * 100, 1) if os_total else 0.0
        except Exception:
            pass

        data_disk_percentage = 0.0
        try:
            data_path = config.get('data_dir') or '/'
            if not os.path.exists(data_path):
                data_path = '/'
            d_total, d_used, _ = shutil.disk_usage(data_path)
            data_disk_percentage = round((d_used / d_total) * 100, 1) if d_total else 0.0
        except Exception:
            pass

        # 5. Database metrics
        db_connections = 1
        db_size_mb = 0.0
        if env and hasattr(env, 'cr'):
            try:
                env.cr.execute("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database();")
                res = env.cr.fetchone()
                db_connections = res[0] if res else 1
                env.cr.execute("SELECT pg_database_size(current_database());")
                res = env.cr.fetchone()
                if res:
                    db_size_mb = round(res[0] / (1024 * 1024), 2)
            except Exception:
                pass

        return {
            'cpu': {
                'percentage': cpu_percentage,
                'cores': cores,
                'load_1m': cpu_load_1m,
                'load_5m': cpu_load_5m,
                'load_15m': cpu_load_15m,
                'model': cpu_model,
            },
            'ram': {
                'percentage': ram_percentage,
                'used_gb': ram_used_gb,
                'free_gb': ram_free_gb,
                'total_gb': ram_total_gb,
            },
            'storage': {
                'os_disk_percentage': os_disk_percentage,
                'data_disk_percentage': data_disk_percentage,
                'database_size_mb': db_size_mb,
            },
            'system': {
                'active_connections': db_connections,
                'uptime': uptime_str,
                'server_time': fields.Datetime.now().strftime('%H:%M:%S'),
            }
        }
