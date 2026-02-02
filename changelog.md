# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-02-02

### Added
- Multi-workspace support with unlimited workspaces
- Terminal emulation using xterm.js
- Support for multiple shells (Bash, Zsh, Fish, Sh)
- Integrated web browser tabs
- Text editor tabs with auto-save
- Proxy configuration per workspace (HTTP, HTTPS, SOCKS5)
- Session management (save/restore complete workspace sessions)
- Code snippets manager with pre-configured security commands
- Multi-language support (Portuguese and English)
- 4 color themes (Green/Matrix, Red, Cyan, Purple)
- Keyboard shortcuts for productivity
- Terminal search functionality
- Split-screen terminal support
- Drag and drop terminal windows
- Terminal log export
- WebSocket-based real-time communication
- LocalStorage for session persistence
- Minimize tabs to dock
- Workspace renaming
- Terminal tab renaming
- Auto-save for editor (every 5 seconds)
- Auto-save for sessions (every 30 seconds)

### Technical Features
- FastAPI backend with async support
- PTY (pseudo-terminal) implementation
- WebSocket connections for terminal I/O
- xterm.js v5.3.0 integration
- Responsive web interface
- CORS-aware browser component
- File upload/download API

### Security
- PTY process isolation
- Configurable proxy authentication
- Secure WebSocket connections
- Local session storage

## [Unreleased]

### Planned Features
- SSH connection support
- SFTP file transfer
- Terminal recording/playback
- Collaborative sessions
- Plugin system
- Custom themes editor
- Terminal history search
- Command autocomplete
- File manager integration
- Network tools integration
- Docker container management
- Kubernetes integration
- Multi-user support with authentication
- End-to-end encryption for sessions
- Mobile responsive design improvements

---

[1.0.0]: https://github.com/yourusername/shell-matrix/releases/tag/v1.0.0
