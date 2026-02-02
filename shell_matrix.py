"""
>_ SHELL MATRIX by Rondinelli Castilho - N0rd
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import asyncio
import os
import uuid
import threading
import select
import fcntl
import termios
import struct
import signal
import pty
import uvicorn
import time
import json
import shutil
from pathlib import Path
from typing import Optional
import base64

app = FastAPI()
pty_manager = None

STORAGE_DIR = Path("/tmp/kali_dashboard")
STORAGE_DIR.mkdir(exist_ok=True)
SESSIONS_FILE = STORAGE_DIR / "sessions.json"
UPLOADS_DIR = STORAGE_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

class TerminalCreate(BaseModel):
    name: str = "Terminal"
    workspace: str = "ws1"
    tab_type: str = "terminal"
    shell: str = "bash"

class PTYManager:
    def __init__(self):
        self.terminals = {}
        self.lock = threading.Lock()
    
    def create_pty(self, name="Terminal", workspace="ws1", shell="bash"):
        master_fd, slave_fd = pty.openpty()
        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))
        
        flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
        fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        
        pid = os.fork()
        if pid == 0:
            os.setsid()
            os.close(master_fd)
            fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)
            os.dup2(slave_fd, 0)
            os.dup2(slave_fd, 1)
            os.dup2(slave_fd, 2)
            os.close(slave_fd)
            os.environ['TERM'] = 'xterm-256color'
            
            shell_cmd = shell if shell in ['bash', 'zsh', 'fish', 'sh'] else 'bash'
            os.execlp(shell_cmd, shell_cmd)
        
        os.close(slave_fd)
        terminal_id = str(uuid.uuid4())
        
        with self.lock:
            self.terminals[terminal_id] = {
                "master_fd": master_fd,
                "pid": pid,
                "name": name,
                "workspace": workspace,
                "shell": shell,
                "pending_output": b"",
                "input_queue": b"",
                "cols": 80,
                "rows": 24,
                "log": [],
                "env_vars": {}
            }
        
        threading.Thread(target=self._pty_reader, args=(terminal_id, master_fd), daemon=True).start()
        threading.Thread(target=self._pty_writer, args=(terminal_id, master_fd), daemon=True).start()
        return terminal_id
    
    def _pty_reader(self, terminal_id, master_fd):
        while terminal_id in self.terminals:
            try:
                r, _, _ = select.select([master_fd], [], [], 0.01)
                if r:
                    data = os.read(master_fd, 16384)
                    if data:
                        with self.lock:
                            term = self.terminals.get(terminal_id)
                            if term:
                                term["pending_output"] += data
                                term["log"].append(data.decode('utf-8', errors='replace'))
            except:
                break
    
    def _pty_writer(self, terminal_id, master_fd):
        while terminal_id in self.terminals:
            try:
                with self.lock:
                    term = self.terminals.get(terminal_id)
                    if term and term["input_queue"]:
                        os.write(master_fd, term["input_queue"])
                        term["input_queue"] = b""
                time.sleep(0.005)
            except:
                break
    
    def write_command(self, terminal_id, data):
        with self.lock:
            term = self.terminals.get(terminal_id)
            if term:
                if isinstance(data, str):
                    term["input_queue"] += data.encode('utf-8', errors='replace')
                else:
                    term["input_queue"] += data
                return True
        return False
    
    def get_output(self, terminal_id):
        with self.lock:
            term = self.terminals.get(terminal_id)
            if term and term["pending_output"]:
                output = term["pending_output"].decode('utf-8', errors='replace')
                term["pending_output"] = b""
                return output
        return ""
    
    def resize_pty(self, terminal_id, cols, rows):
        with self.lock:
            term = self.terminals.get(terminal_id)
            if term:
                term["cols"] = cols
                term["rows"] = rows
                try:
                    fcntl.ioctl(term["master_fd"], termios.TIOCSWINSZ,
                              struct.pack("HHHH", rows, cols, 0, 0))
                except:
                    pass
    
    def get_log(self, terminal_id):
        with self.lock:
            term = self.terminals.get(terminal_id)
            if term:
                return "".join(term["log"])
        return ""
    
    def kill_terminal(self, terminal_id):
        with self.lock:
            term = self.terminals.get(terminal_id)
            if term:
                try:
                    os.kill(term["pid"], signal.SIGTERM)
                    os.close(term["master_fd"])
                except:
                    pass
                self.terminals.pop(terminal_id, None)

pty_manager = PTYManager()

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    html = r"""
<!DOCTYPE html>
<html>
<head>
    <title>>_ SHELL MATRIX - N0rd</title>
    <script src="https://cdn.jsdelivr.net/npm/xterm@5.3.0/lib/xterm.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.8.0/lib/xterm-addon-fit.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/xterm-addon-search@0.13.0/lib/xterm-addon-search.js"></script>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/xterm@5.3.0/css/xterm.css">
    <style>
        :root {
            --bg-dark: #1a1a1a;
            --bg-gray: #2a2a2a;
            --red-dark: #8b0000;
            --red-main: #cc0000;
            --red-glow: rgba(139, 0, 0, 0.6);
            --green: #00ff00;
            --blue: #0066ff;
            --purple: #aa00ff;
            --cyan: #00ffff;
        }
        
        .theme-green { --primary: #00ff00; --primary-glow: rgba(0, 255, 0, 0.6); }
        .theme-red { --primary: #ff0000; --primary-glow: rgba(255, 0, 0, 0.6); }
        .theme-blue { --primary: #00ffff; --primary-glow: rgba(0, 255, 255, 0.6); }
        .theme-purple { --primary: #aa00ff; --primary-glow: rgba(170, 0, 255, 0.6); }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Courier New', monospace; 
            background: var(--bg-dark); 
            color: var(--green); 
            height: 100vh;
        }
        .header {
            background: var(--bg-gray);
            border-bottom: 3px solid var(--red-dark);
            padding: 15px 20px;
            box-shadow: 0 0 40px var(--red-glow);
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 1000;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        h1 {
            color: var(--red-main);
            text-shadow: 0 0 15px var(--red-main);
            font-size: 24px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .prompt-blink {
            animation: blink 1s infinite;
            color: var(--green);
            text-shadow: 0 0 10px var(--green);
        }
        @keyframes blink {
            0%, 49% { opacity: 1; }
            50%, 100% { opacity: 0; }
        }
        .btn {
            background: var(--red-dark);
            color: #fff;
            border: 2px solid var(--red-main);
            padding: 8px 20px;
            font-weight: bold;
            cursor: pointer;
            border-radius: 6px;
            font-family: inherit;
            font-size: 13px;
            margin: 0 5px;
            transition: all 0.2s;
            box-shadow: 0 0 10px var(--red-glow);
        }
        .btn:hover {
            background: var(--red-main);
            box-shadow: 0 0 20px var(--red-glow);
            transform: translateY(-1px);
        }
        .status {
            background: var(--bg-gray);
            border: 2px solid var(--red-dark);
            padding: 10px;
            border-radius: 6px;
            color: var(--green);
            font-size: 12px;
            z-index: 999;
            position: absolute;
            right: 20px;
            top: 10px;
        }
        .workspaces {
            display: flex;
            gap: 5px;
            position: absolute;
            left: 20px;
            top: 70px;
            z-index: 1001;
        }
        .workspace-tab {
            background: var(--bg-gray);
            color: var(--green);
            border: 2px solid var(--red-dark);
            padding: 8px 16px;
            cursor: pointer;
            border-radius: 6px 6px 0 0;
            font-size: 13px;
            font-weight: bold;
            transition: all 0.2s;
            position: relative;
        }
        .workspace-tab:hover {
            box-shadow: 0 0 15px var(--red-glow);
        }
        .workspace-tab.active {
            background: var(--red-main);
            color: #000;
            box-shadow: 0 0 15px var(--red-glow);
        }
        .workspace-tab.has-proxy::after {
            content: '[PROXY]';
            font-size: 8px;
            color: var(--cyan);
            position: absolute;
            top: 2px;
            right: 5px;
        }
        .ws-context-menu {
            display: none;
            position: absolute;
            background: var(--bg-gray);
            border: 2px solid var(--red-main);
            border-radius: 6px;
            padding: 5px;
            z-index: 2000;
            box-shadow: 0 0 20px var(--red-glow);
        }
        .ws-context-menu.active {
            display: block;
        }
        .ws-context-item {
            padding: 8px 15px;
            cursor: pointer;
            color: var(--green);
            font-size: 12px;
            border-radius: 4px;
        }
        .ws-context-item:hover {
            background: var(--red-dark);
        }
        .terminal-container {
            position: absolute;
            border: 3px solid var(--red-dark);
            background: var(--bg-dark);
            border-radius: 12px;
            box-shadow: 0 0 50px var(--red-glow);
            min-width: 700px;
            min-height: 450px;
            resize: both;
            overflow: hidden;
            display: none;
        }
        .terminal-container.active {
            display: block;
        }
        .terminal-container.maximized {
            position: fixed !important;
            top: 60px !important;
            left: 0 !important;
            width: 100% !important;
            height: calc(100% - 60px) !important;
            z-index: 999 !important;
            resize: none !important;
        }
        .terminal-container.split-v {
            width: 49% !important;
        }
        .terminal-header {
            background: var(--bg-gray);
            padding: 12px 20px;
            border-bottom: 2px solid var(--red-dark);
            display: flex;
            justify-content: space-between;
            align-items: center;
            color: var(--green);
            font-weight: bold;
            font-size: 14px;
            cursor: move;
            user-select: none;
        }
        .terminal-title {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .terminal-body {
            height: calc(100% - 50px);
            position: relative;
        }
        #workspace-area {
            height: 100vh;
            padding-top: 120px;
            padding-bottom: 60px;
            overflow: auto;
            position: relative;
        }
        
        #workspace-area::-webkit-scrollbar {
            width: 12px;
            height: 12px;
        }
        
        #workspace-area::-webkit-scrollbar-track {
            background: var(--bg-dark);
            border: 1px solid var(--red-dark);
        }
        
        #workspace-area::-webkit-scrollbar-thumb {
            background: var(--red-dark);
            border-radius: 6px;
        }
        
        #workspace-area::-webkit-scrollbar-thumb:hover {
            background: var(--red-main);
        }
        .btn-small {
            padding: 5px 12px !important;
            font-size: 12px !important;
            margin: 0 2px !important;
        }
        .text-editor {
            width: 100%;
            height: 100%;
            background: var(--bg-dark);
            color: var(--green);
            border: none;
            padding: 20px;
            font-family: 'Courier New', monospace;
            font-size: 15px;
            resize: none;
            outline: none;
        }
        .browser-container {
            width: 100%;
            height: 100%;
            display: flex;
            flex-direction: column;
            background: var(--bg-dark);
        }
        .browser-nav {
            background: var(--bg-gray);
            padding: 10px;
            border-bottom: 2px solid var(--red-dark);
            display: flex;
            gap: 5px;
            align-items: center;
        }
        .browser-nav button {
            background: var(--red-dark);
            border: 1px solid var(--red-main);
            color: var(--green);
            padding: 5px 10px;
            cursor: pointer;
            border-radius: 4px;
            font-family: inherit;
            font-size: 11px;
        }
        .browser-nav button:hover {
            background: var(--red-main);
        }
        .browser-nav input {
            flex: 1;
            background: var(--bg-dark);
            border: 2px solid var(--red-dark);
            color: var(--green);
            padding: 5px 10px;
            font-family: inherit;
            border-radius: 4px;
        }
        .browser-frame {
            flex: 1;
            background: #fff;
            border: none;
            width: 100%;
        }
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            z-index: 2000;
            justify-content: center;
            align-items: center;
        }
        .modal.active { display: flex; }
        .modal-content {
            background: var(--bg-gray);
            border: 3px solid var(--red-main);
            border-radius: 12px;
            padding: 30px;
            min-width: 400px;
            max-width: 600px;
            max-height: 80vh;
            overflow-y: auto;
        }
        .modal-content h2 { color: var(--red-main); margin-bottom: 20px; }
        .modal-content label { display: block; color: var(--green); margin: 15px 0 5px; font-weight: bold; }
        .modal-content input, .modal-content select, .modal-content textarea {
            width: 100%;
            background: var(--bg-dark);
            border: 2px solid var(--red-dark);
            color: var(--green);
            padding: 10px;
            font-family: inherit;
            border-radius: 6px;
            margin-bottom: 10px;
        }
        .modal-buttons { display: flex; gap: 10px; margin-top: 20px; justify-content: flex-end; }
        
        #dock {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: var(--bg-gray);
            border-top: 3px solid var(--red-dark);
            padding: 10px;
            display: flex;
            gap: 10px;
            z-index: 998;
            overflow-x: auto;
        }
        .dock-item {
            background: var(--bg-dark);
            border: 2px solid var(--red-main);
            padding: 8px 15px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
            white-space: nowrap;
        }
        .dock-item:hover {
            background: var(--red-dark);
        }
        
        .theme-selector {
            display: flex;
            gap: 5px;
            margin-top: 10px;
        }
        .theme-btn {
            width: 30px;
            height: 30px;
            border: 2px solid #fff;
            border-radius: 50%;
            cursor: pointer;
        }
        .theme-btn.green { background: #00ff00; }
        .theme-btn.red { background: #ff0000; }
        .theme-btn.blue { background: #00ffff; }
        .theme-btn.purple { background: #aa00ff; }
        
        .search-box {
            position: absolute;
            top: 10px;
            right: 10px;
            z-index: 100;
            display: none;
        }
        .search-box.active {
            display: block;
        }
        .search-box input {
            background: var(--bg-dark);
            border: 2px solid var(--red-main);
            color: var(--green);
            padding: 5px 10px;
            font-family: inherit;
            border-radius: 4px;
        }
        
        .snippets-panel {
            position: fixed;
            right: -300px;
            top: 60px;
            width: 300px;
            height: calc(100vh - 60px);
            background: var(--bg-gray);
            border-left: 3px solid var(--red-dark);
            transition: right 0.3s;
            z-index: 1001;
            overflow-y: auto;
            padding: 20px;
        }
        .snippets-panel.active {
            right: 0;
        }
        .snippet-item {
            background: var(--bg-dark);
            border: 2px solid var(--red-dark);
            padding: 10px;
            margin: 10px 0;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
        }
        .snippet-item:hover {
            border-color: var(--red-main);
        }
        .proxy-indicator {
            font-size: 10px;
            color: var(--cyan);
            margin-left: 10px;
        }
    </style>
</head>
<body class="theme-green">
    <div class="header">
        <h1>
            <span class="prompt-blink">>_</span>
            <span>SHELL MATRIX</span>
            <span style="color: #666; font-size: 14px;">- N0rd</span>
        </h1>
        <div>
            <select id="language-selector" class="btn" style="padding: 8px 15px; margin-right: 10px;">
                <option value="pt">🇧🇷 Português</option>
                <option value="en">🇺🇸 English</option>
            </select>
            <button id="new-tab" class="btn">+ Nova Aba (Ctrl+Shift+T)</button>
            <button id="snippets-btn" class="btn">Snippets</button>
            <button id="sessions-btn" class="btn">Sessoes</button>
            <button id="settings-btn" class="btn">Config</button>
        </div>
    </div>
    
    <div id="status" class="status">
        <div>Abas: <span id="count">0</span></div>
        <div>WS: <span id="active-ws">WS1</span></div>
        <div>Tema: <span id="theme-name">Verde</span></div>
    </div>
    
    <div class="workspaces" id="workspaces">
        <div class="workspace-tab active" data-ws="ws1" oncontextmenu="kaliTerm.showWorkspaceMenu(event, 'ws1'); return false;">
            <span class="ws-name">WS1</span>
        </div>
        <button class="btn" id="new-ws" style="padding: 8px 12px; font-size: 12px;">+ WS</button>
    </div>
    
    <div id="ws-context-menu" class="ws-context-menu">
        <div class="ws-context-item" onclick="kaliTerm.renameWorkspace()">Renomear</div>
        <div class="ws-context-item" onclick="kaliTerm.configProxy()">Configurar Proxy</div>
        <div class="ws-context-item" onclick="kaliTerm.deleteWorkspace()">Deletar</div>
        <div class="ws-context-item" onclick="kaliTerm.closeContextMenu()">Cancelar</div>
    </div>
    
    <div id="workspace-area"></div>
    <div id="dock"></div>

    <div id="new-tab-modal" class="modal">
        <div class="modal-content">
            <h2>Nova Aba</h2>
            <label>Nome:</label>
            <input type="text" id="tab-name" value="Nova Aba">
            
            <label>Tipo:</label>
            <select id="tab-type">
                <option value="terminal">Terminal</option>
                <option value="browser">Navegador</option>
                <option value="editor">Editor de Texto</option>
                <option value="snippet">Snippets</option>
            </select>
            
            <label>Shell (apenas terminal):</label>
            <select id="tab-shell">
                <option value="bash">Bash</option>
                <option value="zsh">Zsh</option>
                <option value="fish">Fish</option>
                <option value="sh">Sh</option>
            </select>
            
            <div class="modal-buttons">
                <button class="btn" id="cancel-tab">Cancelar</button>
                <button class="btn" id="create-tab">Criar</button>
            </div>
        </div>
    </div>

    <div id="proxy-modal" class="modal">
        <div class="modal-content">
            <h2>Configurar Proxy</h2>
            <p style="color: var(--green); font-size: 12px; margin-bottom: 15px;">
                Todas as ferramentas neste workspace usarao este proxy
            </p>
            
            <label>Tipo:</label>
            <select id="proxy-type">
                <option value="http">HTTP</option>
                <option value="https">HTTPS</option>
                <option value="socks5">SOCKS5</option>
            </select>
            
            <label>Host:</label>
            <input type="text" id="proxy-host" placeholder="127.0.0.1">
            
            <label>Porta:</label>
            <input type="number" id="proxy-port" placeholder="8080">
            
            <label>Usuario (opcional):</label>
            <input type="text" id="proxy-user" placeholder="username">
            
            <label>Senha (opcional):</label>
            <input type="password" id="proxy-pass" placeholder="password">
            
            <div style="margin: 15px 0;">
                <button class="btn" onclick="kaliTerm.testProxy()" style="width: 100%;">Testar Proxy</button>
            </div>
            
            <div class="modal-buttons">
                <button class="btn" onclick="kaliTerm.removeProxy()">Remover Proxy</button>
                <button class="btn" id="save-proxy">Salvar</button>
            </div>
        </div>
    </div>

    <div id="settings-modal" class="modal">
        <div class="modal-content">
            <h2>Configuracoes</h2>
            
            <label>Tema:</label>
            <div class="theme-selector">
                <div class="theme-btn green" onclick="kaliTerm.setTheme('green')"></div>
                <div class="theme-btn red" onclick="kaliTerm.setTheme('red')"></div>
                <div class="theme-btn blue" onclick="kaliTerm.setTheme('blue')"></div>
                <div class="theme-btn purple" onclick="kaliTerm.setTheme('purple')"></div>
            </div>
            
            <label>Auto-save Editor (segundos):</label>
            <input type="number" id="autosave-interval" value="5" min="1">
            
            <label>Atalhos de Teclado:</label>
            <div style="font-size: 12px; color: var(--green); margin: 10px 0;">
                • Ctrl+Shift+T - Nova aba<br>
                • Ctrl+W - Fechar aba<br>
                • Ctrl+F - Buscar no terminal<br>
                • Alt+1/2/3 - Trocar workspace<br>
                • F11 - Maximizar aba<br>
                • Clique direito no WS - Menu workspace
            </div>
            
            <div class="modal-buttons">
                <button class="btn" id="close-settings">Fechar</button>
            </div>
        </div>
    </div>

    <div id="sessions-modal" class="modal">
        <div class="modal-content">
            <h2>Gerenciar Sessoes</h2>
            
            <label>Salvar Sessao Atual:</label>
            <input type="text" id="session-name" placeholder="Nome da sessao">
            <button class="btn" id="save-session" style="width: 100%; margin: 10px 0;">Salvar</button>
            
            <label>Sessoes Salvas:</label>
            <div id="sessions-list" style="max-height: 300px; overflow-y: auto;">
            </div>
            
            <div class="modal-buttons">
                <button class="btn" id="close-sessions">Fechar</button>
            </div>
        </div>
    </div>

    <div id="snippets-panel" class="snippets-panel">
        <h3 style="color: var(--red-main); margin-bottom: 20px;">Snippets</h3>
        <button class="btn" style="width: 100%; margin-bottom: 10px;" id="add-snippet">+ Novo Snippet</button>
        <div id="snippets-list"></div>
    </div>

    <script>
        const translations = {
            pt: {
                newTab: '+ Nova Aba (Ctrl+Shift+T)',
                snippets: 'Snippets',
                sessions: 'Sessoes',
                config: 'Config',
                tabs: 'Abas',
                theme: 'Tema',
                green: 'Verde',
                red: 'Vermelho',
                blue: 'Ciano',
                purple: 'Roxo',
                rename: 'Renomear',
                configProxy: 'Configurar Proxy',
                delete: 'Deletar',
                cancel: 'Cancelar',
                newTabModal: 'Nova Aba',
                name: 'Nome:',
                type: 'Tipo:',
                terminal: 'Terminal',
                browser: 'Navegador',
                editor: 'Editor de Texto',
                shellOnly: 'Shell (apenas terminal):',
                create: 'Criar',
                proxyModal: 'Configurar Proxy',
                proxyDesc: 'Todas as ferramentas neste workspace usarao este proxy',
                proxyType: 'Tipo:',
                host: 'Host:',
                port: 'Porta:',
                user: 'Usuario (opcional):',
                password: 'Senha (opcional):',
                testProxy: 'Testar Proxy',
                removeProxy: 'Remover Proxy',
                save: 'Salvar',
                settings: 'Configuracoes',
                autoSave: 'Auto-save Editor (segundos):',
                shortcuts: 'Atalhos de Teclado:',
                shortcutsDesc: '• Ctrl+Shift+T - Nova aba<br>• Ctrl+W - Fechar aba<br>• Ctrl+F - Buscar no terminal<br>• Alt+1/2/3 - Trocar workspace<br>• F11 - Maximizar aba<br>• Clique direito no WS - Menu workspace',
                close: 'Fechar',
                manageSessions: 'Gerenciar Sessoes',
                saveCurrentSession: 'Salvar Sessao Atual:',
                sessionName: 'Nome da sessao',
                savedSessions: 'Sessoes Salvas:',
                newSnippet: '+ Novo Snippet',
                corsNote: 'Nota: Alguns sites bloqueiam carregamento em iframe (CORS). Use URLs diretas como \'example.com\' ou sera aberto em nova janela.',
                search: 'Buscar...',
                splitTerminal: 'Split Terminal',
                closeTab: 'Fechar esta aba?',
                deleteWorkspace: 'Deletar este workspace e todas as abas?',
                cannotDeleteMain: 'Nao pode deletar o workspace principal!',
                newWorkspaceName: 'Novo nome para o workspace:',
                enterName: 'Digite um nome!',
                sessionSaved: 'Sessao salva!',
                textCopied: 'Texto copiado!',
                commandCopied: 'Comando copiado! Cole no terminal com Ctrl+V',
                snippetName: 'Nome do snippet:',
                command: 'Comando:',
                hostPortRequired: 'Host e porta sao obrigatorios!',
                proxyConfigured: 'Proxy configurado! Todas as ferramentas neste workspace usarao este proxy.',
                proxyRemoved: 'Proxy removido deste workspace.',
                testingProxy: 'Testando proxy',
                testProxyDesc: 'Em um ambiente real, isso testaria a conexao.\nPor enquanto, verifique manualmente se o proxy esta ativo.',
                corsError: 'Nao foi possivel carregar no iframe (CORS).\nDeseja abrir em nova janela?',
                newTabName: 'Nova Aba',
                newName: 'Novo nome:',
                editorPlaceholder: 'Digite ou cole seu texto aqui...'
            },
            en: {
                newTab: '+ New Tab (Ctrl+Shift+T)',
                snippets: 'Snippets',
                sessions: 'Sessions',
                config: 'Settings',
                tabs: 'Tabs',
                theme: 'Theme',
                green: 'Green',
                red: 'Red',
                blue: 'Cyan',
                purple: 'Purple',
                rename: 'Rename',
                configProxy: 'Configure Proxy',
                delete: 'Delete',
                cancel: 'Cancel',
                newTabModal: 'New Tab',
                name: 'Name:',
                type: 'Type:',
                terminal: 'Terminal',
                browser: 'Browser',
                editor: 'Text Editor',
                shellOnly: 'Shell (terminal only):',
                create: 'Create',
                proxyModal: 'Configure Proxy',
                proxyDesc: 'All tools in this workspace will use this proxy',
                proxyType: 'Type:',
                host: 'Host:',
                port: 'Port:',
                user: 'User (optional):',
                password: 'Password (optional):',
                testProxy: 'Test Proxy',
                removeProxy: 'Remove Proxy',
                save: 'Save',
                settings: 'Settings',
                autoSave: 'Editor Auto-save (seconds):',
                shortcuts: 'Keyboard Shortcuts:',
                shortcutsDesc: '• Ctrl+Shift+T - New tab<br>• Ctrl+W - Close tab<br>• Ctrl+F - Search in terminal<br>• Alt+1/2/3 - Switch workspace<br>• F11 - Maximize tab<br>• Right-click on WS - Workspace menu',
                close: 'Close',
                manageSessions: 'Manage Sessions',
                saveCurrentSession: 'Save Current Session:',
                sessionName: 'Session name',
                savedSessions: 'Saved Sessions:',
                newSnippet: '+ New Snippet',
                corsNote: 'Note: Some sites block iframe loading (CORS). Use direct URLs like \'example.com\' or it will open in a new window.',
                search: 'Search...',
                splitTerminal: 'Split Terminal',
                closeTab: 'Close this tab?',
                deleteWorkspace: 'Delete this workspace and all tabs?',
                cannotDeleteMain: 'Cannot delete the main workspace!',
                newWorkspaceName: 'New name for workspace:',
                enterName: 'Enter a name!',
                sessionSaved: 'Session saved!',
                textCopied: 'Text copied!',
                commandCopied: 'Command copied! Paste in terminal with Ctrl+V',
                snippetName: 'Snippet name:',
                command: 'Command:',
                hostPortRequired: 'Host and port are required!',
                proxyConfigured: 'Proxy configured! All tools in this workspace will use this proxy.',
                proxyRemoved: 'Proxy removed from this workspace.',
                testingProxy: 'Testing proxy',
                testProxyDesc: 'In a real environment, this would test the connection.\nFor now, check manually if the proxy is active.',
                corsError: 'Could not load in iframe (CORS).\nDo you want to open in a new window?',
                newTabName: 'New Tab',
                newName: 'New name:',
                editorPlaceholder: 'Type or paste your text here...'
            }
        };

        class KaliTerminal {
            constructor() {
                this.terminals = new Map();
                this.zIndex = 100;
                this.currentWorkspace = 'ws1';
                this.workspaceCount = 1;
                this.workspaces = {'ws1': {id: 'ws1', name: 'WS1', proxy: null}};
                this.minimized = new Set();
                this.autoSaveInterval = 5000;
                this.snippets = this.loadSnippets();
                this.sessions = this.loadSessions();
                this.contextMenuWs = null;
                this.currentLang = localStorage.getItem('shell_matrix_lang') || 'pt';
                this.init();
                this.loadLastSession();
                this.applyLanguage();
            }
            
            init() {
                document.getElementById('language-selector').value = this.currentLang;
                document.getElementById('language-selector').onchange = (e) => {
                    this.currentLang = e.target.value;
                    localStorage.setItem('shell_matrix_lang', this.currentLang);
                    this.applyLanguage();
                };
                
                document.getElementById('new-tab').onclick = () => this.showNewTabModal();
                document.getElementById('create-tab').onclick = () => this.createTab();
                document.getElementById('cancel-tab').onclick = () => this.hideNewTabModal();
                document.getElementById('new-ws').onclick = () => this.newWorkspace();
                document.getElementById('settings-btn').onclick = () => this.showSettings();
                document.getElementById('close-settings').onclick = () => this.hideSettings();
                document.getElementById('sessions-btn').onclick = () => this.showSessions();
                document.getElementById('close-sessions').onclick = () => this.hideSessions();
                document.getElementById('save-session').onclick = () => this.saveSession();
                document.getElementById('snippets-btn').onclick = () => this.toggleSnippets();
                document.getElementById('add-snippet').onclick = () => this.addSnippet();
                document.getElementById('save-proxy').onclick = () => this.saveProxy();
                
                document.addEventListener('click', () => this.closeContextMenu());
                
                document.addEventListener('keydown', (e) => {
                    if (e.ctrlKey && e.shiftKey && e.key === 'T') {
                        e.preventDefault();
                        this.showNewTabModal();
                    }
                    if (e.ctrlKey && e.key === 'w') {
                        e.preventDefault();
                        const active = document.querySelector('.terminal-container.active');
                        if (active) this.closeTab(active.id);
                    }
                    if (e.ctrlKey && e.key === 'f') {
                        e.preventDefault();
                        this.showSearch();
                    }
                    if (e.altKey && ['1','2','3','4','5'].includes(e.key)) {
                        e.preventDefault();
                        this.switchWorkspace('ws' + e.key);
                    }
                    if (e.key === 'F11') {
                        e.preventDefault();
                        const active = document.querySelector('.terminal-container.active');
                        if (active) this.toggleMaximize(active.id);
                    }
                    if (e.key === 'Escape') {
                        this.hideNewTabModal();
                        this.hideSettings();
                        this.hideSessions();
                        this.hideProxyModal();
                        this.closeContextMenu();
                    }
                });
                
                setInterval(() => this.autoSaveSession(), 30000);
                this.renderSnippets();
            }
            
            t(key) {
                return translations[this.currentLang][key] || key;
            }
            
            applyLanguage() {
                document.getElementById('new-tab').textContent = this.t('newTab');
                document.getElementById('snippets-btn').textContent = this.t('snippets');
                document.getElementById('sessions-btn').textContent = this.t('sessions');
                document.getElementById('settings-btn').textContent = this.t('config');
                
                const statusLabels = document.querySelectorAll('#status div');
                if (statusLabels[0]) statusLabels[0].innerHTML = this.t('tabs') + ': <span id="count">0</span>';
                if (statusLabels[2]) statusLabels[2].innerHTML = this.t('theme') + ': <span id="theme-name">' + this.t(this.getCurrentThemeName()) + '</span>';
                
                const wsMenu = document.querySelectorAll('.ws-context-item');
                if (wsMenu[0]) wsMenu[0].textContent = this.t('rename');
                if (wsMenu[1]) wsMenu[1].textContent = this.t('configProxy');
                if (wsMenu[2]) wsMenu[2].textContent = this.t('delete');
                if (wsMenu[3]) wsMenu[3].textContent = this.t('cancel');
                
                const newTabModal = document.querySelector('#new-tab-modal .modal-content');
                if (newTabModal) {
                    newTabModal.querySelector('h2').textContent = this.t('newTabModal');
                    const labels = newTabModal.querySelectorAll('label');
                    if (labels[0]) labels[0].textContent = this.t('name');
                    if (labels[1]) labels[1].textContent = this.t('type');
                    if (labels[2]) labels[2].textContent = this.t('shellOnly');
                    
                    document.getElementById('tab-name').value = this.t('newTabName');
                    
                    const options = document.querySelectorAll('#tab-type option');
                    if (options[0]) options[0].textContent = this.t('terminal');
                    if (options[1]) options[1].textContent = this.t('browser');
                    if (options[2]) options[2].textContent = this.t('editor');
                    if (options[3]) options[3].textContent = this.t('snippets');
                    
                    document.getElementById('cancel-tab').textContent = this.t('cancel');
                    document.getElementById('create-tab').textContent = this.t('create');
                }
                
                const proxyModal = document.querySelector('#proxy-modal .modal-content');
                if (proxyModal) {
                    proxyModal.querySelector('h2').textContent = this.t('proxyModal');
                    proxyModal.querySelector('p').textContent = this.t('proxyDesc');
                    const labels = proxyModal.querySelectorAll('label');
                    if (labels[0]) labels[0].textContent = this.t('proxyType');
                    if (labels[1]) labels[1].textContent = this.t('host');
                    if (labels[2]) labels[2].textContent = this.t('port');
                    if (labels[3]) labels[3].textContent = this.t('user');
                    if (labels[4]) labels[4].textContent = this.t('password');
                    
                    const btns = proxyModal.querySelectorAll('button');
                    if (btns[0]) btns[0].textContent = this.t('testProxy');
                    if (btns[1]) btns[1].textContent = this.t('removeProxy');
                    if (btns[2]) btns[2].textContent = this.t('save');
                }
                
                const settingsModal = document.querySelector('#settings-modal .modal-content');
                if (settingsModal) {
                    settingsModal.querySelector('h2').textContent = this.t('settings');
                    const labels = settingsModal.querySelectorAll('label');
                    if (labels[0]) labels[0].textContent = this.t('theme') + ':';
                    if (labels[1]) labels[1].textContent = this.t('autoSave');
                    if (labels[2]) labels[2].textContent = this.t('shortcuts');
                    
                    const shortcutsDiv = settingsModal.querySelector('div[style*="font-size: 12px"]');
                    if (shortcutsDiv) shortcutsDiv.innerHTML = this.t('shortcutsDesc');
                    
                    document.getElementById('close-settings').textContent = this.t('close');
                }
                
                const sessionsModal = document.querySelector('#sessions-modal .modal-content');
                if (sessionsModal) {
                    sessionsModal.querySelector('h2').textContent = this.t('manageSessions');
                    const labels = sessionsModal.querySelectorAll('label');
                    if (labels[0]) labels[0].textContent = this.t('saveCurrentSession');
                    if (labels[1]) labels[1].textContent = this.t('savedSessions');
                    
                    document.getElementById('session-name').placeholder = this.t('sessionName');
                    document.getElementById('save-session').textContent = this.t('save');
                    document.getElementById('close-sessions').textContent = this.t('close');
                }
                
                const snippetsPanel = document.getElementById('snippets-panel');
                if (snippetsPanel) {
                    snippetsPanel.querySelector('h3').textContent = this.t('snippets');
                    document.getElementById('add-snippet').textContent = this.t('newSnippet');
                }
                
                this.updateCount();
            }
            
            getCurrentThemeName() {
                const body = document.body;
                if (body.classList.contains('theme-green')) return 'green';
                if (body.classList.contains('theme-red')) return 'red';
                if (body.classList.contains('theme-blue')) return 'blue';
                if (body.classList.contains('theme-purple')) return 'purple';
                return 'green';
            }
            
            showWorkspaceMenu(event, wsId) {
                event.stopPropagation();
                const menu = document.getElementById('ws-context-menu');
                menu.style.left = event.pageX + 'px';
                menu.style.top = event.pageY + 'px';
                menu.classList.add('active');
                this.contextMenuWs = wsId;
            }
            
            closeContextMenu() {
                document.getElementById('ws-context-menu').classList.remove('active');
            }
            
            configProxy() {
                if (!this.contextMenuWs) return;
                
                const ws = this.workspaces[this.contextMenuWs];
                if (ws.proxy) {
                    document.getElementById('proxy-type').value = ws.proxy.type || 'http';
                    document.getElementById('proxy-host').value = ws.proxy.host || '';
                    document.getElementById('proxy-port').value = ws.proxy.port || '';
                    document.getElementById('proxy-user').value = ws.proxy.user || '';
                    document.getElementById('proxy-pass').value = ws.proxy.pass || '';
                } else {
                    document.getElementById('proxy-type').value = 'http';
                    document.getElementById('proxy-host').value = '';
                    document.getElementById('proxy-port').value = '';
                    document.getElementById('proxy-user').value = '';
                    document.getElementById('proxy-pass').value = '';
                }
                
                document.getElementById('proxy-modal').classList.add('active');
                this.closeContextMenu();
            }
            
            hideProxyModal() {
                document.getElementById('proxy-modal').classList.remove('active');
            }
            
            saveProxy() {
                if (!this.contextMenuWs) return;
                
                const type = document.getElementById('proxy-type').value;
                const host = document.getElementById('proxy-host').value;
                const port = document.getElementById('proxy-port').value;
                const user = document.getElementById('proxy-user').value;
                const pass = document.getElementById('proxy-pass').value;
                
                if (!host || !port) {
                    alert(this.t('hostPortRequired'));
                    return;
                }
                
                this.workspaces[this.contextMenuWs].proxy = {
                    type, host, port, user, pass
                };
                
                this.updateWorkspaceProxyIndicator(this.contextMenuWs);
                this.saveWorkspaces();
                this.hideProxyModal();
                
                this.applyProxyToWorkspace(this.contextMenuWs);
                
                alert(this.t('proxyConfigured'));
            }
            
            removeProxy() {
                if (!this.contextMenuWs) return;
                
                this.workspaces[this.contextMenuWs].proxy = null;
                this.updateWorkspaceProxyIndicator(this.contextMenuWs);
                this.saveWorkspaces();
                this.hideProxyModal();
                
                alert(this.t('proxyRemoved'));
            }
            
            testProxy() {
                const type = document.getElementById('proxy-type').value;
                const host = document.getElementById('proxy-host').value;
                const port = document.getElementById('proxy-port').value;
                
                if (!host || !port) {
                    alert(this.t('hostPortRequired'));
                    return;
                }
                
                alert(`${this.t('testingProxy')} ${type}://${host}:${port}...
                
${this.t('testProxyDesc')}`);
            }
            
            applyProxyToWorkspace(wsId) {
                const proxy = this.workspaces[wsId].proxy;
                if (!proxy) return;
                
                const proxyUrl = `${proxy.type}://${proxy.user ? proxy.user + ':' + proxy.pass + '@' : ''}${proxy.host}:${proxy.port}`;
                
                console.log(`Aplicando proxy ao workspace ${wsId}: ${proxyUrl}`);
            }
            
            updateWorkspaceProxyIndicator(wsId) {
                const tab = document.querySelector(`[data-ws="${wsId}"]`);
                if (tab) {
                    if (this.workspaces[wsId].proxy) {
                        tab.classList.add('has-proxy');
                    } else {
                        tab.classList.remove('has-proxy');
                    }
                }
            }
            
            renameWorkspace() {
                if (!this.contextMenuWs) return;
                
                const currentName = this.workspaces[this.contextMenuWs].name;
                const newName = prompt(this.t('newWorkspaceName'), currentName);
                
                if (newName && newName.trim()) {
                    this.workspaces[this.contextMenuWs].name = newName.trim();
                    const tab = document.querySelector(`[data-ws="${this.contextMenuWs}"]`);
                    if (tab) {
                        tab.querySelector('.ws-name').textContent = newName.trim();
                    }
                    this.saveWorkspaces();
                }
                
                this.closeContextMenu();
            }
            
            deleteWorkspace() {
                if (!this.contextMenuWs) return;
                if (this.contextMenuWs === 'ws1') {
                    alert(this.t('cannotDeleteMain'));
                    this.closeContextMenu();
                    return;
                }
                
                if (confirm(this.t('deleteWorkspace'))) {
                    this.terminals.forEach((data, id) => {
                        if (data.workspace === this.contextMenuWs) {
                            this.closeTab(id);
                        }
                    });
                    
                    delete this.workspaces[this.contextMenuWs];
                    const tab = document.querySelector(`[data-ws="${this.contextMenuWs}"]`);
                    if (tab) tab.remove();
                    
                    this.switchWorkspace('ws1');
                    this.saveWorkspaces();
                }
                
                this.closeContextMenu();
            }
            
            saveWorkspaces() {
                localStorage.setItem('shell_matrix_workspaces', JSON.stringify(this.workspaces));
            }
            
            loadWorkspaces() {
                const saved = localStorage.getItem('shell_matrix_workspaces');
                if (saved) {
                    this.workspaces = JSON.parse(saved);
                    Object.keys(this.workspaces).forEach(wsId => {
                        this.updateWorkspaceProxyIndicator(wsId);
                    });
                }
            }
            
            loadSnippets() {
                const saved = localStorage.getItem('shell_matrix_snippets');
                return saved ? JSON.parse(saved) : [
                    {name: 'Update System', cmd: 'sudo apt update && sudo apt upgrade -y'},
                    {name: 'Scan Network', cmd: 'nmap -sn 192.168.1.0/24'},
                    {name: 'Find Files', cmd: 'find / -name "*.txt" 2>/dev/null'},
                    {name: 'Set HTTP Proxy', cmd: 'export http_proxy=http://127.0.0.1:8080'},
                    {name: 'Burp Suite Proxy', cmd: 'export http_proxy=http://127.0.0.1:8080 && export https_proxy=http://127.0.0.1:8080'}
                ];
            }
            
            saveSnippets() {
                localStorage.setItem('shell_matrix_snippets', JSON.stringify(this.snippets));
            }
            
            addSnippet() {
                const name = prompt(this.t('snippetName'));
                if (!name) return;
                const cmd = prompt(this.t('command'));
                if (!cmd) return;
                this.snippets.push({name, cmd});
                this.saveSnippets();
                this.renderSnippets();
            }
            
            renderSnippets() {
                const list = document.getElementById('snippets-list');
                list.innerHTML = '';
                this.snippets.forEach((snippet, idx) => {
                    const div = document.createElement('div');
                    div.className = 'snippet-item';
                    div.innerHTML = `
                        <strong>${snippet.name}</strong><br>
                        <code style="font-size: 10px;">${snippet.cmd}</code>
                    `;
                    div.onclick = () => this.useSnippet(snippet.cmd);
                    list.appendChild(div);
                });
            }
            
            useSnippet(cmd) {
                navigator.clipboard.writeText(cmd);
                alert(this.t('commandCopied'));
            }
            
            toggleSnippets() {
                document.getElementById('snippets-panel').classList.toggle('active');
            }
            
            loadSessions() {
                const saved = localStorage.getItem('shell_matrix_sessions');
                return saved ? JSON.parse(saved) : {};
            }
            
            saveSessions() {
                localStorage.setItem('shell_matrix_sessions', JSON.stringify(this.sessions));
            }
            
            saveSession() {
                const name = document.getElementById('session-name').value;
                if (!name) return alert(this.t('enterName'));
                
                const session = {
                    workspaces: this.workspaces,
                    tabs: []
                };
                
                this.terminals.forEach((data, id) => {
                    session.tabs.push({
                        name: data.name,
                        type: data.type,
                        workspace: data.workspace,
                        content: data.type === 'editor' ? data.element.querySelector('textarea').value : ''
                    });
                });
                
                this.sessions[name] = session;
                this.saveSessions();
                this.renderSessionsList();
                alert(this.t('sessionSaved'));
            }
            
            loadSession(name) {
                const session = this.sessions[name];
                if (!session) return;
                
                this.terminals.forEach((_, id) => this.closeTab(id));
                
                session.tabs.forEach(tab => {
                    if (tab.type === 'editor') {
                        const id = 'editor-' + Date.now() + Math.random();
                        this.renderEditor(id, tab.name, tab.workspace);
                        setTimeout(() => {
                            const textarea = document.querySelector(`#${id} textarea`);
                            if (textarea) textarea.value = tab.content;
                        }, 100);
                    } else if (tab.type === 'browser') {
                        this.createBrowser(tab.name);
                    } else {
                        this.createTerminal(tab.name);
                    }
                });
                
                this.hideSessions();
            }
            
            autoSaveSession() {
                console.log('Auto-save');
            }
            
            loadLastSession() {
                this.loadWorkspaces();
            }
            
            renderSessionsList() {
                const list = document.getElementById('sessions-list');
                list.innerHTML = '';
                Object.keys(this.sessions).forEach(name => {
                    const div = document.createElement('div');
                    div.className = 'snippet-item';
                    div.innerHTML = `
                        <strong>${name}</strong><br>
                        <small>${this.sessions[name].tabs.length} abas</small>
                    `;
                    div.onclick = () => this.loadSession(name);
                    list.appendChild(div);
                });
            }
            
            showSettings() {
                document.getElementById('settings-modal').classList.add('active');
            }
            
            hideSettings() {
                document.getElementById('settings-modal').classList.remove('active');
            }
            
            showSessions() {
                this.renderSessionsList();
                document.getElementById('sessions-modal').classList.add('active');
            }
            
            hideSessions() {
                document.getElementById('sessions-modal').classList.remove('active');
            }
            
            setTheme(theme) {
                document.body.className = 'theme-' + theme;
                document.getElementById('theme-name').textContent = this.t(theme);
                localStorage.setItem('shell_matrix_theme', theme);
            }
            
            showNewTabModal() {
                document.getElementById('new-tab-modal').classList.add('active');
                document.getElementById('tab-name').focus();
            }
            
            hideNewTabModal() {
                document.getElementById('new-tab-modal').classList.remove('active');
            }
            
            createTab() {
                const name = document.getElementById('tab-name').value || this.t('newTabName');
                const type = document.getElementById('tab-type').value;
                const shell = document.getElementById('tab-shell').value;
                
                this.hideNewTabModal();
                
                if (type === 'browser') {
                    this.createBrowser(name);
                } else if (type === 'editor') {
                    this.createEditor(name);
                } else if (type === 'snippet') {
                    this.createSnippetEditor(name);
                } else {
                    this.createTerminal(name, shell);
                }
            }
            
            createBrowser(name) {
                const browserId = 'browser-' + Date.now();
                this.renderBrowser(browserId, name, this.currentWorkspace);
                this.updateCount();
            }
            
            renderBrowser(browserId, name, workspace) {
                const workspaceArea = document.getElementById('workspace-area');
                
                const browserDiv = document.createElement('div');
                browserDiv.className = 'terminal-container ' + workspace + ' active';
                browserDiv.id = browserId;
                browserDiv.dataset.workspace = workspace;
                
                const terminalCount = this.terminals.size;
                const offsetX = (terminalCount * 30) % 400;
                const offsetY = (terminalCount * 30) % 300;
                
                browserDiv.style.left = (50 + offsetX) + 'px';
                browserDiv.style.top = (100 + offsetY) + 'px';
                browserDiv.style.width = '900px';
                browserDiv.style.height = '600px';
                browserDiv.style.zIndex = this.zIndex++;
                
                const proxyInfo = this.workspaces[workspace].proxy ? 
                    `<span class="proxy-indicator">[PROXY: ${this.workspaces[workspace].proxy.host}:${this.workspaces[workspace].proxy.port}]</span>` : '';
                
                browserDiv.innerHTML = `
                    <div class="terminal-header">
                        <div class="terminal-title">
                            <span ondblclick="kaliTerm.renameTab('${browserId}')">[${this.workspaces[workspace].name}] ${name}${proxyInfo}</span>
                        </div>
                        <div>
                            <button class="btn btn-small" onclick="kaliTerm.minimize('${browserId}')">-</button>
                            <button class="btn btn-small" onclick="kaliTerm.toggleMaximize('${browserId}')">[]</button>
                            <button class="btn btn-small" style="background: #ff4444;" onclick="kaliTerm.closeTab('${browserId}')">X</button>
                        </div>
                    </div>
                    <div class="terminal-body">
                        <div class="browser-container">
                            <div class="browser-nav">
                                <button onclick="kaliTerm.browserBack('${browserId}')">←</button>
                                <button onclick="kaliTerm.browserForward('${browserId}')">→</button>
                                <button onclick="kaliTerm.browserReload('${browserId}')">⟳</button>
                                <input type="text" id="url-${browserId}" placeholder="https://example.com" 
                                       onkeypress="if(event.key==='Enter') kaliTerm.browserGo('${browserId}')">
                                <button onclick="kaliTerm.browserGo('${browserId}')">GO</button>
                            </div>
                            <iframe id="frame-${browserId}" class="browser-frame" sandbox="allow-same-origin allow-scripts allow-forms allow-popups"></iframe>
                            <div style="position: absolute; bottom: 10px; left: 10px; right: 10px; background: var(--bg-gray); padding: 10px; border: 1px solid var(--red-dark); border-radius: 4px; font-size: 11px; color: var(--green);" id="cors-note-${browserId}">
                            </div>
                        </div>
                    </div>
                `;
                
                workspaceArea.appendChild(browserDiv);
                this.setupDrag(browserDiv);
                
                document.getElementById('cors-note-' + browserId).textContent = this.t('corsNote');
                
                const maxBottom = browserDiv.offsetTop + 600 + 100;
                if (maxBottom > workspaceArea.scrollHeight) {
                    workspaceArea.style.minHeight = maxBottom + 'px';
                }
                
                this.terminals.set(browserId, { 
                    type: 'browser',
                    name: name,
                    element: browserDiv, 
                    workspace: workspace,
                    currentUrl: ''
                });
            }
            
            browserGo(id) {
                const url = document.getElementById('url-' + id).value;
                if (url) {
                    const fullUrl = url.startsWith('http') ? url : 'https://' + url;
                    const frame = document.getElementById('frame-' + id);
                    
                    frame.src = fullUrl;
                    
                    const t = this.terminals.get(id);
                    if (t) t.currentUrl = fullUrl;
                    
                    setTimeout(() => {
                        frame.onerror = () => {
                            if (confirm(this.t('corsError'))) {
                                window.open(fullUrl, '_blank', 'width=1200,height=800');
                            }
                        };
                    }, 1000);
                }
            }
            
            browserBack(id) {
                const frame = document.getElementById('frame-' + id);
                if (frame && frame.contentWindow) {
                    try {
                        frame.contentWindow.history.back();
                    } catch(e) {
                        console.error('Cannot go back:', e);
                    }
                }
            }
            
            browserForward(id) {
                const frame = document.getElementById('frame-' + id);
                if (frame && frame.contentWindow) {
                    try {
                        frame.contentWindow.history.forward();
                    } catch(e) {
                        console.error('Cannot go forward:', e);
                    }
                }
            }
            
            browserReload(id) {
                const frame = document.getElementById('frame-' + id);
                if (frame) {
                    frame.src = frame.src;
                }
            }
            
            createTerminal(name, shell = 'bash') {
                fetch('/api/terminals', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        name: name || `Terminal ${this.terminals.size + 1}`, 
                        workspace: this.currentWorkspace,
                        shell: shell
                    })
                })
                .then(r => r.json())
                .then(data => {
                    this.renderTerminal(data, this.currentWorkspace);
                    this.updateCount();
                    
                    const proxy = this.workspaces[this.currentWorkspace].proxy;
                    if (proxy) {
                        setTimeout(() => {
                            const ws = this.terminals.get(data.id).ws;
                            const proxyCmd = `export http_proxy=${proxy.type}://${proxy.host}:${proxy.port}\nexport https_proxy=${proxy.type}://${proxy.host}:${proxy.port}\n`;
                            if (ws && ws.readyState === WebSocket.OPEN) {
                                ws.send(proxyCmd);
                            }
                        }, 1000);
                    }
                })
                .catch(e => console.error('Erro:', e));
            }
            
            createEditor(name) {
                const editorId = 'editor-' + Date.now();
                this.renderEditor(editorId, name, this.currentWorkspace);
                this.updateCount();
            }
            
            createSnippetEditor(name) {
                const id = 'snippet-' + Date.now();
                this.renderEditor(id, name + ' (Snippets)', this.currentWorkspace);
                this.updateCount();
            }
            
            newWorkspace() {
                this.workspaceCount++;
                const wsId = 'ws' + this.workspaceCount;
                const wsName = 'WS' + this.workspaceCount;
                this.workspaces[wsId] = {id: wsId, name: wsName, proxy: null};
                
                const tabs = document.getElementById('workspaces');
                const tab = document.createElement('div');
                tab.className = 'workspace-tab';
                tab.dataset.ws = wsId;
                tab.innerHTML = `<span class="ws-name">${wsName}</span>`;
                tab.onclick = () => this.switchWorkspace(wsId);
                tab.oncontextmenu = (e) => { this.showWorkspaceMenu(e, wsId); return false; };
                tabs.insertBefore(tab, document.getElementById('new-ws'));
                
                this.switchWorkspace(wsId);
                this.saveWorkspaces();
            }
            
            switchWorkspace(wsId) {
                if (!document.querySelector(`[data-ws="${wsId}"]`)) return;
                
                this.currentWorkspace = wsId;
                
                document.querySelectorAll('.workspace-tab').forEach(tab => {
                    tab.classList.toggle('active', tab.dataset.ws === wsId);
                });
                
                document.getElementById('active-ws').textContent = this.workspaces[wsId].name;
                
                document.querySelectorAll('.terminal-container').forEach(container => {
                    const tabData = this.terminals.get(container.id);
                    if (tabData && tabData.workspace === wsId && !this.minimized.has(container.id)) {
                        container.style.display = 'block';
                    } else {
                        container.style.display = 'none';
                    }
                });
            }
            
            minimize(id) {
                const t = this.terminals.get(id);
                if (!t) return;
                
                this.minimized.add(id);
                t.element.style.display = 'none';
                
                const dock = document.getElementById('dock');
                const item = document.createElement('div');
                item.className = 'dock-item';
                item.id = 'dock-' + id;
                item.textContent = t.name;
                item.onclick = () => this.restore(id);
                dock.appendChild(item);
            }
            
            restore(id) {
                const t = this.terminals.get(id);
                if (!t) return;
                
                this.minimized.delete(id);
                t.element.style.display = 'block';
                
                const dockItem = document.getElementById('dock-' + id);
                if (dockItem) dockItem.remove();
            }
            
            toggleMaximize(id) {
                const t = this.terminals.get(id);
                if (!t) return;
                
                t.element.classList.toggle('maximized');
            }
            
            splitVertical(id) {
                const t = this.terminals.get(id);
                if (!t) return;
                
                t.element.classList.add('split-v');
                t.element.style.left = '0';
                
                this.createTerminal('Split Terminal');
                setTimeout(() => {
                    const containers = document.querySelectorAll('.terminal-container.active');
                    const last = containers[containers.length - 1];
                    if (last) {
                        last.classList.add('split-v');
                        last.style.left = '50%';
                    }
                }, 500);
            }
            
            updateCount() {
                document.getElementById('count').textContent = this.terminals.size;
            }
            
            renameTab(tabId) {
                const tabData = this.terminals.get(tabId);
                if (!tabData) return;
                
                const newName = prompt(this.t('newName'), tabData.name);
                if (newName && newName.trim()) {
                    tabData.name = newName.trim();
                    const titleSpan = tabData.element.querySelector('.terminal-title span');
                    if (titleSpan) {
                        titleSpan.textContent = '[' + this.workspaces[tabData.workspace].name + '] ' + newName.trim();
                    }
                }
            }
            
            downloadLog(id) {
                fetch('/api/terminals/' + id + '/log')
                    .then(r => r.text())
                    .then(log => {
                        const blob = new Blob([log], {type: 'text/plain'});
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = 'terminal-log.txt';
                        a.click();
                    });
            }
            
            renderEditor(editorId, name, workspace) {
                const workspaceArea = document.getElementById('workspace-area');
                
                const editorDiv = document.createElement('div');
                editorDiv.className = 'terminal-container ' + workspace + ' active';
                editorDiv.id = editorId;
                editorDiv.dataset.workspace = workspace;
                
                const terminalCount = this.terminals.size;
                const offsetX = (terminalCount * 30) % 400;
                const offsetY = (terminalCount * 30) % 300;
                
                editorDiv.style.left = (50 + offsetX) + 'px';
                editorDiv.style.top = (100 + offsetY) + 'px';
                editorDiv.style.width = '850px';
                editorDiv.style.height = '550px';
                editorDiv.style.zIndex = this.zIndex++;
                
                editorDiv.innerHTML = `
                    <div class="terminal-header">
                        <div class="terminal-title">
                            <span ondblclick="kaliTerm.renameTab('${editorId}')">[${this.workspaces[workspace].name}] ${name}</span>
                        </div>
                        <div>
                            <button class="btn btn-small" onclick="kaliTerm.copyAll('${editorId}')">COPY</button>
                            <button class="btn btn-small" onclick="kaliTerm.downloadEditor('${editorId}')">SAVE</button>
                            <button class="btn btn-small" onclick="kaliTerm.minimize('${editorId}')">-</button>
                            <button class="btn btn-small" onclick="kaliTerm.toggleMaximize('${editorId}')">[]</button>
                            <button class="btn btn-small" style="background: #ff4444;" onclick="kaliTerm.closeTab('${editorId}')">X</button>
                        </div>
                    </div>
                    <div class="terminal-body">
                        <textarea class="text-editor" id="textarea-${editorId}" placeholder=""></textarea>
                    </div>
                `;
                
                workspaceArea.appendChild(editorDiv);
                this.setupDrag(editorDiv);
                
                const textarea = editorDiv.querySelector('#textarea-' + editorId);
                textarea.placeholder = this.t('editorPlaceholder');
                
                const maxBottom = editorDiv.offsetTop + 550 + 100;
                if (maxBottom > workspaceArea.scrollHeight) {
                    workspaceArea.style.minHeight = maxBottom + 'px';
                }
                
                setInterval(() => {
                    localStorage.setItem('editor-' + editorId, textarea.value);
                }, this.autoSaveInterval);
                
                const saved = localStorage.getItem('editor-' + editorId);
                if (saved) textarea.value = saved;
                
                this.terminals.set(editorId, { 
                    type: 'editor',
                    name: name,
                    element: editorDiv, 
                    workspace: workspace 
                });
            }
            
            copyAll(id) {
                const textarea = document.querySelector('#' + id + ' textarea');
                if (textarea) {
                    navigator.clipboard.writeText(textarea.value);
                    alert(this.t('textCopied'));
                }
            }
            
            downloadEditor(id) {
                const textarea = document.querySelector('#' + id + ' textarea');
                if (textarea) {
                    const blob = new Blob([textarea.value], {type: 'text/plain'});
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'editor-content.txt';
                    a.click();
                }
            }
            
            renderTerminal(data, workspace) {
                const terminalId = data.id;
                const workspaceArea = document.getElementById('workspace-area');
                
                const terminalDiv = document.createElement('div');
                terminalDiv.className = 'terminal-container ' + workspace + ' active';
                terminalDiv.id = terminalId;
                terminalDiv.dataset.workspace = workspace;
                
                const terminalCount = this.terminals.size;
                const offsetX = (terminalCount * 30) % 400;
                const offsetY = (terminalCount * 30) % 300;
                
                terminalDiv.style.left = (50 + offsetX) + 'px';
                terminalDiv.style.top = (100 + offsetY) + 'px';
                terminalDiv.style.width = '850px';
                terminalDiv.style.height = '550px';
                terminalDiv.style.zIndex = this.zIndex++;
                
                const proxyInfo = this.workspaces[workspace].proxy ? 
                    `<span class="proxy-indicator">[PROXY: ${this.workspaces[workspace].proxy.host}:${this.workspaces[workspace].proxy.port}]</span>` : '';
                
                terminalDiv.innerHTML = `
                    <div class="terminal-header">
                        <div class="terminal-title">
                            <span ondblclick="kaliTerm.renameTab('${terminalId}')">[${this.workspaces[workspace].name}] ${data.name}${proxyInfo}</span>
                        </div>
                        <div>
                            <button class="btn btn-small" onclick="kaliTerm.showSearch('${terminalId}')">FIND</button>
                            <button class="btn btn-small" onclick="kaliTerm.downloadLog('${terminalId}')">LOG</button>
                            <button class="btn btn-small" onclick="kaliTerm.splitVertical('${terminalId}')">SPLIT</button>
                            <button class="btn btn-small" onclick="kaliTerm.minimize('${terminalId}')">-</button>
                            <button class="btn btn-small" onclick="kaliTerm.toggleMaximize('${terminalId}')">[]</button>
                            <button class="btn btn-small" style="background: #ff4444;" onclick="kaliTerm.closeTab('${terminalId}')">X</button>
                        </div>
                    </div>
                    <div class="terminal-body">
                        <div class="search-box" id="search-${terminalId}">
                            <input type="text" id="search-input-${terminalId}" placeholder="">
                        </div>
                        <div id="xterm-${terminalId}"></div>
                    </div>
                `;
                
                workspaceArea.appendChild(terminalDiv);
                
                const searchInput = document.getElementById('search-input-' + terminalId);
                searchInput.placeholder = this.t('search');
                searchInput.onkeyup = (e) => this.search(terminalId, e.target.value);
                
                const maxBottom = terminalDiv.offsetTop + 550 + 100;
                if (maxBottom > workspaceArea.scrollHeight) {
                    workspaceArea.style.minHeight = maxBottom + 'px';
                }
                
                const term = new Terminal({
                    cursorBlink: true,
                    theme: {
                        background: '#1a1a1a',
                        foreground: '#00ff00',
                        cursor: '#00ff00',
                        selection: 'rgba(0, 255, 0, 0.3)'
                    },
                    fontFamily: "'Courier New', monospace",
                    fontSize: 15,
                    scrollback: 10000
                });
                
                const fitAddon = new FitAddon.FitAddon();
                const searchAddon = new SearchAddon.SearchAddon();
                term.loadAddon(fitAddon);
                term.loadAddon(searchAddon);
                
                term.open(document.getElementById('xterm-' + terminalId));
                fitAddon.fit();
                
                const wsUrl = (window.location.protocol === 'https:' ? 'wss:' : 'ws:') + 
                             '//' + window.location.host + '/ws/' + terminalId;
                const ws = new WebSocket(wsUrl);
                
                ws.onopen = () => console.log('WS conectado');
                ws.onmessage = (e) => term.write(e.data);
                ws.onerror = (e) => console.error('WS erro:', e);
                
                term.onData((data) => {
                    if (ws.readyState === WebSocket.OPEN) {
                        ws.send(data);
                    }
                });
                
                this.setupDrag(terminalDiv);
                
                this.terminals.set(terminalId, { 
                    type: 'terminal',
                    name: data.name,
                    term, ws, searchAddon, fitAddon,
                    element: terminalDiv,
                    workspace: workspace 
                });
            }
            
            showSearch(id) {
                const box = document.getElementById('search-' + id);
                if (box) {
                    box.classList.toggle('active');
                    if (box.classList.contains('active')) {
                        box.querySelector('input').focus();
                    }
                }
            }
            
            search(id, query) {
                const t = this.terminals.get(id);
                if (t && t.searchAddon) {
                    t.searchAddon.findNext(query);
                }
            }
            
            setupDrag(terminalDiv) {
                const header = terminalDiv.querySelector('.terminal-header');
                let dragging = false, startX, startY, startLeft, startTop;
                
                const onMouseDown = (e) => {
                    if (e.target.tagName === 'BUTTON' || e.target.tagName === 'SPAN' || e.target.tagName === 'INPUT') return;
                    
                    dragging = true;
                    startX = e.clientX;
                    startY = e.clientY;
                    startLeft = terminalDiv.offsetLeft;
                    startTop = terminalDiv.offsetTop;
                    terminalDiv.style.zIndex = this.zIndex++;
                    e.preventDefault();
                };
                
                const onMouseMove = (e) => {
                    if (!dragging) return;
                    const dx = e.clientX - startX;
                    const dy = e.clientY - startY;
                    terminalDiv.style.left = Math.max(0, startLeft + dx) + 'px';
                    terminalDiv.style.top = Math.max(0, startTop + dy) + 'px';
                };
                
                const onMouseUp = () => dragging = false;
                
                header.addEventListener('mousedown', onMouseDown);
                document.addEventListener('mousemove', onMouseMove);
                document.addEventListener('mouseup', onMouseUp);
            }
            
            closeTab(id) {
                const t = this.terminals.get(id);
                if (t) {
                    if (confirm(this.t('closeTab'))) {
                        if (t.ws) t.ws.close();
                        if (t.term) t.term.dispose();
                        t.element.remove();
                        this.terminals.delete(id);
                        
                        const dockItem = document.getElementById('dock-' + id);
                        if (dockItem) dockItem.remove();
                        
                        this.updateCount();
                    }
                }
            }
        }
        
        const kaliTerm = new KaliTerminal();
        
        const savedTheme = localStorage.getItem('shell_matrix_theme');
        if (savedTheme) kaliTerm.setTheme(savedTheme);
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html)

@app.get("/debug")
async def debug():
    return {"status": "OK", "terminals": len(pty_manager.terminals)}

@app.post("/api/terminals")
async def create_terminal(term: TerminalCreate):
    terminal_id = pty_manager.create_pty(term.name, term.workspace, term.shell)
    term_data = pty_manager.terminals[terminal_id]
    return {"id": terminal_id, "name": term_data["name"], "pid": term_data["pid"]}

@app.get("/api/terminals/{terminal_id}/log")
async def get_terminal_log(terminal_id: str):
    log = pty_manager.get_log(terminal_id)
    return log

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    file_path = UPLOADS_DIR / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"filename": file.filename, "path": str(file_path)}

@app.get("/api/download/{filename}")
async def download_file(filename: str):
    file_path = UPLOADS_DIR / filename
    if file_path.exists():
        return FileResponse(file_path)
    return {"error": "File not found"}

@app.websocket("/ws/{terminal_id}")
async def websocket_endpoint(websocket: WebSocket, terminal_id: str):
    await websocket.accept()
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=0.05)
                try:
                    parsed = json.loads(data)
                    if parsed.get("type") == "resize":
                        pty_manager.resize_pty(terminal_id, parsed["cols"], parsed["rows"])
                except:
                    pty_manager.write_command(terminal_id, data)
            except asyncio.TimeoutError:
                pass
            
            output = pty_manager.get_output(terminal_id)
            if output:
                await websocket.send_text(output)
            
            await asyncio.sleep(0.01)
    except WebSocketDisconnect:
        pty_manager.kill_terminal(terminal_id)

if __name__ == "__main__":
    print(">_ SHELL MATRIX - N0rd")
    print("Acesse: http://localhost:8000")
    print("")
    uvicorn.run(app, host="0.0.0.0", port=8000)
