<img width="1024" height="656" alt="shell_matrix" src="https://github.com/user-attachments/assets/ab7e2cb9-85d1-4c7c-be40-bf17c77b0fe1" />

# 🖥️ SHELL MATRIX - Advanced Terminal Dashboard

** kali_dashboard was a phase. **

<div align="center">

![Shell Matrix Banner](https://img.shields.io/badge/Shell-Matrix-darkred?style=for-the-badge&logo=linux)
![Python](https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?style=for-the-badge&logo=fastapi)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

**A powerful web-based terminal management system with multi-workspace support, integrated browser, and proxy configuration**

[Features](#-features) • [Installation](#-installation) • [Usage](#-usage) • [Screenshots](#-screenshots) • [Configuration](#-configuration)

</div>

---

## Description

**Shell Matrix** is a sophisticated web-based terminal dashboard that transforms your browser into a powerful multi-terminal environment. Built with Python and FastAPI, it provides a modern, Matrix-themed interface for managing multiple terminal sessions, browser instances, and text editors simultaneously.

Perfect for:
-  Penetration testers and security researchers
-  System administrators managing multiple servers
-  DevOps engineers working with containers
-  Developers needing organized workspace management
-  Anyone who needs to juggle multiple terminals efficiently

---

## Features

### **Multi-Terminal Management**
- Create unlimited terminal tabs with real PTY (pseudo-terminal) support
- Full terminal emulation with **xterm.js**
- Support for multiple shells: Bash, Zsh, Fish, Sh
- Real-time terminal output streaming via WebSockets
- Search functionality within terminal output
- Terminal log export capability

### **Integrated Web Browser**
- Built-in browser tabs for web reconnaissance
- Navigation controls (back, forward, reload)
- Direct URL loading
- CORS-aware with fallback to external window

### **Text Editor**
- Lightweight text editor tabs
- Auto-save functionality
- Copy and download capabilities
- Perfect for note-taking and script editing

### **Workspace Organization**
- Multiple independent workspaces (WS1, WS2, WS3...)
- Rename and customize workspaces
- Per-workspace proxy configuration
- Visual workspace indicators
- Easy workspace switching (Alt+1/2/3)

### **Proxy Support**
- HTTP, HTTPS, and SOCKS5 proxy support
- Per-workspace proxy configuration
- Automatic proxy application to terminals
- Proxy testing functionality
- Visual proxy indicators

### **Session Management**
- Save complete workspace sessions
- Restore all tabs and configurations
- Auto-save every 30 seconds
- Export/import session data

### **Customization**
- 4 color themes: Green (Matrix), Red, Cyan, Purple
- Multi-language support: 🇧🇷 Portuguese / 🇺🇸 English
- Draggable and resizable terminal windows
- Minimize tabs to dock
- Split-screen terminal support

### ⌨️ **Keyboard Shortcuts**
- `Ctrl+Shift+T` - New tab
- `Ctrl+W` - Close tab
- `Ctrl+F` - Search in terminal
- `Alt+1/2/3/4/5` - Switch workspace
- `F11` - Maximize tab
- Right-click on workspace - Workspace menu

### **Code Snippets**
- Built-in snippet manager
- Pre-configured security tool commands
- One-click copy to clipboard
- Add custom snippets

---

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Modern web browser (Chrome, Firefox, Edge)

### Quick Start

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/shell-matrix.git
cd shell-matrix
```

2. **Install dependencies**
```bash
pip install fastapi uvicorn websockets python-multipart
```

3. **Run the application**
```bash
python shell_matrix_clean.py
```

4. **Access the dashboard**
```
Open your browser and navigate to: http://localhost:8000
```

### Docker Installation (Optional)

```bash
docker build -t shell-matrix .
docker run -p 8000:8000 shell-matrix
```

---

## Usage

### Creating a New Terminal
1. Click `+ Nova Aba` (+ New Tab) button
2. Enter a name for your terminal
3. Select shell type (Bash, Zsh, Fish, Sh)
4. Click `Criar` (Create)

### Setting Up a Proxy
1. Right-click on any workspace tab
2. Select `Configurar Proxy` (Configure Proxy)
3. Enter proxy details (type, host, port, credentials)
4. Click `Salvar` (Save)
5. All terminals in that workspace will use the proxy

### Managing Workspaces
1. Click `+ WS` to create a new workspace
2. Right-click on workspace tab for options:
   - Rename workspace
   - Configure proxy
   - Delete workspace

### Using Snippets
1. Click `Snippets` button to open panel
2. Click on any snippet to copy to clipboard
3. Add custom snippets with `+ Novo Snippet`

### Saving Sessions
1. Click `Sessoes` (Sessions) button
2. Enter a session name
3. Click `Salvar` (Save)
4. Restore sessions anytime from saved list

---

## Themes

Choose from 4 beautiful color schemes:
- 🟢 **Green** - Classic Matrix theme (default)
- 🔴 **Red** - Dark red hacker theme
- 🔵 **Cyan** - Cool blue cyberpunk theme
- 🟣 **Purple** - Royal purple theme

Change themes in: `Config` → `Tema` → Select color

---

## Language Support

Switch between languages using the selector in the header:
- 🇧🇷 **Português** (Default)
- 🇺🇸 **English**

All interface elements, messages, and prompts are fully translated.

---

## Screenshots

### Main Dashboard
![Dashboard](screenshots/dashboard.png)
*Multi-workspace terminal environment with Matrix theme*

### Proxy Configuration
![Proxy](screenshots/proxy.png)
*Per-workspace proxy settings*

### Browser Tab
![Browser](screenshots/browser.png)
*Integrated web browser for reconnaissance*

---

## Configuration

### Default Settings
- **Port**: 8000
- **Host**: 0.0.0.0 (accessible on all network interfaces)
- **Storage Directory**: `/tmp/kali_dashboard`
- **Uploads Directory**: `/tmp/kali_dashboard/uploads`

### Customization
Edit the configuration in `shell_matrix_clean.py`:

```python
STORAGE_DIR = Path("/tmp/kali_dashboard")  # Change storage location
app = FastAPI()  # Add FastAPI middleware
uvicorn.run(app, host="0.0.0.0", port=8000)  # Change host/port
```

---

## Technical Details

### Architecture
- **Backend**: FastAPI (Python)
- **Frontend**: Vanilla JavaScript + HTML/CSS
- **Terminal Emulation**: xterm.js v5.3.0
- **PTY Management**: Python pty module
- **WebSocket**: Real-time bidirectional communication
- **Storage**: LocalStorage for sessions/preferences

### Browser Compatibility
- ✅ Chrome/Chromium 90+
- ✅ Firefox 88+
- ✅ Edge 90+
- ✅ Safari 14+

### Security Considerations
- Sessions are stored locally
- No authentication by default (add reverse proxy with auth if exposing publicly)
- PTY processes run with server user permissions
- Use HTTPS in production environments

---

## Contributing

Contributions are welcome! Here's how you can help:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guide for Python code
- Test all features before submitting PR
- Update documentation for new features
- Add comments for complex logic

---

## Changelog

### Version 1.0.0 (Current)
- ✨ Multi-workspace support
- ✨ Integrated browser tabs
- ✨ Text editor tabs
- ✨ Proxy configuration per workspace
- ✨ Session save/restore
- ✨ Code snippets manager
- ✨ Multi-language support (PT/EN)
- ✨ 4 color themes
- ✨ Keyboard shortcuts
- ✨ Terminal search functionality
- ✨ Split-screen terminal support

---

## Known Issues

- Some websites block iframe loading due to CORS policies (opens in new window as fallback)
- Terminal resize may require manual refresh in some cases
- Large terminal logs may impact performance

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Author

**Rondinelli Castilho - N0rd**

- GitHub: [@NORD-Function](https://github.com/NORD-Function)
- Linkedin: (https://www.linkedin.com/in/rondinellicastilho)

---

## 🙏 Acknowledgments

- [xterm.js](https://xtermjs.org/) - Terminal emulation library
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [Uvicorn](https://www.uvicorn.org/) - ASGI server
- Matrix film for the aesthetic inspiration

---

## Support

If you encounter any issues or have questions:
- 🐛 [Open an Issue](https://github.com/yourusername/shell-matrix/issues)
- 💬 [Discussions](https://github.com/yourusername/shell-matrix/discussions)

---

<div align="center">

**⭐ Star this repository if you find it useful! ⭐**

Made with ❤️ by N0rd

</div>
