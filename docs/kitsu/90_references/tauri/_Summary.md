# Tauri Reference Summary

## What this system does
Tauri is a framework for building cross-platform desktop applications using web technologies for the frontend and Rust for the backend.

## What parts are relevant to Kitsu
- **Desktop Shell**: Provides the native desktop window and system integration
- **IPC Communication**: Secure bridge between frontend (JavaScript/TypeScript) and Rust backend
- **System APIs**: File system access, system controls, and OS integration
- **Security Model**: Permission-based access to system resources
- **Cross-platform**: Windows, macOS, Linux support from single codebase

## What can be ignored
- Web-specific deployment targets
- Mobile app development features
- Database integration not used by Kitsu
- Custom plugin development not relevant to Kitsu's needs
- Advanced build system configurations

## Key Integration Points
- Rust backend for performance-critical operations
- Secure IPC for AI pipeline communication
- System permission management and safety
- Desktop overlay and window management
- File system access for configuration and data

## Relationship to Kitsu
Kitsu uses Tauri as the desktop application framework to:
- Provide native desktop integration
- Enable secure system-level operations
- Bridge web-based UI with native performance
- Implement permission-based security model
- Support cross-platform deployment
